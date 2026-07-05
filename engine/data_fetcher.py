"""
engine/data_fetcher.py
Fetches 30-minute OHLC from Yahoo Finance for one ticker.
Returns a clean sorted DataFrame or None on any failure.
"""
import logging
import pandas as pd
import yfinance as yf
from config.alert_config import CANDLE_INTERVAL, CANDLE_PERIOD

logger = logging.getLogger(__name__)


def fetch_30min_candles(symbol: str) -> pd.DataFrame | None:
    """
    Download CANDLE_PERIOD of CANDLE_INTERVAL bars.
    Needs >= 25 rows so EMA20 is meaningful.
    iloc[-1] = latest (may be in-progress during session)
    iloc[-2] = previous completed candle
    """
    try:
        raw = yf.download(
            symbol, period=CANDLE_PERIOD, interval=CANDLE_INTERVAL,
            progress=False, auto_adjust=True,
        )
        if raw is None or raw.empty:
            logger.warning("No data returned for %s", symbol)
            return None

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        if "Close" not in raw.columns:
            return None

        data = raw.sort_index().dropna(subset=["Close"])
        if len(data) < 25:
            logger.warning("Only %d rows for %s — skipping", len(data), symbol)
            return None
        return data

    except Exception as exc:
        logger.error("fetch failed for %s: %s", symbol, exc)
        return None
