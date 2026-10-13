"""Reruns one molecule's FULL adaptive grid (reusing the exact same bond
lengths already validated in results_decoupling/analysis.json) with the
orbital-rotation-augmented ansatz (PUCCD + include_singles=True) instead of
plain PUCCD, at the same validated 12x250 restart budget. This is the
generalization check for the spot-check fix already validated on 4
catastrophic points: does it help across the WHOLE curve, or just those 4?

Usage: python3 rerun_with_rotation.py <MOLECULE_NAME>
Writes to results_decoupling/analysis_<molecule>_rotation.json (own file,
avoids the read-modify-write race from running multiple molecules in
parallel -- merged centrally afterward).
"""
import sys, warnings, logging, json, time
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import numpy as np
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

from qiskit_nature.second_q.circuit.library import HartreeFock, PUCCD

def build_ansatz_with_rotation(sysinfo):
    hf = HartreeFock(sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"])
    ansatz = PUCCD(sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"],
                    initial_state=hf, include_singles=(True, True))
    return vdd.flatten_ansatz(ansatz)

MOL_CONFIGS = {
    "HF": {"geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True},
    "BH": {"geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True},
    "LiH": {"geometry_fn": lambda r: f"Li 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True},
}

name = sys.argv[1]
cfg = MOL_CONFIGS[name]
N_RESTARTS, MAXITER = 12, 250

with open("results_decoupling/analysis.json") as f:
    existing = json.load(f)
final_r = [p["r"] for p in existing[name]["points"]]
print(f"[{name}+rotation] reusing {len(final_r)}-point grid: {final_r}", flush=True)

points = []
warm_start_x = None
t_start = time.time()
for idx, r in enumerate(final_r):
    t0 = time.time()
    sysinfo = vdd.build_problem(cfg, r)
    exact = vdd.exact_solution(sysinfo)
    ansatz = build_ansatz_with_rotation(sysinfo)
    vqe_out = vdd.run_vqe_point(sysinfo, ansatz, N_RESTARTS, MAXITER, warm_start_x=warm_start_x)
    sim_energy = vdd.total_energy(vqe_out["best_electronic_energy"], sysinfo)
    sim_dipole = vdd.evaluate_dipole_at(sysinfo, ansatz, vqe_out["best_x"])
    warm_start_x = vqe_out["best_x"]

    point = {
        "r": float(r), "num_qubits": sysinfo["num_qubits"],
        "exact_energy": exact["energy"], "exact_dipole_mag": float(np.linalg.norm(exact["dipole_xyz"])),
        "sim_energy": sim_energy, "sim_dipole_mag": float(np.linalg.norm(sim_dipole)),
    }
    points.append(point)
    e_err = abs(sim_energy - exact["energy"])
    print(f"  [{name}+rotation] r={r:.3f} ({idx+1}/{len(final_r)}) E_err={e_err:.6f} Ha [{time.time()-t0:.1f}s]", flush=True)

print(f"[{name}+rotation] total time: {time.time()-t_start:.1f}s", flush=True)
with open(f"results_decoupling/analysis_{name}_rotation.json", "w") as f:
    json.dump({f"{name}_rotation": {"points": points}}, f, indent=2)
print(f"[{name}+rotation] DONE, written to analysis_{name}_rotation.json", flush=True)
