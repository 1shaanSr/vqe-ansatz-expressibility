"""Single-threaded merge step, run AFTER run_additional_molecules.py,
rerun_beh2_deep.py, and run_lih_uniform_grid.py have all finished writing
their own dedicated output files. Combines everything into the master
analysis.json / restart_histories.json used by make_figures.py."""
import json
import os

RESULTS_DIR = "results_decoupling"


def load(path):
    full = os.path.join(RESULTS_DIR, path)
    if not os.path.exists(full):
        print(f"  (skipping {path}, not found)")
        return {}
    with open(full) as f:
        return json.load(f)


with open(os.path.join(RESULTS_DIR, "analysis.json")) as f:
    slim = json.load(f)
with open(os.path.join(RESULTS_DIR, "restart_histories.json")) as f:
    histories = json.load(f)

for analysis_file, hist_file in [
    ("analysis_new_molecules.json", "restart_histories_new_molecules.json"),
    ("analysis_beh2_deep.json", "restart_histories_beh2_deep.json"),
    ("analysis_lih_uniform.json", "restart_histories_lih_uniform.json"),
]:
    a = load(analysis_file)
    h = load(hist_file)
    for k, v in a.items():
        print(f"  merging key: {k}")
        slim[k] = v
    for k, v in h.items():
        histories[k] = v

with open(os.path.join(RESULTS_DIR, "analysis.json"), "w") as f:
    json.dump(slim, f, indent=2)
with open(os.path.join(RESULTS_DIR, "restart_histories.json"), "w") as f:
    json.dump(histories, f, indent=2)

print(f"\nFinal molecule keys in analysis.json: {list(slim.keys())}")
