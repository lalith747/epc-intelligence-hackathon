"""
Optional email delivery for notifications. Sends via SMTP if configured
(SMTP_HOST + SMTP_USER in backend/.env); otherwise logs and no-ops. Dashboard
notifications work regardless - email is an additive channel, same
graceful-degradation pattern as services/redis.py.
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _send_smtp(msg: MIMEMultipart, to_email: str) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(msg["From"], [to_email], msg.as_string())


async def send_notification_email(to_email: str, project_name: str, notifications: List) -> bool:
    """Send a summary email for a batch of notifications. Returns True if actually sent."""
    if not settings.smtp_host or not settings.smtp_user:
        logger.info(
            f"SMTP not configured - skipping email to {to_email} "
            f"({len(notifications)} notification(s) for {project_name}). "
            "Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in backend/.env to enable."
        )
        return False

    subject = f"[{project_name}] {len(notifications)} new alert{'s' if len(notifications) != 1 else ''}"
    lines = [f"- [{n.severity.upper()}] {n.title}" for n in notifications]
    body = f"New alerts for {project_name}:\n\n" + "\n".join(lines)

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        await asyncio.to_thread(_send_smtp, msg, to_email)
        logger.info(f"Sent notification email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")
        return False
