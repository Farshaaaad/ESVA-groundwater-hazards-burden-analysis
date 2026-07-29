# -*- coding: utf-8 -*-
"""
Create publication-ready composite seawater-intrusion exposure figures from
a corrected census-block analytical table.

Each bar is the percentage of the corresponding ESVA-wide group total located
in the displayed SWI class. "No SWI" and "Slight" remain in the denominator
even though only Early, Moderate, High, and Extreme are shown.

Regional-composition reference lines are not overlaid because they use a
different denominator. Representation ratios are calculated separately by
04_calculate_representation_ratios.py.

Author: Farshad Hesamfar
Affiliation: University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import numeric, read_table


DISPLAY_CLASSES = ["Early", "Moderate", "High", "Extreme"]

SWI_COLORS = {
    "Early": "#F2A14B",
    "Moderate": "#E6674C",
    "High": "#C4383C",
    "Extreme": "#781F2D",
}

GROUP_SPECS = [
    ("total", "Total Housing and Population"),
    ("black", "Black Residents"),
    ("white", "White Residents"),
    ("hisp", "Hispanic Residents"),
    ("pop_under18", "Residents Under 18 Years"),
    ("jobs_rac_low_Proc", "Low-Wage Jobs by Residence"),
    ("jobs_wac_low", "Low-Wage Jobs by Workplace"),
    ("Pop65_block_cell_rnd_up_ACS_scaled", "Residents Age 65 and Older"),
]

ANNUAL_SCENARIOS = [
    ("SWI_Level_2023", "2023 Baseline"),
    ("SWI_Level_2030_Int", "2030 - SSP2-4.5"),
    ("SWI_Level_2040_Int", "2040 - SSP2-4.5"),
    ("SWI_Level_2050_Int", "2050 - SSP2-4.5"),
    ("SWI_Level_2060_Int", "2060 - SSP2-4.5"),
    ("SWI_Level_2080_Int", "2080 - SSP2-4.5"),
    ("SWI_Level_2030_High", "2030 - SSP5-8.5"),
    ("SWI_Level_2040_High", "2040 - SSP5-8.5"),
    ("SWI_Level_2050_High", "2050 - SSP5-8.5"),
    ("SWI_Level_2060_High", "2060 - SSP5-8.5"),
    ("SWI_Level_2080_High", "2080 - SSP5-8.5"),
]

PEAK_SCENARIOS = [
    ("Haz_SWI_Peak_Int", "Peak SWI - SSP2-4.5, 2030-2080"),
    ("Haz_SWI_Peak_High", "Peak SWI - SSP5-8.5, 2030-2080"),
]


def safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


def percentage_by_class(
    df: pd.DataFrame,
    class_field: str,
    value_field: str,
) -> pd.Series:
    values = numeric(df[value_field]).clip(lower=0.0)
    denominator = float(values.sum())
    if denominator <= 0:
        return pd.Series(0.0, index=DISPLAY_CLASSES, dtype=float)

    numerator = (
        df.assign(_value=values)
        .groupby(class_field, dropna=False)["_value"]
        .sum()
        .reindex(DISPLAY_CLASSES, fill_value=0.0)
    )
    return 100.0 * numerator / denominator


def build_stats(
    df: pd.DataFrame,
    class_field: str,
    available_groups: list[tuple[str, str]],
) -> dict:
    result = {
        "housing": percentage_by_class(
            df, class_field, "housing_units"
        ),
        "population": percentage_by_class(
            df, class_field, "total"
        ),
        "groups": {},
    }
    for field, _ in available_groups:
        if field != "total":
            result["groups"][field] = percentage_by_class(
                df, class_field, field
            )
    return result


def common_y_limit(all_stats: dict[str, dict]) -> float:
    values = []
    for stats in all_stats.values():
        values.extend(stats["housing"].tolist())
        values.extend(stats["population"].tolist())
        for series in stats["groups"].values():
            values.extend(series.tolist())
    maximum = max(values, default=0.0)
    return float(max(10, math.ceil((maximum + 2.0) / 5.0) * 5.0))


def draw_total_panel(ax, stats: dict, y_limit: float) -> None:
    x = np.arange(len(DISPLAY_CLASSES))
    width = 0.36

    housing = stats["housing"].to_numpy(dtype=float)
    population = stats["population"].to_numpy(dtype=float)

    housing_bars = ax.bar(
        x - width / 2,
        housing,
        width,
        label="Housing Units",
        color="#BDC3C7",
        edgecolor="black",
        linewidth=0.7,
        zorder=3,
    )
    population_bars = ax.bar(
        x + width / 2,
        population,
        width,
        label="Population",
        color="#2C3E50",
        edgecolor="black",
        linewidth=0.7,
        zorder=3,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(DISPLAY_CLASSES, fontweight="bold")
    ax.legend(frameon=False, loc="upper right", fontsize=9)

    for bars in (housing_bars, population_bars):
        for bar in bars:
            value = float(bar.get_height())
            if value > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    min(value + 0.35, y_limit - 0.8),
                    f"{value:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )


def draw_group_panel(
    ax,
    values: pd.Series,
    y_limit: float,
) -> None:
    x = np.arange(len(DISPLAY_CLASSES))
    colors = [SWI_COLORS[label] for label in DISPLAY_CLASSES]

    bars = ax.bar(
        x,
        values.to_numpy(dtype=float),
        color=colors,
        edgecolor="black",
        linewidth=0.7,
        zorder=3,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(DISPLAY_CLASSES, fontweight="bold")

    for bar, value in zip(bars, values):
        value = float(value)
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                min(value + 0.35, y_limit - 0.8),
                f"{value:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--y-limit",
        type=float,
        default=None,
        help="Optional fixed y-axis maximum. Default uses a common data-driven limit.",
    )
    parser.add_argument(
        "--exclude-peak",
        action="store_true",
        help="Do not create peak-SWI composite figures.",
    )
    args = parser.parse_args()

    df = read_table(args.input, args.sheet)
    required = {"housing_units", "total"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise KeyError("Missing required fields: " + ", ".join(missing))

    available_groups = [
        (field, title)
        for field, title in GROUP_SPECS
        if field in df.columns
    ]
    for field, _ in GROUP_SPECS:
        if field not in df.columns:
            print(f"Warning: skipped missing group field: {field}")

    scenario_specs = [
        item for item in ANNUAL_SCENARIOS if item[0] in df.columns
    ]
    if not args.exclude_peak:
        scenario_specs.extend(
            item for item in PEAK_SCENARIOS if item[0] in df.columns
        )
    if not scenario_specs:
        raise KeyError("No expected SWI classification fields were found.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_stats = {
        field: build_stats(df, field, available_groups)
        for field, _ in scenario_specs
    }
    y_limit = (
        float(args.y_limit)
        if args.y_limit is not None
        else common_y_limit(all_stats)
    )

    plt.rcParams.update(plt.rcParamsDefault)
    plt.style.use("default")

    for class_field, scenario_title in scenario_specs:
        stats = all_stats[class_field]
        fig, axes = plt.subplots(
            2, 4, figsize=(20, 11), facecolor="white"
        )
        axes_flat = axes.flatten()

        for index, (group_field, group_title) in enumerate(available_groups):
            ax = axes_flat[index]
            ax.set_facecolor("white")
            ax.grid(
                True,
                axis="y",
                linestyle="--",
                linewidth=0.8,
                alpha=0.45,
                color="#BFBFBF",
                zorder=0,
            )
            ax.set_title(
                group_title,
                fontsize=14,
                fontweight="bold",
                pad=10,
            )
            ax.set_ylim(0, y_limit)
            ax.tick_params(axis="both", labelsize=9)

            if group_field == "total":
                draw_total_panel(ax, stats, y_limit)
            else:
                draw_group_panel(
                    ax,
                    stats["groups"][group_field],
                    y_limit,
                )

            if index % 4 == 0:
                ax.set_ylabel(
                    "Share of Regional Total (%)",
                    fontweight="bold",
                    fontsize=11,
                )

        for index in range(len(available_groups), len(axes_flat)):
            axes_flat[index].axis("off")

        fig.suptitle(
            f"SWI Exposure Profile: {scenario_title}",
            fontsize=23,
            fontweight="bold",
            y=0.985,
        )
        fig.text(
            0.5,
            0.012,
            (
                "Bars show the percentage of each ESVA-wide group located in "
                "the displayed SWI class. No SWI and Slight are omitted from "
                "the panels but retained in the denominators."
            ),
            ha="center",
            va="bottom",
            fontsize=10,
        )

        fig.tight_layout(rect=(0.02, 0.045, 0.995, 0.955))
        output_path = (
            output_dir
            / f"SWI_Composite_{safe_filename(class_field)}.png"
        )
        fig.savefig(
            output_path,
            dpi=400,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close(fig)
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
