import jwt
import pytest

from app import utils
from app.core import security
from app.core.resilience import DependencyUnavailableError
from app.utils import (
    generate_new_account_email,
    generate_password_reset_token,
    generate_reset_password_email,
    generate_test_email,
    send_email_best_effort,
    send_email_or_raise,
    verify_password_reset_token,
)


def test_generate_email_helpers_render_expected_subjects_and_context() -> None:
    reset_token = "reset-token"

    test_email = generate_test_email("recipient@example.com")
    reset_email = generate_reset_password_email(
        "recipient@example.com",
        "user@example.com",
        reset_token,
    )
    new_account_email = generate_new_account_email(
        "recipient@example.com",
        "new-user@example.com",
        "SafePass1!",
    )

    assert "Test email" in test_email.subject
    assert "recipient@example.com" in test_email.html_content
    assert "Password recovery" in reset_email.subject
    assert reset_token in reset_email.html_content
    assert "New account" in new_account_email.subject
    assert "new-user@example.com" in new_account_email.html_content


def test_password_reset_token_round_trip_and_invalid_token_returns_none() -> None:
    token = generate_password_reset_token("user@example.com")

    assert verify_password_reset_token(token) == "user@example.com"
    assert verify_password_reset_token("invalid-token") is None


def test_password_reset_token_uses_security_algorithm_and_secret() -> None:
    token = generate_password_reset_token("user@example.com")

    payload = jwt.decode(
        token,
        utils.settings.SECRET_KEY,
        algorithms=[security.ALGORITHM],
    )

    assert payload["sub"] == "user@example.com"
    assert "exp" in payload
    assert "nbf" in payload


def test_send_email_or_raise_unconfigured_email_raises_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils.settings, "RESEND_API_KEY", None)
    monkeypatch.setattr(utils.settings, "EMAILS_FROM_EMAIL", None)

    with pytest.raises(DependencyUnavailableError) as exc_info:
        send_email_or_raise(
            email_to="recipient@example.com",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

    assert exc_info.value.dependency == "resend"
    assert exc_info.value.retryable is False


def test_send_email_or_raise_configured_email_calls_resend_and_marks_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_payloads: list[dict[str, object]] = []
    successes: list[dict[str, object]] = []

    monkeypatch.setattr(utils.settings, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(utils.settings, "EMAILS_FROM_EMAIL", "from@example.com")
    monkeypatch.setattr(utils.settings, "EMAILS_FROM_NAME", "Kiizama")
    monkeypatch.setattr(
        utils.resend.Emails,
        "send",
        lambda payload: sent_payloads.append(payload) or {"id": "email_1"},
    )
    monkeypatch.setattr(
        utils,
        "mark_dependency_success",
        lambda dependency, **kwargs: successes.append(
            {"dependency": dependency, **kwargs}
        ),
    )

    send_email_or_raise(
        email_to="recipient@example.com",
        subject="Subject",
        html_content="<p>Hello</p>",
    )

    assert sent_payloads == [
        {
            "from": "Kiizama <from@example.com>",
            "to": ["recipient@example.com"],
            "subject": "Subject",
            "html": "<p>Hello</p>",
        }
    ]
    assert successes[0]["dependency"] == "resend"


def test_send_email_best_effort_swallows_delivery_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        utils,
        "send_email_or_raise",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("resend down")),
    )

    send_email_best_effort(
        email_to="recipient@example.com",
        subject="Subject",
        html_content="<p>Hello</p>",
    )
