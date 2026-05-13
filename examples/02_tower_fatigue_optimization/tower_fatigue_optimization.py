"""Run a tower fatigue optimization using FLOAT."""

import os

from wisdem import run_wisdem

import pyfloat

# Path to the shared 22MW fatigue inputs.
_INPUTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "input_files",
                 "22mw_fatigue_example"))
_GEOMETRY = "IEA-22-280-RWT"
_MODELING = "modeling_options_tower_fatigue"
_ANALYSIS = "analysis_options_optimization"

# Don't enforce hub_height, use the tower definition instead.
_OVERRIDES = {"configuration.hub_height_user": 0.0}

# Run WISDEM optimization.
wt_opt, _, opt_options = run_wisdem(
    os.path.join(_INPUTS_DIR, f"{_GEOMETRY}.yaml"),
    os.path.join(_INPUTS_DIR, f"{_MODELING}.yaml"),
    os.path.join(_INPUTS_DIR, f"{_ANALYSIS}.yaml"),
    overridden_values=_OVERRIDES,
)

# Recover design variable + constraint bounds from the analysis YAML.
manager = pyfloat.TowerWisdemManager(files_dir=_INPUTS_DIR,
                                     geometry_filename=_GEOMETRY,
                                     modeling_filename=_MODELING,
                                     analysis_filename=_ANALYSIS)
_, dv_bounds = manager.get_design_variables()
_, constraint_bounds = manager.get_design_constraints()
bounds = {**dv_bounds, **constraint_bounds}

# Log a structured summary table.
pyfloat.TowerSummaryExtractor(wt_opt).log_summary_table(
    title="22MW Tower Fatigue Optimization")

# Output key geometry results.
outer_diameter = wt_opt.get_val("towerse.tower_outer_diameter")
wall_thickness = wt_opt.get_val("towerse.tower_wall_thickness") * 1000
z = wt_opt.get_val("towerse.z_param") - wt_opt.get_val("towerse.z_start")
z_mean_section = (z[:-1] + z[1:]) / 2
print("Optimized Tower Outer Diameter (m):", outer_diameter)
print("Optimized Tower Wall Thickness (mm):", wall_thickness)
print("Tower Section Midpoints - z (m):", z_mean_section)

# Output key fatigue results.
section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
constant_c = wt_opt.get_val("towerse.fatigue_c")
print("Fatigue Damage by Section:", section_damage)
print("Fatigue Constant C:", constant_c)

# Plot tower geometry + damage profile with the optimization bounds overlaid.
fig_path = pyfloat.plot_tower_profiles(wt_opt,
                                       opt_options["general"]["folder_output"],
                                       bounds=bounds)
print("Saved tower profiles figure to:", fig_path)
