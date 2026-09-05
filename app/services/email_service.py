"""Outbound email. Uses SMTP when configured; otherwise logs for the operator.

SMTP settings are optional in config (smtp_server et al.). On a deployment
without them, send_email() returns False and the caller decides on a
fallback. For password resets that fallback is logging the reset link at
WARNING — visible only in server logs (`docker compose logs api`), a
deliberate operator-only channel until SMTP is configured.
"""

import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(settings.smtp_server and settings.smtp_port)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not smtp_configured():
        logger.warning("SMTP not configured — email to %s ('%s') not sent", to, subject)
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_username or "no-reply@lexara.tech"
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("failed to send email to %s", to)
        return False
