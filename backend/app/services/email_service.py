"""Send transactional emails via Gmail SMTP (STARTTLS, port 587).

Required env vars:
    SMTP_USER      — your Gmail address (e.g. yourapp@gmail.com)
    SMTP_PASSWORD  — Gmail App Password (not your login password)
    SMTP_FROM      — display name + address, e.g. "SoukPilot <yourapp@gmail.com>"
    APP_URL        — public frontend URL, e.g. https://soukpilot.up.railway.app

If SMTP_USER is not configured the send is skipped and a warning is logged
(safe for local dev where no email config exists).
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_password_reset(to_email: str, reset_token: str) -> None:
    if not settings.smtp_user:
        logger.warning("smtp_not_configured_skipping_email", to=to_email)
        return

    reset_url = f"{settings.app_url.rstrip('/')}/reset-password?token={reset_token}"

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#060818;color:#e2e8f0;border-radius:12px">
      <h2 style="color:#818cf8;margin-bottom:8px">Reset your password</h2>
      <p style="color:#94a3b8;line-height:1.6">
        We received a request to reset the password for your SoukPilot account.
        Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.
      </p>
      <a href="{reset_url}"
         style="display:inline-block;margin:24px 0;padding:12px 28px;background:#6366f1;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px">
        Reset password
      </a>
      <p style="color:#64748b;font-size:12px;margin-top:24px">
        If you didn't request this, you can safely ignore this email — your password won't change.
      </p>
      <p style="color:#64748b;font-size:11px;word-break:break-all">
        Or copy this link: {reset_url}
      </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your SoukPilot password"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_email, msg.as_string())
        logger.info("password_reset_email_sent", to=to_email)
    except Exception as exc:
        logger.error("password_reset_email_failed", to=to_email, err=str(exc))
        raise
