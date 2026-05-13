# pylint: disable=no-member
# pylint: disable=import-error
"""Driver that configures and runs FLOAT (WISDEM) tower simulations."""

import os

from typing import Dict, List, Tuple, Any, Optional

import yaml
import wisdem

from . import summary

# Constants for file names
GEOMETRY_FILENAME = "geometry_options.yaml"
MODELING_FILENAME = "modeling_options.yaml"
ANALYSIS_FILENAME = "analysis_options.yaml"


def get_variable_bounds_from_dict(
    variable_data: Dict[str, Any],
    default_unit_keys: Optional[List[str]] = None
) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """
    Extract bounds for design variables or constraints from a dictionary.

    Args:
        variable_data (Dict[str, Any]): Dict from YAML representing 
          either 'design_variables' or 'design_constraints'.
        default_unit_keys (Optional[List[str]]): Keys that receive default
          bounds if not specified.

    Returns:
        Tuple[List[str], Dict[str, Dict[str, float]]]:
            - List of variable names
            - Dictionary mapping each variable to its bounds
    """
    if default_unit_keys is None:
        default_unit_keys = [
            'stress', 'buckling', 'global_buckling', 'shell_buckling', 'taper',
            'slope', 'thickness_slope'
        ]
    bounds = {}

    def determine_bounds(name: str, entry: Dict[str, Any]) -> Dict[str, float]:
        """
        Determine the lower and upper bounds for a given variable.

        Uses defaults for known keys if bounds are not explicitly provided.

        Args:
            name (str): Name of the variable.
            entry (Dict[str, Any]): Dictionary containing the variable's
              properties.

        Returns:
            Dict[str, float]: Dictionary with 'lower_bound' and/or 'upper_bound'
              if available.
        """
        is_default = name in default_unit_keys or any(
            k in name for k in default_unit_keys)
        lower = entry.get('lower_bound', 0.0 if is_default else None)
        upper = entry.get('upper_bound', 1.0 if is_default else None)
        result = {}
        if lower is not None:
            result['lower_bound'] = lower
        if upper is not None:
            result['upper_bound'] = upper
        return result

    for group_data in variable_data.values():
        if isinstance(group_data, list):
            for entry in group_data:
                name = entry.get('name')
                if name:
                    bounds_info = determine_bounds(name, entry)
                    if bounds_info:
                        bounds[name] = bounds_info

        elif isinstance(group_data, dict):
            for name, props in group_data.items():
                if isinstance(props, dict) and props.get('flag', False):
                    bounds_info = determine_bounds(name, props)
                    if bounds_info:
                        bounds[name] = bounds_info

    return list(bounds.keys()), bounds


class TowerWisdemManager:
    """
    Manages configurations and execution of WISDEM tower simulations.
    
    This class provides utilities for reading input configurations, extracting
    tower heights and design constraints, and running WISDEM simulations with
    the specified settings.
    """

    def __init__(self,
                 files_dir: str,
                 geometry_filename=GEOMETRY_FILENAME,
                 modeling_filename=MODELING_FILENAME,
                 analysis_filename=ANALYSIS_FILENAME):
        """
        Initialize TowerWisdemManager with the directory containing input files.

        Args:
            files_dir (str): Path to the directory containing input YAML files.
            geometry_filename (str): Name of the geometry YAML file (without 
              '.yaml').
            modeling_filename (str): Name of the modeling YAML file (without 
              '.yaml').
            analysis_filename (str): Name of the analysis YAML file (ithout 
             '.yaml').
        """
        self.files_dir = files_dir
        self.geometry_filename = geometry_filename
        self.modeling_filename = modeling_filename
        self.analysis_filename = analysis_filename
        self.geometry_file = os.path.join(self.files_dir,
                                          f"{self.geometry_filename}.yaml")
        self.modeling_file = os.path.join(self.files_dir,
                                          f"{self.modeling_filename}.yaml")
        self.analysis_file = os.path.join(self.files_dir,
                                          f"{self.analysis_filename}.yaml")

    def get_tower_height(self) -> List[float]:
        """
        Extracts the tower height values from the geometry YAML file.
        
        Reads the Z-axis values of the tower's reference axis, representing its
        height.

        Returns:
            List[float]: A list of tower height values along the Z-axis.
        """
        with open(self.geometry_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data['components']['tower']['outer_shape_bem']['reference_axis'][
            'z']['values']

    def get_output_folder_and_filename(self) -> tuple[str, str]:
        """
        Retrieve the output folder and output filename.

        Returns:
            Tuple[str, str]: 
                - Output folder path.
                - Output filename (not full path).
        """
        with open(self.analysis_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        folder_output = data.get('general', {}).get('folder_output')
        fname_output = data.get('general', {}).get('fname_output')

        return folder_output, fname_output

    def get_design_constraints(
            self) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
        """
        Load and extract bounds from the 'constraints' section.

        Returns:
            Tuple:
                - List of constraint names.
                - Dictionary mapping each constraint to its lower and upper
                  bounds.
        """
        with open(self.analysis_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        constraints_data = data.get('constraints', {})
        return get_variable_bounds_from_dict(constraints_data)

    def get_design_variables(
            self) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
        """
        Load and extract bounds from the 'design_variables' section.

        Returns:
            Tuple:
                - List of design variable names.
                - Dictionary mapping each variable to its lower and upper
                  bounds.
        """
        with open(self.analysis_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        design_variables_data = data.get('design_variables', {})
        return get_variable_bounds_from_dict(design_variables_data)

    def run_simulation(self,
                       overridden: bool = True,
                       run_only: bool = False,
                       save_summary: bool = False,
                       log_summary: bool = True) -> Tuple[object, dict, dict]:
        """
        Executes the WISDEM simulation using the configured input files.

        Args:
            overridden (bool): If True, overrides hub height to use tower
              reference only.
            run_only (bool): If True, performs a dry run of the simulation
              without saving outputs
            save_summary (bool): If True, saves the JSON summary to the default
              output directory.
            log_summary (bool): If True, logs the summary table after execution.

        Returns:
            Tuple:
                - wt_opt: The optimized WISDEM model object.
                - modeling_options: The loaded modeling configuration.
                - opt_options: The loaded analysis/optimization configuration.
        """
        # Don't enforce a hub-height, just use tower description
        overridden_values = {
            'configuration.hub_height_user': 0.0
        } if overridden else None

        wt_opt, modeling_options, opt_options = wisdem.run_wisdem(
            fname_wt_input=self.geometry_file,
            fname_modeling_options=self.modeling_file,
            fname_opt_options=self.analysis_file,
            overridden_values=overridden_values,
            run_only=run_only)

        summary_extractor = summary.TowerSummaryExtractor(wt_opt)

        if save_summary:
            folder_output, fname_output = self.get_output_folder_and_filename()
            filename = f"{fname_output}_summary.json"
            summary_extractor.save_to_json(json_dir=folder_output,
                                           filename=filename)

        if log_summary:
            summary_extractor.log_summary_table()

        return wt_opt, modeling_options, opt_options
