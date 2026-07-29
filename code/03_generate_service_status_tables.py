# -*- coding: utf-8 -*-
"""
Generate the populated-block and all-block service-status summary tables.

Author: Farshad Hesamfar
University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import first_existing, numeric, read_table, require_fields, write_csv


def select_metric_fields(df: pd.DataFrame) -> dict[str, str]:
    return {
        "risk_swi": first_existing(df, ["Risk_SWI_recalc", "Risk_SWI_Int"]),
        "risk_dtw": first_existing(df, ["Risk_DTW_recalc", "Risk_DTW_Int"]),
        "risk_wtl": first_existing(df, ["Risk_WTL_recalc", "Risk_WTL_Int"]),
        "risk_deep": first_existing(
            df, ["Risk_DeepGW_recalc", "Risk_DeepGW_Int"]
        ),
        "risk_surf": first_existing(
            df, ["Risk_Surficial_recalc", "Risk_Surficial_Intrmd"]
        ),
        "abs_swi": first_existing(df, ["B_abs_SWI_recalc", "B_abs_SWI"]),
        "abs_dtw": first_existing(df, ["B_abs_DTW_recalc", "B_abs_DTW"]),
        "abs_wtl": first_existing(df, ["B_abs_WTL_recalc", "B_abs_WTL"]),
        "abs_deep": first_existing(
            df, ["B_abs_Deep_Drawdown_recalc", "B_abs_Deep_Drawdown"]
        ),
        "abs_surf": first_existing(
            df, ["B_abs_Surf_Drawdown_recalc", "B_abs_Surf_Drawdown"]
        ),
        "eq_swi": first_existing(
            df,
            ["B_eq_SWI_recalc", "Risk_Pop_Burden_SWI_Int"],
        ),
        "eq_dtw": first_existing(
            df,
            ["B_eq_DTW_recalc", "Risk_Pop_Burden_DTW_Int"],
        ),
        "eq_wtl": first_existing(
            df,
            ["B_eq_WTL_recalc", "Risk_Pop_Burden_WTL_Int"],
        ),
        "eq_deep": first_existing(
            df,
            ["B_eq_Deep_Drawdown_recalc", "Risk_Pop_Burden_DeepGW_Int"],
        ),
        "eq_surf": first_existing(
            df,
            ["B_eq_Surf_Drawdown_recalc", "Burd_Surficial_Intrmd"],
        ),
    }


def summarize_group(
    group: pd.DataFrame,
    service_label: str,
    fields: dict[str, str],
    hazard_group: str,
) -> dict[str, float | int | str]:
    svi = numeric(group["SVI_Score"])
    high_svi = svi.round(6).ge(0.5)

    row = {
        "Service status": service_label,
        "n blocks": int(len(group)),
        "Mean SVI": float(svi.mean()) if len(group) else float("nan"),
        "SVI >= 0.5 blocks, n": int(high_svi.sum()),
        "SVI >= 0.5 blocks, %": (
            100.0 * float(high_svi.mean()) if len(group) else float("nan")
        ),
    }

    if hazard_group == "water":
        row.update(
            {
                "Mean Risk SWI": numeric(group[fields["risk_swi"]]).mean(),
                "Abs. Burden SWI": numeric(group[fields["abs_swi"]]).sum(),
                "Eq. Burden SWI": numeric(group[fields["eq_swi"]]).sum(),
                "Mean Risk Confined drawdown": numeric(
                    group[fields["risk_deep"]]
                ).mean(),
                "Abs. Burden Confined drawdown": numeric(
                    group[fields["abs_deep"]]
                ).sum(),
                "Eq. Burden Confined drawdown": numeric(
                    group[fields["eq_deep"]]
                ).sum(),
                "Mean Risk Surficial drawdown": numeric(
                    group[fields["risk_surf"]]
                ).mean(),
                "Abs. Burden Surficial drawdown": numeric(
                    group[fields["abs_surf"]]
                ).sum(),
                "Eq. Burden Surficial drawdown": numeric(
                    group[fields["eq_surf"]]
                ).sum(),
            }
        )
    else:
        row.update(
            {
                "Mean Risk Septic/DTW": numeric(
                    group[fields["risk_dtw"]]
                ).mean(),
                "Abs. Burden Septic/DTW": numeric(
                    group[fields["abs_dtw"]]
                ).sum(),
                "Eq. Burden Septic/DTW": numeric(
                    group[fields["eq_dtw"]]
                ).sum(),
                "Mean Risk Waterlogging": numeric(
                    group[fields["risk_wtl"]]
                ).mean(),
                "Abs. Burden Waterlogging": numeric(
                    group[fields["abs_wtl"]]
                ).sum(),
                "Eq. Burden Waterlogging": numeric(
                    group[fields["eq_wtl"]]
                ).sum(),
            }
        )

    return row


def make_tables(df: pd.DataFrame, populated_only: bool):
    require_fields(
        df,
        ["total", "SVI_Score", "Deficit_Water", "Deficit_Sewer"],
    )
    fields = select_metric_fields(df)

    working = df.loc[numeric(df["total"]).gt(0)].copy() if populated_only else df.copy()

    water_rows = [
        summarize_group(
            working.loc[numeric(working["Deficit_Water"]).eq(0)],
            "Public water",
            fields,
            "water",
        ),
        summarize_group(
            working.loc[numeric(working["Deficit_Water"]).eq(1)],
            "No public water / private-well-reliant",
            fields,
            "water",
        ),
    ]

    sewer_rows = [
        summarize_group(
            working.loc[numeric(working["Deficit_Sewer"]).eq(0)],
            "Public sewer",
            fields,
            "sewer",
        ),
        summarize_group(
            working.loc[numeric(working["Deficit_Sewer"]).eq(1)],
            "No public sewer / septic-reliant",
            fields,
            "sewer",
        ),
    ]

    return pd.DataFrame(water_rows), pd.DataFrame(sewer_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input CSV or Excel file.")
    parser.add_argument("--sheet", default=None, help="Excel worksheet name.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    df = read_table(args.input, args.sheet)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    st7_water, st7_sewer = make_tables(df, populated_only=True)
    st8_water, st8_sewer = make_tables(df, populated_only=False)

    write_csv(st7_water, output_dir / "Table_ST7A_populated_water.csv")
    write_csv(st7_sewer, output_dir / "Table_ST7B_populated_sewer.csv")
    write_csv(st8_water, output_dir / "Table_ST8A_all_blocks_water.csv")
    write_csv(st8_sewer, output_dir / "Table_ST8B_all_blocks_sewer.csv")

    print(f"Saved service-status tables in: {output_dir}")


if __name__ == "__main__":
    main()
