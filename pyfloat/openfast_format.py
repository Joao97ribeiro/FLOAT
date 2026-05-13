# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=possibly-used-before-assignment
"""Update OpenFAST AeroDyn/ElastoDyn .dat files from FLOAT tower geometries."""

from typing import List, Tuple
import json
import math
import os
import re
import numpy as np
import pandas as pd
import yaml


def _safe_load_wisdem_yaml(path):
    """Load a WISDEM-emitted YAML, quoting unquoted URLs in flow mappings.

    WISDEM occasionally writes inline (flow-style) mappings with unquoted URL
    values whose '?' query string breaks PyYAML. We quote `source: http...`
    values before parsing.
    """
    with open(path, "r", encoding="utf-8") as file:
        text = file.read()
    text = re.sub(r"(source:\s*)(https?://[^,}\n]+)",
                  lambda m: f'{m.group(1)}"{m.group(2).rstrip()}"', text)
    return yaml.safe_load(text)


RESULTS_OUTPUTS_CONSTRAINED_CSV_FILENAME = "log_opt_outputs_constrain.csv"
GEOMETRY_FILENAME = "geometry_options.yaml"
AERO_DYN_FILENAME = "AeroDyn15.dat"
ELASTO_DYN_FILENAME = "ElastoDyn_tower.dat"


