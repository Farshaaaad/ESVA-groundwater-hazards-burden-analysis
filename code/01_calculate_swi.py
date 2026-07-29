# -*- coding: utf-8 -*-
"""
Calculate annual and peak seawater-intrusion (SWI) classifications for
census-block groundwater summaries stored in an ArcGIS feature class.

The final SWI class is the highest class indicated independently by:

1. projected chloride concentration;
2. absolute chloride increase from the 2023 baseline; or
3. relative chloride increase from the 2023 baseline.

Relative-change classes are continuous, with no 100%-250% gap:

    No SWI     < 5%
    Slight      5% to < 10%
    Early      10% to < 20%
    Moderate   20% to < 250%
    High      250% to < 500%
    Extreme   >= 500%

To limit small-denominator artifacts, relative change is set to zero when
the baseline chloride concentration is below 10 mg/L or the absolute increase
is below 10 mg/L.

This script is designed for the Python environment installed with ArcGIS Pro.
It adds missing output fields, recalculates annual and peak SWI results for
both SSP2-4.5 and SSP5-8.5, and can write a CSV quality-assurance log of
changes to output fields that already existed before the script was run.

Author: Farshad Hesamfar
Affiliation: University of Virginia
Contact: wky7xx@virginia.edu

Example
-------
python 01_calculate_swi.py ^
  --feature-class "C:/project/analysis.gdb/ESVA_blocks" ^
  --qa-output "C:/project/outputs/swi_recalculation_qa.csv"
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable, Sequence

import arcpy


DEFAULT_YEARS = (2030, 2040, 2050, 2060, 2080)
DEFAULT_SCENARIOS = ("Int", "High")
DEFAULT_MODELS = ("BCC", "CAN", "ENS", "MIR", "MRI")
DEFAULT_BASE_FIELD = "AW_CONC_MG_T1"
DEFAULT_GEOID_FIELD = "GEOID20"

CLASS_ORDER = {
    "No SWI": 0,
    "Slight": 1,
    "Early": 2,
    "Moderate": 3,
    "High": 4,
    "Extreme": 5,
}

CLASS_SCORE = {
    "No SWI": 0.0,
    "Slight": 0.2,
    "Early": 0.4,
    "Moderate": 0.6,
    "High": 0.8,
    "Extreme": 1.0,
}


def is_missing(value: object) -> bool:
    """Return True for None or non-finite numeric values."""
    if value is None:
        return True
    if isinstance(value, (int, float)):
        return not math.isfinite(float(value))
    return False


def class_from_absolute_concentration(value: float) -> str:
    """Classify projected chloride concentration in mg/L."""
    if value < 100.0:
        return "No SWI"
    if value < 200.0:
        return "Slight"
    if value < 250.0:
        return "Early"
    if value < 500.0:
        return "Moderate"
    if value < 1000.0:
        return "High"
    return "Extreme"


def class_from_absolute_change(value: float) -> str:
    """Classify absolute chloride increase from the 2023 baseline in mg/L."""
    if value < 10.0:
        return "No SWI"
    if value < 25.0:
        return "Slight"
    if value < 50.0:
        return "Early"
    if value < 250.0:
        return "Moderate"
    if value < 1000.0:
        return "High"
    return "Extreme"


def class_from_relative_change(value: float) -> str:
    """Classify filtered relative chloride increase from the baseline."""
    if value < 5.0:
        return "No SWI"
    if value < 10.0:
        return "Slight"
    if value < 20.0:
        return "Early"
    if value < 250.0:
        return "Moderate"
    if value < 500.0:
        return "High"
    return "Extreme"


def highest_class(*labels: str) -> str:
    """Return the most severe valid SWI class."""
    return max(labels, key=CLASS_ORDER.__getitem__)


def classify_swi(
    baseline_concentration: float | None,
    future_concentration: float | None,
) -> tuple[str, float | None, float | None]:
    """
    Return final class, absolute change, and filtered relative change.

    Relative change is set to zero when baseline chloride is below 10 mg/L
    or absolute chloride increase is below 10 mg/L.
    """
    if is_missing(baseline_concentration) or is_missing(future_concentration):
        return "No Data", None, None

    baseline = float(baseline_concentration)
    future = float(future_concentration)
    delta_abs = future - baseline

    if baseline < 10.0 or delta_abs < 10.0:
        delta_pct = 0.0
    else:
        delta_pct = 100.0 * delta_abs / baseline

    final_label = highest_class(
        class_from_absolute_concentration(future),
        class_from_absolute_change(delta_abs),
        class_from_relative_change(delta_pct),
    )
    return final_label, delta_abs, delta_pct


def parse_csv_list(value: str, cast=str) -> tuple:
    """Parse a comma-separated command-line value."""
    return tuple(cast(item.strip()) for item in value.split(",") if item.strip())


def list_field_names(feature_class: str) -> set[str]:
    """Return all field names in a feature class."""
    return {field.name for field in arcpy.ListFields(feature_class)}


def require_fields(feature_class: str, fields: Iterable[str]) -> None:
    """Raise a clear error if required source fields are absent."""
    existing = list_field_names(feature_class)
    missing = [field for field in fields if field not in existing]
    if missing:
        raise KeyError(
            "Required source fields are missing from the feature class: "
            + ", ".join(missing)
        )


def ensure_field(
    feature_class: str,
    field_name: str,
    field_type: str,
    *,
    field_length: int | None = None,
    alias: str | None = None,
) -> None:
    """Add an output field only when it does not already exist."""
    if field_name in list_field_names(feature_class):
        return

    kwargs = {}
    if field_length is not None:
        kwargs["field_length"] = field_length
    if alias is not None:
        kwargs["field_alias"] = alias

    arcpy.management.AddField(
        feature_class,
        field_name,
        field_type,
        **kwargs,
    )


def output_field_names(year: int, scenario: str) -> dict[str, str]:
    """Return annual output fields for one year and scenario."""
    return {
        "maximum": f"Max_Conc_{year}_{scenario}",
        "model": f"SWI_Model_{year}_{scenario}",
        "level": f"SWI_Level_{year}_{scenario}",
        "delta_abs": f"Delta_Abs_{year}_{scenario}",
        "delta_pct": f"Delta_Pct_{year}_{scenario}",
    }


def peak_field_names(scenario: str) -> dict[str, str]:
    """Return peak output fields for one emissions scenario."""
    return {
        "maximum": f"Peak_Conc_{scenario}",
        "year": f"Peak_Year_{scenario}",
        "model": f"Peak_Model_{scenario}",
        "level": f"Haz_SWI_Peak_{scenario}",
        "score": f"Haz_SWI_Score_{scenario}",
        "delta_abs": f"Peak_Delta_Abs_{scenario}",
        "delta_pct": f"Peak_Delta_Pct_{scenario}",
    }


def add_output_fields(
    feature_class: str,
    years: Sequence[int],
    scenarios: Sequence[str],
) -> None:
    """Add all annual and peak fields required by the workflow."""
    ensure_field(
        feature_class,
        "SWI_Level_2023",
        "TEXT",
        field_length=12,
        alias="SWI Class - Baseline 2023",
    )

    year_span = f"{min(years)}-{max(years)}"

    for scenario in scenarios:
        for year in years:
            fields = output_field_names(year, scenario)
            ensure_field(
                feature_class,
                fields["maximum"],
                "DOUBLE",
                alias=f"Peak Chloride - {scenario}, {year} (mg/L)",
            )
            ensure_field(
                feature_class,
                fields["model"],
                "TEXT",
                field_length=12,
                alias=f"Controlling SWI Model - {scenario}, {year}",
            )
            ensure_field(
                feature_class,
                fields["level"],
                "TEXT",
                field_length=12,
                alias=f"SWI Class - {scenario}, {year}",
            )
            ensure_field(
                feature_class,
                fields["delta_abs"],
                "DOUBLE",
                alias=f"Chloride Increase - {scenario}, {year} (mg/L)",
            )
            ensure_field(
                feature_class,
                fields["delta_pct"],
                "DOUBLE",
                alias=f"Chloride Increase - {scenario}, {year} (%)",
            )

        peak = peak_field_names(scenario)
        ensure_field(
            feature_class,
            peak["maximum"],
            "DOUBLE",
            alias=f"Peak Chloride - {scenario}, {year_span} (mg/L)",
        )
        ensure_field(
            feature_class,
            peak["year"],
            "SHORT",
            alias=f"Peak Chloride Year - {scenario}",
        )
        ensure_field(
            feature_class,
            peak["model"],
            "TEXT",
            field_length=12,
            alias=f"Peak SWI Model - {scenario}",
        )
        ensure_field(
            feature_class,
            peak["level"],
            "TEXT",
            field_length=12,
            alias=f"Peak SWI Class - {scenario}",
        )
        ensure_field(
            feature_class,
            peak["score"],
            "DOUBLE",
            alias=f"Peak SWI Hazard Score - {scenario}",
        )
        ensure_field(
            feature_class,
            peak["delta_abs"],
            "DOUBLE",
            alias=f"Peak Chloride Increase - {scenario} (mg/L)",
        )
        ensure_field(
            feature_class,
            peak["delta_pct"],
            "DOUBLE",
            alias=f"Peak Chloride Increase - {scenario} (%)",
        )


def values_differ(
    old_value: object,
    new_value: object,
    tolerance: float = 1e-9,
) -> bool:
    """Compare text or numeric values while treating nulls consistently."""
    old_missing = is_missing(old_value)
    new_missing = is_missing(new_value)

    if old_missing and new_missing:
        return False
    if old_missing != new_missing:
        return True

    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        return abs(float(old_value) - float(new_value)) > tolerance

    return str(old_value).strip() != str(new_value).strip()


def append_qa(
    qa_rows: list[dict[str, object]],
    preexisting_fields: set[str],
    geoid: object,
    field_name: str,
    old_value: object,
    new_value: object,
) -> None:
    """Record a changed value only when the output field pre-existed."""
    if field_name not in preexisting_fields:
        return
    if values_differ(old_value, new_value):
        qa_rows.append(
            {
                "GEOID20": "" if geoid is None else str(geoid),
                "field": field_name,
                "original_value": old_value,
                "recalculated_value": new_value,
            }
        )


def calculate_swi(
    feature_class: str,
    base_field: str,
    geoid_field: str,
    years: Sequence[int],
    scenarios: Sequence[str],
    models: Sequence[str],
    preexisting_fields: set[str],
) -> list[dict[str, object]]:
    """Recalculate baseline, annual, and peak SWI outputs."""
    qa_rows: list[dict[str, object]] = []

    source_fields = [
        f"AW_conc_{year}_mgL_{model}_{scenario}"
        for scenario in scenarios
        for year in years
        for model in models
    ]
    require_fields(feature_class, [geoid_field, base_field, *source_fields])

    with arcpy.da.UpdateCursor(
        feature_class,
        [geoid_field, base_field, "SWI_Level_2023"],
    ) as cursor:
        for row in cursor:
            geoid, baseline, old_level = row
            new_level = (
                "No Data"
                if is_missing(baseline)
                else class_from_absolute_concentration(float(baseline))
            )
            append_qa(
                qa_rows,
                preexisting_fields,
                geoid,
                "SWI_Level_2023",
                old_level,
                new_level,
            )
            row[2] = new_level
            cursor.updateRow(row)

    for scenario in scenarios:
        annual_results: dict[object, list[tuple[int, str, float]]] = {}

        for year in years:
            source_model_fields = [
                f"AW_conc_{year}_mgL_{model}_{scenario}"
                for model in models
            ]
            target = output_field_names(year, scenario)

            cursor_fields = [
                geoid_field,
                base_field,
                *source_model_fields,
                target["maximum"],
                target["model"],
                target["level"],
                target["delta_abs"],
                target["delta_pct"],
            ]
            target_start = 2 + len(source_model_fields)

            with arcpy.da.UpdateCursor(feature_class, cursor_fields) as cursor:
                for row in cursor:
                    geoid = row[0]
                    baseline = row[1]
                    source_values = row[2:target_start]

                    valid = [
                        (model, float(value))
                        for model, value in zip(models, source_values)
                        if not is_missing(value)
                    ]
                    old_values = row[target_start:target_start + 5]

                    if not valid:
                        new_values = [None, "N/A", "No Data", None, None]
                    else:
                        controlling_model, maximum = max(
                            valid,
                            key=lambda item: item[1],
                        )
                        level, delta_abs, delta_pct = classify_swi(
                            baseline,
                            maximum,
                        )
                        new_values = [
                            maximum,
                            controlling_model,
                            level,
                            delta_abs,
                            delta_pct,
                        ]
                        annual_results.setdefault(geoid, []).append(
                            (year, controlling_model, maximum)
                        )

                    for field_name, old_value, new_value in zip(
                        (
                            target["maximum"],
                            target["model"],
                            target["level"],
                            target["delta_abs"],
                            target["delta_pct"],
                        ),
                        old_values,
                        new_values,
                    ):
                        append_qa(
                            qa_rows,
                            preexisting_fields,
                            geoid,
                            field_name,
                            old_value,
                            new_value,
                        )

                    row[target_start:target_start + 5] = new_values
                    cursor.updateRow(row)

        peak = peak_field_names(scenario)
        peak_cursor_fields = [
            geoid_field,
            base_field,
            peak["maximum"],
            peak["year"],
            peak["model"],
            peak["level"],
            peak["score"],
            peak["delta_abs"],
            peak["delta_pct"],
        ]

        with arcpy.da.UpdateCursor(feature_class, peak_cursor_fields) as cursor:
            for row in cursor:
                geoid = row[0]
                baseline = row[1]
                candidates = annual_results.get(geoid, [])
                old_values = row[2:9]

                if not candidates:
                    new_values = [
                        None,
                        None,
                        "N/A",
                        "No Data",
                        None,
                        None,
                        None,
                    ]
                else:
                    peak_year, peak_model, peak_value = max(
                        candidates,
                        key=lambda item: item[2],
                    )
                    peak_level, delta_abs, delta_pct = classify_swi(
                        baseline,
                        peak_value,
                    )
                    new_values = [
                        peak_value,
                        peak_year,
                        peak_model,
                        peak_level,
                        CLASS_SCORE.get(peak_level),
                        delta_abs,
                        delta_pct,
                    ]

                for field_name, old_value, new_value in zip(
                    (
                        peak["maximum"],
                        peak["year"],
                        peak["model"],
                        peak["level"],
                        peak["score"],
                        peak["delta_abs"],
                        peak["delta_pct"],
                    ),
                    old_values,
                    new_values,
                ):
                    append_qa(
                        qa_rows,
                        preexisting_fields,
                        geoid,
                        field_name,
                        old_value,
                        new_value,
                    )

                row[2:9] = new_values
                cursor.updateRow(row)

    return qa_rows


def write_qa_csv(
    qa_rows: Sequence[dict[str, object]],
    output_path: str | Path,
) -> Path:
    """Write the recalculation QA log."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "GEOID20",
        "field",
        "original_value",
        "recalculated_value",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(qa_rows)

    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate annual and peak SWI classifications in an ArcGIS "
            "feature class."
        )
    )
    parser.add_argument(
        "--feature-class",
        required=True,
        help="Path to the input/output ArcGIS feature class.",
    )
    parser.add_argument(
        "--base-field",
        default=DEFAULT_BASE_FIELD,
        help=f"2023 baseline chloride field (default: {DEFAULT_BASE_FIELD}).",
    )
    parser.add_argument(
        "--geoid-field",
        default=DEFAULT_GEOID_FIELD,
        help=f"Block identifier field (default: {DEFAULT_GEOID_FIELD}).",
    )
    parser.add_argument(
        "--years",
        default=",".join(map(str, DEFAULT_YEARS)),
        help="Comma-separated analysis years.",
    )
    parser.add_argument(
        "--scenarios",
        default=",".join(DEFAULT_SCENARIOS),
        help="Comma-separated scenario suffixes.",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated model or ensemble field suffixes.",
    )
    parser.add_argument(
        "--qa-output",
        default=None,
        help=(
            "Optional CSV path documenting changes to output fields that "
            "already existed before the script was run."
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    feature_class = args.feature_class
    if not arcpy.Exists(feature_class):
        raise FileNotFoundError(
            f"ArcGIS feature class not found: {feature_class}"
        )

    years = parse_csv_list(args.years, int)
    scenarios = parse_csv_list(args.scenarios, str)
    models = parse_csv_list(args.models, str)

    if not years or not scenarios or not models:
        raise ValueError(
            "At least one year, scenario, and model must be supplied."
        )

    arcpy.env.overwriteOutput = True
    preexisting_fields = list_field_names(feature_class)

    print(f"Feature class: {feature_class}")
    print(f"Years: {years}")
    print(f"Scenarios: {scenarios}")
    print(f"Models and ensemble fields: {models}")

    add_output_fields(feature_class, years, scenarios)

    qa_rows = calculate_swi(
        feature_class=feature_class,
        base_field=args.base_field,
        geoid_field=args.geoid_field,
        years=years,
        scenarios=scenarios,
        models=models,
        preexisting_fields=preexisting_fields,
    )

    if args.qa_output:
        qa_path = write_qa_csv(qa_rows, args.qa_output)
        print(f"QA log saved to: {qa_path}")

    print(f"Changed pre-existing field values recorded: {len(qa_rows):,}")
    print("Annual and peak SWI calculations completed successfully.")


if __name__ == "__main__":
    main()
