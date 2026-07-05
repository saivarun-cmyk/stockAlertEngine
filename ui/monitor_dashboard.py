"""
ui/monitor_dashboard.py
=======================
Streamlit monitoring dashboard — read-only view of the alert engine's
state and run history. Auto-refreshes every 60 seconds.

Run from the ema_alert_engine/ directory:
    streamlit run ui/monitor_dashboard.py
"""
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.alert_config import (
    STATE_FILE, LOG_FILE, MARKET_TIMEZONE,
    MARKET_OPEN_H, MARKET_OPEN_M, MARKET_CLOSE_H, MARKET_CLOSE_M,
    DASHBOARD_TITLE,
)

IST = pytz.timezone(MARKET_TIMEZONE)

C = {
    "bg":    "#0A0E14", "panel": "#11161F", "panel2": "#161C28",
    "bd":    "rgba(148,163,184,0.08)", "bds": "rgba(148,163,184,0.16)",
    "teal":  "#00D9C0", "green": "#16C784", "red":   "#FF4D4D",
    "amber": "#FFB020", "text":  "#E6EAF0", "muted": "#8A93A6", "faint": "#576075",
}


def rh(html: str) -> None:
    """Strip indentation + blank lines to avoid Streamlit's blank-line HTML bug."""
    lines   = (l.strip() for l in html.split("\n"))
    cleaned = "\n".join(l for l in lines if l)
    st.markdown(cleaned, unsafe_allow_html=True)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def market_open() -> bool:
    now  = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    m = now.hour * 60 + now.minute
    return (MARKET_OPEN_H * 60 + MARKET_OPEN_M) <= m <= (MARKET_CLOSE_H * 60 + MARKET_CLOSE_M)


# ── Page setup ────────────────────────────────────────────────────────────

