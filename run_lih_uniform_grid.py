"""Tests whether the LiH energy-dipole correlation (r=0.79) survives on a
UNIFORM bond-length grid, or whether it was partly an artifact of the
adaptive grid's own sampling logic -- which concentrates points wherever the
dipole changes fastest, and for LiH that happens to be the SAME region
where energy error is also worst (growing multi-reference character near
dissociation). Oversampling the region where both are simultaneously bad
could mechanically inflate the correlation. This reruns LiH on a plain
np.linspace(1.0, 5.0, 20) grid (no prescan, no adaptive densification) at
the same validated deep budget, and stores it under a separate key
"LiH_uniform_grid" so it can be compared directly against the adaptive-grid
"LiH" result rather than replacing it.
"""
import warnings, logging, json, time
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import numpy as np
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

cfg = dict(vdd.MOLECULES["LiH"])
cfg["n_restarts"] = 12
cfg["slsqp_maxiter"] = 250

final_r = np.linspace(cfg["bond_range"][0], cfg["bond_range"][1], 20)
print(f"[LiH-uniform] grid: {np.round(final_r, 3).tolist()}")

points = []
warm_start_x = None
t_start = time.time()
for idx, r in enumerate(final_r):
    t0 = time.time()
    sysinfo = vdd.build_problem(cfg, r)
    exact = vdd.exact_solution(sysinfo)
    ansatz = vdd.build_ansatz(sysinfo)
    vqe_out = vdd.run_vqe_point(sysinfo, ansatz, cfg["n_restarts"], cfg["slsqp_maxiter"], warm_start_x=warm_start_x)
    sim_energy = vdd.total_energy(vqe_out["best_electronic_energy"], sysinfo)
    sim_dipole = vdd.evaluate_dipole_at(sysinfo, ansatz, vqe_out["best_x"])
    warm_start_x = vqe_out["best_x"]
    hf_electronic = vdd.total_energy(vdd.estimator_hf_energy(sysinfo, ansatz), sysinfo)

    point = {
        "r": float(r), "num_qubits": sysinfo["num_qubits"],
        "n_active_electrons": sum(sysinfo["num_particles"]),
        "exact_energy": exact["energy"], "exact_dipole_xyz": exact["dipole_xyz"].tolist(),
        "exact_dipole_mag": float(np.linalg.norm(exact["dipole_xyz"])),
        "hf_energy": hf_electronic, "sim_energy": sim_energy,
        "sim_dipole_xyz": sim_dipole.tolist(), "sim_dipole_mag": float(np.linalg.norm(sim_dipole)),
        "restart_histories": vqe_out["restart_histories"],
    }
    points.append(point)
    print(f"  [LiH-uniform] r={r:.3f} A ({idx+1}/20) E_exact={exact['energy']:.6f} "
          f"E_sim={sim_energy:.6f} mu_exact={point['exact_dipole_mag']:.4f} "
          f"mu_sim={point['sim_dipole_mag']:.4f} [{time.time()-t0:.1f}s]")

print(f"[LiH-uniform] total time: {time.time()-t_start:.1f}s")

slim = {}
histories = {}

slim_points = []
mol_histories = []
for p in points:
    hist = p.pop("restart_histories")
    mol_histories.append({"r": p["r"], "restart_histories": hist})
    slim_points.append(p)

slim["LiH_uniform_grid"] = {
    "config_summary": {"basis": cfg["basis"], "freeze_core": cfg["freeze_core"],
                        "bond_range": cfg["bond_range"], "n_restarts": cfg["n_restarts"],
                        "slsqp_maxiter": cfg["slsqp_maxiter"], "grid_type": "uniform"},
    "prescan_r": final_r.tolist(), "prescan_energy": [], "prescan_dipole_xyz": [], "prescan_dipole_mag": [],
    "dominant_dipole_axis": 2, "points": slim_points,
}
histories["LiH_uniform_grid"] = mol_histories

with open("results_decoupling/analysis_lih_uniform.json", "w") as f:
    json.dump(slim, f, indent=2)
with open("results_decoupling/restart_histories_lih_uniform.json", "w") as f:
    json.dump(histories, f, indent=2)
print("Written LiH_uniform_grid results to analysis_lih_uniform.json")
