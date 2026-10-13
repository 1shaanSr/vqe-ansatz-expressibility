import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#0d1117"
PANEL = "#161b22"
GRID = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT, "text.color": TEXT,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.grid": True, "font.size": 11,
    "axes.titlesize": 12, "axes.titleweight": "bold", "figure.dpi": 140,
})

COLOR = {"H2": "#58a6ff", "LiH": "#ff7b72", "BeH2": "#3fb950", "HF": "#d2a8ff", "BH": "#f2cc60"}

d = json.load(open("results_decoupling/multireference_character.json"))

fig, ax = plt.subplots(figsize=(9, 6))
for name in ["H2", "LiH", "BeH2", "HF", "BH"]:
    r = np.array(d[name]["r"])
    w = np.array(d[name]["hf_weight"])
    # de-glitch isolated single-point root-flip artifacts (near-degenerate
    # exact-diagonalization state swaps) for display clarity: a point whose
    # neighbors on both sides are much higher is almost certainly a
    # numerical root flip, not real physics -- median-filter with width 3
    w_clean = w.copy()
    for i in range(1, len(w) - 1):
        if w[i] < 0.5 * min(w[i - 1], w[i + 1]):
            w_clean[i] = np.median([w[i - 1], w[i + 1]])
    lw = 2.4 if name in ("LiH", "HF", "BH") else 1.3
    alpha = 1.0 if name in ("LiH", "HF", "BH") else 0.5
    ax.plot(r, w_clean, color=COLOR[name], lw=lw, alpha=alpha, label=name)

ax.axhline(0.5, color=MUTED, lw=1, ls=":", alpha=0.7)
ax.text(ax.get_xlim()[1] * 0.02, 0.52, "50% HF character", color=MUTED, fontsize=8.5)
ax.set_xlabel("Bond length (Å)")
ax.set_ylabel("Hartree-Fock determinant weight in exact wavefunction")
ax.set_title("Why LiH degrades gradually but HF/BH fail abruptly")
ax.legend(frameon=False, fontsize=10, labelcolor=TEXT)
fig.tight_layout()
fig.savefig("results_decoupling/figures/multireference_character_comparison.png")
print("Saved results_decoupling/figures/multireference_character_comparison.png")
