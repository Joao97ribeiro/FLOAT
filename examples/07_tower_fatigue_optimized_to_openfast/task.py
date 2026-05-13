# pylint: disable=no-member  # `src` is the FLOAT package on PYTHONPATH at runtime.
"""Update OpenFAST .dat files (AeroDyn / ElastoDyn) from a FLOAT YAML output.

Reads a WISDEM-generated geometry YAML produced by a previous optimization run
and writes a fresh pair of `.dat` files for AeroDyn and ElastoDyn with the
optimized tower section properties.

Example:
    python examples/07_tower_fatigue_optimized_to_openfast/task.py \\
        --flagfile=examples/07_tower_fatigue_optimized_to_openfast/config.cfg
"""

import os

from absl import app
from absl import flags
from absl import logging

import pyfloat

FLAGS = flags.FLAGS

flags.DEFINE_string(
    "wisdem_files_dir", None,
    "Path to the directory containing necessary FLOAT input files.")
flags.DEFINE_string(
    "geometry_filename", "geometry",
    "Filename of the input geometry YAML in --wisdem_files_dir "
    "(without .yaml).")
flags.DEFINE_string(
    "wisdem_results_dir", None,
    "Path to the directory containing the FLOAT optimization output YAML.")
flags.DEFINE_string(
    "wisdem_yaml_output", None,
    "Filename of the WISDEM-generated geometry YAML inside "
    "--wisdem_results_dir (e.g., opt2_tower.yaml).")
flags.DEFINE_string(
    "openfast_inputs_dir", None,
    "Path to the directory containing OpenFAST input templates.")
flags.DEFINE_string("openfast_aero_filename", "AeroDyn15.dat",
                    "Filename of the AeroDyn template in openfast_inputs_dir.")
flags.DEFINE_string(
    "openfast_elasto_filename", "ElastoDyn_tower.dat",
    "Filename of the ElastoDyn template in openfast_inputs_dir.")

flags.mark_flag_as_required("wisdem_files_dir")
flags.mark_flag_as_required("wisdem_results_dir")
flags.mark_flag_as_required("wisdem_yaml_output")
flags.mark_flag_as_required("openfast_inputs_dir")


def main(_):
    """Update OpenFAST .dat files from a FLOAT-optimized geometry YAML."""
    manager = pyfloat.TowerWisdemManager(
        files_dir=FLAGS.wisdem_files_dir,
        geometry_filename=FLAGS.geometry_filename,
    )
    heights = manager.get_tower_height()

    logging.info("Initiating the update of OpenFAST files.")
    processor = pyfloat.TowerDataProcessor(
        input_directory=FLAGS.wisdem_files_dir,
        output_directory=FLAGS.wisdem_results_dir,
        aero_elasto_dir=FLAGS.openfast_inputs_dir,
        heights=heights,
        geometry_filename=f"{FLAGS.geometry_filename}.yaml",
        aero_filename=FLAGS.openfast_aero_filename,
        elasto_filename=FLAGS.openfast_elasto_filename,
    )
    yaml_path = os.path.join(FLAGS.wisdem_results_dir, FLAGS.wisdem_yaml_output)
    dat_dir = processor.generate_dat_files_from_wisdem_yaml(yaml_path)
    logging.info("OpenFAST .dat files written to: %s", dat_dir)


if __name__ == "__main__":
    logging.set_verbosity(logging.INFO)
    app.run(main)
