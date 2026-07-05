# EMA20 Alert Engine

Scans all Indian stocks on **30-minute candles**, detects **EMA20 breakouts
and breakdowns**, and sends email alerts via Gmail (primary) + SendGrid
(fallback). Runs every 15 minutes on GitHub Actions — zero server cost.

---

## How it works

```
GitHub Actions (*/15 * * * *)
  └─ run_scanner.py
       ├─ fetch_30min_candles()   yfinance 30-min OHLC
       ├─ enrich_with_ema()       EMA20 (adjust=False, matches TradingView)
       ├─ detect_crossover()      prev close vs curr close relative to EMA20
       ├─ should_alert()          dedup: alert once per crossing
       ├─ send_alert_email()      Gmail → SendGrid fallback
       └─ save_state() + log      committed back to repo
```

**Alert rule:** fires when a 30-min candle close crosses EMA20 in either
direction. Suppressed on repeat runs while price stays on the same side.
Re-fires only after price reverts AND crosses again.

---

## Project structure

```
ema_alert_engine/
├── .github/workflows/ema_scanner.yml   scheduler
├── config/
│   ├── alert_config.py                 all tunables (recipients, thresholds, etc.)
│   └── stocks.py                       stock universe
├── engine/
│   ├── data_fetcher.py                 yfinance wrapper
│   ├── ema_calculator.py               EMA20 calculation
│   ├── crossover_detector.py           BREAKOUT / BREAKDOWN logic
│   └── state_manager.py                JSON persistence + dedup
├── alerts/
│   ├── email_service.py                Gmail + SendGrid
│   └── alert_formatter.py              HTML + plain-text templates
├── ui/
│   └── monitor_dashboard.py            Streamlit monitoring UI
├── state/alert_state.json              auto-committed by GitHub Actions
├── logs/run_log.json                   auto-committed by GitHub Actions
└── run_scanner.py                      entry point
```

---

## Setup (step by step)

### 1 — Get the code into GitHub

Push this `ema_alert_engine/` folder to the root of a GitHub repository:

```
your-repo/
├── ema_alert_engine/    ← this folder
└── stock_analysis_suite/ ← existing project (optional, can be same repo)
```

### 2 — Create a Gmail App Password

1. Log into the Gmail account you want **alerts to send from**.
2. Enable **2-Step Verification** (mandatory — App Passwords require it).
3. **Google Account → Security → App Passwords → Other (custom name) → Generate**.
4. Copy the **16-character** password that appears.

> This is different from your Gmail login password. It is safe to store as
> a GitHub Secret because it only grants "send mail" permission.

### 3 — Add GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_USER` | The sender Gmail address e.g. `mybot@gmail.com` |
| `GMAIL_APP_PASSWORD` | The 16-char App Password from step 2 |
| `SENDGRID_API_KEY` | *(optional but recommended)* — see below |

### 4 — SendGrid fallback (optional, free)

1. Sign up at [sendgrid.com](https://sendgrid.com) (free = 100 emails/day).
2. **Settings → API Keys → Create API Key** (Mail Send permission only).
3. Add as `SENDGRID_API_KEY` GitHub Secret.

### 5 — Enable GitHub Actions

Repo → **Actions tab** → enable workflows if prompted.

The `ema_scanner.yml` schedule (`*/15 * * * *`) starts immediately.

### 6 — Test without waiting 15 minutes

Actions → **EMA20 Alert Scanner** → **Run workflow** → set
*"Ignore market hours"* = `true` → **Run workflow**.

You should see:
- Green ✅ on the Actions run
- `state/alert_state.json` and `logs/run_log.json` committed to the repo
- Email in your inbox (if a crossover was detected on this run)

---

## Configuration

All tunables in **`config/alert_config.py`**:

```python
# Who gets the emails
ALERT_RECIPIENTS = ["vsai3279@gmail.com", "sandeep.epk@gmail.com"]

# Candle settings
CANDLE_INTERVAL = "30m"   # change to "15m" or "1h" if you want
CANDLE_PERIOD   = "5d"    # lookback for yfinance
EMA_PERIOD      = 20      # the "20" in EMA20

# Skip runs when market is closed (recommended True for production)
MARKET_HOURS_ONLY = True
```

---

## Adding stocks

Edit **`config/stocks.py`** only:

```python
INDIAN_STOCKS = {
    ...
    "Wipro": {"symbol": "WIPRO.NS", "sector": "IT"},
}
```

- `symbol` = Yahoo Finance ticker — NSE stocks need `.NS` suffix
- `sector` = shown in the email and monitoring UI

---

## Running the monitoring UI

```bash
cd ema_alert_engine
pip install -r requirements.txt
streamlit run ui/monitor_dashboard.py
```

Shows:
- **Current Positions** — every stock, its EMA20 position, last crossover time
- **Recent Alerts** — the last 50 alerts sent with email status
- **Run History** — the last 40 runs with scan counts, alert counts, errors

### Deploy on Streamlit Cloud (free, always live)

1. [share.streamlit.io](https://share.streamlit.io) → connect your repo
2. Main file path: `ema_alert_engine/ui/monitor_dashboard.py`
3. Deploy — it rebuilds automatically when GitHub Actions commits state/logs

---

## Local testing (no email sent)

```bash
cd ema_alert_engine
# No secrets set → scanner runs but logs "no_config" instead of sending
python run_scanner.py

# With email (set env vars first)
export GMAIL_USER="sender@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python run_scanner.py
```

---

## State file explained

`state/alert_state.json`:
```json
{
  "last_run": "2026-06-21T10:30:00+05:30",
  "stocks": {
    "TCS": {
      "symbol":      "TCS.NS",
      "sector":      "IT",
      "position":    "above",
      "last_cross":  "BREAKOUT",
      "cross_time":  "2026-06-21T10:00:00+05:30",
      "alerted":     true,
      "close":       3950.25,
      "ema20":       3920.10,
      "initialized": true
    }
  }
}
```

`alerted: true` → already notified for this crossing. Will reset to `false`
when price moves to the other side of EMA20.

---

## FAQ

**Q: First run sent no email — is that normal?**
Yes. The first run initialises positions for all stocks but intentionally
sends no alerts, to avoid a false flood on setup. Alerts fire from the
second run onwards when actual crossovers are detected.

**Q: GitHub Actions says the run was delayed.**
Normal. GitHub may delay scheduled runs by a few minutes under load.
The scanner always reads the latest available candle from Yahoo Finance,
so a small delay doesn't cause missed signals.

**Q: Can I add Telegram / WhatsApp?**
Yes — add a new send function in `alerts/email_service.py` and call it
from `run_scanner.py` alongside `send_alert_email()`. Everything else
stays the same.
