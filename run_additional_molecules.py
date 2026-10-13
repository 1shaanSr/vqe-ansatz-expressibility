"""HF and BH as independent replicate molecules (both real, nonzero-dipole
diatomics, same 10-qubit cost class as LiH) -- the base PUCCD run used a
4-restart budget that we later proved insufficient for reliable convergence
on stretched geometries, so these use the VALIDATED deep budget (12
restarts x 250 iterations) from the start. Appends into the same
analysis.json / restart_histories.json as new top-level molecule keys.
"""
import warnings, logging, json, time
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

NEW_MOLECULES = {
    "HF": {
        "geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}",
        "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True,
        "bond_range": (0.7, 3.5), "n_prescan": 30, "n_vqe_points": 18,
        "n_restarts": 12, "slsqp_maxiter": 250,
    },
    "BH": {
        "geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}",
        "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True,
        "bond_range": (0.8, 3.5), "n_prescan": 30, "n_vqe_points": 18,
        "n_restarts": 12, "slsqp_maxiter": 250,
    },
}

slim = {}
histories = {}

for name, cfg in NEW_MOLECULES.items():
    t0 = time.time()
    res = vdd.run_molecule(name, cfg)
    print(f"[{name}] wall time: {time.time()-t0:.1f}s")

    slim_points = []
    mol_histories = []
    for p in res["points"]:
        hist = p.pop("restart_histories")
        mol_histories.append({"r": p["r"], "restart_histories": hist})
        slim_points.append(p)

    slim[name] = {
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
    histories[name] = mol_histories

    # Dedicated output file -- avoids the read-modify-write race that would
    # happen if multiple concurrently-running scripts all wrote to the same
    # shared analysis.json (whichever finishes last would silently clobber
    # the others' results). Merged into the shared file in one single-
    # threaded pass AFTER all parallel jobs finish (see merge_new_results.py).
    with open("results_decoupling/analysis_new_molecules.json", "w") as f:
        json.dump(slim, f, indent=2)
    with open("results_decoupling/restart_histories_new_molecules.json", "w") as f:
        json.dump(histories, f, indent=2)
    print(f"[{name}] written to analysis_new_molecules.json")

print("ALL NEW MOLECULES DONE")
