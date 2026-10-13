"""
VQE Dipole-Energy Decoupling Study: H2, LiH, BeH2
====================================================

Rebuilt pipeline for the new paper thesis ("When Energy Lies: Dipole-Energy
Error Decoupling in VQE Potential Energy Surfaces"). This is a full rewrite,
not a patch of the old vqe_pes_dipole.py:

  * Built on qiskit-nature (PySCFDriver + JordanWignerMapper +
    FreezeCoreTransformer + ElectronicDipoleMoment) instead of hand-rolled
    OpenFermion bridging. This gives all THREE dipole components (x, y, z)
    for free, with a validated sign/constant convention (see
    NOTE ON DIPOLE CONVENTION below), and removes an entire class of
    qubit-ordering bugs the old manual bridge was exposed to.
  * Ansatz is now HartreeFock-initialized PUCCD (paired UCC doubles) instead
    of a generic hardware-efficient EfficientSU2 circuit. PUCCD is a
    chemistry-structured ansatz restricted to paired double excitations --
    a good match since H2/LiH/BeH2 are all closed-shell singlets. It also
    has far fewer parameters than EfficientSU2 (e.g. 1 for H2, ~4-8 for
    LiH/BeH2), which is what makes the much denser bond-length grids below
    affordable.
  * Restart strategy is now neighbor-geometry parameter warm-starting: one
    restart per point is seeded from the previous (lower-r) point's
    converged parameters, the rest are fresh random restarts. This was
    prototyped earlier and gave large accuracy gains at the same restart
    budget; it is now the default, not a side experiment.
  * Every geometry keeps ALL restart convergence histories (not just the
    winner), so we can plot every optimizer "session" for a given geometry
    on one shared graph -- the "multi-session" figure -- for every
    geometry, not just one representative one.
  * Bond-length grids are chosen adaptively: a fast, exact-diagonalization-
    only PRESCAN at coarse-but-full-range resolution locates where the
    dipole moment changes fastest / changes sign, then the final grid (the
    one VQE actually runs on) is densified there. This directly targets the
    thesis question: is there more going on right where the dipole is doing
    something interesting?

NOTE ON DIPOLE CONVENTION (validated against the prior project's own exact
LiH dipole values before trusting this pipeline -- see project notes):
    total_dipole[component] = nuclear_dipole[component]
                               - (electronic_expectation[component]
                                  + frozen_core_constant[component])
qiskit-nature's ElectronicDiporeMoment.reverse_dipole_sign is True, meaning
the mapped electronic dipole operators return +<r>-like expectation values
that must be SUBTRACTED from the nuclear dipole, not added. Getting this
backwards silently flips every dipole sign, which would be catastrophic for
a paper whose entire thesis is about dipole sign behavior -- hence this is
called out explicitly and was numerically checked against a known reference
value before use.

THIS RUN IS SIMULATION-ONLY. No real IBM Quantum hardware time is spent by
this script. Hardware verification is a deliberately separate, later step
(see README / paper outline "Open Decisions") -- run only once this
simulation-only pipeline's results have been reviewed.
"""

# ==============================================================================
# SECTION 0 -- SETUP
# ==============================================================================
import warnings
import logging

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.transformers import FreezeCoreTransformer
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import HartreeFock, PUCCD
from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import SLSQP
from qiskit.primitives import StatevectorEstimator

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

DEBYE_PER_AU = 2.541746
CHEM_ACCURACY_HA = 0.0016  # 1 kcal/mol, standard energy chemical-accuracy threshold

# Dipole "decoupling" threshold -- fixed BEFORE looking at any results, per the
# paper outline's explicit instruction not to choose this post-hoc.
#   - a geometry counts as "dipole wrong" if the total-dipole-magnitude error
#     exceeds DIPOLE_ERROR_THRESHOLD_AU, OR the sign of the dominant nonzero
#     exact dipole component flips in the computed value (only checked when
#     the exact component magnitude exceeds SIGN_FLIP_MIN_EXACT_AU, to avoid
#     flagging noise around an essentially-zero dipole as a "sign flip").
DIPOLE_ERROR_THRESHOLD_AU = 0.05
SIGN_FLIP_MIN_EXACT_AU = 0.05

