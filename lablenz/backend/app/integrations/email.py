"""
Email integration using the Resend API.

In development (RESEND_API_KEY is None), emails are not sent — the link is
printed to stdout so you can test flows without a real API key.

Usage:
    from app.integrations.email import send_password_reset_email, send_verification_email

    send_password_reset_email(to_email="user@example.com", token="<jwt>")
    send_verification_email(to_email="user@example.com", token="<jwt>")
"""

import logging

from ..config import settings

logger = logging.getLogger(__name__)


def _send(*, to: str, subject: str, html: str) -> None:
    """Low-level send via Resend. Falls back to console log in dev."""
    if not settings.RESEND_API_KEY:
        logger.warning(
            "[EMAIL DEV MODE] Would send '%s' to %s\n%s",
            subject,
            to,
            html,
        )
        return

    import resend  # imported lazily so the app starts without the package in dev

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )


def send_password_reset_email(*, to_email: str, token: str) -> None:
    """Send a password reset link to the user."""
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    html = f"""
    <p>You requested a password reset for your account.</p>
    <p>
      <a href="{reset_url}">Reset your password</a>
    </p>
    <p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
    <p>If you did not request a password reset, you can safely ignore this email.</p>
    """
    _send(
        to=to_email,
        subject="Reset your password",
        html=html,
    )


def send_verification_email(*, to_email: str, token: str) -> None:
    """Send an email address verification link to the user."""
    verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    html = f"""
    <p>Please verify your email address to activate your account.</p>
    <p>
      <a href="{verify_url}">Verify email address</a>
    </p>
    <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} hours.</p>
    <p>If you did not create an account, you can safely ignore this email.</p>
    """
    _send(
        to=to_email,
        subject="Verify your email address",
        html=html,
    )
