from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from .classes import (
    AUDIENCE_OPTIONS,
    BRAND_GOALS_TYPE_OPTIONS,
    CAMPAIGN_TYPE_NAMES,
    CAMPAIGN_TYPE_OPTIONS,
    CREATOR_GOAL_TYPE_OPTIONS,
    TIMEFRAME_OPTIONS,
)

PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9._]{1,30}$")


class CampaignTypeCatalogItem(BaseModel):
    name: str
    title: str
    value: str


class CostTierCatalogItem(BaseModel):
    key: str
    label: str
    min_followers: int | None = None
    max_followers: int | None = None
    typical_deliverable: str
    min_mxn: int
    max_mxn: int
    average_mxn: int
    notes: str
    is_manual: bool = False


class CostSegmentSummaryItem(BaseModel):
    tier_key: str
    tier_label: str
    profiles_count: int = 0
    typical_deliverable: str | None = None
    segment_min_mxn: int = 0
    segment_max_mxn: int = 0
    segment_average_mxn: int = 0
    notes: str | None = None


class CostAnalysisSummary(BaseModel):
    currency: str = "MXN"
    total_profiles: int = 0
    classified_profiles: int = 0
    unclassified_profiles: int = 0
    total_min_mxn: int = 0
    total_max_mxn: int = 0
    total_average_mxn: int = 0


class CostAnalysis(BaseModel):
    summary: CostAnalysisSummary = Field(default_factory=CostAnalysisSummary)
    summary_by_segment: list[CostSegmentSummaryItem] = Field(default_factory=list)


class InfluencerMetricsSummary(BaseModel):
    total_posts: int = 0
    total_comments: int = 0
    total_likes: int = 0
    avg_engagement_rate: float = 0.0
    hashtags_per_post: float = 0.0
    mentions_per_post: float = 0.0
    total_reels: int = 0
    total_plays: int = 0
    overall_engagement_rate: float = 0.0


class InfluencerProfileDirectoryItem(BaseModel):
    username: str
    full_name: str | None = None
    biography: str | None = None
    is_verified: bool = False
    profile_pic_url: str | None = None
    follower_count: int = 0
    ai_categories: list[str] = Field(default_factory=list)
    ai_roles: list[str] = Field(default_factory=list)
    metrics: InfluencerMetricsSummary = Field(default_factory=InfluencerMetricsSummary)


class ProfileExistenceItem(BaseModel):
    username: str
    exists: bool
    expired: bool


class ProfileExistenceCollection(BaseModel):
    profiles: list[ProfileExistenceItem] = Field(default_factory=list)


