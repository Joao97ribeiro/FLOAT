# pylint: disable=no-member
# pylint: disable=import-error
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
# pylint: disable=too-many-lines
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
"""Comparison and visualization of FLOAT tower simulation results."""

import os
from collections import OrderedDict

from typing import List, Optional, Tuple, Dict

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import gridspec
from matplotlib.lines import Line2D
import numpy as np

from .colors import COLORS_DICT
from . import results
from . import summary

plt.style.use("fivethirtyeight")


class TowerWisdemComparator:
    """
    Compares WISDEM tower simulation result CSVs.

    This class enables side-by-side comparisons of key metrics such as geometry,
    stress, damage, deflection, and buckling profiles from different
    WISDEM simulations, typically an original and an optimized tower design.
    """

    def __init__(self,
                 results_paths: list[str],
                 output_dir: str,
                 labels: Optional[list[str]] = None,
                 colors: Optional[list[str]] = None) -> None:
        """
        Initialize the comparator with WISDEM result CSV file paths.

        Args:
            results_paths (list[str]): List of file paths to the WISDEM
              generated.
            output_dir (str): Directory where comparison plots and summary
              outputs will be saved.
            labels (list[str], optional): Custom labels for the tower cases.
              Defaults to ["Original Tower", "Optimized Tower"].
            colors (list[str], optional): Custom colors for the plots.
        """
        self.results_paths = results_paths

        # Initialize result readers
        self.results_readers = [
            results.TowerResultsCSVReader(path) for path in results_paths
        ]

        # Ensure output directory exists
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Assign labels or fallback to default
        self.labels = labels if labels is not None else [
            "Original Tower", "Optimized Tower"
        ]

        # Assign colors or fallback to default
        self.colors = colors if colors is not None else [
            COLORS_DICT["grey_paper"], COLORS_DICT["blue_paper"],
            COLORS_DICT["red_paper"]
        ]

    def plot_all(self, bounds=None, save_svg: bool = False) -> None:
        """Generate all comparison plots for the tower cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Optional bounds to overlay on the plots.
                Pass the full dictionary with keys like:
                    - "outer_diameter"
                    - "layer_thickness"
                    - "towerse.post.axial_stress"
                    - "towerse.fatigue_section_damage"
                    - "towerse.post.tower_deflection"
                    - "shell_buckling"
                    - "global_buckling"
            save_svg (bool): If True, saves plots as SVG files.
        """
        self.plot_tower_geometry_profile(bounds, save_svg)
        self.plot_axial_stress_profile(bounds, save_svg)
        self.plot_damage_profile(bounds, save_svg)
        self.plot_deflection_profile(bounds, save_svg)
        self.plot_buckling_profile(bounds, save_svg)
        self.plot_tower_modeshapes_profile(save_svg=save_svg,
                                           normalize_modes=True)
        self.plot_tower_modeshapes_profile(save_svg=save_svg,
                                           normalize_modes=False)

    def plot_tower_geometry_profile(self,
                                    bounds=None,
                                    save_svg: bool = False) -> None:
        """Compare the geometries of tower cases.

        This plot compares the outer diameter and wall thickness profiles along
        the tower height for both cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Dictionary with optional bounds to overlay on the plots.
                Expected keys:
                    • "outer_diameter": {"lower_bound": float, "upper_bound":
                      float}
                    • "layer_thickness": {"lower_bound": float, "upper_bound":
                      float}
                If provided, vertical dashed lines and numeric labels are drawn
                  at each bound to highlight admissible design ranges.
            save_svg (bool): If True, saves plots as SVG files.
        """

        # Configure the figure and grid layout
        fig = plt.figure(figsize=(8.1, 4), facecolor='white')
        gs = gridspec.GridSpec(1, 2, wspace=0.1)

        # Define subplots
        ax1 = fig.add_subplot(gs[0], facecolor="white")
        ax2 = fig.add_subplot(gs[1], facecolor="white")
        axes = [ax1, ax2]

        # Plot outer diameter
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_geometry_profile()
            ax1.plot(data["outer_diameter"],
                     data["z"],
                     label=label,
                     color=color,
                     linewidth=1.5,
                     markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and 'outer_diameter' in bounds:
            outer_diameter_bounds = bounds['outer_diameter']
            all_z = [
                reader.get_geometry_profile()["z"]
                for reader in self.results_readers
            ]

            # Flatten e calcula limites globais
            ymin = min(z.min() for z in all_z)
            ymax = max(z.max() for z in all_z)

            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in outer_diameter_bounds:
                    val = outer_diameter_bounds[bound_type]
                    ax1.vlines(val,
                               ymin=ymin,
                               ymax=ymax,
                               color=COLORS_DICT["dark_gray_paper"],
                               linestyle="--",
                               linewidth=0.9)
                    ax1.text(val,
                             ymin,
                             f"{label_text} ({val:.2f})",
                             fontsize=7,
                             color=COLORS_DICT["dark_gray_paper"],
                             va="bottom",
                             ha="right",
                             rotation=90)

        # Customize axes and appearance
        ax1.set_xlabel("Outer Diameter (m)", fontsize=10, labelpad=10)
        ax1.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
        ax1.set_title("Tower Outer Diameter Profile", fontsize=12)
        ax1.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
        ax1.tick_params(axis='both',
                        which='major',
                        length=4,
                        width=1,
                        labelsize=10,
                        color=COLORS_DICT["dark_gray_paper"])

        # Plot wall thickness
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_geometry_profile()
            ax2.step(np.array(data["wall_thickness"]) * 1000,
                     data["z_mean_section"],
                     where="mid",
                     label=label,
                     color=color,
                     linewidth=1.5,
                     markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and 'layer_thickness' in bounds:
            layer_thickness_bounds = bounds['layer_thickness']
            all_z_mean = [
                reader.get_geometry_profile()["z_mean_section"]
                for reader in self.results_readers
            ]

            ymin = min(z.min() for z in all_z_mean)
            ymax = max(z.max() for z in all_z_mean)
            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:

                if bound_type in layer_thickness_bounds:
                    val = layer_thickness_bounds[bound_type] * 1000
                    ax2.vlines(val,
                               ymin=ymin,
                               ymax=ymax,
                               color=COLORS_DICT["dark_gray_paper"],
                               linestyle="--",
                               linewidth=0.9)
                    ax2.text(val,
                             ymin,
                             f"{label_text} ({val:.2f})",
                             fontsize=7,
                             color=COLORS_DICT["dark_gray_paper"],
                             va="bottom",
                             ha="right",
                             rotation=90)

        # Customize axes and appearance
        ax2.set_xlabel("Wall Thickness (mm)", fontsize=10, labelpad=10)
        ax2.set_title("Tower Wall Thickness Profile", fontsize=12)
        ax2.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
        ax2.set_yticklabels([])
        ax2.tick_params(axis='both',
                        which='major',
                        length=4,
                        width=1,
                        labelsize=10,
                        color=COLORS_DICT["dark_gray_paper"])

        # Hide unnecessary spines
        for ax in axes:
            for spine in ['top', 'right', 'left', 'bottom']:
                ax.spines[spine].set_visible(True)
                ax.spines[spine].set_linewidth(1)
                ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

            ax.tick_params(axis='both',
                           which='major',
                           length=4,
                           width=1,
                           labelsize=10,
                           color=COLORS_DICT["dark_gray_paper"])
            ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])

        # Legenda
        handles0, labels0 = ax1.get_legend_handles_labels()
        handles1, labels1 = ax2.get_legend_handles_labels()
        all_labels = OrderedDict(zip(labels0 + labels1, handles0 + handles1))
        fig.legend(all_labels.values(),
                   all_labels.keys(),
                   loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.125 * (1 + (len(all_labels) / 25))),
                   fontsize=9,
                   frameon=False)

        # Save the plot
        plot_path = os.path.join(self.output_dir,
                                 "tower_geometry_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight', transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    "tower_geometry_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_axial_stress_profile(self,
                                  bounds=None,
                                  save_svg: bool = False) -> None:
        """Plot comparison of axial stress profiles between tower cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Optional bounds to overlay on the plot.
                Expected key:
                    • "towerse.post.axial_stress": {"lower_bound": float, 
                    "upper_bound": float}
                If provided, vertical dashed lines and labels will be drawn to
                indicate the admissible stress range.
            save_svg (bool): If True, saves plots as SVG files.
        """

        # Configure the figure
        fig, ax = plt.subplots(figsize=(4, 4), facecolor="white")

        # Plot data
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_stress_profile()
            ax.plot(data["stress"] / 1e6,
                    data["z_midpoints"],
                    label=label,
                    color=color,
                    linewidth=1.5,
                    markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and "towerse.post.axial_stress" in bounds:
            axial_stress_bounds = bounds["towerse.post.axial_stress"]
            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in axial_stress_bounds:
                    val = axial_stress_bounds[bound_type] / 1e6
                    z = self.results_readers[0].get_stress_profile(
                    )["z_midpoints"]
                    if isinstance(val, (list, tuple)) and len(val) == len(z):
                        ax.plot(val,
                                z,
                                color=COLORS_DICT["dark_gray_paper"],
                                linestyle="--",
                                linewidth=0.9)
                        ax.text(min(val),
                                min(z),
                                f"{label_text} ({np.mean(val):.2f})",
                                fontsize=7,
                                color=COLORS_DICT["dark_gray_paper"],
                                va="bottom",
                                ha="right",
                                rotation=90)

        # Customize axes and appearance
        ax.set_xlabel("Axial Stress (MPa)", fontsize=10, labelpad=10)
        ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
        ax.set_title("Tower Axial Stress Profile", fontsize=12)
        ax.tick_params(axis='both',
                       which='major',
                       length=4,
                       width=1,
                       labelsize=10,
                       color=COLORS_DICT["dark_gray_paper"])
        ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
        fig.legend(loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.125 * (1 + (len(self.labels) / 25))),
                   fontsize=9,
                   frameon=False)

        # Hide unnecessary spines
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(True)
            ax.spines[spine].set_linewidth(1)
            ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

        # Save the plot
        plot_path = os.path.join(self.output_dir, "tower_stress_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight', transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    "tower_stress_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_damage_profile(self, bounds=None, save_svg: bool = False) -> None:
        """Plot comparison of damage profiles between tower cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Optional bounds to overlay on the plot.
                Expected key:
                    • "towerse.fatigue_section_damage": {"lower_bound": float, 
                    "upper_bound": float}
                If provided, vertical dashed lines and labels will be drawn to
                indicate the admissible damage.
            save_svg (bool): If True, saves plots as SVG files.
        """

        # Configure the figure
        fig, ax = plt.subplots(figsize=(4, 4), facecolor="white")

        # Plot data
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_damage_profile()
            ax.step(data["section_damage"],
                    data["z_mean_section"],
                    where="mid",
                    label=label,
                    color=color,
                    linewidth=1.5,
                    markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and "towerse.fatigue_section_damage" in bounds:
            damage_bounds = bounds["towerse.fatigue_section_damage"]

            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in damage_bounds:
                    val = damage_bounds[bound_type]
                    z = self.results_readers[0].get_damage_profile(
                    )["z_mean_section"]
                    if isinstance(val, (list, tuple)) and len(val) == len(z):
                        ax.plot(val,
                                z,
                                color=COLORS_DICT["dark_gray_paper"],
                                linestyle="--",
                                linewidth=0.9)

                        ax.text(min(val),
                                min(z),
                                f"{label_text} ({np.mean(val):.2f})",
                                fontsize=7,
                                color=COLORS_DICT["dark_gray_paper"],
                                va="bottom",
                                ha="right",
                                rotation=90)

        # Customize axes and appearance
        ax.set_xlabel("Section Damage", fontsize=10, labelpad=10)
        ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
        ax.set_title("Tower Damage Profile", fontsize=12)
        ax.tick_params(axis='both',
                       which='major',
                       length=4,
                       width=1,
                       labelsize=10,
                       color=COLORS_DICT["dark_gray_paper"])
        ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
        fig.legend(loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.125 * (1 + (len(self.labels) / 25))),
                   fontsize=9,
                   frameon=False)

        # Hide unnecessary spines
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(True)
            ax.spines[spine].set_linewidth(1)
            ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

        # Save the plot
        plot_path = os.path.join(self.output_dir, "tower_damage_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight', transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    "tower_damage_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_deflection_profile(self,
                                bounds=None,
                                save_svg: bool = False) -> None:
        """Compare the deflection of tower cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Dictionary with optional bounds to overlay on the plots.
                Expected keys:
                    • "towerse.tower_deflection": {"lower_bound": float, 
                      "upper_bound": float}
                If provided, vertical dashed lines and numeric labels are drawn
                  at each bound to highlight admissible deflectionb ranges.
            save_svg (bool): If True, saves plots as SVG files.
        """

        # Configure the figure
        fig, ax = plt.subplots(figsize=(4, 4), facecolor="white")

        # Plot data
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_deflection_profile()
            ax.step(data["deflection"],
                    data["z_full"],
                    where="mid",
                    label=label,
                    color=color,
                    linewidth=1.5,
                    markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and "towerse.post.tower_deflection" in bounds:
            deflection_bounds = bounds["towerse.post.tower_deflection"]
            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in deflection_bounds:
                    val = deflection_bounds[bound_type] / 1e6

                    z = self.results_readers[0].get_deflection_profile(
                    )["z_full"]
                    if isinstance(val, (list, tuple)) and len(val) == len(z):
                        ax.plot(val,
                                z,
                                color=COLORS_DICT["dark_gray_paper"],
                                linestyle="--",
                                linewidth=0.9)
                        ax.text(min(val),
                                min(z),
                                f"{label_text} ({np.mean(val):.2f})",
                                fontsize=7,
                                color=COLORS_DICT["dark_gray_paper"],
                                va="bottom",
                                ha="right",
                                rotation=90)

        # Customize axes and appearance
        ax.set_xlabel("Deflection (m)", fontsize=10, labelpad=10)
        ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
        ax.set_title("Tower Deflection Profile", fontsize=12)
        ax.tick_params(axis='both',
                       which='major',
                       length=4,
                       width=1,
                       labelsize=10,
                       color=COLORS_DICT["dark_gray_paper"])
        ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
        fig.legend(loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.125 * (1 + (len(self.labels) / 25))),
                   fontsize=9,
                   frameon=False)

        # Hide unnecessary spines
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(True)
            ax.spines[spine].set_linewidth(1)
            ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

        # Save the plot
        plot_path = os.path.join(self.output_dir,
                                 "tower_deflection_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight', transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    "tower_deflection_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_buckling_profile(self,
                              bounds=None,
                              save_svg: bool = False) -> None:
        """Compare the buckling of tower cases.

        This plot compares the shell buckling and gloabl buckling profiles along
        the tower height for both cases.

        Args:
            bounds (dict[str, dict[str, float]], optional):
                Dictionary with optional bounds to overlay on the plots.
                Expected keys:
                    • "shell_buckling": {"lower_bound": float, "upper_bound":
                      float}
                    • "global_buckling": {"lower_bound": float, "upper_bound":
                      float}
                If provided, vertical dashed lines and numeric labels are drawn
                  at each bound to highlight admissible buckling ranges.
            save_svg (bool): If True, saves plots as SVG files.
        """

        # Configure the figure and grid layout
        fig = plt.figure(figsize=(8.1, 4), facecolor='white')
        gs = gridspec.GridSpec(1, 2, wspace=0.1)

        # Define subplots
        ax1 = fig.add_subplot(gs[0], facecolor="white")
        ax2 = fig.add_subplot(gs[1], facecolor="white")
        axes = [ax1, ax2]

        # Plot shell buckling
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_buckling_profile()
            ax1.plot(data["shell_buckling"],
                     data["z_midpoints"],
                     label=label,
                     color=color,
                     linewidth=1.5,
                     markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and 'shell_buckling' in bounds:
            shell_buckling_bounds = bounds['shell_buckling']
            all_z_midpoints = [
                reader.get_buckling_profile()["z_midpoints"]
                for reader in self.results_readers
            ]
            ymin = min(z.min() for z in all_z_midpoints)
            ymax = max(z.max() for z in all_z_midpoints)
            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in shell_buckling_bounds:
                    val = shell_buckling_bounds[bound_type]
                    ax1.vlines(val,
                               ymin=ymin,
                               ymax=ymax,
                               color=COLORS_DICT["dark_gray_paper"],
                               linestyle="--",
                               linewidth=0.9)
                    ax1.text(val,
                             ymin,
                             f"{label_text} ({val:.2f})",
                             fontsize=7,
                             color=COLORS_DICT["dark_gray_paper"],
                             va="bottom",
                             ha="right",
                             rotation=90)

        # Customize axes and appearance
        ax1.set_xlabel("Shell Buckling", fontsize=10, labelpad=10)
        ax1.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
        ax1.set_title("Tower Shell Buckling Profile", fontsize=12)

        # Plot global buckling
        for reader, label, color in zip(self.results_readers, self.labels,
                                        self.colors):
            data = reader.get_buckling_profile()
            ax2.plot(data["global_buckling"],
                     data["z_midpoints"],
                     label=label,
                     color=color,
                     linewidth=1.5,
                     markersize=4)

        # Add optional upper/lower bounds if provided
        if bounds and 'global_buckling' in bounds:
            global_buckling_bounds = bounds['global_buckling']
            all_z_midpoints = [
                reader.get_buckling_profile()["z_midpoints"]
                for reader in self.results_readers
            ]
            ymin = min(z.min() for z in all_z_midpoints)
            ymax = max(z.max() for z in all_z_midpoints)
            for bound_type, label_text in [("lower_bound", "Lower Bound"),
                                           ("upper_bound", "Upper Bound")]:
                if bound_type in global_buckling_bounds:
                    val = global_buckling_bounds[bound_type]
                    ax2.vlines(val,
                               ymin=ymin,
                               ymax=ymax,
                               color=COLORS_DICT["dark_gray_paper"],
                               linestyle="--",
                               linewidth=0.9)
                    ax2.text(val,
                             ymin,
                             f"{label_text} ({val:.2f})",
                             fontsize=7,
                             color=COLORS_DICT["dark_gray_paper"],
                             va="bottom",
                             ha="right",
                             rotation=90)

        # Customize axes and appearance
        ax2.set_xlabel("Global Buckling", fontsize=10, labelpad=10)
        ax2.set_title("Tower Global Buckling Profile", fontsize=12)
        ax2.set_yticklabels([])

        # Hide unnecessary spines
        for ax in axes:
            for spine in ['top', 'right', 'left', 'bottom']:
                ax.spines[spine].set_visible(True)
                ax.spines[spine].set_linewidth(1)
                ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

            ax.tick_params(axis='both',
                           which='major',
                           length=4,
                           width=1,
                           labelsize=10,
                           color=COLORS_DICT["dark_gray_paper"])
            ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])

        # Legenda
        handles0, labels0 = ax1.get_legend_handles_labels()
        handles1, labels1 = ax2.get_legend_handles_labels()
        all_labels = OrderedDict(zip(labels0 + labels1, handles0 + handles1))
        fig.legend(all_labels.values(),
                   all_labels.keys(),
                   loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.125 * (1 + (len(self.labels) / 25))),
                   fontsize=9,
                   frameon=False)

        # Save the plot
        plot_path = os.path.join(self.output_dir,
                                 "tower_buckling_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight', transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    "tower_buckling_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_tower_modeshapes_profile(self,
                                      normalize_modes: bool = False,
                                      save_svg: bool = False) -> None:
        """Compare modal shapes (FA1, FA2, SS1, SS2) for towers.

        Args:
            normalize_modes (bool): If True, modal shapes are normalized by peak
              magnitude.
            save_svg (bool): If True, saves plots as SVG files.
        """

        def poly_shape(coeffs: list[float], x: np.ndarray) -> np.ndarray:
            """Return normalized shape from polynomial coefficients.
            
            Args:
                coeffs (list or array): Polynomial coefficients.
                x (array): Normalized height positions.

            Returns:
                array: Shape profile.
            """
            shape = sum(c * x**(i + 2) for i, c in enumerate(coeffs))
            if normalize_modes is False:
                return shape
            max_idx = np.argmax(np.abs(shape))
            scale = np.abs(shape[max_idx])
            sign = np.sign(shape[max_idx])
            return shape / (scale * sign)

        # Normalized height positions
        x = np.linspace(0, 1, 200)

        # Evaluate shape functions
        modes = {"FA1": [], "FA2": [], "SS1": [], "SS2": []}
        for reader, label in zip(self.results_readers, self.labels):
            data = reader.get_mode_shapes()
            modes["FA1"].append((poly_shape(data["fore_aft"][0], x), label))
            modes["FA2"].append((poly_shape(data["fore_aft"][1], x), label))
            modes["SS1"].append((poly_shape(data["side_side"][0], x), label))
            modes["SS2"].append((poly_shape(data["side_side"][1], x), label))

        # Configure the figure and grid layout
        fig = plt.figure(figsize=(10, 6), facecolor='white')
        gs = gridspec.GridSpec(2, 2, hspace=0.2, wspace=0.2)

        # Define subplots
        ax1 = fig.add_subplot(gs[0, 0], facecolor='white')
        ax2 = fig.add_subplot(gs[0, 1], facecolor='white')
        ax3 = fig.add_subplot(gs[1, 0], facecolor='white')
        ax4 = fig.add_subplot(gs[1, 1], facecolor='white')
        axes = [ax1, ax2, ax3, ax4]
        keys = ["FA1", "FA2", "SS1", "SS2"]

        # Plot each mode shape
        for ax, key in zip(axes, keys):
            for i, (y, lbl) in enumerate(modes[key]):
                ax.plot(x,
                        y,
                        label=lbl,
                        color=self.colors[i],
                        linewidth=2,
                        markersize=4)

            # Customize axes and appearance
            ax.set_xlabel("Normalized Tower Height", fontsize=10, labelpad=10)

            # Remove Y labels on right column
            if ax in [axes[1]]:
                ax.set_ylabel("")
            if ax in [axes[0]]:
                if normalize_modes:
                    ax.set_ylabel("Normalized Shape", fontsize=10)
                else:
                    ax.set_ylabel("Shape (m)", fontsize=10)
            if ax in [axes[3]]:
                ax.set_ylabel("")
            if ax in [axes[2]]:
                if normalize_modes:
                    ax.set_ylabel("Normalized Shape", fontsize=10)
                else:
                    ax.set_ylabel("Shape (m)", fontsize=10)
            if ax in [axes[0], axes[1]]:
                ax.set_xlabel("")

        # Customize axes and appearance
        axes[0].set_title("Mode 1", fontsize=12)
        axes[1].set_title("Mode 2", fontsize=12)
        fig.text(0.02,
                 0.7,
                 "Fore-Aft (FA)",
                 va='center',
                 ha='center',
                 rotation='vertical',
                 fontsize=11)
        fig.text(0.02,
                 0.25,
                 "Side-to-Side (SS)",
                 va='center',
                 ha='center',
                 rotation='vertical',
                 fontsize=11)

        # Hide borders
        for ax in axes:
            for spine in ['top', 'right', 'left', 'bottom']:
                ax.spines[spine].set_visible(True)
                ax.spines[spine].set_linewidth(1)
                ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

            ax.tick_params(axis='both',
                           which='major',
                           length=4,
                           width=1,
                           labelsize=10,
                           color=COLORS_DICT["dark_gray_paper"])
            ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])

        # Legenda
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles,
                   labels,
                   loc="lower center",
                   ncol=10,
                   bbox_to_anchor=(0.5, -0.065 * (1 + (len(labels) / 20))),
                   fontsize=9,
                   frameon=False)

        # Save figure
        suffix = "normalized_" if normalize_modes else ""
        plot_path = os.path.join(self.output_dir,
                                 f"tower_{suffix}modeshapes_comparison.png")
        plt.savefig(plot_path, dpi=300, bbox_inches="tight", transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir,
                                    f"tower_{suffix}modeshapes_comparison.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def extract_summary_comparison(self,
                                   save_summary=False,
                                   log_summary=True,
                                   ref_idx=None) -> None:
        """Compares and logs or saves summary statistics of the simulations.

        Args:
            save_summary (bool): If True, saves JSON file with comparison.
            log_summary (bool): If True, prints comparison to console.
            ref_idx (int): Index of the reference case in the list of CSV paths.
        
        Raises:
            ValueError: If ref_idx is None. 
        """

        if ref_idx is None:
            raise ValueError(
                "ref_id must be provided to select the reference case.")

        # Reference case
        results_ref = self.results_paths[ref_idx]
        label_ref = self.labels[ref_idx]

        # Other cases
        results_list = (self.results_paths[:ref_idx] +
                        self.results_paths[ref_idx + 1:])

        # Compare each case to the reference
        for results_case in results_list:

            comparator = summary.TowerSummaryComparator(results_ref,
                                                        results_case)

            if save_summary:
                label_slug = str(label_ref).replace(" ", "").lower()
                filename = f"tower_summary_comparison_vs_{label_slug}.json"
                comparator.save_to_json(self.output_dir, filename)

            if log_summary:
                comparator.log_summary_table()


