"""
engine/crossover_detector.py
Compares the last two 30-min candle closes vs EMA20 to detect crossovers.

Logic:
    prev_close < prev_ema20  AND curr_close >= curr_ema20  → BREAKOUT
    prev_close >= prev_ema20 AND curr_close <  curr_ema20  → BREAKDOWN
    otherwise                                               → None
"""
import logging
from dataclasses import dataclass
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)
CrossoverType = Literal["BREAKOUT", "BREAKDOWN"]


@dataclass
class CrossoverResult:
    stock_name:  str
    symbol:      str
    sector:      str
    cross_type:  CrossoverType
    curr_close:  float
    curr_ema20:  float
    prev_close:  float
    prev_ema20:  float
    candle_time: str


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return None if v != v else v   # NaN check
    except (TypeError, ValueError):
        return None


def detect_crossover(df: pd.DataFrame, stock_name: str,
                     symbol: str, sector: str) -> CrossoverResult | None:
    """Run crossover detection on an EMA-enriched DataFrame."""
    if "EMA20" not in df.columns or len(df) < 2:
        return None

    vals = [_safe_float(df.iloc[i][col])
            for i in (-1, -2) for col in ("Close", "EMA20")]
    if any(v is None for v in vals):
        return None

    curr_close, curr_ema20, prev_close, prev_ema20 = vals

    prev_above = prev_close >= prev_ema20
    curr_above = curr_close >= curr_ema20

    if not prev_above and curr_above:
        cross_type: CrossoverType = "BREAKOUT"
    elif prev_above and not curr_above:
        cross_type = "BREAKDOWN"
    else:
        return None

    logger.info("%s %s  close=%.2f  ema20=%.2f",
                cross_type, stock_name, curr_close, curr_ema20)

    return CrossoverResult(
        stock_name=stock_name, symbol=symbol, sector=sector,
        cross_type=cross_type,
        curr_close=curr_close, curr_ema20=curr_ema20,
        prev_close=prev_close, prev_ema20=prev_ema20,
        candle_time=str(df.index[-1]),
    )


def current_position(df: pd.DataFrame) -> str | None:
    """Returns 'above' or 'below' for the latest candle, or None on bad data."""
    if "EMA20" not in df.columns or len(df) < 1:
        return None
    c = _safe_float(df.iloc[-1]["Close"])
    e = _safe_float(df.iloc[-1]["EMA20"])
    if c is None or e is None:
        return None
    return "above" if c >= e else "below"
