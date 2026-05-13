"""Run a tower fatigue analysis using FLOAT."""

import os

from wisdem import run_wisdem

import src

# Path to the shared 22MW fatigue inputs.
_INPUTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "input_files",
                 "22mw_fatigue_example"))

# Don't enforce hub_height, use the tower definition instead.
_OVERRIDES = {"configuration.hub_height_user": 0.0}

# Run WISDEM.
wt_opt, _, opt_options = run_wisdem(
    os.path.join(_INPUTS_DIR, "IEA-22-280-RWT_Floater.yaml"),
    os.path.join(_INPUTS_DIR, "modeling_options_tower_fatigue.yaml"),
    os.path.join(_INPUTS_DIR, "analysis_options.yaml"),
    overridden_values=_OVERRIDES,
)

# Log a structured summary table.
src.TowerSummaryExtractor(wt_opt).log_summary_table(
    title="22MW Tower Fatigue Analysis")

# Output key fatigue results.
section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
constant_c = wt_opt.get_val("towerse.fatigue_c")
print("Fatigue Damage by Section:", section_damage)
print("Fatigue Constant C:", constant_c)
