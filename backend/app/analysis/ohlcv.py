"""OHLCV DataFrame contract shared by every analysis module.

Every function in `app/analysis/` accepts a `pandas.DataFrame` with exactly
these columns (any broker gateway is responsible for mapping its native
field names — e.g. MT5's `tick_volume` — onto this shape before the data
reaches the analysis layer):

    time    : datetime64[ns, UTC]
    open    : float64
    high    : float64
    low     : float64
    close   : float64
    volume  : float64

Rows must be sorted ascending by `time` with a clean `RangeIndex` (0..n-1)
so swing/structure detection can use positional indices directly.
"""

from __future__ import annotations

import pandas as pd

from app.core.constants import MIN_CANDLES_FOR_ANALYSIS
from app.core.exceptions import InsufficientDataError

REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "volume")


def validate_ohlcv(
    df: pd.DataFrame, *, min_candles: int = MIN_CANDLES_FOR_ANALYSIS
) -> pd.DataFrame:
    """Validate & normalize an OHLCV DataFrame; returns a clean copy.

    Raises `InsufficientDataError` if required columns are missing or there
    isn't enough history for a meaningful analysis — callers should surface
    this as a 422 rather than let downstream code silently compute on NaNs.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise InsufficientDataError(f"OHLCV data is missing required columns: {missing}")

    clean = df.loc[:, list(REQUIRED_COLUMNS)].copy()
    clean = clean.dropna(subset=["open", "high", "low", "close"])
    clean = clean.sort_values("time").reset_index(drop=True)

    if len(clean) < min_candles:
        raise InsufficientDataError(
            f"Need at least {min_candles} candles for analysis, got {len(clean)}."
        )

    if not pd.api.types.is_datetime64_any_dtype(clean["time"]):
        clean["time"] = pd.to_datetime(clean["time"], utc=True)
    elif clean["time"].dt.tz is None:
        clean["time"] = clean["time"].dt.tz_localize("UTC")

    for col in ("open", "high", "low", "close", "volume"):
        clean[col] = clean[col].astype(float)

    return clean
