# pylint: disable=import-error
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
"""Tower summary analysis utilities for FLOAT results."""

import os
import json
import logging
import ast
from typing import Any, Dict, Union, Optional

import pandas as pd
import numpy as np
from tabulate import tabulate


class TowerSummaryExtractor:
    """
    Extracts and formats summary metrics from WISDEM tower results.
    
    This class supports two input types: a live WISDEM optimization object
    (`wt_opt`) or a CSV file previously saved with variables and values. It
    extracts key metrics such as mass, cost, geometry, and structural
    performance, and provides export functions to JSON, CSV, and human-readable
    table formats.
    """

    def __init__(self, source):
        """
        Initialize the extractor with either a WISDEM object or CSV file.

        Args:
            source: A WISDEM wt_opt object (with .get_val) or a path to a CSV
              file.

        Raises:
            ValueError: If the source type is unsupported.
        """
        if hasattr(source, "get_val"):
            self.mode = "live"
            self.wt_opt = source
            self.df = None
        elif isinstance(source, str) and source.endswith(".csv"):
            self.mode = "csv"
            self.df = pd.read_csv(source)
            self.wt_opt = None
        else:
            raise ValueError(
                "source must be a WISDEM wt_opt object or a .csv file path.")

        self.summary = {}

    def _get_val_safe(self,
                      name: str,
                      unit: Optional[str] = None) -> Optional[Any]:
        """
        Safely retrieves a value by name.

        Args:
            name (str): The variable name to retrieve.
            unit (Optional[str]): Unit to convert to (used only in live mode).

        Returns:
            The value retrieved, parsed and flattened if necessary, or None if
              not found or failed.
        """
        if self.mode == "live":
            try:
                return self.wt_opt.get_val(
                    name, unit) if unit else self.wt_opt.get_val(name)
            except (KeyError, AttributeError, TypeError):
                return None

        if self.mode == "csv":
            try:
                val = self.df.loc[self.df["variables"] == name,
                                  "values"].values[0]
                parsed = ast.literal_eval(val)
                return np.array(parsed).flatten() if isinstance(
                    parsed, (list, tuple)) else float(parsed)
            except (IndexError, ValueError, SyntaxError, TypeError):
                return None

        return None

    def _format_val(self, val: Any,
                    unit: str) -> Optional[Dict[str, Union[float, str]]]:
        """
        Format a scalar or array value into a standardized dictionary format.

        Args:
            val (Any): The value to format. Can be scalar or array-like.
            unit (str): The unit associated with the value.

        Returns:
            dict or None: A dictionary with 'value' or 'min'/'max' and 'unit',
              or None if val is None.
        """
        if val is None:
            return None

        # Scalar case
        if np.isscalar(val) or np.size(val) == 1:
            scalar_val = float(val.item() if hasattr(val, "item") else val)
            return {"value": scalar_val, "unit": unit}

        # Array-like case
        if val.ndim > 1:
            val = val[0]
        result = {
            "min": float(np.min(val)),
            "max": float(np.max(val)),
            "bottom": float(val[0]),
            "top": float(val[-1]),
            "unit": unit
        }
        if np.size(val) > 1:
            result["array"] = np.array(val, dtype=float).tolist()

        return result

    def extract(self) -> dict:
        """
        Extract summary metrics from the WISDEM model or CSV.

        Returns:
            dict: Dictionary containing grouped metrics under keys like 
              'mass_and_cost', 'geometry', and 'analysis', each with value/unit
              or min/max/unit.
        """

        self.summary = {
            "mass_and_cost": {
                "tower_mass":
                    self._format_val(
                        self._get_val_safe("towerse.tower_mass", "kg"), "kg"),
                "tower_cost":
                    self._format_val(
                        self._get_val_safe("towerse.tower_cost", "USD"), "USD"),
            },
            "geometry": {
                "outer_diameter":
                    self._format_val(
                        self._get_val_safe("towerse.tower_outer_diameter", "m"),
                        "m"),
                "layer_thickness":
                    self._format_val(
                        self._get_val_safe("towerse.tower_layer_thickness",
                                           "m"), "m"),
                "wall_thickness":
                    self._format_val(
                        self._get_val_safe("towerse.tower_wall_thickness", "m"),
                        "m"),
                "d_to_t":
                    self._format_val(
                        self._get_val_safe("towerse.constr_d_to_t"), "-"),
                "taper":
                    self._format_val(self._get_val_safe("towerse.constr_taper"),
                                     "-"),
                "slope":
                    self._format_val(self._get_val_safe("towerse.slope"), "-"),
                "thickness_slope":
                    self._format_val(
                        self._get_val_safe("towerse.thickness_slope"), "-"),
            },
            "analysis": {
                "frequency_1":
                    self._format_val(
                        self._get_val_safe("towerse.tower.f1", "Hz"), "Hz"),
                "deflection":
                    self._format_val(
                        self._get_val_safe("towerse.tower.tower_deflection",
                                           "m"), "m"),
                "stress":
                    self._format_val(
                        self._get_val_safe("towerse.post.axial_stress") / 1e6,
                        "MPa"),
                "global_buckling":
                    self._format_val(
                        self._get_val_safe(
                            "towerse.post.constr_global_buckling"), "-"),
                "shell_buckling":
                    self._format_val(
                        self._get_val_safe(
                            "towerse.post.constr_shell_buckling"), "-"),
                "fatigue_damage":
                    self._format_val(
                        self._get_val_safe("towerse.fatigue_section_damage"),
                        "-"),
            }
        }
        return self.summary

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the summary dictionary to a pandas DataFrame.

        Returns:
            pd.DataFrame: Table with columns [Category, Metric, Value, Min, Max, 
              Unit].
        """
        if not self.summary:
            self.extract()

        rows = []
        for category, metrics in self.summary.items():
            for name, val in metrics.items():
                if val is None:
                    continue
                rows.append({
                    "Category": category,
                    "Metric": name,
                    "Value": val.get("value"),
                    "Min": val.get("min"),
                    "Max": val.get("max"),
                    "Unit": val.get("unit", "-")
                })

        return pd.DataFrame(rows)

    def save_to_json(self,
                     json_dir: str,
                     filename: str = "tower_summary.json") -> None:
        """
        Save the full structured summary to a JSON file.

        Args:
            json_dir (str): Directory where the JSON file will be saved.
            filename (str): Filename for the JSON file (default:
              'tower_summary.json').
        """
        if not self.summary:
            self.extract()

        os.makedirs(json_dir, exist_ok=True)
        json_path = os.path.join(json_dir, filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2, ensure_ascii=False)

    def log_summary_table(self, title="Tower Summary") -> None:
        """
        Logs the tower summary table using the logging module.

        Args:
            title (str): Title of the table in the log output.
        """
        logging.basicConfig(level=logging.INFO, format="%(message)s")

        df = self.to_dataframe()
        df["Value"] = df.apply(
            lambda row: f"{row['Min']:.2f} - {row['Max']:.2f}" if pd.isna(row[
                "Value"]) and not pd.isna(row["Min"]) else f"{row['Value']:.2f}"
            if not pd.isna(row["Value"]) else "",
            axis=1)

        header = "\n" + "=" * len(title) + f"\n{title}\n" + "=" * len(title)
        table = tabulate(df[["Category", "Metric", "Value", "Unit"]],
                         headers="keys",
                         tablefmt="grid")

        logging.info(header + "\n" + table)


class TowerSummaryComparator:
    """
    Compares summary metrics between two wind turbine tower configurations.

    This class takes two sources of tower design results—either WISDEM `wt_opt` 
    objects or paths to CSV files exported from WISDEM—and performs a
    metric-by-metric comparison. It supports both scalar and interval-based
    values, such as mass, cost, geometry, and structural performance indicators.
    """

    def __init__(self, source1, source2):
        """
        Initialize the comparator with two tower summary sources.

        Args:
            source1: First tower data source, either a WISDEM wt_opt object or a
              path to a CSV file. Represents the baseline (original or 
              unoptimized) tower.
            source2: Second tower data source, either a WISDEM wt_opt object or
              a path to a CSV file. Represents the optimized tower.
        """
        self.extractor1 = TowerSummaryExtractor(source1)
        self.extractor2 = TowerSummaryExtractor(source2)

        self.summary1 = self.extractor1.extract()
        self.summary2 = self.extractor2.extract()

        self.summary = {}

    def _compute_rel_diff(self,
                          baseline: float,
                          new: float,
                          eps: float = 1e-12) -> float:
        """
        Compute the relative difference (percentage change) between a baseline
        value and a new value, safely handling near-zero denominators.
        
        Args:
            baseline (float): The original value.
            new (float): The new value.
            eps (float): Small threshold to avoid division by zero.
            
        Returns:
            float: Relative difference in percentage, rounded to 2 decimals.
        """
        if baseline is None:
            return np.nan
        b = float(baseline)
        if abs(b) < eps:
            return np.nan
        return round((float(new) - b) / (b) * 100.0, 2)

    def _format_val(self, val: dict) -> str:
        """
        Formats a value dictionary into a string for display.
        
        Handles scalar and interval formats.

        Args:
            val (dict): Dictionary with 'value' or 'min'/'max'.

        Returns:
            str: Formatted string representation.
        """
        if not val:
            return ""

        try:
            if "value" in val and val["value"] is not None:
                return f"{float(val['value']):.3f}"
            if "min" in val and "max" in val and val["min"] is not None and val[
                    "max"] is not None:
                return f"{float(val['min']):.3f} - {float(val['max']):.3f}"
        except (ValueError, TypeError):
            pass

        return ""

    def _compute_metrics_diff_from_dicts(self, val1: dict, val2: dict) -> dict:
        """Compute absolute and relative differences between two dictionaries.

        This method compares scalar values, optional bottom/top values, and
        arrays if present in both dictionaries. It returns a dictionary of
        difference metrics such as relative differences (percent change),
        absolute ranges, and indices of minimum/maximum differences.

        Args:
            val1 (dict): Baseline or reference dictionary with optional keys:
                - "value" (float): scalar reference value
                - "bottom" (float): bottom reference value
                - "top" (float): top reference value
                - "array" (list[float]): sequence of reference values
            val2 (dict): New or updated dictionary with the same optional keys.

        Returns:
            dict: Dictionary with computed metrics. Keys may include:
                - "rel_diff" (str): Relative difference (%) for scalar value or 
                min–max relative difference for arrays.
                - "rel_diff_bottom_top" (str): Relative differences for bottom
                and top values (if available).
                - "array_abs_diff_range" (str): Min–max absolute difference for 
                arrays.
                - "array_rel_diff_id" (str): Indices of min–max relative
                differences in the array.

        Notes:
            - Relative differences are computed as percentage change relative to
              val1.
            - If denominators are near zero, results are set to NaN.
        """
        out = {"rel_diff": ""}

        if not val1 or not val2:
            return out

        try:
            # Scalar comparison
            if "value" in val1 and "value" in val2 and val1[
                    "value"] is not None and val2["value"] is not None:
                before = float(val1["value"])
                after = float(val2["value"])
                rel = self._compute_rel_diff(before, after)

                out["diff"] = f"{after-before:.3f}"
                out["rel_diff"] = f"{rel}"

            # Bottom/Top comparison
            if "bottom" in val1 and "bottom" in val2 and val1[
                    "bottom"] is not None and val2["bottom"] is not None:
                rel_diff_bottom = self._compute_rel_diff(
                    float(val1["bottom"]), float(val2["bottom"]))
                rel_diff_top = self._compute_rel_diff(float(val1["top"]),
                                                      float(val2["top"]))
                rel_diff_bottom = f"{rel_diff_bottom}"
                rel_diff_top = f"{rel_diff_top}"

                before_bottom = float(val1["bottom"])
                after_bottom = float(val2["bottom"])
                before_top = float(val1["top"])
                after_top = float(val2["top"])

                out["before_bottom_top"] = (
                    f"{before_bottom:.3f} - {before_top:.3f}")
                out["after_bottom_top"] = (
                    f"{after_bottom:.3f} - {after_top:.3f}")
                out["rel_diff_bottom_top"] = (
                    f"{rel_diff_bottom} - {rel_diff_top}")

            # Array comparison
            if "array" in val1 and "array" in val2 and val1["array"] and val2[
                    "array"]:
                a1 = np.array(val1["array"], dtype=float)
                a2 = np.array(val2["array"], dtype=float)

                # Relative differences (%), ignoring near-zero denominators
                denom = np.where(np.abs(a1) < 1e-12, np.nan, a1)
                diff = a2 - a1
                rel = diff / denom
                rel = np.round(rel * 100, 2)

                # Min/max relative differences with indices
                if np.all(np.isnan(rel)):
                    array_rel_diff_max = "nan"
                    array_rel_diff_max_id = "-"
                    array_rel_diff_min = "nan"
                    array_rel_diff_min_id = "-"
                else:
                    rel_max_val = np.nanmax(rel)
                    rel_min_val = np.nanmin(rel)
                    rel_max_idx = int(np.nanargmax(rel)) + 1
                    rel_min_idx = int(np.nanargmin(rel)) + 1

                    array_rel_diff_max = f"{rel_max_val}"
                    array_rel_diff_max_id = f"{rel_max_idx}/{len(rel)}"
                    array_rel_diff_min = f"{rel_min_val}"
                    array_rel_diff_min_id = f"{rel_min_idx}/{len(rel)}"

                max_diff = np.nanmax(diff)
                min_diff = np.nanmin(diff)
                max_diif_idx = int(np.nanargmax(diff)) + 1
                min_diff_idx = int(np.nanargmin(diff)) + 1
                rel_max_diff = rel[max_diif_idx -
                                   1] if max_diif_idx > 0 else np.nan
                rel_min_diff = rel[min_diff_idx -
                                   1] if min_diff_idx > 0 else np.nan

                out["diff_min_max"] = f"{min_diff:.3f} - {max_diff:.3f}"
                out["ref_diff_diff_min_max"] = (
                    f"{rel_min_diff:.3f} - {rel_max_diff:.3f}")
                out["min_max_diff_id"] = (
                    f"{min_diff_idx}/{len(diff)} - {max_diif_idx}/{len(diff)}")

                out["rel_diff"] = f"{array_rel_diff_min} - {array_rel_diff_max}"
                out["array_rel_diff_id"] = (
                    f"{array_rel_diff_min_id} - {array_rel_diff_max_id}")

        except (TypeError, ValueError, ZeroDivisionError):
            # Fail gracefully if input parsing or calculations fail
            pass

        return out

    def extract(self) -> dict:
        """
        Extract the comparison as a nested dictionary by category and metric.

        Returns:
            dict: Structured comparison with before, after, diff, and unit.
        """
        summary = {}
        all_categories = set(self.summary1.keys()).union(self.summary2.keys())

        for category in sorted(all_categories):
            metrics1 = self.summary1.get(category, {})
            metrics2 = self.summary2.get(category, {})
            all_metrics = set(metrics1.keys()).union(metrics2.keys())

            summary[category] = {}
            for metric in sorted(all_metrics):
                val1 = metrics1.get(metric)
                val2 = metrics2.get(metric)

                unit = val1.get("unit") if val1 else val2.get("unit", "-")

                diffs = self._compute_metrics_diff_from_dicts(val1, val2)

                summary[category][metric] = {
                    "before": self._format_val(val1),
                    "after": self._format_val(val2),
                    "unit": unit
                }
                # attach optional relative diff keys if present
                for k in ("diff", "rel_diff", "before_bottom_top",
                          "after_bottom_top", "rel_diff_bottom_top",
                          "diff_min_max", "ref_diff_diff_min_max",
                          "min_max_diff_id", "array_rel_diff_id"):
                    if k in diffs and diffs[k] != "":
                        summary[category][metric][k] = diffs[k]

        self.summary = summary
        return self.summary

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the comparison summary dictionary to a pandas DataFrame.

        Returns:
            pd.DataFrame: Table with columns [Category, Metric, Before, After, 
              Diff, Unit].
        """
        if not self.summary:
            self.extract()
        rows = []

        for category, metrics in self.extract().items():
            for metric, values in metrics.items():
                rows.append({
                    "Category":
                        category,
                    "Metric":
                        metric,
                    "Before":
                        values["before"],
                    "After":
                        values["after"],
                    "Unit":
                        values["unit"],
                    "Rel Diff":
                        values.get("rel_diff", ""),
                    "Rel Diff Bottom-Top":
                        values.get("rel_diff_bottom_top", ""),
                })

        return pd.DataFrame(rows)

    def save_to_json(self,
                     json_dir: str,
                     filename: str = "tower_summary_comparison.json") -> None:
        """
        Save the full structured summary to a JSON file.

        Args:
            json_dir (str): Directory where the JSON file will be saved.
            filename (str): Filename for the JSON file (default:
              'tower_summary_comparison.json').
        """
        if not self.summary:
            self.extract()

        os.makedirs(json_dir, exist_ok=True)
        json_path = os.path.join(json_dir, filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2, ensure_ascii=False)

    def log_summary_table(self,
                          title: str = "Tower Summary Comparison") -> None:
        """
            Logs the tower summary table using the logging module.
            
            Args:
                title (str): Title of the table in the log output.
            """
        logging.basicConfig(level=logging.INFO, format="%(message)s")

        df = self.to_dataframe()

        header = "\n" + "=" * len(title) + f"\n{title}\n" + "=" * len(title)
        table = tabulate(df, headers="keys", tablefmt="grid")
        logging.info(header + "\n" + table)
