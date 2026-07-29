# -*- coding: utf-8 -*-
"""
Shared utilities for the ESVA groundwater-hazard reproducibility workflow.

Author: Farshad Hesamfar
University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


LABEL_ORDER = {
    "No SWI": 0,
    "Safe": 0,
    "Slight": 1,
    "Early": 2,
    "Moderate": 3,
    "High": 4,
    "Extreme": 5,
}

LABEL_SCORE = {
    "No SWI": 0.0,
    "Safe": 0.0,
    "Slight": 0.2,
    "Early": 0.4,
    "Moderate": 0.6,
    "High": 0.8,
    "Extreme": 1.0,
}


def read_table(path: str | Path, sheet_name: str | None = None) -> pd.DataFrame:
    """Read a CSV or Excel table and standardize column names."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input table not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, low_memory=False)
    elif suffix in {".xlsx", ".xls"}:
        kwargs = {}
        if sheet_name:
            kwargs["sheet_name"] = sheet_name
        df = pd.read_excel(path, **kwargs)
    else:
        raise ValueError("Input must be a .csv, .xlsx, or .xls file.")

    df.columns = [str(column).strip() for column in df.columns]
    return df


def write_csv(df: pd.DataFrame, path: str | Path) -> Path:
    """Write a reproducible UTF-8 CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def numeric(series: pd.Series, fill: float = 0.0) -> pd.Series:
    """Convert a series to finite numeric values."""
    out = pd.to_numeric(series, errors="coerce")
    out = out.replace([np.inf, -np.inf], np.nan)
    return out.fillna(fill)


def require_fields(df: pd.DataFrame, fields: Iterable[str]) -> None:
    """Raise a clear error when required fields are absent."""
    missing = [field for field in fields if field not in df.columns]
    if missing:
        raise KeyError("Missing required fields: " + ", ".join(missing))


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    """Return the first field name present in the table."""
    for field in candidates:
        if field in df.columns:
            return field
    raise KeyError(
        "None of the expected fields were found: " + ", ".join(candidates)
    )


def score_from_series(series: pd.Series) -> pd.Series:
    """
    Convert either text hazard classes or numeric hazard scores to 0-1 scores.
    """
    numeric_attempt = pd.to_numeric(series, errors="coerce")
    text_scores = (
        series.astype("string")
        .str.strip()
        .map(LABEL_SCORE)
        .astype(float)
    )
    out = numeric_attempt.where(numeric_attempt.notna(), text_scores)
    return out.fillna(0.0).clip(lower=0.0, upper=1.0)


def compare_numeric(
    original: pd.Series,
    recalculated: pd.Series,
    tolerance: float = 1e-8,
) -> pd.Series:
    """Return a Boolean mask identifying material numeric differences."""
    original_num = pd.to_numeric(original, errors="coerce")
    recalculated_num = pd.to_numeric(recalculated, errors="coerce")
    both_missing = original_num.isna() & recalculated_num.isna()
    difference = (original_num - recalculated_num).abs() > tolerance
    one_missing = original_num.isna() ^ recalculated_num.isna()
    return (~both_missing) & (difference | one_missing)
