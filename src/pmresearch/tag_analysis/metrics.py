from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or math.isnan(denominator) or math.isnan(numerator):
        return float("nan")
    return numerator / denominator


def calc_roi(pnl: float, usd_buy_volume: float) -> float:
    return safe_divide(pnl, usd_buy_volume)


def calc_time_to_end_hours(
    first_trade_ts: datetime | None,
    end_ts: datetime | None,
) -> float:
    if first_trade_ts is None or end_ts is None:
        return float("nan")
    if end_ts.tzinfo is None:
        end_ts = end_ts.replace(tzinfo=timezone.utc)
    if first_trade_ts.tzinfo is None:
        first_trade_ts = first_trade_ts.replace(tzinfo=timezone.utc)
    return (end_ts - first_trade_ts).total_seconds() / 3600.0


def calc_winrate(pnl_values: np.ndarray) -> float:
    valid = pnl_values[~np.isnan(pnl_values)]
    if len(valid) == 0:
        return float("nan")
    return float(np.mean(valid > 0))


def nanmean_safe(values: np.ndarray) -> float:
    if len(values) == 0:
        return float("nan")
    result = np.nanmean(values)
    return float(result)


def nanmedian_safe(values: np.ndarray) -> float:
    if len(values) == 0:
        return float("nan")
    result = np.nanmedian(values)
    return float(result)