class TowerOptimizationResultsComparator:
    """
    Compare and visualize results from multiple WISDEM tower optimization runs.

    This class reads results from multiple optimization runs, extracts key
    metrics, and generates comparative plots to analyze differences in tower
    mass, constraints, and geometry profiles.

    Attributes:
        sql_paths (List[str]): List of file paths to the SQL result files.
        csv_paths (List[str]): List of file paths to the CSV result files.
        labels (List[str]): Labels for each optimization run for plot legends.
        output_dir (str): Directory to save the generated plots.
        colors (List[str], optional): Custom colors for the plots.
    """

    def __init__(self,
                 sql_paths: List[str],
                 csv_paths: List[str],
                 labels: List[str],
                 output_dir: str,
                 colors: Optional[List[str]] = None) -> None:
        """
    
        """
        self.sql_paths = sql_paths
        self.csv_paths = csv_paths

        # Ensure output directory exists
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Assign labels or fallback to default
        self.labels = labels if labels is not None else ["Optimized Tower"]

        # Assign colors or fallback to default
        self.colors = colors if colors is not None else [
            COLORS_DICT["blue_paper"], COLORS_DICT["red_paper"]
        ]

    def get_objective_function_evolution(
            self) -> Tuple[List[List[int]], List[List[float]], List[str]]:
        """Get objective function evolution from all SQL files.

        Returns:
            A tuple containing:
                iterations_list (list[list[int]]):  Iteration indices.
                objective_values_list (list[list[float]]): Objective values.
                objective_function_list (list[str]): Name of the objective
                  function.
        """
        objective_function_list = []
        iterations_list = []
        objective_values_list = []

        # Read data from each SQL file
        for sql_path in self.sql_paths:

            sql_reader = results.TowerOptimizationResultsSQLReader(
                sql_path, self.output_dir)
            (iterations, objective_values, objective_function
            ) = sql_reader.get_objective_function_evolution()

            iterations_list.append(iterations)
            objective_values_list.append(objective_values)
            objective_function_list.append(objective_function)

        return iterations_list, objective_values_list, objective_function_list

    def get_constraints_evolution(
        self
    ) -> Tuple[List[Dict[str, List[float]]], List[Dict[str, List[float]]],
               List[Dict[str, bool]]]:
        """Get constraints evolution from all SQL files.

        Returns:
            A tuple containing:
                constraints_evolution_max_list (list[dict]): Max values per
                  constraint per iteration.
                constraints_evolution_min_list (list[dict]): Min values per
                  constraint per iteration.
                constraints_is_vector_list (list[dict]): Whether each constraint
                  is vector-valued.
        """
        constraints_evolution_max_list = []
        constraints_evolution_min_list = []
        constraints_is_vector_list = []

        # Read data from each SQL file
        for sql_path in self.sql_paths:

            sql_reader = results.TowerOptimizationResultsSQLReader(
                sql_path, self.output_dir)
            (constraints_evolution_max, constraints_evolution_min,
             constraints_is_vector) = sql_reader.get_constraints_evolution()

            constraints_evolution_max_list.append(constraints_evolution_max)
            constraints_evolution_min_list.append(constraints_evolution_min)
            constraints_is_vector_list.append(constraints_is_vector)

        return (constraints_evolution_max_list, constraints_evolution_min_list,
                constraints_is_vector_list)

    def plot_objective_function_comparison(self, save_svg) -> None:
        """
        Generate a convergence plot of the optimization objective function.

        The plot shows how the objective (e.g., tower mass or cost) evolves over 
        iterations, providing insight into the convergence behavior.
        
        Args:
            save_svg (bool): If True, saves plots as SVG files.
        
        Raises:
            ValueError: If objective functions differ across SQL files.
        """

        # Extract objective function evolution data
        (iterations_list, objective_values_list,
         objective_function_list) = self.get_objective_function_evolution()

        # Configure the figure
        fig, ax = plt.subplots(figsize=(7, 4), facecolor="white")

        # Determine common objective function
        if all(obj == objective_function_list[0]
               for obj in objective_function_list):
            objective_function = objective_function_list[0]
        else:
            raise ValueError("Objective functions differ across SQL files.")

        # Plot
        for i in range(len(self.sql_paths)):
            iterations = iterations_list[i]
            objective_values = objective_values_list[i]

            if self.labels == []:
                label = None
            else:
                label = self.labels[i]

            ax.plot(iterations,
                    objective_values,
                    color=self.colors[i],
                    marker="o",
                    linewidth=2,
                    markersize=4,
                    label=label)

        # Customize axes and appearance
        ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
        label = results.OBJECTIVE_FUNC_LABELS.get(objective_function,
                                                  objective_function)
        ax.set_ylabel(label, fontsize=10, labelpad=10)
        ax.set_title("Objective Function Evolution", fontsize=12)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        max_value = max(max(iterations) for iterations in iterations_list)
        ax.set_xlim(left=0 - 0.5, right=max_value + 0.5)
        ax.tick_params(axis='both',
                       which='major',
                       length=4,
                       width=1,
                       labelsize=10,
                       color=COLORS_DICT["dark_gray_paper"])
        ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])

        #legend
        ax.legend(fontsize=9,
                  frameon=False,
                  loc="lower center",
                  ncol=10,
                  bbox_to_anchor=(0.5,
                                  -0.255 * (1 + (len(self.sql_paths) / 50))))

        # Hide unnecessary spines
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(True)
            ax.spines[spine].set_linewidth(1)
            ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

        # Save the plot
        plot_path = os.path.join(self.output_dir, "objective_function.png")
        plt.savefig(plot_path, dpi=300, bbox_inches="tight", transparent=True)

        if save_svg:
            svg_path = os.path.join(self.output_dir, "objective_function.svg")
            plt.savefig(svg_path,
                        bbox_inches='tight',
                        transparent=True,
                        format="svg")

        plt.close(fig)

    def plot_constraints_evolution(self,
                                   constraints_bounds: dict = None,
                                   save_svg: bool = False,
                                   mode: str = "both") -> None:
        """
        Plot the evolution of constraint values across optimization iterations.

        Supports both individual plots per constraint and a single grid layout
          plot.

        Args:
            constraints_bounds (dict): Optional bounds to overlay on plots.
            save_svg (bool): If True, saves plots as SVG files.
            mode (str): "single" for one plot per constraint, 
                        "grid" for all constraints in one figure,
                        "both" for both types.
        """

        # Extract constraints evolution data
        (constraints_evolution_max_list, constraints_evolution_min_list,
         constraints_is_vector_list) = self.get_constraints_evolution()

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
            name for name in desired_order
            if name in constraints_evolution_max_list[0]
        ]

        # Single plot per constraint
        if mode in ["single", "both"]:

            for name in constraint_names:

                # Configure the figure
                fig, ax = plt.subplots(figsize=(7, 4), facecolor="white")

                iterations_list = []
                max_min = False

                for i in range(len(self.sql_paths)):
                    constraints_evolution_max = constraints_evolution_max_list[
                        i]
                    constraints_evolution_min = constraints_evolution_min_list[
                        i]
                    constraints_is_vector = constraints_is_vector_list[i]

                    iterations = np.arange(len(constraints_evolution_max[name]))
                    iterations_list.append(iterations)

                    # Plot max and min values for vector constraints
                    if constraints_is_vector[name]:
                        ax.plot(iterations,
                                constraints_evolution_max[name],
                                color=self.colors[i],
                                linestyle="-",
                                marker="o",
                                linewidth=2,
                                markersize=4)
                        ax.plot(iterations,
                                constraints_evolution_min[name],
                                color=self.colors[i],
                                linestyle="--",
                                marker="x",
                                linewidth=2,
                                markersize=4)
                        max_min = True
                    else:
                        ax.plot(iterations,
                                constraints_evolution_max[name],
                                color=self.colors[i],
                                marker="o",
                                linewidth=2,
                                markersize=4)

                    if len(self.labels) == 1:
                        label = None
                    else:
                        label = self.labels[i]

                    ax.plot([], [], color=self.colors[i], label=label)

                max_value = max(
                    max(iterations) for iterations in iterations_list)
                if constraints_bounds is None:
                    constraints_bounds = {}

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
                                     color=COLORS_DICT["dark_gray_paper"],
                                     linestyle="--",
                                     linewidth=0.9)
                        else:
                            ax.hlines(bound_val,
                                      iterations[0],
                                      max_value,
                                      color=COLORS_DICT["dark_gray_paper"],
                                      linestyle="--",
                                      linewidth=0.9)
                            va_align = "bottom"
                            ax.text(max_value,
                                    bound_val,
                                    f"{label_text} ({bound_val:.2f})",
                                    fontsize=7,
                                    color=COLORS_DICT["dark_gray_paper"],
                                    va=va_align,
                                    ha="right")

                # Customize axes and appearance
                label = results.CONSTRAINT_LABELS.get(name, name)
                ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
                ax.set_ylabel(label, fontsize=10, labelpad=10)
                ax.set_title(f"{label} Evolution", fontsize=12)
                ax.grid(True,
                        linestyle="-",
                        color=COLORS_DICT["light_gray_paper"])
                ax.tick_params(axis='both',
                               which='major',
                               length=4,
                               width=1,
                               labelsize=10,
                               color=COLORS_DICT["dark_gray_paper"])
                ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
                ax.set_xlim(left=0 - 0.5, right=max_value + 0.5)

                if max_min:
                    if len(self.sql_paths) == 1:
                        color = self.colors[0]
                    else:
                        color = "black"

                handles, labels = ax.get_legend_handles_labels()

                if max_min:
                    custom_lines = [
                        Line2D([0], [0],
                               color=color,
                               linestyle="-",
                               marker="o",
                               label="Max",
                               linewidth=2,
                               markersize=4),
                        Line2D([0], [0],
                               color=color,
                               linestyle="--",
                               marker="x",
                               label="Min",
                               linewidth=2,
                               markersize=4),
                    ]

                    # fundir
                    handles = handles + custom_lines
                    labels = labels + ["Max", "Min"]

                # criar só uma legenda
                ax.legend(handles,
                          labels,
                          fontsize=9,
                          frameon=False,
                          loc="lower center",
                          ncol=10,
                          bbox_to_anchor=(0.5,
                                          -0.255 * (1 + (len(labels) / 50))))

                # Hide unnecessary spines
                for spine in ['top', 'right', 'left', 'bottom']:
                    ax.spines[spine].set_visible(True)
                    ax.spines[spine].set_linewidth(1)
                    ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])

                # Save the plot
                filename = name.replace("/", "_").replace(" ", "_").replace(
                    ".", "_") + ".png"
                plt.savefig(os.path.join(self.output_dir, filename),
                            dpi=300,
                            bbox_inches="tight",
                            transparent=True)

                if save_svg:
                    svg_path = os.path.join(self.output_dir,
                                            filename.replace(".png", ".svg"))
                    plt.savefig(svg_path,
                                bbox_inches='tight',
                                transparent=True,
                                format="svg")

                plt.close(fig)

        # Grid plot for all constraints together
        if mode in ["grid", "both"]:
            n_constraints = len(constraint_names)
            n_cols = min(n_constraints, 3)
            n_rows = -(-n_constraints // n_cols)

            # Configure the figure and grid layout
            fig = plt.figure(figsize=(21.4, 12.2), facecolor="white")
            gs = gridspec.GridSpec(n_rows, n_cols, wspace=0.2, hspace=0.1)

            for i, name in enumerate(constraint_names):
                ax = fig.add_subplot(gs[i])

                for j in range(len(self.sql_paths)):
                    constraints_evolution_max = constraints_evolution_max_list[
                        j]
                    constraints_evolution_min = constraints_evolution_min_list[
                        j]
                    constraints_is_vector = constraints_is_vector_list[j]
                    iterations = iterations_list[j]

                    # Plot max and min values for vector constraints
                    if constraints_is_vector[name]:
                        ax.plot(iterations,
                                constraints_evolution_max[name],
                                color=self.colors[j],
                                linestyle="-",
                                marker="o",
                                linewidth=2,
                                markersize=4)
                        ax.plot(iterations,
                                constraints_evolution_min[name],
                                color=self.colors[j],
                                linestyle="--",
                                marker="x",
                                linewidth=2,
                                markersize=4)
                        max_min = True
                    else:
                        ax.plot(iterations,
                                constraints_evolution_max[name],
                                color=self.colors[j],
                                marker="o",
                                linewidth=2,
                                markersize=4)

                    if i == 0:
                        if len(self.labels) == 1:
                            label = None
                        else:
                            label = self.labels[i]

                        ax.plot([], [], color=self.colors[j], label=label)

                        handles, labels = ax.get_legend_handles_labels()

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
                                     color=COLORS_DICT["dark_gray_paper"],
                                     linestyle="--",
                                     linewidth=0.9)
                        else:
                            ax.hlines(bound_val,
                                      iterations[0],
                                      max_value,
                                      color=COLORS_DICT["dark_gray_paper"],
                                      linestyle="--",
                                      linewidth=0.9)
                            va_align = "bottom"
                            ax.text(max_value,
                                    bound_val,
                                    f"{label_text} ({bound_val:.2f})",
                                    fontsize=7,
                                    color=COLORS_DICT["dark_gray_paper"],
                                    va=va_align,
                                    ha="right")

                    # Customize axes and appearance
                    label = results.CONSTRAINT_LABELS.get(name, name)
                    row = i // n_cols
                    if row == n_rows - 1:
                        ax.set_xlabel("Iteration", fontsize=10, labelpad=10)
                    else:
                        ax.set_xticklabels([])
                        ax.set_xticks([])
                    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
                    ax.tick_params(axis='both',
                                   which='major',
                                   length=4,
                                   width=1,
                                   labelsize=10,
                                   color=COLORS_DICT["dark_gray_paper"])
                    ax.set_ylabel(label, fontsize=10, labelpad=10)
                    ax.set_xlim(left=0 - 0.5, right=max_value + 0.5)

                    # Hide unnecessary spines
                    for spine in ["top", "right", "left", "bottom"]:
                        ax.spines[spine].set_visible(True)
                        ax.spines[spine].set_linewidth(1)
                        ax.spines[spine].set_color(
                            COLORS_DICT["light_gray_paper"])

            if max_min:
                if len(self.sql_paths) == 1:
                    color = self.colors[0]
                else:
                    color = "black"

                custom_lines = [
                    Line2D([0], [0],
                           color=color,
                           linestyle="-",
                           marker="o",
                           label="Max",
                           linewidth=2,
                           markersize=4),
                    Line2D([0], [0],
                           color=color,
                           linestyle="--",
                           marker="x",
                           label="Min",
                           linewidth=2,
                           markersize=4),
                ]

                # fundir
                handles = handles + custom_lines
                labels = labels + ["Max", "Min"]

                # criar só uma legenda
                ax.legend(handles,
                          labels,
                          fontsize=9,
                          frameon=False,
                          loc="lower center",
                          ncol=25,
                          bbox_to_anchor=(-0.75, -0.255 *
                                          (1 + (len(self.sql_paths) / 75))))

            # Save final grid
            grid_path = os.path.join(self.output_dir,
                                     "all_constraints_evolution.png")
            plt.savefig(grid_path,
                        dpi=300,
                        bbox_inches="tight",
                        transparent=True)

            if save_svg:
                svg_path = os.path.join(self.output_dir,
                                        "all_constraints_evolution.svg")
                plt.savefig(svg_path,
                            bbox_inches='tight',
                            transparent=True,
                            format="svg")

            plt.close(fig)

    def plot_all(self, constraints_bounds=None, save_svg: bool = False) -> None:
        """Generate all optimization plots.

        Args:
            constraints_bounds (dict, optional): Optional bounds to show on
              constraint plots.
        """
        self.plot_objective_function_comparison(save_svg)
        self.plot_constraints_evolution(constraints_bounds=constraints_bounds,
                                        save_svg=save_svg)

    def extract_summary(self, save_summary=False, log_summary=True) -> None:
        """Logs or saves summary of the tower optimization results.

        Args:
            save_summary (bool): If True, saves JSON file with results summary.
            log_summary (bool): If True, prints results summary to console.
        """
        for csv_path in self.csv_paths:
            summary_extractor = summary.TowerSummaryExtractor(csv_path)

            if save_summary:
                filename = "tower_optimization_summary.json"
                filename = filename.replace(" ", "")
                summary_extractor.save_to_json(json_dir=self.output_dir,
                                               filename=filename)

            if log_summary:
                summary_extractor.log_summary_table()
