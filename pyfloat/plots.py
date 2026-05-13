"""Reusable plot helpers for FLOAT tutorials and tasks."""

import os

import matplotlib.pyplot as plt
import numpy as np

from .colors import COLORS_DICT

_BOUND_LABELS = [("lower_bound", "Lower Bound"), ("upper_bound", "Upper Bound")]


def _style_axis(ax):
    """Apply consistent paper-style cosmetics to an axis."""
    ax.tick_params(axis="both",
                   which="major",
                   length=4,
                   width=1,
                   labelsize=10,
                   color=COLORS_DICT["dark_gray_paper"])
    ax.grid(True, linestyle="-", color=COLORS_DICT["light_gray_paper"])
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(True)
        ax.spines[spine].set_linewidth(1)
        ax.spines[spine].set_color(COLORS_DICT["light_gray_paper"])


def _draw_scalar_bound(ax, val, label, y_label, scale=1.0):
    """Draw a vertical dashed line + label for a scalar bound."""
    x = val * scale
    ax.axvline(x,
               color=COLORS_DICT["dark_gray_paper"],
               linestyle="--",
               linewidth=0.9)
    ax.text(x,
            y_label,
            f"{label} ({x:.2f})  ",
            fontsize=7,
            color=COLORS_DICT["dark_gray_paper"],
            va="bottom",
            ha="right",
            rotation=90)


def _draw_bound(ax, var_bounds, z, scale=1.0, y_label=0.0):
    """Draw lower/upper bound lines on `ax`.

    Scalar bounds become vertical lines; per-section lists are plotted as
    a curve along `z` (one value per section).
    """
    for key, label in _BOUND_LABELS:
        if key not in var_bounds:
            continue
        val = var_bounds[key]
        if isinstance(val, (list, tuple)) and len(val) == len(z):
            scaled = np.array(val, dtype=float) * scale
            ax.plot(scaled,
                    z,
                    color=COLORS_DICT["dark_gray_paper"],
                    linestyle="--",
                    linewidth=0.9)
            ax.text(min(scaled),
                    y_label,
                    f"{label} ({np.mean(scaled):.2f})  ",
                    fontsize=7,
                    color=COLORS_DICT["dark_gray_paper"],
                    va="bottom",
                    ha="right",
                    rotation=90)
        else:
            _draw_scalar_bound(ax, float(val), label, y_label, scale=scale)


def _save_figure(fig, output_dir, basename, save_svg):
    """Save a figure as PNG (and optionally SVG); return the PNG path.

    Plots are written under ``<output_dir>/plots/profiles/`` to keep them
    grouped away from both the raw FLOAT outputs and the optimization
    evolution plots.
    """
    plots_dir = os.path.join(output_dir, "plots", "profiles")
    os.makedirs(plots_dir, exist_ok=True)
    png_path = os.path.join(plots_dir, f"{basename}.png")
    fig.savefig(png_path, dpi=300, bbox_inches="tight", transparent=True)
    if save_svg:
        fig.savefig(os.path.join(plots_dir, f"{basename}.svg"),
                    bbox_inches="tight",
                    transparent=True,
                    format="svg")
    plt.close(fig)
    return png_path


def _tower_heights(wt_opt):
    """Compute z (nodes) and z_mean (midpoints) relative to z_start."""
    z = wt_opt.get_val("towerse.z_param") - wt_opt.get_val("towerse.z_start")
    return z, (z[:-1] + z[1:]) / 2


def _full_heights(wt_opt):
    """Compute z_full (every FE node) relative to z_start."""
    return wt_opt.get_val("towerse.z_full") - wt_opt.get_val("towerse.z_start")