RESULTS_DIR = "results_decoupling"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

print("=" * 78)
print("VQE DIPOLE-ENERGY DECOUPLING STUDY -- H2 / LiH / BeH2")
print("=" * 78)

# ==============================================================================
# SECTION 1 -- MOLECULE CONFIGURATION
# ==============================================================================
# geometry_fn(r) -> PySCF atom string. bond_range is the FULL span the
# adaptive prescan explores; n_prescan is how many exact-only points sample
# that span; n_vqe_points is the size of the final (denser-where-it-matters)
# grid that actually gets a PUCCD/VQE run.
MOLECULES = {
    "H2": {
        "geometry_fn": lambda r: f"H 0 0 0; H 0 0 {r}",
        "basis": "sto3g",
        "charge": 0,
        "spin": 0,
        "freeze_core": False,
        "bond_range": (0.4, 3.0),
        "n_prescan": 30,
        "n_vqe_points": 16,
        "n_restarts": 4,
        "slsqp_maxiter": 100,
    },
    "LiH": {
        "geometry_fn": lambda r: f"Li 0 0 0; H 0 0 {r}",
        "basis": "sto3g",
        "charge": 0,
        "spin": 0,
        "freeze_core": True,
        # Deliberately wide: LiH's restricted-Hartree-Fock dissociation
        # problem (incorrect ionic character surviving to large r) is a
        # textbook source of exactly the energy/dipole decoupling this paper
        # is about, and it shows up well past the old pilot's 3.0 A cutoff.
        "bond_range": (1.0, 5.0),
        "n_prescan": 36,
        "n_vqe_points": 20,
        "n_restarts": 4,
        "slsqp_maxiter": 100,
    },
    "BeH2": {
        "geometry_fn": lambda r: f"Be 0 0 0; H 0 0 {-r}; H 0 0 {r}",
        "basis": "sto3g",
        "charge": 0,
        "spin": 0,
        "freeze_core": True,
        "bond_range": (0.9, 3.2),
        "n_prescan": 30,
        "n_vqe_points": 18,
        "n_restarts": 4,
        "slsqp_maxiter": 100,
    },
}


# ==============================================================================
# SECTION 2 -- PROBLEM CONSTRUCTION (qiskit-nature)
# ==============================================================================
def build_problem(cfg, r):
    """PySCF -> (optionally frozen-core-reduced) ElectronicStructureProblem,
    plus the mapped qubit Hamiltonian and the three mapped dipole-component
    operators, plus everything needed to reconstruct TOTAL (not just
    electronic-active-space) energy and dipole afterward."""
    driver = PySCFDriver(
        atom=cfg["geometry_fn"](r),
        basis=cfg["basis"],
        charge=cfg["charge"],
        spin=cfg["spin"],
    )
    problem = driver.run()
    energy_shift = 0.0
    dipole_shift = np.zeros(3)
    if cfg["freeze_core"]:
        fc = FreezeCoreTransformer(freeze_core=True)
        problem = fc.transform(problem)
        energy_shift = problem.hamiltonian.constants.get("FreezeCoreTransformer", 0.0)

    mapper = JordanWignerMapper()
    h_op = mapper.map(problem.hamiltonian.second_q_op())

    dip_property = problem.properties.electronic_dipole_moment
    dipole_ops = {k: mapper.map(v) for k, v in dip_property.second_q_ops().items()}
    nuclear_dipole = np.array(dip_property.nuclear_dipole_moment)
    if cfg["freeze_core"] and "FreezeCoreTransformer" in dip_property.constants:
        dipole_shift = np.array(dip_property.constants["FreezeCoreTransformer"])

    return {
        "problem": problem,
        "mapper": mapper,
        "h_op": h_op,
        "dipole_ops": dipole_ops,  # dict: "XDipole"/"YDipole"/"ZDipole" -> SparsePauliOp
        "nuclear_repulsion": problem.hamiltonian.nuclear_repulsion_energy,
        "energy_shift": energy_shift,
        "nuclear_dipole": nuclear_dipole,
        "dipole_shift": dipole_shift,
        "num_qubits": h_op.num_qubits,
        "num_spatial_orbitals": problem.num_spatial_orbitals,
        "num_particles": problem.num_particles,
    }


