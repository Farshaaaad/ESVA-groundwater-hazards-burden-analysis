# -*- coding: utf-8 -*-
"""
Calculate group-specific severe-SWI exposure rates and representation ratios.

For population groups:
RR = (group share among residents in High/Extreme SWI blocks)
     / (group share in the regional population)

For employment groups, the same calculation uses the corresponding job totals
rather than population totals.

Author: Farshad Hesamfar
University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import numeric, read_table, write_csv


GROUPS = {
    "Black residents": ("black", "total"),
    "White residents": ("white", "total"),
    "Hispanic residents": ("hisp", "total"),
    "Residents under 18": ("pop_under18", "total"),
    "Residents age 65+": (
        "Pop65_block_cell_rnd_up_ACS_scaled",
        "total",
    ),
    "Low-wage jobs, residence-based": (
        "jobs_rac_low_Proc",
        "jobs_rac_processed",
    ),
    "Low-wage jobs, workplace-based": (
        "jobs_wac_low",
        "jobs_wac_processed",
    ),
}


def find_swi_level_fields(df: pd.DataFrame) -> list[str]:
    pattern = re.compile(
        r"^SWI_Level_(2023|2030|2040|2050|2060|2080)"
        r"(?:_(Int|High))?(?:_recalc)?$"
    )
    return [field for field in df.columns if pattern.match(field)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input CSV or Excel file.")
    parser.add_argument("--sheet", default=None, help="Excel worksheet name.")
    parser.add_argument("--output", required=True, help="Output CSV.")
    args = parser.parse_args()

    df = read_table(args.input, args.sheet)
    level_fields = find_swi_level_fields(df)
    if not level_fields:
        raise KeyError("No SWI_Level_* fields were found.")

    rows = []
    for level_field in level_fields:
        severe = (
            df[level_field]
            .astype("string")
            .str.strip()
            .isin(["High", "Extreme"])
        )

        for group_name, (group_field, denominator_field) in GROUPS.items():
            if group_field not in df.columns or denominator_field not in df.columns:
                continue

            group_values = numeric(df[group_field]).clip(lower=0.0)
            denominator_values = numeric(df[denominator_field]).clip(lower=0.0)

            regional_group = group_values.sum()
            regional_denominator = denominator_values.sum()
            exposed_group = group_values.loc[severe].sum()
            exposed_denominator = denominator_values.loc[severe].sum()

            exposure_rate = (
                exposed_group / regional_group
                if regional_group > 0
                else np.nan
            )
            exposed_share = (
                exposed_group / exposed_denominator
                if exposed_denominator > 0
                else np.nan
            )
            regional_share = (
                regional_group / regional_denominator
                if regional_denominator > 0
                else np.nan
            )
            representation_ratio = (
                exposed_share / regional_share
                if regional_share > 0
                else np.nan
            )

            rows.append(
                {
                    "SWI field": level_field,
                    "Group": group_name,
                    "Group field": group_field,
                    "Denominator field": denominator_field,
                    "Regional group total": regional_group,
                    "Exposed group total": exposed_group,
                    "Exposure rate": exposure_rate,
                    "Exposed-group share": exposed_share,
                    "Regional share": regional_share,
                    "Representation ratio": representation_ratio,
                }
            )

    result = pd.DataFrame(rows)
    write_csv(result, args.output)
    print(f"Saved representation-ratio table: {args.output}")


if __name__ == "__main__":
    main()
