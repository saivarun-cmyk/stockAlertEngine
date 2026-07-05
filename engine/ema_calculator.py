"""
engine/ema_calculator.py
Pure EMA20 calculation on a OHLC DataFrame. No I/O, no side effects.
adjust=False matches TradingView / Zerodha Kite convention.
"""
import pandas as pd
from config.alert_config import EMA_PERIOD


def enrich_with_ema(df: pd.DataFrame, span: int = EMA_PERIOD) -> pd.DataFrame:
    """Return a copy of df with an EMA20 column appended."""
    result = df.copy()
    result["EMA20"] = result["Close"].ewm(span=span, adjust=False).mean()
    return result
