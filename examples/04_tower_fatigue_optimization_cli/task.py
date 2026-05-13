"""CLI runner for FLOAT tower fatigue optimization with plot output.

Same as `tasks/run_wisdem/task.py` but also calls `src.plot_tower_profiles`
with the design variable + constraint bounds recovered from the analysis YAML.

Example:
    python examples/04_tower_fatigue_optimization_cli/task.py \\
        --flagfile=examples/04_tower_fatigue_optimization_cli/config.cfg
"""

import os

from absl import app
from absl import flags
from absl import logging

import src

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
    "deflection) with design bounds.")
flags.DEFINE_boolean(
    "export_to_openfast", False,
    "If True, regenerate OpenFAST .dat files (AeroDyn/ElastoDyn) "
    "from the optimized tower geometry. Requires --openfast_inputs_dir.")
flags.DEFINE_string(
    "openfast_inputs_dir", None,
    "Path to the directory with OpenFAST input templates to update. "
    "Used only when --export_to_openfast=True.")
flags.DEFINE_string(
    "output_dir", None,
    "Output directory for plots and exports. Defaults to "
    "general.folder_output from the analysis YAML.")
flags.DEFINE_string("openfast_aero_filename", "AeroDyn15.dat",
                    "Filename of the AeroDyn template in openfast_inputs_dir.")
flags.DEFINE_string(
    "openfast_elasto_filename", "ElastoDyn_tower.dat",
    "Filename of the ElastoDyn template in openfast_inputs_dir.")

flags.mark_flag_as_required("files_dir")


def main(_):
    """Execute the FLOAT tower optimization, plot, and optionally export."""
    logging.info("Starting FLOAT tower simulation...")
    manager = src.TowerWisdemManager(files_dir=FLAGS.files_dir,
                                     geometry_filename=FLAGS.geometry_filename,
                                     modeling_filename=FLAGS.modeling_filename,
                                     analysis_filename=FLAGS.analysis_filename)
    wt_opt, _, _ = manager.run_simulation(overridden=FLAGS.overridden,
                                          run_only=FLAGS.run_only,
                                          save_summary=FLAGS.save_summary,
                                          log_summary=FLAGS.log_summary)
    output_dir = FLAGS.output_dir or manager.get_output_folder_and_filename()[0]

    if FLAGS.save_plot:
        _, dv_bounds = manager.get_design_variables()
        _, constraint_bounds = manager.get_design_constraints()
        bounds = {**dv_bounds, **constraint_bounds}
        src.plot_all_profiles(wt_opt, output_dir, bounds=bounds)
        logging.info("Saved tower profile plots to: %s/plots", output_dir)

        sql_path = os.path.join(output_dir, "log_opt.sql")
        if os.path.exists(sql_path):
            optim_plots_dir = os.path.join(output_dir, "plots", "optimization")
            sql_reader = src.TowerOptimizationResultsSQLReader(
                sql_path, optim_plots_dir)
            sql_reader.plot_all(constraints_bounds=constraint_bounds)
            logging.info("Saved optimization evolution plots to: %s",
                         optim_plots_dir)

    if FLAGS.export_to_openfast:
        if not FLAGS.openfast_inputs_dir:
            raise ValueError(
                "--openfast_inputs_dir is required when "
                "--export_to_openfast=True")
        logging.info("Exporting tower geometry to OpenFAST .dat files...")
        heights = manager.get_tower_height()
        processor = src.TowerDataProcessor(
            input_directory=FLAGS.files_dir,
            output_directory=output_dir,
            aero_elasto_dir=FLAGS.openfast_inputs_dir,
            heights=heights,
            geometry_filename=f"{FLAGS.geometry_filename}.yaml",
            aero_filename=FLAGS.openfast_aero_filename,
            elasto_filename=FLAGS.openfast_elasto_filename,
        )
        dat_dir = processor.generate_dat_files_from_wt_opt(wt_opt)
        logging.info("OpenFAST .dat files written to: %s", dat_dir)

    logging.info("FLOAT tower simulation completed successfully.")


if __name__ == "__main__":
    logging.set_verbosity(logging.INFO)
    app.run(main)
