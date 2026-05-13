"""Analyze FLOAT tower optimization results.

Builds the constraint bounds from the analysis YAML and produces a single
combined comparison (plots) for the optimization runs listed via --sql_paths
and --csv_paths (matching order).

Example:
    python examples/06_tower_fatigue_optimization_comparison/task.py \\
        --flagfile=examples/06_tower_fatigue_optimization_comparison/config.cfg
"""

from absl import app
from absl import flags
from absl import logging

import src

FLAGS = flags.FLAGS

# General flags
flags.DEFINE_string("output_dir", None, "Folder to save output files.")

# Results flags
flags.DEFINE_list("sql_paths", None,
                  "Path to the FLOAT-generated SQL output files.")
flags.DEFINE_list("csv_paths", None,
                  "Path to the FLOAT-generated CSV output files.")
flags.DEFINE_list("labels", None, "Custom labels for the tower cases.")

# Constraints flags
flags.DEFINE_string(
    "files_dir", None,
    "Path to the directory containing all necessary FLOAT input files.")
flags.DEFINE_string("analysis_filename", None,
                    "Name of the analysis YAML file (without .yaml).")

# Plot flags
flags.DEFINE_bool("save_svg", False, "If True, saves plots as SVG files.")

flags.mark_flag_as_required("output_dir")
flags.mark_flag_as_required("files_dir")
flags.mark_flag_as_required("analysis_filename")
flags.mark_flag_as_required("sql_paths")
flags.mark_flag_as_required("csv_paths")
flags.mark_flag_as_required("labels")


def main(_):
    """Analyze results from one or more FLOAT tower optimizations."""
    manager = src.TowerWisdemManager(files_dir=FLAGS.files_dir,
                                     analysis_filename=FLAGS.analysis_filename)
    _, constraints_bounds = manager.get_design_constraints()

    logging.info("Starting analysis of FLOAT tower optimization results...")

    results_reader = src.TowerOptimizationResultsComparator(
        sql_paths=FLAGS.sql_paths,
        csv_paths=FLAGS.csv_paths,
        labels=FLAGS.labels,
        output_dir=FLAGS.output_dir)
    results_reader.plot_all(constraints_bounds=constraints_bounds,
                            save_svg=FLAGS.save_svg)

    logging.info("FLOAT tower optimization analysis completed successfully.")


if __name__ == "__main__":
    logging.set_verbosity(logging.INFO)
    app.run(main)