class ReputationSignalsInput(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    incidents: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    def has_any_value(self) -> bool:
        return any(
            (
                self.strengths,
                self.weaknesses,
                self.incidents,
                self.concerns,
            )
        )


class ReputationCampaignStrategyRequest(BaseModel):
    brand_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Nombre de la marca.",
    )
    brand_context: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contexto general de la marca (max 250 caracteres).",
    )
    brand_urls: list[HttpUrl] = Field(
        default_factory=list,
        max_length=3,
        description="Lista de URLs de marca (max 3).",
    )
    brand_goals_type: str = Field(
        ...,
        description="Goal principal de marca.",
    )
    brand_goals_context: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contexto adicional del goal de marca (max 250 caracteres).",
    )
    audience: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Audiencias objetivo de la campana.",
    )
    timeframe: str = Field(
        ...,
        description="Horizonte temporal de la campana.",
    )
    profiles_list: list[str] = Field(
        ...,
        min_length=1,
        max_length=15,
        description="Lista de perfiles (max 15).",
    )
    campaign_type: str = Field(
        ...,
        description="Estrategia de campana seleccionada.",
        examples=["all_micro_performance_community_trust"],
    )
    generate_html: bool = Field(
        default=True,
        description="Indica si debe generarse el HTML.",
    )
    generate_pdf: bool = Field(
        default=False,
        description="Indica si debe generarse el PDF.",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "brand_name": "Acme",
                "brand_context": "Marca de skincare con enfoque en ingredientes limpios.",
                "brand_urls": ["https://acme.com", "https://instagram.com/acme"],
                "brand_goals_type": "Trust & Credibility Acceleration",
                "brand_goals_context": "Incrementar la confianza de compra en Q2.",
                "audience": ["Gen Z", "Millennials"],
                "timeframe": "6 months",
                "profiles_list": ["creator_one", "creator_two"],
                "campaign_type": "all_micro_performance_community_trust",
                "generate_html": True,
                "generate_pdf": False,
            }
        },
    )

    @field_validator("brand_context", "brand_goals_context")
    @classmethod
    def validate_non_empty_context(cls, value: str) -> str:
        if not value:
            raise ValueError("El campo no puede estar vacio.")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_input_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if "brand_urls" not in normalized and "brand_url" in normalized:
            normalized["brand_urls"] = normalized["brand_url"]
        if "audience" not in normalized and "Audience" in normalized:
            normalized["audience"] = normalized["Audience"]
        return normalized

    @field_validator("brand_goals_type")
    @classmethod
    def validate_brand_goals_type(cls, value: str) -> str:
        if value not in BRAND_GOALS_TYPE_OPTIONS:
            raise ValueError(
                "brand_goals_type invalido. Opciones permitidas: "
                + ", ".join(BRAND_GOALS_TYPE_OPTIONS)
            )
        return value

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: list[str]) -> list[str]:
        unique_values: list[str] = []
        seen: set[str] = set()

        for item in value:
            if item not in AUDIENCE_OPTIONS:
                raise ValueError(
                    "Audience invalido. Opciones permitidas: "
                    + ", ".join(AUDIENCE_OPTIONS)
                )
            if item in seen:
                raise ValueError("Audience no debe contener valores duplicados.")
            seen.add(item)
            unique_values.append(item)

        return unique_values

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        if value not in TIMEFRAME_OPTIONS:
            raise ValueError(
                "timeframe invalido. Opciones permitidas: "
                + ", ".join(TIMEFRAME_OPTIONS)
            )
        return value

    @field_validator("profiles_list")
    @classmethod
    def validate_profiles_list(cls, value: list[str]) -> list[str]:
        normalized_profiles: list[str] = []
        seen: set[str] = set()

        for profile in value:
            if not PROFILE_PATTERN.fullmatch(profile):
                raise ValueError(
                    "Cada valor en profiles_list debe cumplir: "
                    "1-30 caracteres, letras, numeros, punto o guion bajo, sin espacios."
                )
            normalized = profile.lower()
            if normalized in seen:
                raise ValueError("profiles_list no debe contener valores duplicados.")
            seen.add(normalized)
            normalized_profiles.append(normalized)

        return normalized_profiles

    @field_validator("campaign_type")
    @classmethod
    def validate_campaign_type(cls, value: str) -> str:
        if value not in CAMPAIGN_TYPE_NAMES:
            raise ValueError(
                "campaign_type invalido. Debe usar los nombres de variable definidos."
            )
        return value

    @model_validator(mode="after")
    def validate_output_flags(self) -> ReputationCampaignStrategyRequest:
        if not self.generate_html and not self.generate_pdf:
            raise ValueError("Debe solicitar al menos un formato (HTML o PDF).")
        return self


class ReputationCampaignStrategyConfirmResponse(BaseModel):
    status: Literal["confirmed"] = "confirmed"
    message: str
    payload: ReputationCampaignStrategyRequest
    template_name: str
    template_path: str
    campaign_type_catalog: list[CampaignTypeCatalogItem] = Field(default_factory=list)
    cost_tier_directory: list[CostTierCatalogItem] = Field(default_factory=list)
    selected_campaign_types: list[CampaignTypeCatalogItem] = Field(default_factory=list)
    influencer_profiles_directory: list[InfluencerProfileDirectoryItem] = Field(
        default_factory=list
    )
    cost_analysis: CostAnalysis = Field(default_factory=CostAnalysis)
    missing_profiles: list[str] = Field(default_factory=list)


