"""
Generates three light-themed, proposal-ready summary figures from the
project's existing, already-validated result files (no new VQE runs --
this is a visualization pass over completed simulations, built for the
BlueQubit Quantum Flywheel application rather than the paper-style dark
figures in results_decoupling/figures/).

  1. error_reduction_summary.png -- energy error (log scale) vs. bond
     length, plain PUCCD vs. PUCCD+orbital-rotation, for HF/LiH/BH,
     against the chemical-accuracy threshold.
  2. multireference_mechanism.png -- the classical (non-VQE) HF-determinant
     weight diagnostic that explains *why* HF/BH fail and LiH doesn't.
  3. hardware_measurement_budget.png -- qubits / Pauli terms / commuting
     measurement groups per molecule, the real numbers behind the Month 1
     QPU shot-budget estimate in the proposal.

Run from the repository root: python3 make_proposal_figures.py
"""
import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore")

RESULTS_DIR = "results_decoupling"
OUT_DIR = os.path.join(RESULTS_DIR, "figures_proposal")
os.makedirs(OUT_DIR, exist_ok=True)

CHEM_ACC_HA = 0.0016

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.size": 10.5,
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#222222",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
})

MOLECULE_COLORS = {"HF": "#1f77b4", "LiH": "#2ca02c", "BH": "#d62728"}

# ==============================================================================
# FIGURE 1 -- before/after energy error vs. bond length
# ==============================================================================
def load_plain(mol):
    d = json.load(open(os.path.join(RESULTS_DIR, "analysis.json")))
    pts = d[mol]["points"]
    r = np.array([p["r"] for p in pts])
    err = np.abs(np.array([p["sim_energy"] - p["exact_energy"] for p in pts]))
    order = np.argsort(r)
    return r[order], err[order]


def load_rotation(mol):
    fname = os.path.join(RESULTS_DIR, f"analysis_{mol}_rotation.json")
    d = json.load(open(fname))
    pts = d[f"{mol}_rotation"]["points"]
    r = np.array([p["r"] for p in pts])
    err = np.abs(np.array([p["sim_energy"] - p["exact_energy"] for p in pts]))
    order = np.argsort(r)
    return r[order], err[order]


fig, axes = plt.subplots(1, 3, figsize=(13, 4.0), sharey=True)
for ax, mol in zip(axes, ["HF", "LiH", "BH"]):
    r_before, err_before = load_plain(mol)
    r_after, err_after = load_rotation(mol)
    color = MOLECULE_COLORS[mol]
    ax.semilogy(r_before, np.clip(err_before, 1e-7, None), "o--", color="#999999",
                markersize=4, linewidth=1.2, label="PUCCD (before)")
    ax.semilogy(r_after, np.clip(err_after, 1e-7, None), "o-", color=color,
                markersize=4, linewidth=1.6, label="PUCCD + rotation (after)")
    ax.axhline(CHEM_ACC_HA, color="#888888", linestyle=":", linewidth=1.2)
    ax.set_title(mol, fontsize=12, fontweight="bold", color=color)
    ax.set_xlabel("Bond length (Å)")
    ax.legend(fontsize=8, loc="upper left" if mol != "BH" else "lower left")
axes[0].set_ylabel("Energy error |E$_{sim}$ − E$_{exact}$| (Ha, log scale)")
axes[1].text(axes[1].get_xlim()[1], CHEM_ACC_HA, "  chemical accuracy (1.6 mHa)",
             fontsize=7.5, color="#888888", va="center")
