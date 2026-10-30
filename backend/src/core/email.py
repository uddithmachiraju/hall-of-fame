import hashlib
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


def generate_token() -> str:
    """Generates a random token for email verification."""

    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hashes the token using SHA-256."""

    return hashlib.sha256(token.encode()).hexdigest()


def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send an email using SMTP."""

    if not settings.SMTP_HOST:
        logger.info("email_skipped_no_smtp", to=to_email, subject=subject, preview=text_body[:200])

        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info("email_sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", to=to_email, subject=subject, error=str(e))
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send an email verification email to the user after registration."""

    verify_url = f"{settings.APP_BASE_URL}/auth/verify-email?token={token}"

    text = f"""Hi {username},

    Welcome! Please verify your email address by clicking the link below:
    {verify_url}
    This link will expire in {settings.EMAIL_VERIFY_EXPIRE_HOURS} hours. If you did not create an account, please ignore this email.

    - The {settings.APP_NAME} Team
    """

    html = f"""
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:40px auto;color:#111928">
  <h2 style="color:#1A56DB">Verify your email address</h2>
  <p>Hi <strong>{username}</strong>,</p>
  <p>Welcome! Click the button below to verify your email and activate your account.</p>
  <p style="margin:32px 0">
    <a href="{verify_url}"
       style="background:#1A56DB;color:white;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold;display:inline-block">
      Verify Email Address
    </a>
  </p>
  <p style="color:#6B7280;font-size:13px">
    This link expires in <strong>24 hours</strong>.<br>
    If you did not create an account, you can safely ignore this email.
  </p>
  <hr style="border:none;border-top:1px solid #E5E7EB;margin:32px 0">
  <p style="color:#6B7280;font-size:12px">— {settings.APP_NAME} Team</p>
</body></html>
"""
    return _send_email(to_email, "Please verify your account", html, text)