def total_energy(electronic_energy, sysinfo):
    return electronic_energy + sysinfo["nuclear_repulsion"] + sysinfo["energy_shift"]


def total_dipole(electronic_dipole_xyz, sysinfo):
    """electronic_dipole_xyz: length-3 array of <XDipole>,<YDipole>,<ZDipole>
    expectation values. Returns total (nuclear + electronic) x,y,z in a.u."""
    return sysinfo["nuclear_dipole"] - (np.array(electronic_dipole_xyz) + sysinfo["dipole_shift"])


def exact_solution(sysinfo):
    solver = NumPyMinimumEigensolver()
    result = solver.compute_minimum_eigenvalue(sysinfo["h_op"], aux_operators=sysinfo["dipole_ops"])
    e_elec = result.eigenvalue.real
    dip_elec = np.array([
        result.aux_operators_evaluated["XDipole"][0].real,
        result.aux_operators_evaluated["YDipole"][0].real,
        result.aux_operators_evaluated["ZDipole"][0].real,
    ])
    return {
        "energy": total_energy(e_elec, sysinfo),
        "dipole_xyz": total_dipole(dip_elec, sysinfo),
    }


# ==============================================================================
# SECTION 3 -- ANSATZ + LOCAL VQE (PUCCD, warm-started multi-restart)
# ==============================================================================
def build_ansatz(sysinfo):
    hf = HartreeFock(sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"])
    ansatz = PUCCD(
        sysinfo["num_spatial_orbitals"], sysinfo["num_particles"], sysinfo["mapper"], initial_state=hf
    )
    return flatten_ansatz(ansatz)


def flatten_ansatz(ansatz, max_reps=12):
    """PUCCD's excitation gates are high-level Instruction objects whose
    `.definition` gets re-synthesized from scratch on every bind+simulate
    call -- measured at ~10s/evaluation for BeH2's 12-qubit ansatz, which
    would make the full grid take hours. Fully decomposing ONCE into basis
    gates (a ~0.3s one-time cost) and reusing that flat circuit for every
    subsequent evaluation cuts per-eval cost to ~0.13s (verified numerically
    identical energy, to ~1e-8 Ha, against the un-flattened ansatz -- well
    beyond the precision VQE needs). Iterates decompose() until circuit size
    stops changing, i.e. until nothing but basis gates remains."""
    flat = ansatz
    prev_size = -1
    for _ in range(max_reps):
        flat = flat.decompose()
        if flat.size() == prev_size:
            break
        prev_size = flat.size()
    return flat


def run_vqe_point(sysinfo, ansatz, n_restarts, slsqp_maxiter, warm_start_x=None):
    """Runs n_restarts SLSQP optimizations (one warm-started from the previous
    geometry's best parameters if warm_start_x is given, the rest fresh random)
    and returns the best result plus every restart's full convergence history
    (this is what feeds the multi-session overlay figures)."""
    estimator = StatevectorEstimator()

    def make_cost_fn(history):
        def cost_fn(params):
            val = estimator.run([(ansatz, sysinfo["h_op"], params)]).result()[0].data.evs.item()
            history.append(val)
            return val
        return cost_fn

    restart_histories = []
    best = None
    best_history = None
    for i in range(n_restarts):
        if i == 0 and warm_start_x is not None:
            x0 = warm_start_x
            seed_type = "warm_start"
        else:
            x0 = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)
            seed_type = "random"
        history = []
        cost_fn = make_cost_fn(history)
        result = SLSQP(maxiter=slsqp_maxiter).minimize(fun=cost_fn, x0=x0)
        restart_histories.append({"seed_type": seed_type, "history": history, "final": result.fun})
        if best is None or result.fun < best.fun:
            best = result
            best_history = history

    return {
        "best_x": best.x,
        "best_electronic_energy": best.fun,
        "restart_histories": restart_histories,
    }


def _safe_expectation(estimator, ansatz, op, params):
    """A dipole component along a symmetry-forbidden axis (e.g. x/y for a
    molecule lying on the z-axis) maps to a literally-zero SparsePauliOp,
    which Qiskit's estimator rejects as an 'empty observable' rather than
    just returning 0. Short-circuit that case instead of erroring."""
    if len(op) == 0 or np.allclose(op.coeffs, 0):
        return 0.0
    return estimator.run([(ansatz, op, params)]).result()[0].data.evs.item()


