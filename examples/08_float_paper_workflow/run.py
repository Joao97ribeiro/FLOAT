"""Replicate the FLOAT paper workflow by chaining the existing task CLIs.

Steps (each one calls the corresponding task with the right flags):
  1. examples/03_tower_fatigue_analysis_cli      -> reference (analysis only)
  2. examples/04_tower_fatigue_optimization_cli  -> opt1 optimization
  3. examples/04_tower_fatigue_optimization_cli  -> opt2 optimization
  4. examples/05_tower_fatigue_optimized_comparison    -> overlay of the 3 cases
  5. examples/06_tower_fatigue_optimization_comparison -> opt1 vs opt2 evolution
  6. examples/07_tower_fatigue_optimized_to_openfast   -> OpenFAST .dat export
     for the final (opt2) design

Run from the FLOAT repo root:
    python examples/08_float_paper_workflow/run.py
"""

import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

INPUTS_DIR = "examples/input_files/float_paper"
OPENFAST_INPUTS_DIR = "examples/input_files/22mw_openfast"
OUTPUT_BASE = "outputs/08_float_paper_workflow"


def run_task(task_relpath, flags):
    """Invoke a FLOAT task with the given flags, run from the repo root."""
    args = [sys.executable, str(ROOT / task_relpath)]
    for key, value in flags.items():
        args.append(f"--{key}={value}")
    # Prepend the FLOAT root to PYTHONPATH so the task's `import pyfloat`
    # resolves to FLOAT's package even when another `pyfloat/` is on sys.path.
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT),
                                         env.get("PYTHONPATH",
                                                 "")]).rstrip(os.pathsep)
    print(f"\n>>> {' '.join(args)}")
    subprocess.run(args, cwd=str(ROOT), env=env, check=True)


# Step 1: Reference (analysis only).
run_task(
    "examples/03_tower_fatigue_analysis_cli/task.py",
    {
        "files_dir": INPUTS_DIR,
        "geometry_filename": "IEA-22-280-RWT",
        "modeling_filename": "modeling_options_tower_fatigue_ref",
        "analysis_filename": "analysis_options_tower_fatigue_ref",
        "save_summary": "True",
        "log_summary": "True",
        "save_plot": "True",
    },
)

# Step 2: Opt1 optimization. Always starts from the ref geometry
# (IEA-22-280-RWT); modeling=ref means FLOAT scales damage against the ref
# tower. The opt1 analysis defines the constraints + design variables.
run_task(
    "examples/04_tower_fatigue_optimization_cli/task.py",
    {
        "files_dir": INPUTS_DIR,
        "geometry_filename": "IEA-22-280-RWT",
        "modeling_filename": "modeling_options_tower_fatigue_ref",
        "analysis_filename": "analysis_options_tower_fatigue_opt1",
        "save_summary": "True",
        "log_summary": "True",
        "save_plot": "True",
        "export_to_openfast": "False",
    },
)

# Step 3: Opt2 optimization (final design). Same ref starting geometry, but
# modeling=opt1 so FLOAT now scales damage against the opt1 tower (closer
# reference -> more accurate scaling). The opt2 analysis tightens the
# constraints accordingly.
run_task(
    "examples/04_tower_fatigue_optimization_cli/task.py",
    {
        "files_dir": INPUTS_DIR,
        "geometry_filename": "IEA-22-280-RWT",
        "modeling_filename": "modeling_options_tower_fatigue_opt1",
        "analysis_filename": "analysis_options_tower_fatigue_opt2",
        "save_summary": "True",
        "log_summary": "True",
        "save_plot": "True",
        "export_to_openfast": "False",
    },
)

# Step 4: Compare the three designs (overlay plots + JSON summary).
REF_CSV = f"{OUTPUT_BASE}/ref/ref_tower.csv"
OPT1_CSV = f"{OUTPUT_BASE}/opt1/opt1_tower.csv"
OPT2_CSV = f"{OUTPUT_BASE}/opt2/opt2_tower.csv"
run_task(
    "examples/05_tower_fatigue_optimized_comparison/task.py",
    {
        "output_dir": f"{OUTPUT_BASE}/tower_comparison_results",
        "csv_paths": f"{REF_CSV},{OPT1_CSV},{OPT2_CSV}",
        "labels": "Reference,Opt1,Opt2",
        "ref_idx": "0",
        "files_dir": INPUTS_DIR,
        "analysis_filename": "analysis_options_tower_fatigue_opt2",
        "save_summary": "True",
        "log_summary": "True",
    },
)

# Step 5: Compare the two optimization processes (opt1 vs opt2 convergence).
OPT1_SQL = f"{OUTPUT_BASE}/opt1/log_opt.sql"
OPT2_SQL = f"{OUTPUT_BASE}/opt2/log_opt.sql"
run_task(
    "examples/06_tower_fatigue_optimization_comparison/task.py",
    {
        "output_dir": f"{OUTPUT_BASE}/tower_optimization_results",
        "sql_paths": f"{OPT1_SQL},{OPT2_SQL}",
        "csv_paths": f"{OPT1_CSV},{OPT2_CSV}",
        "labels": "Opt1,Opt2",
        "files_dir": INPUTS_DIR,
        "analysis_filename": "analysis_options_tower_fatigue_opt2",
    },
)

# Step 6: Export opt2 design to OpenFAST .dat files (via 07_).
run_task(
    "examples/07_tower_fatigue_optimized_to_openfast/task.py",
    {
        "wisdem_files_dir": INPUTS_DIR,
        "geometry_filename": "IEA-22-280-RWT",
        "wisdem_results_dir": f"{OUTPUT_BASE}/opt2",
        "wisdem_yaml_output": "opt2_tower.yaml",
        "openfast_inputs_dir": OPENFAST_INPUTS_DIR,
        "openfast_aero_filename": "IEA-22-280-RWT-Semi_AeroDyn15.dat",
        "openfast_elasto_filename": "IEA-22-280-RWT-Semi_ElastoDyn_tower.dat",
    },
)

print(f"\nFull workflow outputs under: {ROOT / OUTPUT_BASE}")
