"""Regenerate the JSON data consumed by the FLOAT project page.

Run from the repo root:

    python docs/scripts/build_data.py

The script reads the bundled paper-workflow outputs under
`outputs/08_float_paper_workflow/` and writes:
- `docs/static/data/tower_profiles.json` (geometry + damage + stress profiles)
- `docs/static/data/optimization_convergence.json` (objective + constraints)
"""

import json
import pathlib

import pyfloat

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "static" / "data"
OUT.mkdir(parents=True, exist_ok=True)

CASES = {
    "ref": ROOT / "outputs/08_float_paper_workflow/ref/ref_tower.csv",
    "opt1": ROOT / "outputs/08_float_paper_workflow/opt1/opt1_tower.csv",
    "opt2": ROOT / "outputs/08_float_paper_workflow/opt2/opt2_tower.csv",
}

SQLS = {
    "opt1": ROOT / "outputs/08_float_paper_workflow/opt1/log_opt.sql",
    "opt2": ROOT / "outputs/08_float_paper_workflow/opt2/log_opt.sql",
}


def tower_profiles():
    """Extract per-section profiles from each case's tower CSV."""
    out = {}
    for tag, path in CASES.items():
        reader = pyfloat.TowerResultsCSVReader(str(path))
        geom = reader.get_geometry_profile()
        damage = reader.get_damage_profile()
        stress = reader.get_stress_profile()
        deflection = reader.get_deflection_profile()
        buckling = reader.get_buckling_profile()
        out[tag] = {
            "z": list(map(float, geom["z"])),
            "outer_diameter": list(map(float, geom["outer_diameter"])),
            "wall_thickness_mm": [
                x * 1000 for x in map(float, geom["wall_thickness"])
            ],
            "z_mean_section": list(map(float, damage["z_mean_section"])),
            "section_damage": list(map(float, damage["section_damage"])),
            "z_stress": list(map(float, stress["z_midpoints"])),
            "stress_MPa": [x / 1e6 for x in map(float, stress["stress"])],
            "z_deflection": list(map(float, deflection["z_full"])),
            "deflection": list(map(float, deflection["deflection"])),
            "z_buckling": list(map(float, buckling["z_midpoints"])),
            "shell_buckling": list(map(float, buckling["shell_buckling"])),
            "global_buckling": list(map(float, buckling["global_buckling"])),
        }
    return out


def optimization_convergence():
    """Pull objective + constraints evolution from each optimization's SQL."""
    out = {}
    for tag, path in SQLS.items():
        reader = pyfloat.TowerOptimizationResultsSQLReader(str(path), "tmp")
        iterations, obj, obj_name = reader.get_objective_function_evolution()
        cmax, cmin, is_vec = reader.get_constraints_evolution()
        out[tag] = {
            "iterations": list(map(int, iterations)),
            "objective_values": list(map(float, obj)),
            "objective_function": obj_name,
            "constraints_max": {
                k: list(map(float, v)) for k, v in cmax.items()
            },
            "constraints_min": {
                k: list(map(float, v)) for k, v in cmin.items()
            },
            "constraints_is_vector": {
                k: bool(v) for k, v in is_vec.items()
            },
        }
    return out


def main():
    """Build the two JSON files consumed by the project page."""
    with open(OUT / "tower_profiles.json", "w", encoding="utf-8") as file:
        json.dump(tower_profiles(), file)
    with open(OUT / "optimization_convergence.json", "w",
              encoding="utf-8") as file:
        json.dump(optimization_convergence(), file)
    print(f"Wrote tower_profiles.json + optimization_convergence.json to {OUT}")


if __name__ == "__main__":
    main()
