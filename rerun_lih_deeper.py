"""Standalone re-run of LiH ONLY, with a much bigger restart/iteration budget,
to test whether the earlier strong energy-dipole correlation for LiH was a
convergence artifact (too few restarts) or a real result. Merges the new LiH
entry into the existing results_decoupling/analysis.json and
restart_histories.json, leaving H2 and BeH2 untouched.
"""
import warnings, logging, json, time
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

cfg = dict(vdd.MOLECULES["LiH"])
cfg["n_restarts"] = 12
cfg["slsqp_maxiter"] = 250
print(f"[LiH-deep] n_restarts={cfg['n_restarts']} slsqp_maxiter={cfg['slsqp_maxiter']}")

t0 = time.time()
res = vdd.run_molecule("LiH-deep", cfg)
print(f"[LiH-deep] total time: {time.time()-t0:.1f}s")

with open("results_decoupling/analysis.json") as f:
    slim = json.load(f)
with open("results_decoupling/restart_histories.json") as f:
    histories = json.load(f)

slim_points = []
new_histories = []
for p in res["points"]:
    hist = p.pop("restart_histories")
    new_histories.append({"r": p["r"], "restart_histories": hist})
    slim_points.append(p)

slim["LiH"] = {
    "config_summary": {
        "basis": cfg["basis"], "freeze_core": cfg["freeze_core"],
        "bond_range": cfg["bond_range"], "n_restarts": cfg["n_restarts"],
        "slsqp_maxiter": cfg["slsqp_maxiter"],
    },
    "prescan_r": res["grid_info"]["prescan_r"].tolist(),
    "prescan_energy": res["grid_info"]["prescan_energy"].tolist(),
    "prescan_dipole_xyz": res["grid_info"]["prescan_dipole_xyz"].tolist(),
    "prescan_dipole_mag": res["grid_info"]["prescan_dipole_mag"].tolist(),
    "dominant_dipole_axis": res["grid_info"]["dominant_axis"],
    "points": slim_points,
}
histories["LiH"] = new_histories

with open("results_decoupling/analysis.json", "w") as f:
    json.dump(slim, f, indent=2)
with open("results_decoupling/restart_histories.json", "w") as f:
    json.dump(histories, f, indent=2)

print("Merged deeper LiH results into results_decoupling/analysis.json + restart_histories.json")
