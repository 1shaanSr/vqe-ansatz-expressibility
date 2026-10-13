import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#0d1117"; PANEL = "#161b22"; GRID = "#30363d"; TEXT = "#e6edf3"; MUTED = "#8b949e"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT, "text.color": TEXT,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.grid": True, "font.size": 10.5,
    "axes.titlesize": 12, "axes.titleweight": "bold", "figure.dpi": 140,
})

main = json.load(open("results_decoupling/analysis.json"))
rot = {}
for mol in ["HF", "BH", "LiH"]:
    rot[mol] = json.load(open(f"results_decoupling/analysis_{mol}_rotation.json"))[f"{mol}_rotation"]["points"]

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
for ax, mol in zip(axes, ["HF", "LiH", "BH"]):
    plain_pts = main[mol]["points"]
    r_plain = [p["r"] for p in plain_pts]
    e_plain = [abs(p["sim_energy"] - p["exact_energy"]) for p in plain_pts]
    r_rot = [p["r"] for p in rot[mol]]
    e_rot = [abs(p["sim_energy"] - p["exact_energy"]) for p in rot[mol]]

    order_p = np.argsort(r_plain); order_r = np.argsort(r_rot)
    ax.plot(np.array(r_plain)[order_p], np.array(e_plain)[order_p], "o-", color="#f85149",
            ms=5, mec="white", mew=0.4, label="PUCCD only", lw=1.5)
    ax.plot(np.array(r_rot)[order_r], np.array(e_rot)[order_r], "o-", color="#3fb950",
            ms=5, mec="white", mew=0.4, label="PUCCD + rotation", lw=1.5)
    ax.axhline(0.0016, color=MUTED, ls="--", lw=1)
    ax.set_yscale("log")
    ax.set_xlabel("Bond length (Å)")
    ax.set_ylabel("Energy error (Ha)")
    ax.set_title(mol)
    ax.legend(frameon=False, fontsize=9, labelcolor=TEXT)

fig.suptitle("Orbital rotation vs. plain PUCCD, full bond-length curves", fontsize=14, y=1.03)
fig.tight_layout()
fig.savefig("results_decoupling/figures/rotation_fix_full_curves.png", bbox_inches="tight")
print("Saved")
