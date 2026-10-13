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
    "grid.linewidth": 0.6, "axes.grid": True, "font.size": 11,
    "axes.titlesize": 13, "axes.titleweight": "bold", "figure.dpi": 140,
})

d = json.load(open("results_decoupling/qnp_style_test.json"))
labels = [f"{r['molecule']}\nr={r['r']}" for r in d]
plain = [r["puccd_only_error"] for r in d]
rot = [r["puccd_plus_rotation_error"] for r in d]

fig, ax = plt.subplots(figsize=(8, 5.5))
x = np.arange(len(labels))
w = 0.35
ax.bar(x - w/2, plain, w, color="#f85149", label="PUCCD only (paired doubles)")
ax.bar(x + w/2, rot, w, color="#3fb950", label="PUCCD + orbital rotation")
ax.axhline(0.0016, color=MUTED, lw=1.2, ls="--")
ax.text(len(labels) - 0.5, 0.0016, " chemical accuracy", color=MUTED, fontsize=8.5, va="bottom", ha="right")
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Energy error |E$_{sim}$ − E$_{exact}$| (Ha)")
ax.set_title("Orbital rotation fixes the catastrophic curve-crossing failures")
ax.legend(frameon=False, fontsize=9.5, labelcolor=TEXT)
fig.tight_layout()
fig.savefig("results_decoupling/figures/qnp_style_fix_comparison.png")
print("Saved")
