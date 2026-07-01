import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from app.config import get_settings

settings = get_settings()


def generate_pin() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def generate_registration_id() -> str:
    return f"REG-{secrets.token_hex(8).upper()}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def send_email(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to

    if settings.app_env == "development":
        print(f"[EMAIL] To: {to} | Subject: {subject} | Body: {body}")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_user and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def send_pin_email(email: str, pin: str, registration_id: str) -> None:
    body = (
        f"Welcome to JSE Analytics Platform.\n\n"
        f"Your Registration ID: {registration_id}\n"
        f"Your PIN: {pin}\n\n"
        f"This PIN expires in 15 minutes.\n"
        f"Please confirm your account at the registration confirmation page."
    )
    send_email(email, "JSE Analytics - Account Activation PIN", body)


def send_verification_email(email: str, token: str) -> None:
    body = (
        f"Please verify your email address.\n\n"
        f"Verification token: {token}\n\n"
        f"Use this token on the email verification page."
    )
    send_email(email, "JSE Analytics - Email Verification", body)


def send_password_reset_email(email: str, token: str) -> None:
    body = (
        f"You requested a password reset.\n\n"
        f"Reset token: {token}\n\n"
        f"This token expires in 1 hour."
    )
    send_email(email, "JSE Analytics - Password Reset", body)


def pin_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=15)


def token_expiry_hours(hours: int = 1) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)
