from typing import Any

import pytest
from pydantic import ValidationError

from app.features.brand_intelligence.classes import (
    AUDIENCE_OPTIONS,
    BRAND_GOALS_TYPE_OPTIONS,
    CREATOR_GOAL_TYPE_OPTIONS,
    TIMEFRAME_OPTIONS,
)
from app.features.brand_intelligence.schemas import (
    ReputationCampaignStrategyRequest,
    ReputationCreatorStrategyRequest,
    ReputationSignalsInput,
    normalize_lookup_usernames,
)

VALID_CAMPAIGN_TYPE = "all_micro_performance_community_trust"


def _campaign_payload() -> dict[str, Any]:
    return {
        "brand_name": "Acme",
        "brand_context": "Skincare brand focused on clean ingredients.",
        "brand_urls": ["https://acme.com"],
        "brand_goals_type": BRAND_GOALS_TYPE_OPTIONS[0],
        "brand_goals_context": "Increase trust and purchase confidence.",
        "audience": [AUDIENCE_OPTIONS[0]],
        "timeframe": TIMEFRAME_OPTIONS[0],
        "profiles_list": ["creator_one"],
        "campaign_type": VALID_CAMPAIGN_TYPE,
        "generate_html": True,
        "generate_pdf": False,
    }


def _creator_payload() -> dict[str, Any]:
    return {
        "creator_username": "creator.one",
        "creator_context": "Wellness creator with an engaged community.",
        "creator_urls": ["https://instagram.com/creator.one"],
        "goal_type": CREATOR_GOAL_TYPE_OPTIONS[0],
        "goal_context": "Reinforce trust during sponsored launches.",
        "audience": [AUDIENCE_OPTIONS[0]],
        "timeframe": TIMEFRAME_OPTIONS[0],
        "primary_platforms": ["Instagram"],
        "generate_html": True,
        "generate_pdf": False,
    }


def test_campaign_strategy_request_aliases_normalize_payload() -> None:
    # Arrange
    payload = _campaign_payload() | {
        "brand_urls": None,
        "brand_url": ["https://acme.com"],
        "audience": None,
        "Audience": [AUDIENCE_OPTIONS[1]],
        "profiles_list": ["Creator.One", "CREATOR_TWO"],
    }
    payload.pop("brand_urls")
    payload.pop("audience")

    # Act
    request = ReputationCampaignStrategyRequest.model_validate(payload)

    # Assert
    assert [str(url) for url in request.brand_urls] == ["https://acme.com/"]
    assert request.audience == [AUDIENCE_OPTIONS[1]]
    assert request.profiles_list == ["creator.one", "creator_two"]


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("brand_goals_type", "Invalid Goal", "brand_goals_type invalido"),
        ("audience", ["Invalid Audience"], "Audience invalido"),
        ("timeframe", "24 months", "timeframe invalido"),
        ("campaign_type", "invalid_campaign", "campaign_type invalido"),
    ],
)
def test_campaign_strategy_request_rejects_invalid_goal_audience_timeframe_campaign(
    field: str,
    value: Any,
    expected_message: str,
) -> None:
    # Arrange
    payload = _campaign_payload() | {field: value}

    # Act / Assert
    with pytest.raises(ValidationError, match=expected_message):
        ReputationCampaignStrategyRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("profiles_list", "expected_message"),
    [
        (
            ["creator_one", "CREATOR_ONE"],
            "profiles_list no debe contener valores duplicados",
        ),
        (["creator one"], "Cada valor en profiles_list debe cumplir"),
    ],
)
def test_campaign_strategy_request_rejects_duplicate_or_invalid_profiles(
    profiles_list: list[str],
    expected_message: str,
) -> None:
    # Arrange
    payload = _campaign_payload() | {"profiles_list": profiles_list}

    # Act / Assert
    with pytest.raises(ValidationError, match=expected_message):
        ReputationCampaignStrategyRequest.model_validate(payload)


def test_campaign_strategy_request_allows_empty_profiles_only_for_crisis() -> None:
    # Arrange
    valid_payload = _campaign_payload() | {
        "brand_goals_type": "Crisis",
        "profiles_list": [],
    }
    invalid_payload = _campaign_payload() | {"profiles_list": []}

    # Act
    valid_request = ReputationCampaignStrategyRequest.model_validate(valid_payload)

    # Assert
    assert valid_request.profiles_list == []
    with pytest.raises(
        ValidationError,
        match="Debe agregar al menos 1 creator username salvo que brand_goals_type sea Crisis",
    ):
        ReputationCampaignStrategyRequest.model_validate(invalid_payload)


def test_campaign_strategy_request_requires_at_least_one_output_format() -> None:
    # Arrange
    payload = _campaign_payload() | {"generate_html": False, "generate_pdf": False}

    # Act / Assert
    with pytest.raises(
        ValidationError,
        match="Debe solicitar al menos un formato \\(HTML o PDF\\)",
    ):
        ReputationCampaignStrategyRequest.model_validate(payload)