class TowerDataProcessor:
    """
    Generates AeroDyn and ElastoDyn files from tower geometry.

    This class handles the generation of AeroDyn and ElastoDyn `.dat` files
    for tower configurations based on input geometry, templates, and
    configuration data. It processes a CSV containing tower parameters and
    applies modifications using the provided heights and diameter data.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(self,
                 input_directory: str,
                 output_directory: str,
                 aero_elasto_dir: str,
                 heights: list,
                 geometry_filename: str = GEOMETRY_FILENAME,
                 aero_filename: str = AERO_DYN_FILENAME,
                 elasto_filename: str = ELASTO_DYN_FILENAME):
        """
        Initializes the TowerDataProcessor.

        The CSV at ``constrained_outputs/log_opt_outputs_constrain.csv`` is
        loaded lazily, so this constructor works even when the CSV does not
        exist (useful for the wt_opt-based code path).

        Args:
            input_directory (str): Path to directory containing input geometry
              files.
            output_directory (str): Path to directory where generated .dat files
              will be saved.
            aero_elasto_dir (str): Path to directory containing AeroDyn and
              ElastoDyn templates.
            heights (list): Array of tower section heights used for generating
              .dat files.
            geometry_filename (str): Filename of the geometry YAML inside
              `input_directory`. Defaults to GEOMETRY_FILENAME.
            aero_filename (str): Filename of the AeroDyn template inside
              `aero_elasto_dir`. Defaults to AERO_DYN_FILENAME.
            elasto_filename (str): Filename of the ElastoDyn template inside
              `aero_elasto_dir`. Defaults to ELASTO_DYN_FILENAME.
        """
        self.output_directory = output_directory
        self.results_csv_path = os.path.join(
            self.output_directory, "constrained_outputs",
            RESULTS_OUTPUTS_CONSTRAINED_CSV_FILENAME)
        self.aero_path = os.path.join(aero_elasto_dir, aero_filename)
        self.elasto_path = os.path.join(aero_elasto_dir, elasto_filename)
        self.geometry_file = os.path.join(input_directory, geometry_filename)
        self.heights = heights
        self._data = None

    @property
    def data(self):
        """Lazily load the constrained-results CSV when first accessed."""
        if self._data is None:
            self._data = pd.read_csv(self.results_csv_path).iloc[1:]
        return self._data

    def create_output_folder(self, idx: int) -> str:
        """
        Creates a folder for the output files if it doesn't exist.

        Args:
            idx (int): Index of the current row in the CSV.

        Returns:
            str: Path to the created folder.
        """
        folder_name = os.path.join(self.output_directory,
                                   f"Constrained_Tower_{idx}")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        return folder_name

    def generate_aero_elasto_dyn_file(self, folder_name, diameter_array,
                                      thick_array):
        """
        Generates the AeroDyn and ElastoDyn `.dat` file.

        Args:
            folder_name (str): Folder to save the generated file.
            diameter_array (np.array): Tower diameter data.
            thick_array (np.array): Tower layer thickness data.
        """
        output_file_aero = os.path.join(folder_name, "AeroDyn15.dat")
        output_file_elasto = os.path.join(folder_name, "ElastoDyn_tower.dat")
        tower_config = (self.geometry_file, self.aero_path, self.elasto_path,
                        diameter_array, thick_array)
        modifier = TowerModifier(
            tower_config=tower_config,
            output_file_path=(output_file_aero, output_file_elasto),
            heights_array=self.heights,
        )
        modifier.update_tower_data_in_aerodyn()
        modifier.update_tower_data_in_elastodyn_tower()

    def generate_dat_files(self):
        """
        Updates OpenFAST files for each geometry using template files.

        Iterates over the rows in the constrained-results CSV (each row is one
        design that survived the constraints filter) and writes a fresh pair of
        .dat files per design under ``Constrained_Tower_<idx>/``.
        """
        for idx, row in self.data.iterrows():
            diameter_array = np.array(
                json.loads(row['wt.wt_prop.wt_init.tower.diameter']))
            thick_array = np.array(
                json.loads(row['wt.wt_prop.wt_init.tower.layer_thickness']))
            folder_name = self.create_output_folder(idx)

            self.generate_aero_elasto_dyn_file(folder_name, diameter_array,
                                               thick_array)

    def generate_dat_files_from_wisdem_yaml(self,
                                            wisdem_yaml_path,
                                            folder_name=None):
        """
        Generate OpenFAST .dat files from a WISDEM-generated geometry YAML.

        Reads the optimized diameter and layer thickness arrays directly from
        the YAML output that WISDEM writes after running (`<output>/X.yaml`).
        Material properties (steel rho/E) are also read from that same YAML.

        Args:
            wisdem_yaml_path (str): Path to the WISDEM-generated geometry YAML.
            folder_name (str, optional): Destination folder for the .dat files.

        Returns:
            str: Path to the folder containing the generated .dat files.
        """
        data = _safe_load_wisdem_yaml(wisdem_yaml_path)

        tower = data["components"]["tower"]
        diameter_array = np.asarray(
            tower["outer_shape_bem"]["outer_diameter"]["values"], dtype=float)
        thick_array = np.atleast_2d([
            layer["thickness"]["values"]
            for layer in tower["internal_structure_2d_fem"]["layers"]
        ])

        # The optimized YAML also contains the materials section, so use it as
        # the geometry file so TowerModifier reads the matching rho/E.
        self.geometry_file = wisdem_yaml_path

        if folder_name is None:
            folder_name = os.path.join(self.output_directory,
                                       "tower_optimized_openfast")
        os.makedirs(folder_name, exist_ok=True)

        self.generate_aero_elasto_dyn_file(folder_name, diameter_array,
                                           thick_array)
        return folder_name

    def generate_dat_files_from_wt_opt(self, wt_opt, folder_name=None):
        """
        Update OpenFAST .dat files directly from a WISDEM wt_opt object.

        Bypasses the CSV-based pipeline. The optimized tower diameter and layer
        thickness are read from `wt_opt` in-memory, and a single set of .dat
        files is written under `folder_name` (defaults to
        ``<output_directory>/Optimized_Tower/``).

        Args:
            wt_opt: WISDEM problem object returned by ``run_wisdem``.
            folder_name (str, optional): Destination folder for the .dat files.

        Returns:
            str: Path to the folder containing the generated .dat files.
        """
        diameter_array = np.asarray(
            wt_opt.get_val("towerse.tower_outer_diameter")).flatten()
        # Layer thickness is expected as 2D (n_layers, n_sections); for a
        # single-layer steel tower the array shape is (1, n_sections).
        thick_array = np.atleast_2d(
            wt_opt.get_val("towerse.tower_wall_thickness"))

        if folder_name is None:
            folder_name = os.path.join(self.output_directory,
                                       "tower_optimized_openfast")
        os.makedirs(folder_name, exist_ok=True)

        self.generate_aero_elasto_dyn_file(folder_name, diameter_array,
                                           thick_array)
        return folder_name


class TowerModifier:
    """
    Modifies tower configs and .dat files for analysis.

    The `TowerModifier` class provides functionality to update tower
    configuration files and perform calculations related to tower geometry,
    material properties, and dynamic properties. It supports updating node
    heights, diameters, mass densities, and stiffness values based on input data
    and material parameters.
    """

    def __init__(self, tower_config: tuple, output_file_path: tuple,
                 heights_array: np.ndarray):
        """
        Initializes the TowerModifierBoth.

        Args:
            tower_config (tuple): Contains the file paths and data for
              modification.
            output_file_path (tuple): The file paths where the updated .dat
              files will be saved.
            heights_array (numpy.ndarray, optional): Array of tower heights. 
        """

        self.geometry_file_path = tower_config[0]
        self.aero_dat_file_path = tower_config[1]
        self.elasto_dat_file_path = tower_config[2]
        self.tower_data = {
            "diameter": tower_config[3],
            "thickness": tower_config[4],
            "height": heights_array
        }

        self.aero_file_path = output_file_path[0]
        self.elasto_file_path = output_file_path[1]

        data = _safe_load_wisdem_yaml(self.geometry_file_path)

        materials = data['materials']
        steel_material = next(
            (mat for mat in materials if mat['name'] == 'steel'), None)

        if steel_material:
            self.rho_steel = steel_material['rho']
            self.e_steel = steel_material['E']
        else:
            raise ValueError("Steel material not found in the materials list.")

        self.num_twr_nodes = len(self.tower_data["diameter"])

    def calculate_tmassden(self, material_density: float, outer_diameter: float,
                           thickness: float) -> float:
        """
        Computes linear mass density of a cylinder.

        Args:
            material_density (float): The density of the material (kg/m^3).
            outer_diameter (float): The outer diameter of the cylindrical
              section (m).
            thickness (float): The wall thickness of the cylindrical section
              (m).

        Returns:
            float: The linear mass density of the section (kg/m).
        """
        return material_density * math.pi * (outer_diameter * thickness -
                                             thickness**2)

    def calculate_twstiff(self, youngs_modulus: float, outer_diameter: float,
                          thickness: float) -> float:
        """
        Calculate the stiffness of a cylindrical section.

        Args:
            youngs_modulus (float): Young's modulus of the material (Pa).
            outer_diameter (float): Outer diameter of the cylindrical section 
              (m).
            thickness (float): Wall thickness of the cylindrical section (m).

        Returns:
            float: The stiffness of the section (N·m^2).
        """
        return youngs_modulus * (math.pi / 8) * (
            outer_diameter**3 * thickness - 3 * outer_diameter**2 * thickness**2
            + 4 * outer_diameter * thickness**3 - 2 * thickness**4)

    def normalize_heights(self, heights: list[float]) -> list[float]:
        """
        Normalizes the given height values to a range of 0 to 1.

        Args:
            heights (List[float]): A list of height values to be normalized.

        Returns:
            List[float]: A list of normalized height values, scaled between 0
              and 1.
        """
        min_height = min(heights)
        max_height = max(heights)
        return [(h - min_height) / (max_height - min_height) for h in heights]

    def calculate_tmassden_and_twstiff_all_sections(
            self) -> Tuple[List[float], List[float]]:
        """
        Calculates mass density and stiffness for each tower section.

        Returns:
            tuple:
                - mass_densities (List[float]): The mass densities for each
                  tower section (kg/m^3).
                - stiffnesses (List[float]): The stiffness values for each tower
                  section (N/m).
        """
        mass_density_all_sections = []
        stiffness_all_sections = []
        for outer_diameter, thickness in\
            zip(self.tower_data["diameter"], self.tower_data["thickness"][0]):
            mass_density_all_sections.append(
                self.calculate_tmassden(self.rho_steel, outer_diameter,
                                        thickness))
            stiffness_all_sections.append(
                self.calculate_twstiff(self.e_steel, outer_diameter, thickness))
        return mass_density_all_sections, stiffness_all_sections

    def update_tower_data_in_aerodyn(self):
        """
        Updates the TwrElev, TwrDiam sections, and NumTwrNds in the .dat file.
        """
        with open(self.aero_dat_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if "TwrElev" in line and "TwrDiam" in line:
                start_index = i + 2
            if "======  Outputs" in line:
                outputs_index = i
                break
            # Update NumTwrNds in the file
            if "NumTwrNds" in line:
                parts = line.split()
                parts[0] = str(self.num_twr_nodes)
                lines[i] = " ".join(parts) + "\n"

        normalize_heights_all_sections = self.normalize_heights(
            self.tower_data["height"])

        # Updates the values of TwrElev and TwrDiam
        for index, diameter in enumerate(self.tower_data["diameter"]):
            current_line_index = start_index + index
            if current_line_index < len(lines):
                original_line = lines[start_index + index]
                line_parts = original_line.split()

                height = normalize_heights_all_sections[index]

                leading_whitespace = original_line[:len(original_line) -
                                                   len(original_line.lstrip())]
                new_line = (
                    f"{leading_whitespace}{height:.15e} {diameter:.15e} "
                    f"{' '.join(line_parts[2:])}\n")

                lines[current_line_index] = new_line

        # Calculates the index where the updated tower data ends
        end_index = start_index + self.num_twr_nodes

        if end_index < outputs_index:
            #Removes extra lines between the end of the updated data and the
            # output index
            lines = lines[:end_index] + lines[outputs_index:]

        # Writes the updated content to the file
        with open(self.aero_file_path, 'w', encoding="utf-8") as file:
            file.writelines(lines)

    def update_tower_data_in_elastodyn_tower(self):
        """
            Updates the TwFAStif, TwSSStif, HtFract sections
            and NTwInpSt in the .dat file.
        """

        with open(self.elasto_dat_file_path, 'r', encoding="utf-8") as file:
            lines = file.readlines()


        mass_density_all_sections, stiffness_all_sections =\
            self.calculate_tmassden_and_twstiff_all_sections()
        normalize_heights_all_sections = self.normalize_heights(
            self.tower_data["height"])

        for i, line in enumerate(lines):
            if "TwFAStif" in line and "TwSSStif" in line and "HtFract" in line:
                start_index = i + 2
            if ("---------------------- TOWER FORE-AFT MODE SHAPES -----------"
                    in line):
                outputs_index = i
                break

            # Update NTwInpSt in the file
            if "NTwInpSt" in line:
                parts = line.split()
                parts[0] = str(self.num_twr_nodes)
                lines[i] = " ".join(parts) + "\n"

        for index, (htfract, tmassden, twstif) in\
            enumerate(zip(normalize_heights_all_sections ,
            mass_density_all_sections, stiffness_all_sections)):
            current_line_index = start_index + index
            if current_line_index < len(lines):

                original_line = lines[current_line_index]
                leading_whitespace = original_line[:len(original_line) -
                                                   len(original_line.lstrip())]

                lines[current_line_index] = (
                    f"{leading_whitespace}{htfract:.15e}  {tmassden:.15e} "
                    f"{twstif:.15e}  {twstif:.15e} \n")

        # Calculates the index where the updated tower data ends
        end_index = start_index + self.num_twr_nodes

        if end_index < outputs_index:
            #Removes extra lines between the end of the updated data and the
            # output index
            lines = lines[:end_index] + lines[outputs_index:]

        # Writes the updated content to the file
        with open(self.elasto_file_path, 'w', encoding="utf-8") as file:
            file.writelines(lines)