fig.suptitle("Orbital-rotation fix: energy error across the full bond-length curve",
             fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "error_reduction_summary.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("Wrote error_reduction_summary.png")

# ==============================================================================
# FIGURE 2 -- multi-reference (classical, non-VQE) mechanism diagnostic
# ==============================================================================
mref = json.load(open(os.path.join(RESULTS_DIR, "multireference_character.json")))

# NOTE: LiH's prescan diagnostic grid has one isolated outlier at r=4.7714
# (hf_weight drops to 0.046 then immediately recovers to the smooth trend at
# the very next point). This was checked, not assumed: NumPyEigensolver(k=3)
# at that geometry finds the ground/first-excited gap is only ~3e-4 Ha (a
# genuine near-degeneracy from LiH's well-known large-r ionic/covalent
# character mixing), which makes the exact diagonalizer's eigenvector
# selection numerically unstable at that single point -- not a new sharp
# transition. That geometry was never part of the 20-point VQE-tested grid
# (confirmed against results_decoupling/analysis.json), so it has no effect
# on any reported VQE/error-reduction result; it is excluded here only so
# this diagnostic figure doesn't visually overstate a single-point artifact.
LIH_DIAGNOSTIC_ARTIFACT_R = 4.7714

fig, ax = plt.subplots(figsize=(7.5, 4.3))
for mol in ["LiH", "HF", "BH"]:
    r = np.array(mref[mol]["r"])
    w = np.array(mref[mol]["hf_weight"])
    if mol == "LiH":
        keep = np.abs(r - LIH_DIAGNOSTIC_ARTIFACT_R) > 1e-3
        r, w = r[keep], w[keep]
    order = np.argsort(r)
    ax.plot(r[order], w[order], "-o", color=MOLECULE_COLORS[mol], markersize=4,
            linewidth=1.8, label=mol)
ax.set_xlabel("Bond length (Å)")
ax.set_ylabel("Hartree-Fock determinant weight\nin the exact (FCI) wavefunction")
ax.set_title("Classical, non-VQE diagnostic: LiH decays smoothly;\nHF and BH collapse at a genuine curve crossing",
              fontsize=12, fontweight="bold")
ax.legend(fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "multireference_mechanism.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("Wrote multireference_mechanism.png")

# ==============================================================================
# FIGURE 3 -- hardware measurement budget (Hamiltonian stats, computed live)
# ==============================================================================
# Re-derives the measurement cost directly from each molecule's
# Jordan-Wigner-mapped Hamiltonian via PySCF + qiskit-nature, run fresh
# every time this script executes (not a cached/hardcoded number).
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.transformers import FreezeCoreTransformer
from qiskit_nature.second_q.mappers import JordanWignerMapper

HAM_MOLECULES = {
    "H2":   {"geometry_fn": lambda r: f"H 0 0 0; H 0 0 {r}",             "basis": "sto3g", "freeze_core": False, "r": 0.74},
    "LiH":  {"geometry_fn": lambda r: f"Li 0 0 0; H 0 0 {r}",            "basis": "sto3g", "freeze_core": True,  "r": 1.6},
    "BeH2": {"geometry_fn": lambda r: f"Be 0 0 0; H 0 0 {-r}; H 0 0 {r}", "basis": "sto3g", "freeze_core": True,  "r": 1.3},
    "HF":   {"geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}",             "basis": "sto3g", "freeze_core": True,  "r": 0.92},
    "BH":   {"geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}",             "basis": "sto3g", "freeze_core": True,  "r": 1.23},
}

HAM_STATS = {}
for name, cfg in HAM_MOLECULES.items():
    driver = PySCFDriver(atom=cfg["geometry_fn"](cfg["r"]), basis=cfg["basis"], charge=0, spin=0)
    problem = driver.run()
    if cfg["freeze_core"]:
        problem = FreezeCoreTransformer(freeze_core=True).transform(problem)
    h_op = JordanWignerMapper().map(problem.hamiltonian.second_q_op())
    HAM_STATS[name] = {
        "qubits": h_op.num_qubits,
        "pauli_terms": len(h_op),
        "groups": len(h_op.group_commuting(qubit_wise=True)),
    }
    print(f"  {name}: {HAM_STATS[name]}")

mols = list(HAM_STATS.keys())
groups = [HAM_STATS[m]["groups"] for m in mols]
terms = [HAM_STATS[m]["pauli_terms"] for m in mols]
colors = [MOLECULE_COLORS.get(m, "#7f7f7f") for m in mols]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax1.bar(mols, terms, color=colors, alpha=0.85)
ax1.set_ylabel("Pauli terms in mapped Hamiltonian")
ax1.set_title("Hamiltonian size", fontsize=11, fontweight="bold")
for i, v in enumerate(terms):
    ax1.text(i, v + 5, str(v), ha="center", fontsize=9)

ax2.bar(mols, groups, color=colors, alpha=0.85)
ax2.set_ylabel("Qubit-wise commuting measurement groups")
ax2.set_title("Hardware circuits needed per geometry", fontsize=11, fontweight="bold")
for i, v in enumerate(groups):
    ax2.text(i, v + 1, str(v), ha="center", fontsize=9)

fig.suptitle("Month 1 QPU budget is computed, not guessed: measurement cost per geometry",
             fontsize=12.5, fontweight="bold", y=1.03)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "hardware_measurement_budget.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("Wrote hardware_measurement_budget.png")

print(f"\nAll figures written to {OUT_DIR}/")
