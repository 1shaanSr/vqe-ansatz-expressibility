import warnings, logging, time, json
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import numpy as np
import importlib.util

spec = importlib.util.spec_from_file_location("vdd", "/Users/ishaans/Documents/Quantum Comp./vqe_dipole_decoupling.py")
vdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdd)

from qiskit_nature.second_q.circuit.library import HartreeFock, PUCCD

def build_ansatz_with_singles(sysinfo):
    hf = HartreeFock(sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"])
    ansatz = PUCCD(sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"],
                    initial_state=hf, include_singles=(True, True))
    return vdd.flatten_ansatz(ansatz)

# The exact catastrophic-failure points identified earlier
TEST_POINTS = [
    ("HF", {"geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True}, 2.534),
    ("HF", {"geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True}, 3.5),
    ("BH", {"geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True}, 3.221),
    ("BH", {"geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}", "basis": "sto3g", "charge": 0, "spin": 0, "freeze_core": True}, 3.5),
]

results = []
for name, cfg, r in TEST_POINTS:
    t0 = time.time()
    sysinfo = vdd.build_problem(cfg, r)
    exact = vdd.exact_solution(sysinfo)

    # baseline: plain PUCCD (paired doubles only) at the SAME deep budget
    ansatz_plain = vdd.build_ansatz(sysinfo)
    rng = np.random.default_rng(42)
    best_plain = None
    for i in range(12):
        x0 = rng.uniform(-np.pi, np.pi, ansatz_plain.num_parameters)
        out = vdd.run_vqe_point(sysinfo, ansatz_plain, 1, 250, warm_start_x=x0)
        if best_plain is None or out["best_electronic_energy"] < best_plain:
            best_plain = out["best_electronic_energy"]
    e_plain = vdd.total_energy(best_plain, sysinfo)

    # test: PUCCD + singles (orbital rotation)
    ansatz_rot = build_ansatz_with_singles(sysinfo)
    rng = np.random.default_rng(42)
    best_rot = None
    for i in range(12):
        x0 = rng.uniform(-np.pi, np.pi, ansatz_rot.num_parameters)
        out = vdd.run_vqe_point(sysinfo, ansatz_rot, 1, 250, warm_start_x=x0)
        if best_rot is None or out["best_electronic_energy"] < best_rot:
            best_rot = out["best_electronic_energy"]
    e_rot = vdd.total_energy(best_rot, sysinfo)

    err_plain = abs(e_plain - exact["energy"])
    err_rot = abs(e_rot - exact["energy"])
    print(f"[{name} r={r}] exact={exact['energy']:.6f}  "
          f"PUCCD-only err={err_plain:.6f} Ha  PUCCD+rotation err={err_rot:.6f} Ha  "
          f"improvement={err_plain - err_rot:+.6f} Ha  [{time.time()-t0:.1f}s]")
    results.append({"molecule": name, "r": r, "exact": exact["energy"],
                     "puccd_only_error": err_plain, "puccd_plus_rotation_error": err_rot})

with open("results_decoupling/qnp_style_test.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved results_decoupling/qnp_style_test.json")