class ReputationCreatorStrategyRequest(BaseModel):
    creator_username: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Username del creador.",
    )
    creator_context: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contexto general del creador.",
    )
    creator_urls: list[HttpUrl] = Field(
        default_factory=list,
        max_length=3,
        description="Lista de URLs del creador (max 3).",
    )
    goal_type: str = Field(
        ...,
        description="Goal principal de reputacion para creator strategy.",
    )
    goal_context: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contexto adicional del goal de reputacion.",
    )
    audience: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Audiencias objetivo.",
    )
    timeframe: str = Field(
        ...,
        description="Horizonte temporal de la estrategia.",
    )
    primary_platforms: list[str] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Plataformas principales del creador.",
    )
    reputation_signals: ReputationSignalsInput | None = Field(
        default=None,
        description=(
            "Senales de reputacion con opciones: strengths, weaknesses, "
            "incidents, concerns."
        ),
    )
    collaborators_list: list[str] | None = Field(
        default=None,
        max_length=10,
        description="Lista de colaboradores relevantes (max 10).",
    )
    generate_html: bool = Field(
        default=True,
        description="Indica si debe generarse el HTML.",
    )
    generate_pdf: bool = Field(
        default=False,
        description="Indica si debe generarse el PDF.",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "creator_username": "creator_one",
                "creator_context": "Creador de bienestar y productividad con comunidad activa.",
                "creator_urls": [
                    "https://instagram.com/creator_one",
                    "https://youtube.com/@creator_one",
                ],
                "goal_type": "Community Trust",
                "goal_context": "Fortalecer percepcion de credibilidad en lanzamientos patrocinados.",
                "audience": ["Gen Z", "Millennials"],
                "timeframe": "6 months",
                "primary_platforms": ["Instagram", "YouTube"],
                "reputation_signals": {
                    "strengths": ["transparencia", "consistencia de contenido"],
                    "concerns": ["fatiga por exceso de colaboraciones"],
                },
                "collaborators_list": ["brand_one", "brand_two"],
                "generate_html": True,
                "generate_pdf": False,
            }
        },
    )

    @field_validator("creator_context", "goal_context")
    @classmethod
    def validate_non_empty_creator_context(cls, value: str) -> str:
        if not value:
            raise ValueError("El campo no puede estar vacio.")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_creator_input_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if "creator_urls" not in normalized and "creator_url" in normalized:
            normalized["creator_urls"] = normalized["creator_url"]
        if "audience" not in normalized and "Audience" in normalized:
            normalized["audience"] = normalized["Audience"]
        if "collaborators_list" not in normalized and "collaborators" in normalized:
            normalized["collaborators_list"] = normalized["collaborators"]
        return normalized

    @field_validator("creator_username")
    @classmethod
    def validate_creator_username(cls, value: str) -> str:
        if not PROFILE_PATTERN.fullmatch(value):
            raise ValueError(
                "creator_username debe cumplir: 1-30 caracteres, letras, numeros, "
                "punto o guion bajo, sin espacios."
            )
        return value.lower()

    @field_validator("goal_type")
    @classmethod
    def validate_goal_type(cls, value: str) -> str:
        if value not in CREATOR_GOAL_TYPE_OPTIONS:
            raise ValueError(
                "goal_type invalido. Opciones permitidas: "
                + ", ".join(CREATOR_GOAL_TYPE_OPTIONS)
            )
        return value

    @field_validator("audience")
    @classmethod
    def validate_creator_audience(cls, value: list[str]) -> list[str]:
        unique_values: list[str] = []
        seen: set[str] = set()

        for item in value:
            if item not in AUDIENCE_OPTIONS:
                raise ValueError(
                    "Audience invalido. Opciones permitidas: "
                    + ", ".join(AUDIENCE_OPTIONS)
                )
            if item in seen:
                raise ValueError("Audience no debe contener valores duplicados.")
            seen.add(item)
            unique_values.append(item)

        return unique_values

    @field_validator("timeframe")
    @classmethod
    def validate_creator_timeframe(cls, value: str) -> str:
        if value not in TIMEFRAME_OPTIONS:
            raise ValueError(
                "timeframe invalido. Opciones permitidas: "
                + ", ".join(TIMEFRAME_OPTIONS)
            )
        return value

    @field_validator("primary_platforms")
    @classmethod
    def validate_primary_platforms(cls, value: list[str]) -> list[str]:
        normalized_platforms: list[str] = []
        seen: set[str] = set()

        for platform in value:
            cleaned = platform.strip()
            if not cleaned:
                raise ValueError("primary_platforms no debe contener valores vacios.")
            marker = cleaned.lower()
            if marker in seen:
                raise ValueError(
                    "primary_platforms no debe contener valores duplicados."
                )
            seen.add(marker)
            normalized_platforms.append(cleaned)

        return normalized_platforms

    @field_validator("reputation_signals", mode="before")
    @classmethod
    def validate_reputation_signals(
        cls,
        value: ReputationSignalsInput | dict[str, Any] | None,
    ) -> ReputationSignalsInput | dict[str, Any] | None:
        if value is None:
            return None

        if isinstance(value, ReputationSignalsInput):
            if not value.has_any_value():
                return None
            value = value.model_dump()

        if not isinstance(value, dict):
            raise ValueError("reputation_signals debe ser un objeto o null.")

        allowed_keys = {"strengths", "weaknesses", "incidents", "concerns"}
        unknown_keys = sorted(set(value) - allowed_keys)
        if unknown_keys:
            allowed = ", ".join(sorted(allowed_keys))
            unknown = ", ".join(unknown_keys)
            raise ValueError(
                "reputation_signals solo admite estas llaves: "
                f"{allowed}. Recibido: {unknown}"
            )

        normalized: dict[str, list[str]] = {}
        for key in sorted(allowed_keys):
            raw_items = value.get(key)
            if raw_items is None:
                continue
            if isinstance(raw_items, list):
                cleaned: list[str] = []
                for item in raw_items:
                    if item is None:
                        continue
                    cleaned_item = str(item).strip()
                    if not cleaned_item:
                        continue
                    if len(cleaned_item) > 30:
                        raise ValueError(
                            f"Cada valor en reputation_signals.{key} debe tener maximo 30 caracteres."
                        )
                    cleaned.append(cleaned_item)
            else:
                text = str(raw_items).strip()
                if not text:
                    cleaned = []
                else:
                    if len(text) > 30:
                        raise ValueError(
                            f"Cada valor en reputation_signals.{key} debe tener maximo 30 caracteres."
                        )
                    cleaned = [text]
            if cleaned:
                normalized[key] = cleaned

        return normalized or None

    @field_validator("collaborators_list")
    @classmethod
    def validate_collaborators_list(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None

        normalized_collaborators: list[str] = []
        for collaborator in value:
            cleaned = collaborator.strip()
            if not cleaned:
                raise ValueError("collaborators_list no debe contener valores vacios.")
            normalized_collaborators.append(cleaned)
        return normalized_collaborators or None

    @model_validator(mode="after")
    def validate_creator_output_flags(self) -> ReputationCreatorStrategyRequest:
        if not self.generate_html and not self.generate_pdf:
            raise ValueError("Debe solicitar al menos un formato (HTML o PDF).")
        return self


class ReputationCreatorStrategyConfirmResponse(BaseModel):
    status: Literal["confirmed"] = "confirmed"
    message: str
    payload: ReputationCreatorStrategyRequest
    template_name: str
    template_path: str
    creator_full_name: str | None = None
    creator_biography: str | None = None
    creator_profile_pic_url: str | None = None
    creator_is_verified: bool = False
    creator_follower_count: int = 0
    creator_ai_categories: list[str] = Field(default_factory=list)
    creator_ai_roles: list[str] = Field(default_factory=list)
    current_metrics: dict[str, Any] = Field(default_factory=dict)
    missing_creator: bool = False


class CampaignTypeCatalogResponse(BaseModel):
    items: list[CampaignTypeCatalogItem] = Field(default_factory=list)


def normalize_lookup_usernames(usernames: list[str] | None) -> list[str]:
    if not usernames:
        raise ValueError("usernames cannot be empty")

    normalized_usernames: list[str] = []
    for username in usernames:
        cleaned = username.strip()
        if not cleaned:
            raise ValueError("usernames cannot contain empty values")
        if not PROFILE_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Cada username debe cumplir: "
                "1-30 caracteres, letras, numeros, punto o guion bajo, sin espacios."
            )
        normalized_usernames.append(cleaned.lower())

    return normalized_usernames


def build_campaign_type_catalog() -> list[CampaignTypeCatalogItem]:
    return [
        CampaignTypeCatalogItem(
            name=option.name,
            title=option.title,
            value=option.value,
        )
        for option in CAMPAIGN_TYPE_OPTIONS
    ]


__all__ = [
    "CampaignTypeCatalogItem",
    "CampaignTypeCatalogResponse",
    "CostTierCatalogItem",
    "CostSegmentSummaryItem",
    "CostAnalysisSummary",
    "CostAnalysis",
    "InfluencerMetricsSummary",
    "InfluencerProfileDirectoryItem",
    "ProfileExistenceCollection",
    "ProfileExistenceItem",
    "ReputationSignalsInput",
    "ReputationCampaignStrategyRequest",
    "ReputationCampaignStrategyConfirmResponse",
    "ReputationCreatorStrategyRequest",
    "ReputationCreatorStrategyConfirmResponse",
    "build_campaign_type_catalog",
]
