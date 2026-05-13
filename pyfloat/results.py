# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=import-error
# pylint: disable=no-member
"""Process FLOAT tower simulation results (CSV/SQL) for export and plotting."""

import os
import ast
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import gridspec
import openmdao.api as om

# Mapping of internal constraint names to human-readable
CONSTRAINT_LABELS = {
    "stress": "Stress Ratio",
    "global_buckling": "Global Buckling Ratio",
    "shell_buckling": "Shell Buckling Ratio",
    "d_to_t": "Diameter-to-Thickness Ratio",
    "taper": "Taper Ratio",
    "slope": "Diameter Slope",
    "thickness_slope": "Thickness Slope",
    "frequency_1": "First Natural Frequency",
    "towerse.fatigue_section_damage": "Fatigue Damage",
}

# Mapping of internal objective function names to human-readable
OBJECTIVE_FUNC_LABELS = {
    "towerse.tower_mass": "Tower Mass (t)",
}


class TowerResultsCSVReader:
    """
    Read and extract structured tower results from a WISDEM-generated CSV file.
    
    This reader loads a CSV file typically produced after a tower performance 
    or structural simulation, enabling further processing, visualization, 
    or export of relevant results.

    Attributes:
        csv_path (str): Path to the WISDEM output CSV file.
        df (pd.DataFrame): DataFrame containing all CSV data.
        output_dir (str): Directory where additional outputs (plots, exports)
          can be saved.
    """

    def __init__(self, csv_path: str, output_dir: str = None):
        """
        Initialize the reader and load the CSV into memory.

        Args:
            csv_path (str): Path to the WISDEM output CSV file.
            output_dir (str, optional): Directory to store outputs. Defaults to
              CSV file's directory.
        """
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.output_dir = output_dir or os.path.dirname(self.csv_path)

    def get_variable(self, var_name: str) -> Optional[Any]:
        """
        Retrieve and parse a variable from the CSV.

        Args:
            var_name (str): The variable name to search for.

        Returns:
            Parsed value (float, array, or string), or None if not found.
        """
        matches = self.df.loc[self.df["variables"] == var_name, "values"].values
        if len(matches) == 0:
            return None

        value = matches[0]
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            try:
                parsed = float(value)
            except ValueError:
                return value

        return np.array(parsed) if isinstance(parsed, (list, tuple)) else parsed

    def get_geometry_profile(self) -> pd.DataFrame:
        """
        Extract typical geometric tower profile.
        
        Returns:
            Dict[str, np.ndarray]: Dictionary with:
                - 'z': corrected height (m)
                - 'z_mean_section': midpoints between thickness segments (m)
                - 'z': corrected height (m)
                - 'outer_diameter': outer diameter (m)
                - 'wall_thickness': wall thickness (m)
        """

        z = self.get_variable("towerse.z_param")
        outer_diameter = self.get_variable("towerse.tower_outer_diameter")
        wall_thickness = self.get_variable("towerse.tower_wall_thickness")
        z_start = self.get_variable("towerse.z_start")

        z_corrected = z - z_start
        z_mean_section = (z_corrected[:-1] + z_corrected[1:]) / 2

        return {
            "z": z_corrected,
            "z_mean_section": z_mean_section,
            "outer_diameter": outer_diameter,
            "wall_thickness": wall_thickness
        }

    def get_stress_profile(self) -> Dict[str, np.ndarray]:
        """
        Extract geometric profile of the tower.

        Returns:
            Dict[str, np.ndarray]: Dictionary with:
                - 'z_midpoints': midpoints between vertical nodes (m)
                - 'stress': axial stress at each section (Pa)
        """
        z_full = self.get_variable("towerse.z_full")
        stress = self.get_variable("towerse.post.axial_stress")

        z_midpoints = (z_full[:-1] + z_full[1:]) / 2

        return {"z_midpoints": z_midpoints, "stress": stress}

    def get_damage_profile(self) -> Dict[str, np.ndarray]:
        """
        Extract fatigue damage profile.

        Returns:
            Dict[str, np.ndarray]: Dictionary with keys:
                - 'z_mean_section': vertical positions along the tower (m)
                - 'section_damage': fatigue damage per section
        """
        z_mean_section = self.get_variable("towerse.fatigue_z")
        damage = self.get_variable("towerse.fatigue_section_damage")

        return {"z_mean_section": z_mean_section, "section_damage": damage}

    def get_deflection_profile(self) -> Dict[str, np.ndarray]:
        """
        Extract tower deflection profile.

        Returns:
            Dict[str, np.ndarray]: Dictionary with keys:
                - 'z_full': full vertical coordinate along the tower (m)
                - 'deflection': lateral displacement at each point (m)

        Raises:
            ValueError: If required variables are missing in the CSV.
        """
        z_full = self.get_variable("towerse.z_full")
        deflection = self.get_variable("towerse.tower.tower_deflection")

        return {"z_full": z_full, "deflection": deflection}

    def get_buckling_profile(self) -> Dict[str, np.ndarray]:
        """
        Extract shell and global buckling profiles along the tower.

        Returns:
            Dict[str, np.ndarray]: Dictionary with:
                - 'z_midpoints': midpoints along the tower height (m)
                - 'shell_buckling': shell buckling constraint values
                - 'global_buckling': global buckling constraint values

        Raises:
            ValueError: If required variables are missing in the CSV.
        """
        z_full = self.get_variable("towerse.z_full")
        shell_buckling = self.get_variable("towerse.post.constr_shell_buckling")
        global_buckling = self.get_variable(
            "towerse.post.constr_global_buckling")

        z_midpoints = (z_full[:-1] + z_full[1:]) / 2

        return {
            "z_midpoints": z_midpoints,
            "shell_buckling": shell_buckling,
            "global_buckling": global_buckling
        }

    def get_structural_profile(self) -> Dict[str, np.ndarray]:
        """
        Retrieve the structural tower profile used in .dat files.

        Returns:
            Dict[str, np.ndarray]: Dictionary with:
                - 'sec_loc': relative height locations (-)
                - 'mass_den': mass density distribution (kg/m)
                - 'foreaft_stff': fore-aft stiffness distribution (Nm^2)
                - 'sideside_stff': side-to-side stiffness distribution (Nm^2)
        """
        sec_loc = self.get_variable("towerse.member.sec_loc")
        mass_den = self.get_variable("towerse.member.mass_den")
        foreaft_stff = self.get_variable("towerse.member.foreaft_stff")
        sideside_stff = self.get_variable("towerse.member.sideside_stff")

        return {
            "sec_loc": sec_loc,
            "mass_den": mass_den,
            "foreaft_stff": foreaft_stff,
            "sideside_stff": sideside_stff
        }

    def get_mode_shapes(self, n_modes: int = None) -> Dict[str, np.ndarray]:
        """
        Get mode shape coefficients for fore-aft and side-side modes.

        Args:
            n_modes (int, optional): Number of modes to return (must be 1, 2, or
              3). If None, returns all.

        Returns:
            Dict[str, np.ndarray]: Dictionary with:
                - 'fore_aft': array (n_modes x 5) of fore-aft mode coefficients
                - 'side_side': array (n_modes x 5) of side-to-side mode
                  coefficients
                
        Raises:
            ValueError: If n_modes is not None and not in [1, 2, 3].
        """
        if n_modes is not None and (n_modes < 1 or n_modes > 3):
            raise ValueError("n_modes must be 1, 2, or 3")

        fore_aft = self.get_variable("towerse.tower.fore_aft_modes")
        side_side = self.get_variable("towerse.tower.side_side_modes")

        fore_aft_modes = np.array(fore_aft)
        side_side_modes = np.array(side_side)

        if n_modes is not None:
            fore_aft_modes = fore_aft_modes[:n_modes]
            side_side_modes = side_side_modes[:n_modes]

        return {"fore_aft": fore_aft_modes, "side_side": side_side_modes}


