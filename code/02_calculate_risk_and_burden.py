# -*- coding: utf-8 -*-
"""
Calculate census-block groundwater risk intensity, absolute burden, and
equity-weighted burden from the final hazard and service-status fields.

Author: Farshad Hesamfar
University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    compare_numeric,
    first_existing,
    numeric,
    read_table,
    require_fields,
    score_from_series,
    write_csv,
)


def calculate_svi_qa(df: pd.DataFrame) -> pd.Series:
    """
    Recalculate the three-pillar SVI for quality assurance.

    The existing SVI_Score remains the analysis field unless the user
    intentionally replaces it after reviewing the QA comparison.
    """
    require_fields(
        df,
        [
            "jobs_rac_low_Proc",
            "jobs_rac_processed",
            "white",
            "total",
            "Pop65_block_cell_rnd_up_ACS_scaled",
            "pop_under18",
        ],
    )

    total = numeric(df["total"])
    jobs = numeric(df["jobs_rac_processed"])
    low_wage = numeric(df["jobs_rac_low_Proc"])
    white = numeric(df["white"])
    older = numeric(df["Pop65_block_cell_rnd_up_ACS_scaled"])
    under18 = numeric(df["pop_under18"])

    econ = np.where(jobs > 0, low_wage / jobs, 0.0)
    race = np.where(total > 0, (total - white) / total, 0.0)
    age = np.where(total > 0, (older + under18) / total, 0.0)

    # Clip component ratios to their valid 0-1 range.
    econ = np.clip(econ, 0.0, 1.0)
    race = np.clip(race, 0.0, 1.0)
    age = np.clip(age, 0.0, 1.0)

    return pd.Series((econ + race + age) / 3.0, index=df.index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input CSV or Excel file.")
    parser.add_argument("--sheet", default=None, help="Excel worksheet name.")
    parser.add_argument("--output", required=True, help="Output CSV.")
    parser.add_argument(
        "--qa-output",
        default=None,
        help="Optional CSV listing material differences from existing fields.",
    )
    args = parser.parse_args()

    df = read_table(args.input, args.sheet)

    require_fields(
        df,
        [
            "SVI_Score",
            "Deficit_Water",
            "Deficit_Sewer",
            "Self_Sup_Dom_Pop_20_Rnd",
            "Est_OWTS_Count",
            "total",
            "Haz_Surficial_Intrmd",
        ],
    )

    svi = numeric(df["SVI_Score"]).clip(0.0, 1.0)
    water_deficit = numeric(df["Deficit_Water"]).clip(0.0, 1.0)
    sewer_deficit = numeric(df["Deficit_Sewer"]).clip(0.0, 1.0)
    private_well_population = numeric(df["Self_Sup_Dom_Pop_20_Rnd"]).clip(lower=0.0)
    owts_count = numeric(df["Est_OWTS_Count"]).clip(lower=0.0)
    total_population = numeric(df["total"]).clip(lower=0.0)

    swi_field = first_existing(
        df,
        [
            "Haz_SWI_Peak_Int_recalc",
            "Haz_SWI_Peak_Int",
            "Haz_SWI_Peak",
        ],
    )
    dtw_field = first_existing(
        df, ["Haz_DTW_Peak_Int", "Haz_DTW_Peak"]
    )
    wtl_field = first_existing(
        df, ["Haz_WTL_Peak_Int", "Haz_WTL_Peak"]
    )
    deep_field = first_existing(
        df, ["Haz_DeepGW_Peak_Int", "Haz_DeepGW_Peak"]
    )

    h_swi = score_from_series(df[swi_field])
    h_dtw = score_from_series(df[dtw_field])
    h_wtl = score_from_series(df[wtl_field])
    h_deep = score_from_series(df[deep_field])
    h_surf_continuous = score_from_series(df["Haz_Surficial_Intrmd"])

    if "Haz_Surficial_Intrmd_Text" in df.columns:
        h_surf_class = score_from_series(df["Haz_Surficial_Intrmd_Text"])
    else:
        h_surf_class = h_surf_continuous

    # Risk intensity.
    df["Risk_SWI_recalc"] = h_swi * svi * water_deficit
    df["Risk_DTW_recalc"] = h_dtw * svi * sewer_deficit
    df["Risk_WTL_recalc"] = h_wtl * svi
    df["Risk_DeepGW_recalc"] = h_deep * svi * water_deficit
    df["Risk_Surficial_recalc"] = (
        h_surf_continuous * svi * water_deficit
    )

    # Absolute burden: hazard score multiplied by the relevant exposed unit.
    df["B_abs_SWI_recalc"] = h_swi * private_well_population
    df["B_abs_DTW_recalc"] = h_dtw * owts_count
    df["B_abs_WTL_recalc"] = h_wtl * total_population
    df["B_abs_Deep_Drawdown_recalc"] = h_deep * private_well_population

    # The manuscript implementation uses the ordinal surficial hazard-class
    # score for absolute burden, while risk uses the continuous hazard score.
    df["B_abs_Surf_Drawdown_recalc"] = (
        h_surf_class * private_well_population
    )

    # Equity-weighted burden: risk intensity multiplied by the relevant unit.
    df["B_eq_SWI_recalc"] = (
        df["Risk_SWI_recalc"] * private_well_population
    )
    df["B_eq_DTW_recalc"] = (
        df["Risk_DTW_recalc"] * owts_count
    )
    df["B_eq_WTL_recalc"] = (
        df["Risk_WTL_recalc"] * total_population
    )
    df["B_eq_Deep_Drawdown_recalc"] = (
        df["Risk_DeepGW_recalc"] * private_well_population
    )
    df["B_eq_Surf_Drawdown_recalc"] = (
        df["Risk_Surficial_recalc"] * private_well_population
    )

    df["SVI_Score_recalc_QA"] = calculate_svi_qa(df)

    comparison_map = {
        "Risk_SWI_Int": "Risk_SWI_recalc",
        "Risk_DTW_Int": "Risk_DTW_recalc",
        "Risk_WTL_Int": "Risk_WTL_recalc",
        "Risk_DeepGW_Int": "Risk_DeepGW_recalc",
        "Risk_Surficial_Intrmd": "Risk_Surficial_recalc",
        "B_abs_SWI": "B_abs_SWI_recalc",
        "B_abs_DTW": "B_abs_DTW_recalc",
        "B_abs_WTL": "B_abs_WTL_recalc",
        "B_abs_Deep_Drawdown": "B_abs_Deep_Drawdown_recalc",
        "B_abs_Surf_Drawdown": "B_abs_Surf_Drawdown_recalc",
        "Risk_Pop_Burden_SWI_Int": "B_eq_SWI_recalc",
        "Risk_Pop_Burden_DTW_Int": "B_eq_DTW_recalc",
        "Risk_Pop_Burden_WTL_Int": "B_eq_WTL_recalc",
        "Risk_Pop_Burden_DeepGW_Int": "B_eq_Deep_Drawdown_recalc",
        "Burd_Surficial_Intrmd": "B_eq_Surf_Drawdown_recalc",
    }

    qa_rows = []
    for original_field, recalculated_field in comparison_map.items():
        if original_field not in df.columns:
            continue

        changed = compare_numeric(
            df[original_field], df[recalculated_field], tolerance=1e-6
        )
        for index in df.index[changed]:
            qa_rows.append(
                {
                    "row_index": int(index),
                    "GEOID20": (
                        str(df.at[index, "GEOID20"])
                        if "GEOID20" in df.columns
                        else ""
                    ),
                    "original_field": original_field,
                    "recalculated_field": recalculated_field,
                    "original_value": df.at[index, original_field],
                    "recalculated_value": df.at[index, recalculated_field],
                }
            )

    qa = pd.DataFrame(qa_rows)
    write_csv(df, args.output)

    qa_path = args.qa_output or str(
        Path(args.output).with_name("risk_burden_qa.csv")
    )
    write_csv(qa, qa_path)

    print(f"Saved recalculated metric table: {args.output}")
    print(f"Saved risk/burden QA comparison: {qa_path}")
    print(f"Material field differences identified: {len(qa):,}")


if __name__ == "__main__":
    main()
