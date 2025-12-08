"""Run a tower fatigue analysis using FLOAT."""

import os

from wisdem import run_wisdem

# File Paths Setup
mydir = os.path.dirname(os.path.realpath(__file__))

# Path to input files
fname_wt_input = mydir + os.sep + "IEA-22-280-RWT_Floater.yaml"
fname_modeling_options = mydir + os.sep + "modeling_options_tower_fatigue.yaml"
fname_analysis_options = mydir + os.sep + "analysis_options.yaml"

# By setting hub height to 0.0, WISDEM uses the tower definition
overrides = {'configuration.hub_height_user': 0.0}

# Run WISDEM
wt_opt, analysis_options, opt_options = run_wisdem(fname_wt_input,
                                                   fname_modeling_options,
                                                   fname_analysis_options,
                                                   overridden_values=overrides)

# Output Key Fatigue Results
section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
constant_c = wt_opt.get_val("towerse.fatigue_c")

print("Fatigue Damage by Section:", section_damage)
print("Fatigue Constant C:", constant_c)
