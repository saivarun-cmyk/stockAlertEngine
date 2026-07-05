"""
config/alert_config.py
All tunables for the alert engine. Edit ONLY this file to change
recipients, thresholds, candle timeframe, or market hours.

GitHub Secrets required:
    GMAIL_USER          sender Gmail address
    GMAIL_APP_PASSWORD  Gmail App Password (NOT your login password)
    SENDGRID_API_KEY    SendGrid API key (fallback, optional)
"""
import os

# ── Recipients ─────────────────────────────────────────────────────────────
ALERT_RECIPIENTS = [
    "vsai3279@gmail.com",
    "sandeep.epk@gmail.com",
]

# ── Technical settings ──────────────────────────────────────────────────────
CANDLE_INTERVAL = "30m"   # yfinance interval  (try "15m", "1h" etc.)
CANDLE_PERIOD   = "5d"    # yfinance period    (enough for EMA20)
EMA_PERIOD      = 20      # EMA span on 30-min candles

# ── Market hours guard (IST, 24h) ──────────────────────────────────────────
# When True the scanner exits silently outside NSE hours so GitHub Actions
# doesn't waste quota on dead-market runs.  Set False for local testing.
MARKET_HOURS_ONLY = True
MARKET_OPEN_H,  MARKET_OPEN_M  = 9,  15   # 09:15 IST
MARKET_CLOSE_H, MARKET_CLOSE_M = 15, 45   # 15:45 IST (15-min buffer)
MARKET_TIMEZONE = "Asia/Kolkata"

# ── State and log paths ─────────────────────────────────────────────────────
STATE_FILE      = "state/alert_state.json"
LOG_FILE        = "logs/run_log.json"
MAX_LOG_ENTRIES = 200

# ── Gmail SMTP (primary) ────────────────────────────────────────────────────
GMAIL_USER         = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_SMTP_HOST    = "smtp.gmail.com"
GMAIL_SMTP_PORT    = 587

# ── SendGrid (fallback) ─────────────────────────────────────────────────────
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_FROM    = os.environ.get("GMAIL_USER", "")

# ── UI ──────────────────────────────────────────────────────────────────────
DASHBOARD_TITLE = "EMA20 Alert Monitor"