def plot_tower_geometry_profile(wt_opt,
                                output_dir,
                                bounds=None,
                                save_svg=False):
    """Plot outer diameter + wall thickness vs height (2 panels)."""
    outer_diameter = wt_opt.get_val("towerse.tower_outer_diameter")
    wall_thickness = wt_opt.get_val("towerse.tower_wall_thickness") * 1000
    z, z_mean = _tower_heights(wt_opt)

    fig, axes = plt.subplots(1,
                             2,
                             figsize=(6, 5),
                             sharey=True,
                             facecolor="white")
    ax_d, ax_t = axes
    ax_d.plot(outer_diameter, z, color=COLORS_DICT["blue_paper"], linewidth=1.5)
    ax_d.set_xlabel("Outer Diameter (m)", fontsize=10, labelpad=10)
    ax_d.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax_d.set_title("Outer Diameter", fontsize=12)

    ax_t.step(wall_thickness,
              z_mean,
              where="mid",
              color=COLORS_DICT["blue_paper"],
              linewidth=1.5)
    ax_t.set_xlabel("Wall Thickness (mm)", fontsize=10, labelpad=10)
    ax_t.set_title("Wall Thickness", fontsize=12)

    for ax in axes:
        _style_axis(ax)
        ax.set_ylim(0, float(np.max(z)))

    if bounds:
        if "outer_diameter" in bounds:
            _draw_bound(ax_d, bounds["outer_diameter"], z)
        if "layer_thickness" in bounds:
            _draw_bound(ax_t, bounds["layer_thickness"], z_mean, scale=1000.0)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_geometry_profile", save_svg)


def plot_damage_profile(wt_opt, output_dir, bounds=None, save_svg=False):
    """Plot fatigue section damage vs height (1 panel)."""
    section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
    z, z_mean = _tower_heights(wt_opt)
    try:
        fatigue_z = wt_opt.get_val("towerse.fatigue_z") - wt_opt.get_val(
            "towerse.z_start")
    except KeyError:
        fatigue_z = z_mean

    fig, ax = plt.subplots(figsize=(4, 5), facecolor="white")
    ax.step(section_damage,
            fatigue_z,
            where="mid",
            color=COLORS_DICT["red_paper"],
            linewidth=1.5)
    ax.set_xlabel("Section Damage", fontsize=10, labelpad=10)
    ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax.set_title("Fatigue Damage", fontsize=12)
    _style_axis(ax)
    ax.set_ylim(0, float(np.max(z)))

    if bounds and "towerse.fatigue_section_damage" in bounds:
        _draw_bound(ax, bounds["towerse.fatigue_section_damage"], fatigue_z)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_damage_profile", save_svg)


def plot_axial_stress_profile(wt_opt, output_dir, bounds=None, save_svg=False):
    """Plot axial stress vs height in MPa (1 panel)."""
    z_full = _full_heights(wt_opt)
    z_mid = (z_full[:-1] + z_full[1:]) / 2
    stress = wt_opt.get_val("towerse.post.axial_stress").flatten() / 1e6

    fig, ax = plt.subplots(figsize=(4, 5), facecolor="white")
    ax.step(stress,
            z_mid,
            where="mid",
            color=COLORS_DICT["red_paper"],
            linewidth=1.5)
    ax.set_xlabel("Axial Stress (MPa)", fontsize=10, labelpad=10)
    ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax.set_title("Axial Stress", fontsize=12)
    _style_axis(ax)
    ax.set_ylim(0, float(np.max(z_full)))

    if bounds and "towerse.post.axial_stress" in bounds:
        _draw_bound(ax, bounds["towerse.post.axial_stress"], z_mid, scale=1e-6)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_stress_profile", save_svg)


def plot_buckling_profile(wt_opt, output_dir, bounds=None, save_svg=False):
    """Plot global + shell buckling vs height (2 panels)."""
    z_full = _full_heights(wt_opt)
    z_mid = (z_full[:-1] + z_full[1:]) / 2
    global_buckling = wt_opt.get_val(
        "towerse.post.constr_global_buckling").flatten()
    shell_buckling = wt_opt.get_val(
        "towerse.post.constr_shell_buckling").flatten()

    fig, axes = plt.subplots(1,
                             2,
                             figsize=(6, 5),
                             sharey=True,
                             facecolor="white")
    ax_gb, ax_sb = axes
    ax_gb.step(global_buckling,
               z_mid,
               where="mid",
               color=COLORS_DICT["red_paper"],
               linewidth=1.5)
    ax_gb.set_xlabel("Global Buckling", fontsize=10, labelpad=10)
    ax_gb.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax_gb.set_title("Global Buckling", fontsize=12)

    ax_sb.step(shell_buckling,
               z_mid,
               where="mid",
               color=COLORS_DICT["red_paper"],
               linewidth=1.5)
    ax_sb.set_xlabel("Shell Buckling", fontsize=10, labelpad=10)
    ax_sb.set_title("Shell Buckling", fontsize=12)

    for ax in axes:
        _style_axis(ax)
        ax.set_ylim(0, float(np.max(z_full)))

    if bounds:
        if "towerse.post.constr_global_buckling" in bounds:
            _draw_bound(ax_gb, bounds["towerse.post.constr_global_buckling"],
                        z_mid)
        if "towerse.post.constr_shell_buckling" in bounds:
            _draw_bound(ax_sb, bounds["towerse.post.constr_shell_buckling"],
                        z_mid)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_buckling_profile", save_svg)