def evaluate_dipole_at(sysinfo, ansatz, params):
    estimator = StatevectorEstimator()
    dip_elec = np.array([
        _safe_expectation(estimator, ansatz, sysinfo["dipole_ops"]["XDipole"], params),
        _safe_expectation(estimator, ansatz, sysinfo["dipole_ops"]["YDipole"], params),
        _safe_expectation(estimator, ansatz, sysinfo["dipole_ops"]["ZDipole"], params),
    ])
    return total_dipole(dip_elec, sysinfo)


# ==============================================================================
# SECTION 4 -- ADAPTIVE BOND-LENGTH GRID (prescan -> densify near features)
# ==============================================================================
def prescan_and_build_grid(name, cfg):
    r_lo, r_hi = cfg["bond_range"]
    prescan_r = np.linspace(r_lo, r_hi, cfg["n_prescan"])
    prescan_energy = np.zeros_like(prescan_r)
    prescan_dipole_mag = np.zeros_like(prescan_r)
    prescan_dipole_xyz = np.zeros((len(prescan_r), 3))

    print(f"[{name}] Prescanning {len(prescan_r)} points (exact diagonalization only) "
          f"over {r_lo}-{r_hi} A to locate dipole features...")
    for i, r in enumerate(prescan_r):
        sysinfo = build_problem(cfg, r)
        exact = exact_solution(sysinfo)
        prescan_energy[i] = exact["energy"]
        prescan_dipole_xyz[i] = exact["dipole_xyz"]
        prescan_dipole_mag[i] = np.linalg.norm(exact["dipole_xyz"])

    # Feature score: how fast the dipole magnitude is changing, per unit r.
    d_dipole = np.abs(np.gradient(prescan_dipole_mag, prescan_r))
    # Also flag a sign change in whichever component has the largest overall
    # magnitude along the scan (that's the "physical" dipole axis here).
    dominant_axis = int(np.argmax(np.abs(prescan_dipole_xyz).sum(axis=0)))
    signs = np.sign(prescan_dipole_xyz[:, dominant_axis])
    sign_change_mask = np.diff(signs) != 0
    feature_weight = d_dipole.copy()
    feature_weight[:-1][sign_change_mask] += feature_weight.max() + 1e-9  # heavily upweight sign-change bins

    # Turn the feature weight into a sampling density: more VQE points where
    # feature_weight is large. Implemented via inverse-CDF sampling on the
    # normalized cumulative feature weight, then merged with a uniform base
    # grid so the whole range still gets baseline coverage.
    n_total = cfg["n_vqe_points"]
    n_uniform = max(4, n_total // 3)
    n_adaptive = n_total - n_uniform
    uniform_part = np.linspace(r_lo, r_hi, n_uniform)

    cdf = np.cumsum(feature_weight - feature_weight.min() + 1e-6)
    cdf = cdf / cdf[-1]
    quantiles = np.linspace(0.02, 0.98, n_adaptive)
    adaptive_part = np.interp(quantiles, cdf, prescan_r)

    final_r = np.unique(np.round(np.concatenate([uniform_part, adaptive_part]), 4))
    final_r.sort()

    return {
        "prescan_r": prescan_r,
        "prescan_energy": prescan_energy,
        "prescan_dipole_xyz": prescan_dipole_xyz,
        "prescan_dipole_mag": prescan_dipole_mag,
        "dominant_axis": dominant_axis,
        "final_r": final_r,
    }


# ==============================================================================
# SECTION 5 -- MAIN PER-MOLECULE PIPELINE
# ==============================================================================
def run_molecule(name, cfg):
    t_molecule_start = time.time()
    grid_info = prescan_and_build_grid(name, cfg)
    final_r = grid_info["final_r"]
    print(f"[{name}] Final VQE grid: {len(final_r)} points -> {np.round(final_r, 3).tolist()}")

    points = []
    warm_start_x = None
    for idx, r in enumerate(final_r):
        t0 = time.time()
        sysinfo = build_problem(cfg, r)
        exact = exact_solution(sysinfo)
        ansatz = build_ansatz(sysinfo)

        vqe_out = run_vqe_point(
            sysinfo, ansatz, cfg["n_restarts"], cfg["slsqp_maxiter"], warm_start_x=warm_start_x
        )
        sim_energy = total_energy(vqe_out["best_electronic_energy"], sysinfo)
        sim_dipole = evaluate_dipole_at(sysinfo, ansatz, vqe_out["best_x"])
        warm_start_x = vqe_out["best_x"]  # seed the NEXT geometry

        hf_electronic = total_energy(
            estimator_hf_energy(sysinfo, ansatz), sysinfo
        )

        point = {
            "r": float(r),
            "num_qubits": sysinfo["num_qubits"],
            "n_active_electrons": sum(sysinfo["num_particles"]),
            "exact_energy": exact["energy"],
            "exact_dipole_xyz": exact["dipole_xyz"].tolist(),
            "exact_dipole_mag": float(np.linalg.norm(exact["dipole_xyz"])),
            "hf_energy": hf_electronic,
            "sim_energy": sim_energy,
            "sim_dipole_xyz": sim_dipole.tolist(),
            "sim_dipole_mag": float(np.linalg.norm(sim_dipole)),
            "restart_histories": vqe_out["restart_histories"],
        }
        points.append(point)
        print(f"  [{name}] r={r:.3f} A  ({idx+1}/{len(final_r)})  "
              f"E_exact={exact['energy']:.6f}  E_sim={sim_energy:.6f}  "
              f"|mu|_exact={point['exact_dipole_mag']:.4f}  |mu|_sim={point['sim_dipole_mag']:.4f}  "
              f"[{time.time()-t0:.1f}s]")

    print(f"[{name}] Done in {time.time()-t_molecule_start:.1f}s total.")
    return {"config_summary": {
                "basis": cfg["basis"], "freeze_core": cfg["freeze_core"],
                "bond_range": cfg["bond_range"], "n_restarts": cfg["n_restarts"],
                "slsqp_maxiter": cfg["slsqp_maxiter"],
            },
            "grid_info": grid_info, "points": points}


def estimator_hf_energy(sysinfo, ansatz):
    """Energy of the bare Hartree-Fock reference (all ansatz params = 0,
    since PUCCD is HF-initialized and its excitation amplitudes are additive
    rotations away from the zero-parameter HF state)."""
    estimator = StatevectorEstimator()
    zero_params = np.zeros(ansatz.num_parameters)
    return estimator.run([(ansatz, sysinfo["h_op"], zero_params)]).result()[0].data.evs.item()


# ==============================================================================
# SECTION 6 -- RUN EVERYTHING
# ==============================================================================
if __name__ == "__main__":
    all_results = {}
    for name, cfg in MOLECULES.items():
        all_results[name] = run_molecule(name, cfg)

    # Strip restart histories out of the main JSON dump (kept in a separate
    # file since they're large) so analysis.json stays small and readable.
    slim = {}
    histories_dump = {}
    for name, res in all_results.items():
        slim_points = []
        histories_dump[name] = []
        for p in res["points"]:
            hist = p.pop("restart_histories")
            histories_dump[name].append({"r": p["r"], "restart_histories": hist})
            slim_points.append(p)
        slim[name] = {
            "config_summary": res["config_summary"],
            "prescan_r": res["grid_info"]["prescan_r"].tolist(),
            "prescan_energy": res["grid_info"]["prescan_energy"].tolist(),
            "prescan_dipole_xyz": res["grid_info"]["prescan_dipole_xyz"].tolist(),
            "prescan_dipole_mag": res["grid_info"]["prescan_dipole_mag"].tolist(),
            "dominant_dipole_axis": res["grid_info"]["dominant_axis"],
            "points": slim_points,
        }

    with open(os.path.join(RESULTS_DIR, "analysis.json"), "w") as f:
        json.dump(slim, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "restart_histories.json"), "w") as f:
        json.dump(histories_dump, f, indent=2)

    print("\nAll molecules complete. Data written to results_decoupling/analysis.json")
    print("Restart histories written to results_decoupling/restart_histories.json")
    print("Run make_figures.py next to generate the figure set.")
