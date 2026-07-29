# -*- coding: utf-8 -*-
"""
Calculate census-block area-weighted means from an ArcGIS intersection layer.

This optional ArcPy script is intended for researchers who have access to the
underlying groundwater-model grid intersections. It is not required when the
repository begins with the shared analysis-ready block-level table.

Author: Farshad Hesamfar
University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import arcpy


def safe_name(name: str, max_length: int = 45) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or not name[0].isalpha():
        name = "F_" + name
    return name[:max_length]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intersect-fc", required=True)
    parser.add_argument("--blocks-fc", required=True)
    parser.add_argument("--block-id", default="GEOID20")
    parser.add_argument("--area-field", default="Shape_Area")
    parser.add_argument(
        "--value-fields",
        required=True,
        help="Semicolon-separated numeric fields to aggregate.",
    )
    parser.add_argument("--output-table", required=True)
    parser.add_argument(
        "--join-results",
        action="store_true",
        help="Join calculated fields back to the block feature class.",
    )
    args = parser.parse_args()

    arcpy.env.overwriteOutput = True

    value_fields = [
        field.strip()
        for field in args.value_fields.split(";")
        if field.strip()
    ]
    if not value_fields:
        raise ValueError("At least one value field is required.")

    existing = {field.name for field in arcpy.ListFields(args.intersect_fc)}
    required = {args.block_id, args.area_field, *value_fields}
    missing = sorted(required.difference(existing))
    if missing:
        raise KeyError("Missing fields: " + ", ".join(missing))

    temporary_fields = []
    output_fields = []
    statistics_fields = [[args.area_field, "SUM"]]

    for index, value_field in enumerate(value_fields, start=1):
        product_field = safe_name(f"AWP_{index}_{value_field}")
        if product_field not in existing:
            arcpy.management.AddField(
                args.intersect_fc, product_field, "DOUBLE"
            )
            temporary_fields.append(product_field)
            existing.add(product_field)

        expression = (
            f"(!{value_field}! * !{args.area_field}!) "
            f"if !{value_field}! is not None and "
            f"!{args.area_field}! not in (None, 0) else None"
        )
        arcpy.management.CalculateField(
            args.intersect_fc,
            product_field,
            expression,
            "PYTHON3",
        )

        statistics_fields.append([product_field, "SUM"])
        output_fields.append(
            (value_field, product_field, safe_name(f"AW_{value_field}", 60))
        )

    arcpy.analysis.Statistics(
        args.intersect_fc,
        args.output_table,
        statistics_fields,
        args.block_id,
    )

    sum_area_field = f"SUM_{args.area_field}"
    stats_existing = {
        field.name for field in arcpy.ListFields(args.output_table)
    }

    for _, product_field, output_field in output_fields:
        if output_field not in stats_existing:
            arcpy.management.AddField(
                args.output_table, output_field, "DOUBLE"
            )
            stats_existing.add(output_field)

        sum_product_field = f"SUM_{product_field}"
        expression = (
            f"(!{sum_product_field}! / !{sum_area_field}!) "
            f"if !{sum_area_field}! not in (None, 0) else None"
        )
        arcpy.management.CalculateField(
            args.output_table,
            output_field,
            expression,
            "PYTHON3",
        )

    if args.join_results:
        join_fields = [field[2] for field in output_fields]
        arcpy.management.JoinField(
            args.blocks_fc,
            args.block_id,
            args.output_table,
            args.block_id,
            join_fields,
        )

    if temporary_fields:
        arcpy.management.DeleteField(
            args.intersect_fc, temporary_fields
        )

    print(f"Area-weighted statistics saved to: {args.output_table}")


if __name__ == "__main__":
    main()