st.set_page_config(page_title=DASHBOARD_TITLE, page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

rh(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
.stApp{{background:{C['bg']};color:{C['text']};}}
.block-container{{padding-top:0.75rem;padding-bottom:3rem;max-width:1200px;}}
.stButton>button{{background:linear-gradient(135deg,{C['teal']},#00B8A3);color:#04211D;border:none;border-radius:10px;font-weight:600;padding:0.45rem 1rem;}}
.stTabs [data-baseweb="tab-list"]{{background:{C['panel']};border:1px solid {C['bd']};border-radius:12px;padding:4px;gap:4px;}}
.stTabs [data-baseweb="tab"]{{color:{C['muted']};border-radius:8px;font-size:0.85rem;}}
.stTabs [aria-selected="true"]{{background:rgba(0,217,192,0.1)!important;color:{C['teal']}!important;}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{display:none;}}
div[data-testid="stTextInput"] input{{background:{C['panel2']}!important;border:1px solid {C['bds']}!important;border-radius:8px!important;color:{C['text']}!important;}}
</style>
""")

# ── Auto-refresh every 60 s ───────────────────────────────────────────────

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = datetime.now()
if (datetime.now() - st.session_state["last_refresh"]).total_seconds() > 60:
    st.session_state["last_refresh"] = datetime.now()
    st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────

state        = load_json(STATE_FILE, {"last_run": None, "stocks": {}})
logs         = load_json(LOG_FILE, [])
stocks_state = state.get("stocks", {})
last_run_raw = state.get("last_run")
now_ist      = datetime.now(IST)
mkt_open     = market_open()

# ── Header ────────────────────────────────────────────────────────────────

mkt_color    = C["green"] if mkt_open else C["faint"]
mkt_label    = "OPEN" if mkt_open else "CLOSED"
last_run_str = (last_run_raw or "")[:16].replace("T", " ") or "Never"
next_run_min = 15 - (now_ist.minute % 15)
next_run_str = (now_ist + timedelta(minutes=next_run_min)).strftime("%I:%M %p")

rh(f"""
<div style="background:linear-gradient(180deg,{C['panel']},{C['panel2']});border:1px solid {C['bd']};border-radius:16px;padding:18px 22px;margin-bottom:16px;">
<div style="font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:{C['text']};">📊 {DASHBOARD_TITLE}</div>
<div style="color:{C['muted']};font-size:0.82rem;margin-top:2px;margin-bottom:12px;">EMA20 crossover alerts · 30-min candles · NSE stocks · runs every 15 min</div>
<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
<span style="background:{C['panel2']};border:1px solid {mkt_color}55;border-radius:999px;padding:5px 12px;font-size:0.76rem;display:flex;align-items:center;gap:6px;">
<span style="width:8px;height:8px;border-radius:50%;background:{mkt_color};display:inline-block;"></span>
<span style="color:{C['muted']};">NSE Market</span><span style="color:{mkt_color};font-weight:700;">{mkt_label}</span></span>
<span style="background:{C['panel2']};border:1px solid {C['bd']};border-radius:999px;padding:5px 12px;font-size:0.76rem;color:{C['muted']};font-family:'JetBrains Mono',monospace;">🕐 IST {now_ist.strftime('%I:%M:%S %p')}</span>
<span style="background:{C['panel2']};border:1px solid {C['bd']};border-radius:999px;padding:5px 12px;font-size:0.76rem;color:{C['muted']};font-family:'JetBrains Mono',monospace;">⟳ Last scan {last_run_str}</span>
<span style="background:{C['panel2']};border:1px solid {C['bd']};border-radius:999px;padding:5px 12px;font-size:0.76rem;color:{C['muted']};font-family:'JetBrains Mono',monospace;">⏭ Next ~{next_run_str}</span>
</div></div>
""")

# ── KPI cards ─────────────────────────────────────────────────────────────

total   = len(stocks_state)
above   = sum(1 for s in stocks_state.values() if s.get("position") == "above")
below   = sum(1 for s in stocks_state.values() if s.get("position") == "below")
tot_runs = len(logs)
tot_alerts = sum(r.get("alerts_sent", 0) for r in logs)

def kpi(col, icon, label, value, color):
    with col:
        rh(f"""
        <div style="background:linear-gradient(180deg,{C['panel']},{C['panel2']});border:1px solid {C['bd']};border-top:3px solid {color};border-radius:14px;padding:16px 14px;margin-bottom:4px;">
        <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;color:{C['muted']};font-weight:600;">{icon} {label}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.7rem;font-weight:700;color:{C['text']};margin-top:6px;">{value}</div>
        </div>""")

c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "📊", "Tracked Stocks",   total,      C["teal"])
kpi(c2, "▲",  "Above EMA20",      above,      C["green"])
kpi(c3, "▼",  "Below EMA20",      below,      C["red"])
kpi(c4, "⟳",  "Total Runs",       tot_runs,   C["amber"])
kpi(c5, "🔔", "Total Alerts",     tot_alerts, C["teal"])

st.markdown("")

# ── Tabs ──────────────────────────────────────────────────────────────────

t1, t2, t3 = st.tabs(["📋 Current Positions", "🔔 Recent Alerts", "📜 Run History"])

# ── Tab 1: Positions ──────────────────────────────────────────────────────

with t1:
    if not stocks_state:
        rh(f"""<div style="background:{C['panel']};border:1px solid {C['bd']};border-radius:12px;padding:32px;text-align:center;color:{C['muted']};">No state data yet. Wait for the first GitHub Actions run.</div>""")
    else:
        search = st.text_input("🔍 Filter", placeholder="Stock name, sector, ABOVE, BELOW…", key="pos_q")
        ca, cb = st.columns([2, 1])
        rows = [{
            "Stock":      n,
            "Sector":     s.get("sector","—"),
            "Position":   s.get("position","—").upper(),
            "Close":      s.get("close", 0),
            "EMA20":      s.get("ema20", 0),
            "Dist %":     round(((s.get("close",0)-s.get("ema20",1))/max(s.get("ema20",1),0.01))*100, 2),
            "Last Cross": s.get("last_cross") or "—",
            "Cross Time": (s.get("cross_time") or "—")[:16].replace("T"," "),
            "Alerted":    "✅" if s.get("alerted") else "—",
        } for n, s in stocks_state.items()]
        df = pd.DataFrame(rows)
        if search:
            mask = df.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False)).any(axis=1)
            df = df[mask]
        with ca:
            sort_col = st.selectbox("Sort by", df.columns.tolist(), index=5, key="pos_sort")
        with cb:
            asc = st.checkbox("Asc", key="pos_asc")
        df = df.sort_values(sort_col, ascending=asc)

        th_s = f"padding:9px 12px;text-align:left;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.03em;color:{C['muted']};background:{C['panel2']};border-bottom:1px solid {C['bds']};white-space:nowrap;"
        headers_html = "".join(f"<th style='{th_s}'>{c}</th>" for c in df.columns)

        def build_row(row):
            pos = row["Position"]
            pc  = C["green"] if pos == "ABOVE" else C["red"] if pos == "BELOW" else C["muted"]
            cells = []
            for col_name, val in row.items():
                base = f"padding:9px 12px;border-bottom:1px solid {C['bd']};font-size:0.82rem;"
                if col_name == "Position":
                    cells.append(f'<td style="{base}"><span style="color:{pc};font-weight:700;font-family:\'JetBrains Mono\',monospace;">{val}</span></td>')
                elif col_name in ("Close","EMA20","Dist %"):
                    cells.append(f'<td style="{base}font-family:\'JetBrains Mono\',monospace;color:{C["text"]};">{val}</td>')
                else:
                    cells.append(f'<td style="{base}color:{C["text"]};">{val}</td>')
            return f"<tr>{''.join(cells)}</tr>"

        rows_html = "".join(build_row(r) for _, r in df.iterrows())
        rh(f"""
        <div style="border:1px solid {C['bd']};border-radius:12px;overflow:auto;background:{C['panel']};max-height:500px;">
        <table style="width:100%;border-collapse:collapse;font-size:0.83rem;">
        <thead><tr>{headers_html}</tr></thead><tbody>{rows_html}</tbody>
        </table></div>
        <div style="color:{C['faint']};font-size:0.72rem;margin-top:6px;">Showing {len(df)} of {len(stocks_state)} stocks</div>
        """)

# ── Tab 2: Alerts ─────────────────────────────────────────────────────────

with t2:
    all_alerts = []
    for run in reversed(logs):
        rt = run.get("timestamp_ist","")[:16].replace("T"," ")
        for a in run.get("alerts", []):
            all_alerts.append({**a, "_run_time": rt, "_email": run.get("email_status","—")})

    if not all_alerts:
        rh(f"""<div style="background:{C['panel']};border:1px solid {C['bd']};border-radius:12px;padding:32px;text-align:center;color:{C['muted']};">No alerts yet — crossovers will appear here once detected.</div>""")
    else:
        rh(f"""<div style="margin-bottom:10px;color:{C['muted']};font-size:0.82rem;">{len(all_alerts)} alerts across all runs · most recent first</div>""")
        for a in all_alerts[:50]:
            ib    = a["type"] == "BREAKOUT"
            color = C["green"] if ib else C["red"]
            icon  = "▲" if ib else "▼"
            dist  = ((a["close"] - a["ema20"]) / max(a["ema20"], 0.01)) * 100
            rh(f"""
            <div style="background:{C['panel']};border:1px solid {C['bd']};border-left:3px solid {color};border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <span style="color:{color};font-weight:700;font-size:1.1rem;min-width:20px;">{icon}</span>
            <div style="flex:1;min-width:130px;">
            <div style="font-weight:700;color:{C['text']};font-size:0.95rem;">{a['stock']}</div>
            <div style="color:{C['muted']};font-size:0.72rem;">{a.get('sector','—')} · {a['_run_time']}</div>
            </div>
            <div style="text-align:right;min-width:160px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:{C['text']};">Close: {a['close']:.2f} | EMA20: {a['ema20']:.2f}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{color};">{dist:+.2f}% · {a['_email']}</div>
            </div></div>
            """)

# ── Tab 3: Run history ────────────────────────────────────────────────────

with t3:
    if not logs:
        rh(f"""<div style="background:{C['panel']};border:1px solid {C['bd']};border-radius:12px;padding:32px;text-align:center;color:{C['muted']};">No run history yet.</div>""")
    else:
        for run in reversed(logs[-40:]):
            ts       = run.get("timestamp_ist","—")[:16].replace("T"," ")
            n_scan   = run.get("stocks_scanned", 0)
            n_alert  = run.get("alerts_sent", 0)
            status   = run.get("email_status","—")
            errs     = run.get("errors", [])
            mkt      = run.get("market_open", True)
            sc       = C["green"] if status in ("gmail_ok","sendgrid_ok") else C["amber"] if status in ("no_alerts","skipped_market_closed") else C["red"]
            err_tag  = f'<span style="font-size:0.75rem;color:{C["red"]};">⚠ {len(errs)} error(s)</span>' if errs else ""
            mkt_tag  = f'<span style="font-size:0.75rem;color:{C["faint"]};">Market closed</span>' if not mkt else ""
            rh(f"""
            <div style="background:{C['panel']};border:1px solid {C['bd']};border-radius:10px;padding:10px 16px;margin-bottom:6px;display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{C['muted']};min-width:130px;">{ts}</span>
            <span style="font-size:0.8rem;color:{C['text']};">Scanned <b>{n_scan}</b></span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{C['amber']};">🔔 {n_alert} alert{'s' if n_alert!=1 else ''}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:{sc};">{status}</span>
            {err_tag}{mkt_tag}
            </div>
            """)

# ── Footer ────────────────────────────────────────────────────────────────

rh(f"""
<div style="margin-top:24px;padding:14px;text-align:center;color:{C['faint']};font-size:0.72rem;border-top:1px solid {C['bd']};">
Auto-refreshes every 60 s &nbsp;·&nbsp; State: <code style="color:{C['muted']};">{STATE_FILE}</code> &nbsp;·&nbsp; Logs: <code style="color:{C['muted']};">{LOG_FILE}</code>
</div>
""")
