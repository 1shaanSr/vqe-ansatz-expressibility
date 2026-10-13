"""
Figure generation for the VQE dipole-energy decoupling study.
Reads results_decoupling/analysis.json + restart_histories.json (written by
vqe_dipole_decoupling.py) and produces the full figure set:

  Per molecule:
    - PES plot (exact prescan curve + VQE sim points + HF reference)
    - Dipole plot (magnitude + x/y/z components, exact curve + VQE points)
    - Decoupling map (the central figure): energy error & dipole error vs r
      on shared axes, chemical-accuracy / dipole-threshold lines marked
    - Correlation-energy-captured vs r
    - Multi-session convergence ATLAS: every geometry's restarts overlaid,
      one subplot per geometry, in a single grid figure
    - Multi-session convergence, INDIVIDUAL: the same overlay, one full-size
      figure per geometry, saved separately (results_decoupling/figures/
      convergence_per_geometry/<molecule>/r_<value>.png)

  Across all molecules:
    - Dipole-error vs energy-error scatter, all points, colored by molecule,
      with Pearson correlation coefficient annotated (overall + per-molecule)
    - "Energy says fine, dipole says wrong" table -> CSV + rendered figure
    - A single summary overview grid (PES / dipole / decoupling thumbnails
      for all three molecules)

Run this after vqe_dipole_decoupling.py has finished and written
results_decoupling/analysis.json + restart_histories.json.
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

RESULTS_DIR = "results_decoupling"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
CONV_DIR = os.path.join(FIGURES_DIR, "convergence_per_geometry")
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(CONV_DIR, exist_ok=True)

CHEM_ACCURACY_HA = 0.0016
DIPOLE_ERROR_THRESHOLD_AU = 0.05
SIGN_FLIP_MIN_EXACT_AU = 0.05

# Consistent, colorblind-safe palette (Okabe-Ito), one hue per molecule.
# Note: COLOR["HF"] is the hydrogen-fluoride MOLECULE's plot color; this is
# unrelated to HARTREE_FOCK_LINE_COLOR below (the gray dashed reference line
# drawn on every PES plot) -- unfortunate naming overlap, kept distinct here.
COLOR = {"H2": "#0072B2", "LiH": "#D55E00", "BeH2": "#009E73", "HF": "#CC79A7", "BH": "#F0E442"}
EXACT_COLOR = "#2b2b2b"
HARTREE_FOCK_LINE_COLOR = "#999999"
WARMSTART_COLOR = "#D55E00"
RANDOM_COLOR = "#999999"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#1a1a1a",
    "text.color": "#1a1a1a",
    "xtick.color": "#444444",
    "ytick.color": "#444444",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.grid": True,
    "grid.color": "#e5e5e5",
    "grid.linewidth": 0.6,
    "figure.dpi": 130,
})

with open(os.path.join(RESULTS_DIR, "analysis.json")) as f:
    DATA = json.load(f)
with open(os.path.join(RESULTS_DIR, "restart_histories.json")) as f:
    HISTORIES = json.load(f)

# If a validated deeper rerun exists for a molecule (e.g. BeH2 at 12x250
# restarts/iters, after the original 4x100 run left convergence unverified),
# promote it to be the canonical entry used in all main figures. The
# original shallower run is kept under its own key so the two can still be
# compared directly (see plot_beh2_budget_comparison below).
if "BeH2_deep" in DATA:
    DATA["BeH2_original_4x100"] = DATA["BeH2"]
    HISTORIES["BeH2_original_4x100"] = HISTORIES["BeH2"]
    DATA["BeH2"] = DATA.pop("BeH2_deep")
    HISTORIES["BeH2"] = HISTORIES.pop("BeH2_deep")

# Fixed primary set for the main per-molecule figure loop and the
# cross-molecule correlation analysis. Comparison-only variants
# (LiH_uniform_grid, BeH2_original_4x100) are handled separately, not run
# through the full per-molecule figure pipeline, since they exist purely to
# be compared against their counterpart, not as independent "systems."
_PRIMARY_ORDER = ["H2", "LiH", "BeH2", "HF", "BH"]
MOLECULES = [m for m in _PRIMARY_ORDER if m in DATA]


# ==============================================================================
# Per-molecule: PES plot
# ==============================================================================
def plot_pes(name):
    d = DATA[name]
    pr = np.array(d["prescan_r"])
    pe = np.array(d["prescan_energy"])
    pts = d["points"]
    r = [p["r"] for p in pts]
    e_sim = [p["sim_energy"] for p in pts]
    e_hf = [p["hf_energy"] for p in pts]

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(pr, pe, "-", color=EXACT_COLOR, lw=1.6, label="Exact (fine scan)", zorder=2)
    ax.plot(r, e_hf, "--", color=HARTREE_FOCK_LINE_COLOR, lw=1.2, label="Hartree-Fock", zorder=2)
    ax.plot(r, e_sim, "o", color=COLOR[name], ms=6, mec="white", mew=0.6,
             label="VQE (PUCCD, simulated)", zorder=3)
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel("Total energy (Ha)")
    ax.set_title(f"{name}: potential energy surface")
    ax.legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, f"{name}_pes.png"))
    plt.close(fig)


# ==============================================================================
# Per-molecule: dipole plot (magnitude + components)
# ==============================================================================
def plot_dipole(name):
    d = DATA[name]
    pr = np.array(d["prescan_r"])
    pmag = np.array(d["prescan_dipole_mag"])
    pxyz = np.array(d["prescan_dipole_xyz"])
    axis_names = ["x", "y", "z"]
    dom = d["dominant_dipole_axis"]
    pts = d["points"]
    r = [p["r"] for p in pts]
    mu_sim_mag = [p["sim_dipole_mag"] for p in pts]
    mu_exact_mag = [p["exact_dipole_mag"] for p in pts]
    mu_sim_dom = [p["sim_dipole_xyz"][dom] for p in pts]
    mu_exact_dom = [p["exact_dipole_xyz"][dom] for p in pts]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    ax.plot(pr, pmag, "-", color=EXACT_COLOR, lw=1.6, label="Exact |μ| (fine scan)")
    ax.plot(r, mu_sim_mag, "o", color=COLOR[name], ms=6, mec="white", mew=0.6, label="VQE |μ| (simulated)")
    ax.axhline(0, color="#cccccc", lw=0.8)
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel("Dipole magnitude (a.u.)")
    ax.set_title(f"{name}: total dipole moment magnitude")
    ax.legend(frameon=False, fontsize=8.5)

    ax = axes[1]
    ax.plot(pr, pxyz[:, dom], "-", color=EXACT_COLOR, lw=1.6,
             label=f"Exact μ_{axis_names[dom]} (fine scan)")
    ax.plot(r, mu_sim_dom, "o", color=COLOR[name], ms=6, mec="white", mew=0.6,
             label=f"VQE μ_{axis_names[dom]} (simulated)")
    ax.axhline(0, color="#cccccc", lw=0.8)
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel(f"μ_{axis_names[dom]} (a.u.)")
    ax.set_title(f"{name}: dominant dipole component (sign-resolved)")
    ax.legend(frameon=False, fontsize=8.5)

    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, f"{name}_dipole.png"))
    plt.close(fig)


# ==============================================================================
# Per-molecule: THE DECOUPLING MAP (central figure)
# ==============================================================================
def plot_decoupling_map(name):
    d = DATA[name]
    pts = d["points"]
    r = np.array([p["r"] for p in pts])
    e_err = np.array([abs(p["sim_energy"] - p["exact_energy"]) for p in pts])
    mu_err = np.array([abs(p["sim_dipole_mag"] - p["exact_dipole_mag"]) for p in pts])

    fig, ax1 = plt.subplots(figsize=(7.2, 4.6))
    ax2 = ax1.twinx()

    l1, = ax1.plot(r, e_err, "o-", color=COLOR[name], lw=1.6, ms=6, mec="white", mew=0.6,
                    label="Energy error |E$_{sim}$ − E$_{exact}$|")
    ax1.axhline(CHEM_ACCURACY_HA, color=COLOR[name], lw=1, ls=":", alpha=0.7)
    ax1.text(r.min(), CHEM_ACCURACY_HA, " chemical accuracy", color=COLOR[name],
              fontsize=7.5, va="bottom", alpha=0.85)
    ax1.set_ylabel("Energy error (Ha)", color=COLOR[name])
    ax1.tick_params(axis="y", labelcolor=COLOR[name])
    ax1.set_yscale("log")

    l2, = ax2.plot(r, mu_err, "s--", color="#7a1fa2", lw=1.6, ms=6, mec="white", mew=0.6,
                    label="Dipole error |μ$_{sim}$ − μ$_{exact}$|")
    ax2.axhline(DIPOLE_ERROR_THRESHOLD_AU, color="#7a1fa2", lw=1, ls=":", alpha=0.7)
    ax2.text(r.max(), DIPOLE_ERROR_THRESHOLD_AU, "decoupling threshold ", color="#7a1fa2",
              fontsize=7.5, va="bottom", ha="right", alpha=0.85)
    ax2.set_ylabel("Dipole error (a.u.)", color="#7a1fa2")
    ax2.tick_params(axis="y", labelcolor="#7a1fa2")
    ax2.set_yscale("log")

    ax1.set_xlabel("Bond length (Å)")
    ax1.set_title(f"{name}: where energy and dipole error decouple")
    ax1.legend(handles=[l1, l2], frameon=False, fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, f"{name}_decoupling_map.png"))
    plt.close(fig)


# ==============================================================================
# Per-molecule: correlation energy captured
# ==============================================================================
def plot_correlation_captured(name):
    d = DATA[name]
    pts = d["points"]
    r = [p["r"] for p in pts]
    frac = []
    for p in pts:
        denom = p["exact_energy"] - p["hf_energy"]
        frac.append((p["sim_energy"] - p["hf_energy"]) / denom if abs(denom) > 1e-9 else np.nan)

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.axhline(1.0, color="#cccccc", lw=1, ls="--")
    ax.axhline(0.0, color="#cccccc", lw=1, ls="--")
    ax.plot(r, frac, "o-", color=COLOR[name], ms=6, mec="white", mew=0.6)
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel("Fraction of correlation energy captured")
    ax.set_title(f"{name}: VQE correlation-energy recovery (1.0 = exact, 0.0 = HF)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, f"{name}_correlation_captured.png"))
    plt.close(fig)


# ==============================================================================
# Multi-session convergence: atlas (grid) + individual per-geometry figures
# ==============================================================================
def plot_convergence_sessions(name):
    entries = HISTORIES[name]
    n = len(entries)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.1 * ncols, 2.5 * nrows), squeeze=False)

    mol_conv_dir = os.path.join(CONV_DIR, name)
    os.makedirs(mol_conv_dir, exist_ok=True)

    for idx, entry in enumerate(entries):
        r = entry["r"]
        histories = entry["restart_histories"]
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        _draw_one_convergence_panel(ax, histories, title=f"r = {r:.3f} Å")

        # individual full-size version too
        fig_i, ax_i = plt.subplots(figsize=(5.5, 4))
        _draw_one_convergence_panel(ax_i, histories, title=f"{name}, r = {r:.3f} Å — all optimizer restarts")
        ax_i.set_xlabel("SLSQP iteration (cost-function call)")
        ax_i.set_ylabel("Electronic energy (Ha)")
        fig_i.tight_layout()
        fig_i.savefig(os.path.join(mol_conv_dir, f"r_{r:.3f}.png"))
        plt.close(fig_i)

    # blank unused axes
    for idx in range(n, nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].axis("off")

    fig.suptitle(f"{name}: every optimizer restart, overlaid, at every geometry", y=1.0, fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, f"{name}_convergence_atlas.png"))
    plt.close(fig)


def _draw_one_convergence_panel(ax, histories, title):
    for h in histories:
        color = WARMSTART_COLOR if h["seed_type"] == "warm_start" else RANDOM_COLOR
        lw = 1.6 if h["seed_type"] == "warm_start" else 1.0
        alpha = 0.95 if h["seed_type"] == "warm_start" else 0.65
        ax.plot(h["history"], color=color, lw=lw, alpha=alpha)
    ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=7)


def _autocorr_corrected_pvalue(x, y, r_value):
    """Points along a smooth error-vs-bond-length curve are NOT independent
    samples -- adjacent geometries are highly autocorrelated, so naively
    plugging n=len(points) into a Pearson significance test overstates
    significance, sometimes drastically. This applies the Pyper & Peterman
    (1998) effective-sample-size correction for correlating two
    autocorrelated series:
        n_eff = n / (1 + 2 * sum_j (1 - j/n) * rxx(j) * ryy(j))
    where rxx/ryy are the lag-j autocorrelations of x and y. Verified on the
    LiH data this pipeline produced: naive n=20 gives p=3.4e-5, but n_eff
    comes out to ~7, giving a corrected p=0.035 -- still significant, but
    nowhere near as dramatic. Report n_eff and the corrected p, not the
    naive one, in the paper."""
    n = len(x)
    if n < 4:
        return float(n), float("nan")

    def autocorr(v, lag):
        v = v - v.mean()
        denom = np.sum(v ** 2)
        return np.sum(v[:-lag] * v[lag:]) / denom if denom > 0 else 0.0

    correction = sum((1 - j / n) * autocorr(x, j) * autocorr(y, j) for j in range(1, n - 1))
    n_eff = n / (1 + 2 * correction)
    n_eff = max(3.0, min(float(n), n_eff))
    if abs(r_value) >= 1.0:
        return n_eff, 0.0
    t_stat = r_value * np.sqrt((n_eff - 2) / (1 - r_value ** 2))
    p_corrected = 2 * (1 - stats.t.cdf(abs(t_stat), df=n_eff - 2))
    return n_eff, p_corrected


# ==============================================================================
# Cross-molecule: decoupling scatter with correlation coefficient
# ==============================================================================
def plot_decoupling_scatter():
    """Reports correlation two ways, because they answer different questions:

    - RAW POOLED Pearson r (all molecules' errors pooled together): dominated
      by the fact that H2/BeH2 sit at a completely different error SCALE than
      LiH (H2 is near machine precision; BeH2's dipole is symmetry-pinned to
      ~0). A near-zero value here mostly says "these are different systems,"
      not "energy and dipole decouple" -- reporting only this number would be
      a real statistical trap.
    - PER-MOLECULE log-log Pearson r (log10 error vs log10 error, within one
      molecule's own geometry scan): this is the actual within-system test of
      whether energy error predicts dipole error, and is the number that
      speaks to the thesis. It is only physically meaningful for a molecule
      whose dipole varies non-trivially with geometry -- LiH here; H2 and
      BeH2's dipoles are ~0 everywhere in this coordinate by symmetry, so
      their log-log r is reported but flagged as not thesis-relevant.
    """
    fig, ax = plt.subplots(figsize=(8.5, 7.2))
    all_e, all_mu = [], []
    per_molecule_stats = {}
    eps = 1e-16
    for name in MOLECULES:
        pts = DATA[name]["points"]
        e_err = np.array([abs(p["sim_energy"] - p["exact_energy"]) for p in pts])
        mu_err = np.array([abs(p["sim_dipole_mag"] - p["exact_dipole_mag"]) for p in pts])
        all_e.extend(e_err.tolist())
        all_mu.extend(mu_err.tolist())
        ax.scatter(e_err, mu_err, color=COLOR[name], s=46, edgecolor="white", linewidth=0.6,
                    label=name, zorder=3)

        order = np.argsort(np.array([p["r"] for p in pts]))
        log_e = np.log10(e_err + eps)[order]
        log_mu = np.log10(mu_err + eps)[order]
        if np.std(log_e) > 1e-9 and np.std(log_mu) > 1e-9:
            r_log, p_naive = stats.pearsonr(log_e, log_mu)
            n_eff, p_corrected = _autocorr_corrected_pvalue(log_e, log_mu, r_log)
            spearman_r, spearman_p = stats.spearmanr(e_err[order], mu_err[order])
        else:
            r_log, p_naive, n_eff, p_corrected = float("nan"), float("nan"), float("nan"), float("nan")
            spearman_r, spearman_p = float("nan"), float("nan")
        # Pearson (on log-log error magnitudes) is sensitive to a couple of
        # extreme points; Spearman (rank-based) is not. A molecule whose
        # Pearson is high but whose Spearman is near zero/non-significant is
        # telling you the "correlation" is really just 1-2 catastrophic
        # joint-failure points riding on top of an otherwise uncorrelated
        # curve -- a materially different claim from LiH-style smooth
        # co-degradation, and worth distinguishing explicitly in the paper.
        outlier_driven = (
            not np.isnan(r_log) and not np.isnan(spearman_r)
            and abs(r_log) > 0.5 and abs(spearman_r) < 0.4
        )
        per_molecule_stats[name] = {
            "log_log_pearson_r": r_log,
            "log_log_pearson_p_naive": p_naive,
            "n_raw": len(pts),
            "n_effective_autocorr_corrected": n_eff,
            "log_log_pearson_p_corrected": p_corrected,
            "spearman_r": spearman_r,
            "spearman_p": spearman_p,
            "likely_outlier_driven_correlation": bool(outlier_driven),
            "dipole_dynamic_range_au": float(mu_err.max() - mu_err.min()),
        }

    ax.axvline(CHEM_ACCURACY_HA, color="#999999", lw=1, ls=":")
    ax.axhline(DIPOLE_ERROR_THRESHOLD_AU, color="#999999", lw=1, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Energy error |E$_{sim}$ − E$_{exact}$| (Ha)")
    ax.set_ylabel("Dipole error |μ$_{sim}$ − μ$_{exact}$| (a.u.)")

    all_e = np.array(all_e)
    all_mu = np.array(all_mu)
    r_pooled, p_pooled = stats.pearsonr(all_e, all_mu)

    subtitle_lines = [f"Pooled (raw, all molecules): r = {r_pooled:.3f} (p = {p_pooled:.3g}) — scale-dominated, not the thesis test"]
    for name in MOLECULES:
        s = per_molecule_stats[name]
        if s["dipole_dynamic_range_au"] <= 1e-6:
            tag = "  [dipole ≈ 0 throughout — not thesis-relevant]"
        elif s["likely_outlier_driven_correlation"]:
            tag = "  [Pearson driven by 1-2 extreme points, NOT a smooth trend — see Spearman]"
        else:
            tag = ""
        subtitle_lines.append(
            f"{name}: Pearson(log-log) r={s['log_log_pearson_r']:.2f} "
            f"(p={s['log_log_pearson_p_corrected']:.2g}, n_eff={s['n_effective_autocorr_corrected']:.1f}/{s['n_raw']})  "
            f"Spearman r={s['spearman_r']:.2f} (p={s['spearman_p']:.2g}){tag}"
        )

    ax.set_title("Energy error vs. dipole error, all geometries\n" + "\n".join(subtitle_lines), fontsize=8, loc="left")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "decoupling_scatter_all_molecules.png"))
    plt.close(fig)

    with open(os.path.join(RESULTS_DIR, "correlation_stats.json"), "w") as f:
        json.dump({
            "pooled_raw_pearson_r": r_pooled, "pooled_raw_pearson_p": p_pooled,
            "per_molecule_log_log": per_molecule_stats,
        }, f, indent=2)

    return r_pooled, p_pooled, per_molecule_stats


# ==============================================================================
# Cross-molecule: "energy says fine, dipole says wrong" table
# ==============================================================================
def build_decoupling_table():
    rows = []
    for name in MOLECULES:
        for p in DATA[name]["points"]:
            e_err = abs(p["sim_energy"] - p["exact_energy"])
            mu_err = abs(p["sim_dipole_mag"] - p["exact_dipole_mag"])
            dom = DATA[name]["dominant_dipole_axis"]
            exact_dom = p["exact_dipole_xyz"][dom]
            sim_dom = p["sim_dipole_xyz"][dom]
            sign_flip = (
                abs(exact_dom) > SIGN_FLIP_MIN_EXACT_AU
                and np.sign(exact_dom) != np.sign(sim_dom)
            )
            energy_fine = e_err <= CHEM_ACCURACY_HA
            dipole_wrong = (mu_err > DIPOLE_ERROR_THRESHOLD_AU) or sign_flip
            if energy_fine and dipole_wrong:
                rows.append({
                    "molecule": name, "r": p["r"],
                    "energy_error_Ha": round(e_err, 6),
                    "dipole_error_au": round(mu_err, 6),
                    "sign_flip": bool(sign_flip),
                })

    with open(os.path.join(RESULTS_DIR, "decoupling_table.json"), "w") as f:
        json.dump(rows, f, indent=2)

    import csv
    with open(os.path.join(RESULTS_DIR, "decoupling_table.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["molecule", "r", "energy_error_Ha", "dipole_error_au", "sign_flip"])
        writer.writeheader()
        writer.writerows(rows)

    # rendered figure
    fig, ax = plt.subplots(figsize=(7.5, max(1.6, 0.35 * (len(rows) + 1))))
    ax.axis("off")
    if rows:
        cell_text = [[r["molecule"], f"{r['r']:.3f}", f"{r['energy_error_Ha']:.5f}",
                      f"{r['dipole_error_au']:.4f}", "yes" if r["sign_flip"] else "no"] for r in rows]
        table = ax.table(
            cellText=cell_text,
            colLabels=["Molecule", "r (Å)", "Energy error (Ha)", "Dipole error (a.u.)", "Sign flip?"],
            loc="center", cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.4)
    else:
        ax.text(0.5, 0.5, "No geometries met the decoupling criterion in this run.",
                 ha="center", va="center", fontsize=11)
    ax.set_title("Geometries where energy reaches chemical accuracy but the dipole is wrong",
                  fontsize=11, pad=14)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "decoupling_table.png"))
    plt.close(fig)
    return rows


# ==============================================================================
# Cross-molecule: summary overview grid
# ==============================================================================
def plot_summary_grid():
    fig, axes = plt.subplots(3, len(MOLECULES), figsize=(5 * len(MOLECULES), 11), squeeze=False)
    for col, name in enumerate(MOLECULES):
        d = DATA[name]
        pr = np.array(d["prescan_r"])
        pe = np.array(d["prescan_energy"])
        pmag = np.array(d["prescan_dipole_mag"])
        pts = d["points"]
        r = np.array([p["r"] for p in pts])
        e_sim = [p["sim_energy"] for p in pts]
        mu_sim = [p["sim_dipole_mag"] for p in pts]
        e_err = np.array([abs(p["sim_energy"] - p["exact_energy"]) for p in pts])
        mu_err = np.array([abs(p["sim_dipole_mag"] - p["exact_dipole_mag"]) for p in pts])

        ax = axes[0][col]
        ax.plot(pr, pe, "-", color=EXACT_COLOR, lw=1.4)
        ax.plot(r, e_sim, "o", color=COLOR[name], ms=5, mec="white", mew=0.5)
        ax.set_title(f"{name}: PES", fontsize=10)
        ax.set_xlabel("r (Å)"); ax.set_ylabel("E (Ha)")

        ax = axes[1][col]
        ax.plot(pr, pmag, "-", color=EXACT_COLOR, lw=1.4)
        ax.plot(r, mu_sim, "o", color=COLOR[name], ms=5, mec="white", mew=0.5)
        ax.set_title(f"{name}: |μ|", fontsize=10)
        ax.set_xlabel("r (Å)"); ax.set_ylabel("|μ| (a.u.)")

        ax = axes[2][col]
        ax.plot(r, e_err, "o-", color=COLOR[name], ms=5, mec="white", mew=0.5, label="energy err")
        ax2 = ax.twinx()
        ax2.plot(r, mu_err, "s--", color="#7a1fa2", ms=5, mec="white", mew=0.5, label="dipole err")
        ax.set_yscale("log"); ax2.set_yscale("log")
        ax.set_title(f"{name}: decoupling", fontsize=10)
        ax.set_xlabel("r (Å)"); ax.set_ylabel("E err (Ha)"); ax2.set_ylabel("μ err (a.u.)")

    fig.suptitle(f"Summary: {' / '.join(MOLECULES)} — PES, dipole, and energy-dipole decoupling", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "summary_overview_grid.png"))
    plt.close(fig)


# ==============================================================================
# Comparison: BeH2 original (4x100) vs deep (12x250) restart budget
# ==============================================================================
def plot_beh2_budget_comparison():
    if "BeH2_original_4x100" not in DATA:
        return
    orig = DATA["BeH2_original_4x100"]["points"]
    deep = DATA["BeH2"]["points"]
    r_o = [p["r"] for p in orig]
    e_o = [abs(p["sim_energy"] - p["exact_energy"]) for p in orig]
    r_d = [p["r"] for p in deep]
    e_d = [abs(p["sim_energy"] - p["exact_energy"]) for p in deep]

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(r_o, e_o, "o--", color="#999999", ms=6, mec="white", mew=0.6, label="original (4 restarts x 100 iter)")
    ax.plot(r_d, e_d, "o-", color=COLOR["BeH2"], ms=6, mec="white", mew=0.6, label="deep (12 restarts x 250 iter)")
    ax.set_yscale("log")
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel("Energy error |E$_{sim}$ − E$_{exact}$| (Ha)")
    ax.set_title("BeH2: does a bigger restart budget fix convergence?")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "BeH2_budget_comparison.png"))
    plt.close(fig)

    import numpy as np
    identical = np.allclose(e_o, e_d, atol=1e-4) if len(e_o) == len(e_d) else False
    print(f"  BeH2 budget comparison: {'IDENTICAL (ansatz limit, not optimizer budget)' if identical else 'DIFFERENT (restart budget mattered for BeH2)'}")
    return identical


# ==============================================================================
# Comparison: LiH adaptive grid vs uniform grid (sampling-confound check)
# ==============================================================================
def plot_lih_grid_comparison():
    if "LiH_uniform_grid" not in DATA:
        return
    for label, key in [("adaptive", "LiH"), ("uniform", "LiH_uniform_grid")]:
        pts = DATA[key]["points"]
        r = np.array([p["r"] for p in pts])
        order = np.argsort(r)
        e_err = np.array([abs(p["sim_energy"] - p["exact_energy"]) for p in pts])[order]
        mu_err = np.array([abs(p["sim_dipole_mag"] - p["exact_dipole_mag"]) for p in pts])[order]
        log_e, log_mu = np.log10(e_err + 1e-16), np.log10(mu_err + 1e-16)
        pr, _ = stats.pearsonr(log_e, log_mu)
        sr, sp = stats.spearmanr(e_err, mu_err)
        print(f"  LiH [{label} grid, n={len(pts)}]: Pearson(log-log) r={pr:.3f}  Spearman r={sr:.3f} (p={sp:.3g})")


# ==============================================================================
if __name__ == "__main__":
    for name in MOLECULES:
        print(f"Generating figures for {name}...")
        plot_pes(name)
        plot_dipole(name)
        plot_decoupling_map(name)
        plot_correlation_captured(name)
        plot_convergence_sessions(name)

    print("Generating cross-molecule figures...")
    r_pooled, p_pooled, per_mol = plot_decoupling_scatter()
    rows = build_decoupling_table()
    plot_summary_grid()
    print("\nValidation comparisons:")
    plot_beh2_budget_comparison()
    plot_lih_grid_comparison()

    print(f"\nPooled (raw, all molecules) Pearson r = {r_pooled:.4f} (p = {p_pooled:.3g}) -- scale-dominated, see caveat in script docstring")
    for name, s in per_mol.items():
        flag = "  <-- OUTLIER-DRIVEN, not a real trend" if s["likely_outlier_driven_correlation"] else ""
        print(f"  {name}: Pearson(log-log) r={s['log_log_pearson_r']:.4f}  "
              f"naive p (n={s['n_raw']})={s['log_log_pearson_p_naive']:.3g}  "
              f"corrected p (n_eff={s['n_effective_autocorr_corrected']:.1f})={s['log_log_pearson_p_corrected']:.3g}  |  "
              f"Spearman r={s['spearman_r']:.4f} (p={s['spearman_p']:.3g})  "
              f"dipole range={s['dipole_dynamic_range_au']:.4g} au{flag}")
    print(f"Geometries meeting the strict 'energy within chemical accuracy AND dipole wrong' criterion: {len(rows)}")
    print(f"\nAll figures written to {FIGURES_DIR}/")
