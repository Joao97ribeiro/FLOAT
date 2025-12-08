"""Run a tower fatigue optimization using FLOAT."""

import os

import matplotlib.pyplot as plt

from wisdem import run_wisdem

# File Paths Setup
mydir = os.path.dirname(os.path.realpath(__file__))

# Path to input files
fname_wt_input = mydir + os.sep + "IEA-22-280-RWT.yaml"
fname_modeling_options = mydir + os.sep + "modeling_options_tower_fatigue.yaml"
fname_analysis_options = mydir + os.sep + "analysis_options.yaml"

# By setting hub height to 0.0, WISDEM uses the tower definition
overrides = {'configuration.hub_height_user': 0.0}

# Run WISDEM Optimization
wt_opt, analysis_options, opt_options = run_wisdem(fname_wt_input,
                                                   fname_modeling_options,
                                                   fname_analysis_options,
                                                   overridden_values=overrides)

# Output Key Geometry Results
outer_diameter = wt_opt.get_val("towerse.tower_outer_diameter")
wall_thickness = wt_opt.get_val("towerse.tower_wall_thickness") * 1000
z = wt_opt.get_val("towerse.z_param") - wt_opt.get_val("towerse.z_start")
z_mean_section = (z[:-1] + z[1:]) / 2

print("Optimized Tower Outer Diameter (m):", outer_diameter)
print("Optimized Tower Wall Thickness (mm):", wall_thickness)
print("Tower Section Midpoints - z (m):", z_mean_section)

# Output Key Fatigue Results
section_damage = wt_opt.get_val("towerse.fatigue_section_damage")
constant_c = wt_opt.get_val("towerse.fatigue_c")

print("Fatigue Damage by Section:", section_damage)
print("Fatigue Constant C:", constant_c)

# Plot Tower Geometry and Fatigue Results
fig, axes = plt.subplots(1, 3, figsize=(10, 10), sharey=True)
# --- 1) Outer Diameter vs Height ---
axes[0].plot(outer_diameter, z, label='Outer Diameter (m)', color='blue')
axes[0].set_xlabel('Outer Diameter (m)')
axes[0].set_ylabel('Height (m)')
axes[0].set_title('Tower Outer Diameter vs Height')
axes[0].grid()
axes[0].legend()
axes[0].set_ylim(0, max(z))

# --- 2) Wall Thickness vs Height ---
axes[1].step(wall_thickness,
             z_mean_section,
             where="mid",
             label='Wall Thickness (m)',
             color='green')
axes[1].set_xlabel('Wall Thickness (m)')
axes[1].set_title('Tower Wall Thickness vs Height')
axes[1].grid()
axes[1].legend()
axes[1].set_ylim(0, max(z))

# --- 3) Fatigue Damage vs Height ---
axes[2].plot(section_damage,
             z_mean_section,
             label='Fatigue Damage',
             color='red')
axes[2].set_xlabel('Fatigue Damage')
axes[2].set_title('Tower Fatigue Damage vs Height')
axes[2].grid()
axes[2].legend()
axes[2].set_ylim(0, max(z))

plt.tight_layout()

plot_dir = opt_options['general']['folder_output']
plt.savefig(os.path.join(plot_dir, 'tower_fatigue_results.png'))
plt.close()
