import uuid
from datetime import UTC, datetime
from typing import Any, Literal, cast

from kiizama_scrape_core.ig_scraper.sqlmodels import (
    PRIVATE_SCHEMA,
    IgCredential,
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
    IgScrapeJob,
)
from pydantic import EmailStr
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import generate_uuid7
from app.core.password_policy import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    NewPasswordStr,
)
from app.features.billing.models import (
    BillingCustomerSyncTask,
    BillingSubscription,
    BillingWebhookEvent,
    LuBillingFeature,
    SubscriptionPlan,
    SubscriptionPlanFeatureLimit,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserAccessOverride,
    UserBillingAccount,
)
from app.features.billing.schemas import (
    AccessProfile,
    BillingCustomerSyncStatus,
    BillingCustomerSyncType,
    ManagedAccessSource,
    PlanStatus,
)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: NewPasswordStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


LegalDocumentType = Literal["privacy_notice", "terms_conditions"]
LegalAcceptanceSource = Literal["public_signup"]


class LegalAcceptances(SQLModel):
    privacy_notice: Literal[True]
    terms_conditions: Literal[True]


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: NewPasswordStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    full_name: str | None = Field(default=None, max_length=255)
    legal_acceptances: LegalAcceptances


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: NewPasswordStr | None = Field(
        default=None,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: NewPasswordStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


# Database model, database table inferred from class name
class User(UserBase, table=True):
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    hashed_password: str


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class AdminUserCreate(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: NewPasswordStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    access_profile: AccessProfile = "standard"


class AdminUserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: NewPasswordStr | None = Field(
        default=None,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    access_profile: AccessProfile | None = None


class AdminUserPublic(UserPublic):
    access_profile: AccessProfile = "standard"
    managed_access_source: ManagedAccessSource | None = None
    billing_eligible: bool = True
    plan_status: PlanStatus = "none"


class AdminUsersPublic(SQLModel):
    data: list[AdminUserPublic]
    count: int


class UserLegalAcceptance(SQLModel, table=True):
    __tablename__ = cast(Any, "user_legal_acceptance")
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_private_user_legal_acceptance_user_document_version",
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    document_type: str = Field(max_length=64)
    document_version: str = Field(max_length=32)
    accepted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    source: str = Field(max_length=32)


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None
    principal_type: Literal["user", "admin"] | None = None
    role: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: NewPasswordStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


class LuAdminRole(SQLModel, table=True):
    __tablename__ = cast(Any, "lu_admin_role")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: int = Field(primary_key=True)
    code: str = Field(unique=True, index=True, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class UserAdminBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True


class UserAdmin(UserAdminBase, table=True):
    __tablename__ = cast(Any, "user_admin")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    hashed_password: str
    role_id: int = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.lu_admin_role.id", nullable=False
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )


class UserAdminPublic(SQLModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool


class FeatureFlagBase(SQLModel):
    key: str = Field(unique=True, index=True, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_enabled: bool = False
    is_public: bool = False


class FeatureFlagCreate(SQLModel):
    key: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_enabled: bool = False
    is_public: bool = False


class FeatureFlagUpdate(SQLModel):
    description: str | None = Field(default=None, max_length=500)
    is_enabled: bool | None = None
    is_public: bool | None = None


class FeatureFlag(FeatureFlagBase, table=True):
    __tablename__ = cast(Any, "feature_flag")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )


class FeatureFlagPublic(SQLModel):
    key: str
    description: str | None = None
    is_enabled: bool
    is_public: bool


class FeatureFlagsPublic(SQLModel):
    data: list[FeatureFlagPublic]
    count: int


class FeatureFlagAudit(SQLModel, table=True):
    __tablename__ = cast(Any, "feature_flag_audit")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    feature_flag_id: uuid.UUID | None = None
    feature_flag_key: str = Field(index=True, max_length=100)
    action: str = Field(max_length=32)
    old_is_enabled: bool | None = None
    new_is_enabled: bool | None = None
    old_is_public: bool | None = None
    new_is_public: bool | None = None
    changed_by_user_id: uuid.UUID | None = None
    changed_by_admin_id: uuid.UUID | None = None
    changed_by_email: str | None = Field(default=None, max_length=255)
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )


class FeatureFlagAuditPublic(SQLModel):
    id: uuid.UUID
    feature_flag_key: str
    action: str
    old_is_enabled: bool | None = None
    new_is_enabled: bool | None = None
    old_is_public: bool | None = None
    new_is_public: bool | None = None
    changed_by_email: str | None = None
    changed_at: datetime


class FeatureFlagAuditsPublic(SQLModel):
    data: list[FeatureFlagAuditPublic]
    count: int


class LegalDocumentPublic(SQLModel):
    type: LegalDocumentType
    title: str
    url: str
    version: str
    required: bool = True


class PublicLegalDocuments(SQLModel):
    simplified_notice: str
    documents: list[LegalDocumentPublic]


WaitingListInterest = Literal[
    "public_relations",
    "marketing",
    "creator",
    "creator_talent_management",
    "publicity",
    "other",
]


class WaitingListCreate(SQLModel):
    email: EmailStr = Field(max_length=255)
    interest: WaitingListInterest


class WaitingList(SQLModel, table=True):
    __tablename__ = cast(Any, "waiting_list")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    interest: str = Field(max_length=64)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )


__all__ = [
    "AccessProfile",
    "BillingCustomerSyncStatus",
    "BillingCustomerSyncTask",
    "BillingCustomerSyncType",
    "AdminUserCreate",
    "AdminUserPublic",
    "AdminUsersPublic",
    "AdminUserUpdate",
    "PRIVATE_SCHEMA",
    "BillingSubscription",
    "BillingWebhookEvent",
    "FeatureFlag",
    "FeatureFlagAudit",
    "FeatureFlagAuditPublic",
    "FeatureFlagAuditsPublic",
    "FeatureFlagBase",
    "FeatureFlagCreate",
    "FeatureFlagPublic",
    "FeatureFlagsPublic",
    "FeatureFlagUpdate",
    "IgCredential",
    "IgMetrics",
    "IgPostsDocument",
    "IgProfile",
    "IgProfileSnapshot",
    "IgReelsDocument",
    "IgScrapeJob",
    "LegalAcceptances",
    "LegalAcceptanceSource",
    "LegalDocumentPublic",
    "LegalDocumentType",
    "LuBillingFeature",
    "LuAdminRole",
    "Message",
    "NewPassword",
    "PlanStatus",
    "PublicLegalDocuments",
    "SubscriptionPlan",
    "SubscriptionPlanFeatureLimit",
    "Token",
    "TokenPayload",
    "UpdatePassword",
    "UsageCycle",
    "UsageCycleFeature",
    "UsageEvent",
    "UsageReservation",
    "User",
    "UserAccessOverride",
    "UserAdmin",
    "UserAdminBase",
    "UserAdminPublic",
    "UserBase",
    "UserBillingAccount",
    "UserCreate",
    "UserLegalAcceptance",
    "UserPublic",
    "UserRegister",
    "UsersPublic",
    "UserUpdate",
    "UserUpdateMe",
    "WaitingList",
    "WaitingListCreate",
    "WaitingListInterest",
]
