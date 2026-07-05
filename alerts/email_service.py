"""
alerts/email_service.py
Gmail SMTP (primary) → SendGrid REST (fallback).
Returns a status string so the caller can log which channel was used.

Gmail setup:
    1. Enable 2-Step Verification on the sender account.
    2. Google Account → Security → App Passwords → Mail → Generate.
    3. Store the 16-char password as GMAIL_APP_PASSWORD GitHub Secret.

SendGrid setup (free 100 emails/day):
    1. sendgrid.com → Settings → API Keys → Mail Send only.
    2. Store as SENDGRID_API_KEY GitHub Secret.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.alert_config import (
    ALERT_RECIPIENTS,
    GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_SMTP_HOST, GMAIL_SMTP_PORT,
    SENDGRID_API_KEY, SENDGRID_FROM,
)

logger = logging.getLogger(__name__)


def _send_gmail(subject: str, html: str, plain: str) -> bool:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.warning("Gmail credentials not set (GMAIL_USER / GMAIL_APP_PASSWORD)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"EMA Alert Engine <{GMAIL_USER}>"
        msg["To"]      = ", ".join(ALERT_RECIPIENTS)
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=30) as s:
            s.ehlo(); s.starttls(); s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, ALERT_RECIPIENTS, msg.as_string())
        logger.info("Gmail sent to %s", ALERT_RECIPIENTS)
        return True
    except Exception as exc:
        logger.error("Gmail failed: %s", exc)
        return False


def _send_sendgrid(subject: str, html: str, plain: str) -> bool:
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set")
        return False
    try:
        from sendgrid import SendGridAPIClient          # late import
        from sendgrid.helper.mail import Mail, Content, To
        msg = Mail(
            from_email=SENDGRID_FROM or "alerts@example.com",
            to_emails=[To(r) for r in ALERT_RECIPIENTS],
            subject=subject,
        )
        msg.content = [Content("text/plain", plain), Content("text/html", html)]
        resp = SendGridAPIClient(SENDGRID_API_KEY).send(msg)
        if resp.status_code in (200, 202):
            logger.info("SendGrid sent (status %d)", resp.status_code)
            return True
        logger.error("SendGrid status %d: %s", resp.status_code, resp.body)
        return False
    except ImportError:
        logger.error("sendgrid package not installed — pip install sendgrid")
        return False
    except Exception as exc:
        logger.error("SendGrid failed: %s", exc)
        return False


def send_alert_email(subject: str, html: str, plain: str) -> str:
    """Try Gmail first, fall back to SendGrid. Returns status string."""
    if not GMAIL_USER and not SENDGRID_API_KEY:
        logger.warning("No email credentials configured — alert not sent")
        return "no_config"
    if _send_gmail(subject, html, plain):
        return "gmail_ok"
    logger.warning("Gmail failed — trying SendGrid fallback")
    if _send_sendgrid(subject, html, plain):
        return "sendgrid_ok"
    return "both_failed"