class TowerOptimizationResultsSQLReader:
    """
    Read and visualize WISDEM tower optimization results from an SQL file.

    This class initializes an OpenMDAO CaseReader for accessing the 
    recorded optimization data, and prepares a directory to store 
    plots or exported results.

    Attributes:
        sql_path (str): Path to the OpenMDAO .sql output file.
        output_dir (str): Directory to store output files (plots, CSVs, etc.).
        cr (CaseReader): OpenMDAO CaseReader object for accessing recorded
          cases.
    """

    def __init__(self, sql_path: str, output_dir: str = None):
        """
        Initialize the SQL results reader and prepare the output directory.

        Args:
            sql_path (str): Path to the WISDEM-generated SQL output file.
            output_dir (str, optional): Folder to save output files. 
                                           Defaults to the SQL file's directory.
        """
        self.sql_path = sql_path
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(self.sql_path), "tower_optimization_results")
        os.makedirs(self.output_dir, exist_ok=True)
        self.cr = om.CaseReader(sql_path)

    def _clean_constraint_name(self, name):
        """Simplify constraint names."""

        # Remove known module prefixes
        prefixes = [
            "towerse.post.", "towerse.tower.", "towerse.", "tower.",
            "floatingse.", "floatingse.tower."
        ]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Remove 'constr_' prefix if present
        if name.startswith("constr_"):
            name = name[len("constr_"):]

        # Map internal names to standardized versions
        if name == "structural_frequencies":
            return "frequency_1"
        if name == "fatigue_section_damage":
            return "towerse.fatigue_section_damage"

        return name

    def get_objective_function_evolution(
            self) -> Tuple[List[int], List[float], str]:
        """
        Extract the evolution of the optimization objective function.
        
        Returns:
            iterations (list[int]): Iteration indices.
            objective_values (list[float]): Objective values.
            objective_function (str): Name of the objective function.
        """
        iterations = []
        objective_values = []

        # Get all optimization cases
        cases = self.cr.get_cases()

        # Extract objective value from each case
        for i, case in enumerate(cases):
            objective = case.get_objectives()
            if objective:
                iterations.append(i)
                value = list(objective.values())[0]
                objective_values.append(value * 1000)
        objective_function = list(objective.keys())[0]

        return iterations, objective_values, objective_function

    def get_constraints_evolution(
        self
    ) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, bool]]:
        """
        Extract the evolution of constraints across optimization iterations.

        Returns:
            constraints_evolution_max (dict): Max values per constraint per
              iteration.
            constraints_evolution_min (dict): Min values per constraint per
              iteration.
            constraints_is_vector (dict): Whether each constraint is
              vector-valued.
        """
        constraints_evolution_max = {}
        constraints_evolution_min = {}
        constraints_is_vector = {}

        # Get all optimization cases
        cases = self.cr.get_cases()

        # Extract constraint values
        for case in cases:
            constraints = case.get_constraints()
            for raw_name, value in constraints.items():
                name = self._clean_constraint_name(raw_name)

                # Initialize storage if encountering this constraint
                if name not in constraints_evolution_max:
                    constraints_evolution_max[name] = []
                    constraints_evolution_min[name] = []
                    constraints_is_vector[name] = isinstance(
                        value, np.ndarray) and value.size > 1

                # Compute max/min values
                max_val = np.max(
                    value) if constraints_is_vector[name] else float(value)
                min_val = np.min(value) if constraints_is_vector[name] else None

                constraints_evolution_max[name].append(max_val)
                if min_val is not None:
                    constraints_evolution_min[name].append(min_val)

        return (constraints_evolution_max, constraints_evolution_min,
                constraints_is_vector)

    def plot_all(self,
                 constraints_bounds: dict = None,
                 mode: str = "both") -> None:
        """
        Generate all optimization plots.

        Args:
            constraints_bounds (dict, optional): Optional bounds to show on
              constraint plots.
            mode (str): Plot mode for constraints. Options:
                - "single": individual plot per constraint
                - "grid": single grid with subplots
                - "both": generates both types
        """
        self.plot_objective_function_evolution()
        self.plot_constraints_evolution(constraints_bounds=constraints_bounds,
                                        mode=mode)

    def plot_objective_function_evolution(self) -> None:
        """
        Generate a convergence plot of the optimization objective function.

        The plot shows how the objective (e.g., tower mass or cost) evolves over 
        iterations, providing insight into the convergence behavior.
        """

        # Extract objective function evolution data
        (iterations, objective_values,
         objective_function) = self.get_objective_function_evolution()

        # Set global plot style
        plt.style.use("fivethirtyeight")

        # Configure the figure
        fig, ax = plt.subplots(figsize=(8, 4), facecolor="white")

        # Plot
        ax.plot(iterations,
                objective_values,
                color='midnightblue',
                marker="o",
                linewidth=1.5,
                markersize=4)

        # Customize axes and appearance
        ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
        label = OBJECTIVE_FUNC_LABELS.get(objective_function,
                                          objective_function)
        ax.set_ylabel(label, fontsize=10, labelpad=10)
        ax.set_title("Objective Function Evolution", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.tick_params(axis='both', which='major', labelsize=9)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.set_xlim(left=0 - 0.5, right=max(iterations) + 0.5)

        # Hide unnecessary spines
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(False)

        # Save the plot
        plot_path = os.path.join(self.output_dir, "objective_function.png")
        plt.savefig(plot_path, dpi=300, bbox_inches="tight", transparent=True)

        plt.close(fig)

    def plot_constraints_evolution(self,
                                   constraints_bounds: dict = None,
                                   mode: str = "both") -> None:
        """
        Plot the evolution of constraint values across optimization iterations.

        Supports both individual plots per constraint and a single grid layout
          plot.

        Args:
            constraints_bounds (dict): Optional bounds to overlay on plots.
            mode (str): "single" for one plot per constraint, 
                        "grid" for all constraints in one figure,
                        "both" for both types.
        """
        if constraints_bounds is None:
            constraints_bounds = {}

        # Extract constraints evolution data
        (constraints_evolution_max, constraints_evolution_min,
         constraints_is_vector) = self.get_constraints_evolution()

        # Define desired order of constraints for consistent plotting
        desired_order = [
            "d_to_t",
            "taper",
            "slope",
            "thickness_slope",
            "stress",
            "frequency_1",
            "global_buckling",
            "shell_buckling",
            "towerse.fatigue_section_damage",
        ]
        constraint_names = [
            name for name in desired_order if name in constraints_evolution_max
        ]

        # Single plot per constraint
        if mode in ["single", "both"]:
            for name in constraint_names:
                iterations = np.arange(len(constraints_evolution_max[name]))

                # Set global plot style
                plt.style.use("fivethirtyeight")

                # Configure the figure
                fig, ax = plt.subplots(figsize=(8, 4), facecolor="white")

                # Plot max and min values for vector constraints
                if constraints_is_vector[name]:
                    ax.plot(iterations,
                            constraints_evolution_max[name],
                            label="Max",
                            color="firebrick",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)
                    ax.plot(iterations,
                            constraints_evolution_min[name],
                            label="Min",
                            color="midnightblue",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)
                else:
                    ax.plot(iterations,
                            constraints_evolution_max[name],
                            label=None,
                            color="midnightblue",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)

                # Add optional upper/lower bounds if provided
                bounds = constraints_bounds.get(name, {})
                for bound_type, label_text in [("upper_bound", "Upper Bound"),
                                               ("lower_bound", "Lower Bound")]:
                    bound_val = bounds.get(bound_type)

                    if isinstance(bound_val, list):
                        bound_val = bound_val[0]

                    if bound_val is not None:
                        if isinstance(bound_val, (list, np.ndarray)):
                            plt.plot(iterations,
                                     np.array(bound_val)[:len(iterations)],
                                     color="gray",
                                     linestyle="--",
                                     linewidth=0.9)
                        else:
                            ax.hlines(bound_val,
                                      iterations[0],
                                      iterations[-1],
                                      color="gray",
                                      linestyle="--",
                                      linewidth=0.9)
                            va_align = ("top" if bound_type == "lower_bound"
                                        else "bottom")
                            ax.text(iterations[-1],
                                    bound_val,
                                    f"{label_text} ({bound_val:.2f})",
                                    fontsize=7,
                                    color="gray",
                                    va=va_align,
                                    ha="right")

                # Customize axes and appearance
                label = CONSTRAINT_LABELS.get(name, name)
                ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
                ax.set_ylabel(label, fontsize=10, labelpad=10)
                ax.set_title(f"{label} Evolution", fontsize=12)
                if constraints_is_vector[name]:
                    ax.legend(
                        fontsize=9,
                        frameon=False,
                        loc="lower right",
                        ncol=2,
                        bbox_to_anchor=(1, -0.175),
                    )
                ax.grid(True, linestyle="--", alpha=0.5)
                ax.tick_params(axis='both', labelsize=9)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
                ax.set_xlim(left=0 - 0.5, right=max(iterations) + 0.5)

                # Hide unnecessary spines
                for spine in ['top', 'right', 'left', 'bottom']:
                    ax.spines[spine].set_visible(False)

                # Save the plot
                filename = name.replace("/", "_").replace(" ", "_").replace(
                    ".", "_") + ".png"
                plt.savefig(os.path.join(self.output_dir, filename),
                            dpi=300,
                            bbox_inches="tight",
                            transparent=True)

                plt.close(fig)

        # Grid plot for all constraints together (only if >1 constraint).
        if mode in ["grid", "both"] and len(constraint_names) > 1:
            n_constraints = len(constraint_names)
            n_cols = min(n_constraints, 3)
            n_rows = -(-n_constraints // n_cols)

            # Set global plot style
            plt.style.use("fivethirtyeight")

            # Configure the figure and grid layout
            fig = plt.figure(figsize=(20, 10), facecolor="white")
            gs = gridspec.GridSpec(n_rows, n_cols, wspace=0.2, hspace=0.1)

            for i, name in enumerate(constraint_names):
                ax = fig.add_subplot(gs[i])
                iterations = np.arange(len(constraints_evolution_max[name]))

                # Plot max and min values for vector constraints
                if constraints_is_vector[name]:
                    ax.plot(iterations,
                            constraints_evolution_max[name],
                            label="Max",
                            color="firebrick",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)
                    ax.plot(iterations,
                            constraints_evolution_min[name],
                            label="Min",
                            color="midnightblue",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)
                else:
                    ax.plot(iterations,
                            constraints_evolution_max[name],
                            label=None,
                            color="midnightblue",
                            marker="o",
                            linewidth=1.5,
                            markersize=4)

                # Add optional upper/lower bounds if provided
                bounds = constraints_bounds.get(name, {})
                for bound_type, label_text in [
                    ("upper_bound", "Upper Bound"),
                    ("lower_bound", "Lower Bound"),
                ]:
                    bound_val = bounds.get(bound_type)

                    if isinstance(bound_val, list):
                        bound_val = bound_val[0]

                    if bound_val is not None:
                        if isinstance(bound_val, (list, np.ndarray)):
                            plt.plot(iterations,
                                     np.array(bound_val)[:len(iterations)],
                                     color="gray",
                                     linestyle="--",
                                     linewidth=0.9)
                        else:
                            ax.hlines(bound_val,
                                      iterations[0],
                                      iterations[-1],
                                      color="gray",
                                      linestyle="--",
                                      linewidth=0.9)
                            va_align = ("top" if bound_type == "lower_bound"
                                        else "bottom")
                            ax.text(iterations[-1],
                                    bound_val,
                                    f"{label_text} ({bound_val:.2f})",
                                    fontsize=7,
                                    color="gray",
                                    va=va_align,
                                    ha="right")

                    # Customize axes and appearance
                    label = CONSTRAINT_LABELS.get(name, name)
                    row = i // n_cols
                    if row == n_rows - 1:
                        ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
                    else:
                        ax.set_xticklabels([])
                        ax.set_xticks([])
                    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
                    ax.tick_params(axis='both', labelsize=9)
                    ax.set_ylabel(label, fontsize=10, labelpad=10)
                    ax.set_xlim(left=0 - 0.5, right=max(iterations) + 0.5)

                    # Hide unnecessary spines
                    for spine in ["top", "right", "left", "bottom"]:
                        ax.spines[spine].set_visible(False)

                fig.legend(labels=["Max", "Min"],
                           loc="lower right",
                           ncol=2,
                           fontsize=9,
                           bbox_to_anchor=(0.95, -0.005),
                           frameon=False)

            # Save final grid
            grid_path = os.path.join(self.output_dir,
                                     "all_constraints_evolution.png")
            plt.savefig(grid_path,
                        dpi=300,
                        bbox_inches="tight",
                        transparent=True)

            plt.close(fig)
