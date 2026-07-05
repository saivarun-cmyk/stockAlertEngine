"""
engine/state_manager.py
JSON-based state persistence committed back to GitHub after every run.

Deduplication rule (your requirement):
    Alert ONCE per crossover. Re-alert only after price reverts
    to the other side AND crosses again.

Implementation:
    state.stocks[stock]["alerted"] = True  → suppress further alerts
    When position flips → set alerted = False → next crossover fires
"""
import json
import logging
import os
from datetime import datetime

import pytz

from config.alert_config import STATE_FILE, LOG_FILE, MAX_LOG_ENTRIES, MARKET_TIMEZONE

logger = logging.getLogger(__name__)
IST = pytz.timezone(MARKET_TIMEZONE)


def _now_ist() -> str:
    return datetime.now(IST).isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


# ── State ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"last_run": None, "stocks": {}}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("load_state failed: %s", exc)
        return {"last_run": None, "stocks": {}}


def save_state(state: dict) -> None:
    state["last_run"] = _now_ist()
    _ensure_dir(STATE_FILE)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    logger.info("State saved → %s", STATE_FILE)


def is_new_stock(state: dict, stock_name: str) -> bool:
    """True if this stock has never been seen (first run or new addition)."""
    s = state.get("stocks", {}).get(stock_name, {})
    return not s.get("initialized", False)


def should_alert(state: dict, stock_name: str, new_position: str) -> bool:
    """
    Returns True if an alert should fire for this stock.

    Cases:
    1. First-ever scan (not initialized) → record, no alert
    2. Position same as stored AND alerted=True → no alert (dedup)
    3. Position flipped from stored → set alerted=False, alert fires
    4. Position same AND alerted=False → alert (state was externally reset)
    """
    entry = state.get("stocks", {}).get(stock_name, {})

    if not entry.get("initialized", False):
        return False

    stored_pos     = entry.get("position", "unknown")
    stored_alerted = entry.get("alerted", False)

    if new_position == stored_pos:
        return not stored_alerted    # only if we haven't alerted yet

    # Position changed → update in-place so save_state captures it
    entry["position"] = new_position
    entry["alerted"]  = False        # will become True after alert is sent
    return True


def update_stock(state: dict, stock_name: str, symbol: str, sector: str,
                 position: str, close: float, ema20: float,
                 alerted: bool, cross_type: str | None = None) -> None:
    """Write latest values into the in-memory state dict."""
    stocks = state.setdefault("stocks", {})
    prev   = stocks.get(stock_name, {})
    stocks[stock_name] = {
        "symbol":      symbol,
        "sector":      sector,
        "position":    position,
        "last_cross":  cross_type or prev.get("last_cross"),
        "cross_time":  _now_ist() if cross_type else prev.get("cross_time"),
        "alerted":     alerted,
        "close":       round(close, 2),
        "ema20":       round(ema20, 2),
        "initialized": True,
    }


# ── Run log ────────────────────────────────────────────────────────────────

def load_log() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def append_log(entry: dict) -> None:
    logs = load_log()
    logs.append(entry)
    if len(logs) > MAX_LOG_ENTRIES:
        logs = logs[-MAX_LOG_ENTRIES:]
    _ensure_dir(LOG_FILE)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def build_log_entry(run_id: str, stocks_scanned: int,
                    alerts: list, email_status: str,
                    errors: list, market_open: bool) -> dict:
    return {
        "run_id":         run_id,
        "timestamp_ist":  _now_ist(),
        "stocks_scanned": stocks_scanned,
        "alerts_sent":    len(alerts),
        "alerts":         alerts,
        "email_status":   email_status,
        "errors":         errors,
        "market_open":    market_open,
    }
