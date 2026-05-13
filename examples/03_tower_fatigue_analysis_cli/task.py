"""Generic CLI runner for FLOAT tower simulations.

Wraps `pyfloat.TowerWisdemManager` so any analysis or optimization case can be
launched from the command line by pointing to a directory of input YAMLs.

Example:
    python examples/03_tower_fatigue_analysis_cli/task.py \\
        --flagfile=examples/03_tower_fatigue_analysis_cli/config.cfg
"""

from absl import app
from absl import flags
from absl import logging

import pyfloat

FLAGS = flags.FLAGS

# General flags
flags.DEFINE_string(
    "files_dir", None,
    "Path to the directory containing all necessary FLOAT input files.")

# Files flags (filenames without the .yaml extension)
flags.DEFINE_string("geometry_filename", "geometry",
                    "Name of the geometry YAML file (without .yaml).")
flags.DEFINE_string("modeling_filename", "modeling",
                    "Name of the modeling YAML file (without .yaml).")
flags.DEFINE_string("analysis_filename", "analysis",
                    "Name of the analysis YAML file (without .yaml).")

# Simulation behavior flags
flags.DEFINE_boolean(
    "overridden", True,
    "If True, overrides hub height to use tower reference only.")
flags.DEFINE_boolean(
    "run_only", False,
    "If True, performs a dry run of the simulation without saving outputs.")
flags.DEFINE_boolean(
    "save_summary", True,
    "If True, saves a summary JSON file to the output directory.")
flags.DEFINE_boolean("log_summary", True,
                     "If True, logs the summary table after execution.")
flags.DEFINE_boolean(
    "save_plot", True,
    "If True, save all tower profile plots (geometry+damage, stress+buckling, "
    "deflection).")
flags.DEFINE_string(
    "output_dir", None,
    "Output directory for plots. Defaults to general.folder_output from the "
    "analysis YAML.")

flags.mark_flag_as_required("files_dir")


def main(_):
    """Execute the FLOAT tower analysis and optionally plot the result."""
    logging.info("Starting FLOAT tower simulation...")
    manager = pyfloat.TowerWisdemManager(
        files_dir=FLAGS.files_dir,
        geometry_filename=FLAGS.geometry_filename,
        modeling_filename=FLAGS.modeling_filename,
        analysis_filename=FLAGS.analysis_filename)
    wt_opt, _, _ = manager.run_simulation(overridden=FLAGS.overridden,
                                          run_only=FLAGS.run_only,
                                          save_summary=FLAGS.save_summary,
                                          log_summary=FLAGS.log_summary)
    if FLAGS.save_plot:
        output_dir = FLAGS.output_dir or manager.get_output_folder_and_filename(
        )[0]
        pyfloat.plot_all_profiles(wt_opt, output_dir)
        logging.info("Saved tower profile plots to: %s/plots", output_dir)

    logging.info("FLOAT tower simulation completed successfully.")


if __name__ == "__main__":
    logging.set_verbosity(logging.INFO)
    app.run(main)
