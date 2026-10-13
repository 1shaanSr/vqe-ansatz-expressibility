"""Full BeH2 rerun at the validated deep budget (12 restarts x 250 iters)
to settle the previously-unresolved question: was BeH2's poor convergence
(mean 0.10 Ha, max 0.64 Ha error at the original 4x100 budget) an
optimizer-budget problem or a genuine ansatz limit like LiH's? Unlike the
LiH check, this reruns the FULL grid (not just one spot-check point) since
BeH2 was never checked at all. Merges into the same result files, replacing
only the "BeH2" key.
"""
import warnings, logging, json, time
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

cfg = dict(vdd.MOLECULES["BeH2"])
cfg["n_restarts"] = 12
cfg["slsqp_maxiter"] = 250
print(f"[BeH2-deep] n_restarts={cfg['n_restarts']} slsqp_maxiter={cfg['slsqp_maxiter']}")

t0 = time.time()
res = vdd.run_molecule("BeH2-deep", cfg)
print(f"[BeH2-deep] total time: {time.time()-t0:.1f}s")

slim = {}
histories = {}

slim_points = []
mol_histories = []
for p in res["points"]:
    hist = p.pop("restart_histories")
    mol_histories.append({"r": p["r"], "restart_histories": hist})
    slim_points.append(p)

slim["BeH2_deep"] = {
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
histories["BeH2_deep"] = mol_histories

with open("results_decoupling/analysis_beh2_deep.json", "w") as f:
    json.dump(slim, f, indent=2)
with open("results_decoupling/restart_histories_beh2_deep.json", "w") as f:
    json.dump(histories, f, indent=2)
print("Written deeper BeH2 results to analysis_beh2_deep.json (key: BeH2_deep)")
