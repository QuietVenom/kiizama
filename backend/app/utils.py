import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
import resend
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings
from app.core.resilience import (
    mark_dependency_failure,
    mark_dependency_success,
    translate_resend_exception,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


class EmailNotConfiguredError(RuntimeError):
    pass


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def _send_email_via_resend(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    resend.api_key = settings.RESEND_API_KEY
    from_email = str(settings.EMAILS_FROM_EMAIL)
    from_name = settings.EMAILS_FROM_NAME
    sender = f"{from_name} <{from_email}>" if from_name else from_email
    response = resend.Emails.send(
        {
            "from": sender,
            "to": [email_to],
            "subject": subject,
            "html": html_content,
        }
    )
    logger.info("send email result: %s", response)


def send_email_or_raise(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    if not settings.emails_enabled:
        translated = translate_resend_exception(
            EmailNotConfiguredError("Email service is not configured."),
            detail="Email service is not configured.",
            retryable=False,
        )
        mark_dependency_failure(
            "resend",
            context="email-send",
            detail=translated.detail,
            status="degraded",
        )
        raise translated

    try:
        _send_email_via_resend(
            email_to=email_to,
            subject=subject,
            html_content=html_content,
        )
    except Exception as exc:
        translated = translate_resend_exception(exc)
        mark_dependency_failure(
            "resend",
            context="email-send",
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
        raise translated from exc

    mark_dependency_success(
        "resend",
        context="email-send",
        detail="Resend email sent successfully.",
    )


def send_email_best_effort(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    try:
        send_email_or_raise(
            email_to=email_to,
            subject=subject,
            html_content=html_content,
        )
    except Exception as exc:
        logger.warning("Skipping email delivery after Resend failure: %s", exc)


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    send_email_or_raise(
        email_to=email_to,
        subject=subject,
        html_content=html_content,
    )


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


__all__ = [
    "EmailData",
    "EmailNotConfiguredError",
    "generate_new_account_email",
    "generate_password_reset_token",
    "generate_reset_password_email",
    "generate_test_email",
    "render_email_template",
    "send_email",
    "send_email_best_effort",
    "send_email_or_raise",
    "verify_password_reset_token",
]
