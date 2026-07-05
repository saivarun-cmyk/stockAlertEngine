"""
run_scanner.py — main entry point
===================================
Pipeline:
    1. Market-hours guard (exits silently if closed & MARKET_HOURS_ONLY=True)
    2. Load state from state/alert_state.json
    3. For every Indian stock:
         fetch 30-min candles → EMA20 → crossover → dedup → queue alert
    4. If alerts queued → format HTML email → send (Gmail → SendGrid)
    5. Save updated state + append run log

Run locally:
    python run_scanner.py
    (No email is sent unless GMAIL_APP_PASSWORD / SENDGRID_API_KEY are set)
"""
import logging
import os
import sys
from datetime import datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.alert_config import (
    MARKET_HOURS_ONLY, MARKET_OPEN_H, MARKET_OPEN_M,
    MARKET_CLOSE_H, MARKET_CLOSE_M, MARKET_TIMEZONE,
)
from config.stocks import INDIAN_STOCKS
from engine.data_fetcher      import fetch_30min_candles
from engine.ema_calculator    import enrich_with_ema
from engine.crossover_detector import detect_crossover, current_position
from engine.state_manager     import (
    load_state, save_state,
    is_new_stock, should_alert, update_stock,
    append_log, build_log_entry,
)
from alerts.alert_formatter   import build_subject, build_email_html, build_email_text
from alerts.email_service     import send_alert_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_scanner")
IST = pytz.timezone(MARKET_TIMEZONE)


def _run_id() -> str:
    return datetime.now(IST).strftime("%Y%m%d_%H%M%S")


def _market_open() -> bool:
    now  = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return (MARKET_OPEN_H * 60 + MARKET_OPEN_M) <= mins <= (MARKET_CLOSE_H * 60 + MARKET_CLOSE_M)


def main() -> None:
    run_id     = _run_id()
    mkt_open   = _market_open()
    logger.info("═══ EMA Alert Engine  run=%s  market_open=%s ═══", run_id, mkt_open)

    if MARKET_HOURS_ONLY and not mkt_open:
        logger.info("Market closed — exiting (set MARKET_HOURS_ONLY=False to override)")
        append_log(build_log_entry(run_id, 0, [], "skipped_market_closed", [], False))
        return

    state          = load_state()
    alerts_to_send = []
    errors         = []
    scanned        = 0

    for stock_name, info in INDIAN_STOCKS.items():
        symbol = info["symbol"]
        sector = info.get("sector", "Unknown")

        # ── 1. Fetch ───────────────────────────────────────────────────
        df = fetch_30min_candles(symbol)
        if df is None:
            errors.append(f"fetch_failed:{stock_name}")
            continue

        # ── 2. EMA20 ───────────────────────────────────────────────────
        df = enrich_with_ema(df)
        scanned += 1

        try:
            curr_close = float(df.iloc[-1]["Close"])
            curr_ema20 = float(df.iloc[-1]["EMA20"])
        except (TypeError, ValueError, IndexError):
            errors.append(f"bad_values:{stock_name}")
            continue

        pos = current_position(df)
        if pos is None:
            errors.append(f"no_position:{stock_name}")
            continue

        # ── 3. First-ever scan: initialise without alerting ────────────
        if is_new_stock(state, stock_name):
            update_stock(state, stock_name, symbol, sector,
                         pos, curr_close, curr_ema20, alerted=False)
            logger.info("Initialised %s → %s", stock_name, pos)
            continue

        # ── 4. Crossover detection ────────────────────────────────────
        cross = detect_crossover(df, stock_name, symbol, sector)

        if cross is not None and should_alert(state, stock_name, pos):
            logger.info("ALERT: %s %s", cross.cross_type, stock_name)
            alerts_to_send.append({
                "stock":       stock_name,
                "symbol":      symbol,
                "sector":      sector,
                "type":        cross.cross_type,
                "close":       curr_close,
                "ema20":       curr_ema20,
                "candle_time": cross.candle_time,
            })
            update_stock(state, stock_name, symbol, sector,
                         pos, curr_close, curr_ema20,
                         alerted=True, cross_type=cross.cross_type)
        else:
            # No new crossover — refresh prices, preserve alerted flag
            existing    = state["stocks"].get(stock_name, {})
            stored_pos  = existing.get("position", "unknown")
            # If price quietly reverted without crossing, reset alerted so
            # the next real crossover in this new direction can fire
            new_alerted = existing.get("alerted", False) if pos == stored_pos else False
            update_stock(state, stock_name, symbol, sector,
                         pos, curr_close, curr_ema20,
                         alerted=new_alerted,
                         cross_type=existing.get("last_cross"))

    # ── 5. Send email ─────────────────────────────────────────────────
    email_status = "no_alerts"
    if alerts_to_send:
        subject      = build_subject(alerts_to_send)
        html         = build_email_html(alerts_to_send, run_id)
        plain        = build_email_text(alerts_to_send, run_id)
        email_status = send_alert_email(subject, html, plain)
        logger.info("Email status: %s", email_status)
    else:
        logger.info("No new crossovers this run")

    # ── 6. Persist ────────────────────────────────────────────────────
    save_state(state)
    append_log(build_log_entry(run_id, scanned, alerts_to_send,
                               email_status, errors, mkt_open))
    logger.info("Done  scanned=%d  alerts=%d  errors=%d  email=%s",
                scanned, len(alerts_to_send), len(errors), email_status)


if __name__ == "__main__":
    main()
