"""Multi-reference diagnostic: how much weight does the single Hartree-Fock
determinant retain in the EXACT (FCI) ground state as bond length increases?
This is a standard, well-established measure of how "single-reference" a
wavefunction is -- a fast decay means the system needs multi-determinant
character (which paired-UCC's restricted excitation set struggles to
capture) developing quickly; a slow, late decay means single-reference
character survives much further out.

This directly tests the open hypothesis from the outline: does LiH's HF
weight decay smoothly across its whole range (matching its smooth,
continuous PUCCD failure), while HF/BH's HF weight stays high right up
until a sudden drop (matching their sudden, catastrophic PUCCD failure)?

No VQE needed -- purely classical exact diagonalization, using the same
PySCF/qiskit-nature stack as the main pipeline. Uses the fine PRESCAN grids
already computed (dense, and free -- no new expensive VQE runs).
"""
import warnings, logging, json
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import numpy as np
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.transformers import FreezeCoreTransformer
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import HartreeFock
from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit.quantum_info import Statevector

MOLECULES = {
    "H2": {"geometry_fn": lambda r: f"H 0 0 0; H 0 0 {r}", "freeze_core": False},
    "LiH": {"geometry_fn": lambda r: f"Li 0 0 0; H 0 0 {r}", "freeze_core": True},
    "BeH2": {"geometry_fn": lambda r: f"Be 0 0 0; H 0 0 {-r}; H 0 0 {r}", "freeze_core": True},
    "HF": {"geometry_fn": lambda r: f"F 0 0 0; H 0 0 {r}", "freeze_core": True},
    "BH": {"geometry_fn": lambda r: f"B 0 0 0; H 0 0 {r}", "freeze_core": True},
}

with open("results_decoupling/analysis.json") as f:
    DATA = json.load(f)

results = {}
for name, cfg in MOLECULES.items():
    r_grid = np.array(DATA[name]["prescan_r"])
    hf_weights = []
    print(f"[{name}] computing HF-determinant weight across {len(r_grid)} points...")
    for r in r_grid:
        driver = PySCFDriver(atom=cfg["geometry_fn"](r), basis="sto3g", charge=0, spin=0)
        problem = driver.run()
        if cfg["freeze_core"]:
            problem = FreezeCoreTransformer(freeze_core=True).transform(problem)
        mapper = JordanWignerMapper()
        h_op = mapper.map(problem.hamiltonian.second_q_op())
        exact = NumPyMinimumEigensolver().compute_minimum_eigenvalue(h_op)
        exact_state = exact.eigenstate  # Statevector

        hf_circuit = HartreeFock(problem.num_spatial_orbitals, problem.num_particles, mapper)
        hf_state = Statevector(hf_circuit)

        weight = abs(hf_state.inner(exact_state)) ** 2
        hf_weights.append(float(weight))

    results[name] = {"r": r_grid.tolist(), "hf_weight": hf_weights}
    print(f"[{name}] HF weight: {hf_weights[0]:.4f} (r={r_grid[0]:.2f}) -> {hf_weights[-1]:.4f} (r={r_grid[-1]:.2f})")

with open("results_decoupling/multireference_character.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nWritten to results_decoupling/multireference_character.json")
