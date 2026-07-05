"""
alerts/alert_formatter.py
Builds the HTML email + plain-text fallback for crossover alerts.
Uses inline styles throughout — many email clients strip <style> blocks.
"""
from datetime import datetime
import pytz
from config.alert_config import MARKET_TIMEZONE

IST = pytz.timezone(MARKET_TIMEZONE)

# Inline colour tokens (safe for all email clients)
BG     = "#0A0E14"
PANEL  = "#11161F"
PANEL2 = "#161C28"
BORDER = "#1E2535"
TEXT   = "#E6EAF0"
MUTED  = "#8A93A6"
GREEN  = "#16C784"
RED    = "#FF4D4D"


def _stock_row(a: dict) -> str:
    is_break    = a["type"] == "BREAKOUT"
    color       = GREEN if is_break else RED
    badge_bg    = "#0F2B1E" if is_break else "#2B0F0F"
    badge_label = "▲ BREAKOUT" if is_break else "▼ BREAKDOWN"
    dist        = ((a["close"] - a["ema20"]) / a["ema20"]) * 100
    td          = f'border-bottom:1px solid {BORDER};padding:10px 12px;'

    return (
        f'<tr>'
        f'<td style="{td}font-weight:600;color:{TEXT};">{a["stock"]}</td>'
        f'<td style="{td}color:{MUTED};font-size:12px;">{a.get("sector","—")}</td>'
        f'<td style="{td}font-family:monospace;color:{TEXT};">{a["close"]:.2f}</td>'
        f'<td style="{td}font-family:monospace;color:{MUTED};">{a["ema20"]:.2f}</td>'
        f'<td style="{td}font-family:monospace;color:{color};">{dist:+.2f}%</td>'
        f'<td style="{td}">'
        f'<span style="background:{badge_bg};color:{color};border:1px solid {color}44;'
        f'border-radius:4px;padding:3px 8px;font-size:11px;font-weight:700;">'
        f'{badge_label}</span></td>'
        f'</tr>'
    )


def build_subject(alerts: list) -> str:
    b = sum(1 for a in alerts if a["type"] == "BREAKOUT")
    d = sum(1 for a in alerts if a["type"] == "BREAKDOWN")
    parts = []
    if b: parts.append(f"▲ {b} Breakout{'s' if b > 1 else ''}")
    if d: parts.append(f"▼ {d} Breakdown{'s' if d > 1 else ''}")
    return "🚨 EMA20 Alert: " + " | ".join(parts) + " | NSE 30min"


def build_email_html(alerts: list, run_id: str) -> str:
    now    = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p IST")
    b      = sum(1 for a in alerts if a["type"] == "BREAKOUT")
    d      = sum(1 for a in alerts if a["type"] == "BREAKDOWN")
    summary_parts = []
    if b: summary_parts.append(f'<span style="color:{GREEN};font-weight:700;">▲ {b} Breakout{"s" if b>1 else ""}</span>')
    if d: summary_parts.append(f'<span style="color:{RED};font-weight:700;">▼ {d} Breakdown{"s" if d>1 else ""}</span>')
    summary = " &nbsp;|&nbsp; ".join(summary_parts)

    th = (f'background:{PANEL};border-bottom:1px solid {BORDER};'
          f'padding:9px 12px;text-align:left;font-size:11px;'
          f'text-transform:uppercase;color:{MUTED};')

    headers = "".join(f"<th style='{th}'>{h}</th>"
                      for h in ["Stock","Sector","Close","EMA20","Distance","Signal"])
    rows = "".join(_stock_row(a) for a in alerts)

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EMA20 Alert</title></head>
<body style="margin:0;padding:0;background:{BG};font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:20px 16px;">
<table width="100%" style="max-width:680px;margin:0 auto;">
<tr><td style="background:linear-gradient(135deg,#00D9C0,#16C784);border-radius:12px 12px 0 0;padding:22px 24px;">
<div style="font-size:21px;font-weight:700;color:#04211D;">📈 EMA20 Crossover Alert</div>
<div style="font-size:13px;color:#04211D;opacity:0.8;margin-top:4px;">{now} · Run: {run_id}</div>
</td></tr>
<tr><td style="background:{PANEL};padding:14px 24px;border-left:1px solid {BORDER};border-right:1px solid {BORDER};">
<div style="font-size:14px;">{summary}</div>
<div style="font-size:12px;color:{MUTED};margin-top:4px;">EMA20 on 30-minute candles · NSE stocks</div>
</td></tr>
<tr><td style="background:{PANEL2};border:1px solid {BORDER};border-top:none;">
<table width="100%" style="border-collapse:collapse;font-size:13px;">
<thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>
</td></tr>
<tr><td style="background:{PANEL};padding:14px 24px;text-align:center;border:1px solid {BORDER};
border-top:none;border-radius:0 0 12px 12px;">
<div style="font-size:11px;color:{MUTED};">Alerts fire once per crossover and reset only after
price reverts and crosses again. To unsubscribe, remove your address from
config/alert_config.py.</div>
</td></tr>
</table>
</td></tr></table></body></html>"""


def build_email_text(alerts: list, run_id: str) -> str:
    now = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p IST")
    lines = [f"EMA20 Crossover Alert — {now}", f"Run: {run_id}", "="*60]
    for a in alerts:
        dist = ((a["close"] - a["ema20"]) / a["ema20"]) * 100
        lines.append(f"{a['type']:<10} {a['stock']:<22} Close:{a['close']:>8.2f}  "
                     f"EMA20:{a['ema20']:>8.2f}  Dist:{dist:+.2f}%")
    lines += ["="*60, "Alerts reset only after price reverts and crosses again."]
    return "\n".join(lines)