def test_creator_strategy_request_aliases_normalize_payload() -> None:
    # Arrange
    payload = _creator_payload() | {
        "creator_urls": None,
        "creator_url": ["https://instagram.com/creator.one"],
        "audience": None,
        "Audience": [AUDIENCE_OPTIONS[1]],
        "collaborators": [" Brand One ", "Brand Two"],
    }
    payload.pop("creator_urls")
    payload.pop("audience")

    # Act
    request = ReputationCreatorStrategyRequest.model_validate(payload)

    # Assert
    assert [str(url) for url in request.creator_urls] == [
        "https://instagram.com/creator.one"
    ]
    assert request.audience == [AUDIENCE_OPTIONS[1]]
    assert request.collaborators_list == ["Brand One", "Brand Two"]


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("creator_username", "creator one", "creator_username debe cumplir"),
        ("goal_type", "Invalid Goal", "goal_type invalido"),
        ("audience", ["Invalid Audience"], "Audience invalido"),
        ("timeframe", "24 months", "timeframe invalido"),
    ],
)
def test_creator_strategy_request_rejects_invalid_username_goal_audience_timeframe(
    field: str,
    value: Any,
    expected_message: str,
) -> None:
    # Arrange
    payload = _creator_payload() | {field: value}

    # Act / Assert
    with pytest.raises(ValidationError, match=expected_message):
        ReputationCreatorStrategyRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("primary_platforms", "expected_message"),
    [
        (
            ["Instagram", " instagram "],
            "primary_platforms no debe contener valores duplicados",
        ),
        (["Instagram", "   "], "primary_platforms no debe contener valores vacios"),
    ],
)
def test_creator_strategy_request_rejects_empty_or_duplicate_primary_platforms(
    primary_platforms: list[str],
    expected_message: str,
) -> None:
    # Arrange
    payload = _creator_payload() | {"primary_platforms": primary_platforms}

    # Act / Assert
    with pytest.raises(ValidationError, match=expected_message):
        ReputationCreatorStrategyRequest.model_validate(payload)


def test_creator_strategy_request_normalizes_reputation_signals() -> None:
    # Arrange
    payload = _creator_payload() | {
        "reputation_signals": {
            "strengths": " Trust ",
            "weaknesses": [" Low cadence ", None],
            "incidents": "",
            "concerns": ["Disclosure"],
        }
    }

    # Act
    request = ReputationCreatorStrategyRequest.model_validate(payload)

    # Assert
    assert request.reputation_signals is not None
    assert request.reputation_signals.model_dump() == {
        "strengths": ["Trust"],
        "weaknesses": ["Low cadence"],
        "incidents": [],
        "concerns": ["Disclosure"],
    }


@pytest.mark.parametrize(
    ("signals", "expected_message"),
    [
        (
            {"unknown": ["Trust"]},
            "reputation_signals solo admite estas llaves",
        ),
        (
            {"strengths": ["x" * 31]},
            "Cada valor en reputation_signals.strengths debe tener maximo 30 caracteres",
        ),
        (
            {"concerns": "x" * 31},
            "Cada valor en reputation_signals.concerns debe tener maximo 30 caracteres",
        ),
    ],
)
def test_creator_strategy_request_rejects_unknown_or_too_long_reputation_signals(
    signals: dict[str, Any],
    expected_message: str,
) -> None:
    # Arrange
    payload = _creator_payload() | {"reputation_signals": signals}

    # Act / Assert
    with pytest.raises(ValidationError, match=expected_message):
        ReputationCreatorStrategyRequest.model_validate(payload)


def test_creator_strategy_request_normalizes_collaborators_or_returns_none() -> None:
    # Arrange
    payload_with_values = _creator_payload() | {
        "collaborators_list": [" Brand One ", "Brand Two "]
    }
    payload_without_values = _creator_payload() | {"collaborators_list": []}

    # Act
    request_with_values = ReputationCreatorStrategyRequest.model_validate(
        payload_with_values
    )
    request_without_values = ReputationCreatorStrategyRequest.model_validate(
        payload_without_values
    )

    # Assert
    assert request_with_values.collaborators_list == ["Brand One", "Brand Two"]
    assert request_without_values.collaborators_list is None


def test_normalize_lookup_usernames_rejects_empty_invalid_and_normalizes_valid() -> (
    None
):
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="usernames cannot be empty"):
        normalize_lookup_usernames([])

    with pytest.raises(ValueError, match="usernames cannot contain empty values"):
        normalize_lookup_usernames(["creator_one", " "])

    with pytest.raises(ValueError, match="Cada username debe cumplir"):
        normalize_lookup_usernames(["creator one"])

    assert normalize_lookup_usernames([" Creator.One ", "CREATOR_TWO"]) == [
        "creator.one",
        "creator_two",
    ]


def test_creator_strategy_request_accepts_reputation_signals_model_input() -> None:
    # Arrange
    payload = _creator_payload() | {
        "reputation_signals": ReputationSignalsInput(
            strengths=["Trust"],
            concerns=["Disclosure"],
        )
    }

    # Act
    request = ReputationCreatorStrategyRequest.model_validate(payload)

    # Assert
    assert request.reputation_signals is not None
    assert request.reputation_signals.strengths == ["Trust"]
    assert request.reputation_signals.concerns == ["Disclosure"]