def plot_deflection_profile(wt_opt, output_dir, bounds=None, save_svg=False):
    """Plot tower deflection vs height (1 panel)."""
    z_full = _full_heights(wt_opt)
    deflection = wt_opt.get_val("towerse.tower.tower_deflection").flatten()

    fig, ax = plt.subplots(figsize=(4, 5), facecolor="white")
    ax.plot(deflection, z_full, color=COLORS_DICT["red_paper"], linewidth=1.5)
    ax.set_xlabel("Deflection (m)", fontsize=10, labelpad=10)
    ax.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax.set_title("Tower Deflection", fontsize=12)
    _style_axis(ax)
    ax.set_ylim(0, float(np.max(z_full)))

    if bounds and "towerse.tower.tower_deflection" in bounds:
        _draw_bound(ax, bounds["towerse.tower.tower_deflection"], z_full)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_deflection_profile", save_svg)


def plot_tower_profiles(wt_opt, output_dir, bounds=None, save_svg=False):
    # pylint: disable=too-many-locals
    """Plot diameter + wall thickness + fatigue damage vs height (3 panels)."""
    outer_diameter = wt_opt.get_val("towerse.tower_outer_diameter")
    wall_thickness = wt_opt.get_val("towerse.tower_wall_thickness") * 1000
    z, z_mean = _tower_heights(wt_opt)
    section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
    try:
        fatigue_z = wt_opt.get_val("towerse.fatigue_z") - wt_opt.get_val(
            "towerse.z_start")
    except KeyError:
        fatigue_z = z_mean

    fig, axes = plt.subplots(1,
                             3,
                             figsize=(9, 5),
                             sharey=True,
                             facecolor="white")
    ax_d, ax_t, ax_dam = axes

    ax_d.plot(outer_diameter, z, color=COLORS_DICT["blue_paper"], linewidth=1.5)
    ax_d.set_xlabel("Outer Diameter (m)", fontsize=10, labelpad=10)
    ax_d.set_ylabel("Tower Height (m)", fontsize=10, labelpad=10)
    ax_d.set_title("Outer Diameter", fontsize=12)

    ax_t.step(wall_thickness,
              z_mean,
              where="mid",
              color=COLORS_DICT["blue_paper"],
              linewidth=1.5)
    ax_t.set_xlabel("Wall Thickness (mm)", fontsize=10, labelpad=10)
    ax_t.set_title("Wall Thickness", fontsize=12)

    ax_dam.step(section_damage,
                fatigue_z,
                where="mid",
                color=COLORS_DICT["red_paper"],
                linewidth=1.5)
    ax_dam.set_xlabel("Section Damage", fontsize=10, labelpad=10)
    ax_dam.set_title("Fatigue Damage", fontsize=12)

    for ax in axes:
        _style_axis(ax)
        ax.set_ylim(0, float(np.max(z)))

    if bounds:
        if "outer_diameter" in bounds:
            _draw_bound(ax_d, bounds["outer_diameter"], z)
        if "layer_thickness" in bounds:
            _draw_bound(ax_t, bounds["layer_thickness"], z_mean, scale=1000.0)
        if "towerse.fatigue_section_damage" in bounds:
            _draw_bound(ax_dam, bounds["towerse.fatigue_section_damage"],
                        fatigue_z)

    plt.tight_layout()
    return _save_figure(fig, output_dir, "tower_geometry_damage_profile",
                        save_svg)


def plot_all_profiles(wt_opt, output_dir, bounds=None, save_svg=False):
    """Generate every available tower profile plot.

    Saves the 3-panel combined (tower_geometry_damage_profile) plus each
    granular plot. Returns the list of saved paths.
    """
    return [
        plot_tower_profiles(wt_opt, output_dir, bounds, save_svg),
        plot_tower_geometry_profile(wt_opt, output_dir, bounds, save_svg),
        plot_damage_profile(wt_opt, output_dir, bounds, save_svg),
        plot_axial_stress_profile(wt_opt, output_dir, bounds, save_svg),
        plot_buckling_profile(wt_opt, output_dir, bounds, save_svg),
        plot_deflection_profile(wt_opt, output_dir, bounds, save_svg),
    ]
