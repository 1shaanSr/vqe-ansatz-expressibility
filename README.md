# Ansatz Expressibility Failures in VQE: Diagnosis and a Validated Fix

A joint energy/dipole-moment error study of the Variational Quantum Eigensolver (VQE)
across five molecules, identifying two distinct ansatz failure modes, a first-principles
mechanistic explanation for both, and an architectural fix validated to resolve them.

## Summary of findings

Using a Hartree-Fock-initialized **PUCCD** ansatz (paired unitary coupled-cluster
doubles) with warm-started multi-restart classical optimization, we scanned the full
potential energy surface of **H2, LiH, BeH2, HF, and BH** (4-12 qubits, STO-3G basis)
across 87 bond-length geometries, in noiseless classical simulation. Hardware
verification (`ibm_kingston`) is planned as a deliberately separate, later step.

**Two distinct failure modes emerged:**
- **LiH** degrades *gradually* as the bond stretches (Spearman r=0.71 between energy
  and dipole error across the curve — robust to an autocorrelation-corrected
  significance test and to the choice of sampling grid).
- **HF and BH** instead track the exact answer closely, then undergo a sharp,
  localized collapse at a specific bond length.

**We ruled out insufficient optimization as the cause.** At HF's worst-affected
geometries, 12 independent optimizer restarts — from both random and warm-started
initial points — converge to the *identical* energy to within 1e-6 Ha, regardless
of starting point. This is a genuine ansatz expressibility ceiling, not an
under-optimized run. BH and LiH show a rougher multi-restart landscape at a subset
of geometries (spreads up to roughly 1 Ha near BH's curve crossing); all reported
energies use the best of twelve restarts to control for this.

**We explained the dichotomy with a purely classical diagnostic.** Computing the
weight of the Hartree-Fock determinant in the *exact* (FCI) wavefunction across the
same geometries — no VQE required — shows LiH's weight decaying smoothly, while HF
and BH's each collapse almost vertically at essentially the same bond length where
PUCCD fails catastrophically. HF and BH undergo a genuine electronic-structure curve
crossing; LiH does not.

**We then validated a targeted fix.** PUCCD is restricted to paired double
excitations and has no orbital-rotation degree of freedom — exactly the capability
needed to track a wavefunction across a crossing. This is grounded directly in
Anselmetti et al.'s result ([NJP 23, 113010 (2021)](https://arxiv.org/abs/2104.05695))
that pair-exchange-only and orbital-rotation-only ansätze are each individually
non-universal, while their combination is. Adding single (orbital-rotation)
excitations to PUCCD resolved the catastrophic failures by up to **~38,766x**
(0.69 Ha -> 1.8e-5 Ha, HF) and brought **36 of 37** previously-failing geometries in two
of the three affected molecules to chemical accuracy; the third (BH) improved at
every one of 18 geometries tested (up to 446x at its best point, 0.47 Ha -> 0.0011 Ha),
with a smaller residual gap.

This fix is currently validated only in noiseless simulation.

## Repository structure

| File | Purpose |
|---|---|
| `vqe_dipole_decoupling.py` | Core pipeline: PySCF -> qiskit-nature -> PUCCD ansatz, adaptive bond-length sampling, warm-started multi-restart VQE, for all 5 molecules |
| `make_figures.py` | Generates the full figure/analysis set, including the autocorrelation-corrected significance test and outlier-robust correlation analysis |
| `analyze_multireference_character.py` | Classical (non-VQE) Hartree-Fock-determinant-weight diagnostic explaining the two failure modes |
| `rerun_with_rotation.py` | Reruns full molecular curves with the orbital-rotation-augmented ansatz (the validated fix) |
| `test_qnp_style_ansatz.py` | Spot-check of the fix at the specific geometries where plain PUCCD catastrophically fails |
| `rerun_beh2_deep.py`, `rerun_lih_deeper.py`, `run_lih_uniform_grid.py` | Robustness checks: restart-budget sensitivity, sampling-grid sensitivity |
| `run_additional_molecules.py` | Extends the study to HF and BH as independent replicate molecules |
| `merge_new_results.py` | Consolidates parallel run outputs into the master result files |
| `plot_*.py` | Supplementary figure generation |
| `results_decoupling/` | All numerical results (JSON) and figures (PNG) referenced above |

## Methodology notes

- **Statistical rigor**: an initial analysis found a strong raw correlation between
  energy and dipole error (naive p=3.4e-5). Because consecutive bond-length points are
  autocorrelated (not independent samples), this was corrected using the effective
  sample size method of Pyper & Peterman (1998), giving a more defensible p≈0.035.
  A second check (outlier-robust Spearman rank correlation) further revealed that two
  molecules' apparent strong correlation was driven entirely by 1-2 extreme points,
  not a real trend — both corrections are implemented directly in `make_figures.py`
  and documented in its docstrings.
- **Leakage discipline**: every reported result was checked against a matched baseline
  (plain PUCCD vs. PUCCD+rotation, same restart budget, same grid) before being
  attributed to the ansatz change rather than to noise or budget differences.

## Dependencies

`qiskit`, `qiskit-nature`, `pymatgen`, `pyscf`, `numpy`, `scipy`, `matplotlib`,
`scikit-learn`. No API keys or external credentials are required to rerun the
simulation-only pipeline.
