"""Sends Campus Customs emails (password reset links).

If SMTP settings are in backend/.env (SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASSWORD, SMTP_FROM), the email is sent to the shopper's inbox. Without
them (for example on a grader's laptop), the email is saved to
backend/logs/outbox/ instead so the reset link can still be opened and tested.
That folder is in .gitignore, so these emails never go to GitHub.

Emails never contain a password, only a one-time reset link.
"""

import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

OUTBOX_DIR = Path(__file__).resolve().parent / "logs" / "outbox"


def site_url() -> str:
    return os.environ.get("SITE_URL", "http://localhost:5173").rstrip("/")


def send_password_reset(to_email: str, first_name: str, token: str, minutes: int) -> str:
    """Email the reset link. Returns 'smtp' or the outbox file path it was saved to."""
    link = f"{site_url()}/reset-password?token={token}"
    msg = EmailMessage()
    msg["Subject"] = "Reset your Campus Customs password"
    msg["From"] = os.environ.get("SMTP_FROM", "Campus Customs <no-reply@campuscustoms.local>")
    msg["To"] = to_email
    msg.set_content(
        f"Hi {first_name or 'there'},\n\n"
        "Someone tried to log in to your Campus Customs account 3 times with the wrong "
        "password. To keep your account safe, please choose a new password using this link:\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {minutes} minutes. If this wasn't you, "
        "changing your password is still a good idea.\n\n"
        "Boola boola,\nCampus Customs\n"
    )
    host = os.environ.get("SMTP_HOST")
    if host:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as smtp:
            smtp.starttls()
            if os.environ.get("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return "smtp"
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTBOX_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{int(time.time() * 1000) % 1000:03d}-password-reset.eml"
    path.write_bytes(bytes(msg))
    print(f"[mailer] No SMTP settings, so the password reset email was saved to {path}")
    return str(path)
