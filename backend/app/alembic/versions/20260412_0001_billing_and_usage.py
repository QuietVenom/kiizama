"""add billing, usage, and access override tables

Revision ID: 20260412_0001
Revises: 20260411_0001
Create Date: 2026-04-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260412_0001"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lu_billing_feature",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("code"),
        schema="private",
    )
    op.create_index(
        "ix_private_lu_billing_feature_code",
        "lu_billing_feature",
        ["code"],
        unique=True,
        schema="private",
    )

    op.create_table(
        "subscription_plan",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("billing_source", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("code"),
        schema="private",
    )
    op.create_index(
        "ix_private_subscription_plan_code",
        "subscription_plan",
        ["code"],
        unique=True,
        schema="private",
    )

    op.create_table(
        "subscription_plan_feature_limit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("monthly_limit", sa.Integer(), nullable=False),
        sa.Column("is_unlimited", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["private.subscription_plan.id"]),
        sa.ForeignKeyConstraint(["feature_id"], ["private.lu_billing_feature.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "feature_id",
            name="uq_private_subscription_plan_feature_limit_plan_feature",
        ),
        schema="private",
    )
    op.create_index(
        "ix_private_subscription_plan_feature_limit_plan_id",
        "subscription_plan_feature_limit",
        ["plan_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_subscription_plan_feature_limit_feature_id",
        "subscription_plan_feature_limit",
        ["feature_id"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "user_billing_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("has_used_trial", sa.Boolean(), nullable=False),
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("stripe_customer_id"),
        schema="private",
    )
    op.create_index(
        "ix_private_user_billing_account_user_id",
        "user_billing_account",
        ["user_id"],
        unique=True,
        schema="private",
    )
    op.create_index(
        "ix_private_user_billing_account_stripe_customer_id",
        "user_billing_account",
        ["stripe_customer_id"],
        unique=True,
        schema="private",
    )

    op.create_table(
        "billing_subscription",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("collection_method", sa.String(length=64), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("latest_invoice_status", sa.String(length=64), nullable=True),
        sa.Column("access_revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_revoked_reason", sa.String(length=128), nullable=True),
        sa.Column("last_stripe_event_created", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
        schema="private",
    )
    op.create_index(
        "ix_private_billing_subscription_user_id",
        "billing_subscription",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_subscription_stripe_subscription_id",
        "billing_subscription",
        ["stripe_subscription_id"],
        unique=True,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_subscription_stripe_customer_id",
        "billing_subscription",
        ["stripe_customer_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_subscription_status",
        "billing_subscription",
        ["status"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "billing_webhook_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_error", sa.String(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id"),
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_stripe_event_id",
        "billing_webhook_event",
        ["stripe_event_id"],
        unique=True,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_event_type",
        "billing_webhook_event",
        ["event_type"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_stripe_customer_id",
        "billing_webhook_event",
        ["stripe_customer_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_stripe_subscription_id",
        "billing_webhook_event",
        ["stripe_subscription_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_stripe_invoice_id",
        "billing_webhook_event",
        ["stripe_invoice_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_webhook_event_processing_status",
        "billing_webhook_event",
        ["processing_status"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "user_access_override",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("is_unlimited", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["private.user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="private",
    )
    op.create_index(
        "ix_private_user_access_override_user_id",
        "user_access_override",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_user_access_override_code",
        "user_access_override",
        ["code"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "billing_notice",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notice_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notice_key", sa.String(length=255), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notice_key", name="uq_private_billing_notice_notice_key"),
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_user_id",
        "billing_notice",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_notice_type",
        "billing_notice",
        ["notice_type"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_status",
        "billing_notice",
        ["status"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_notice_key",
        "billing_notice",
        ["notice_key"],
        unique=True,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_stripe_event_id",
        "billing_notice",
        ["stripe_event_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_stripe_subscription_id",
        "billing_notice",
        ["stripe_subscription_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_notice_stripe_invoice_id",
        "billing_notice",
        ["stripe_invoice_id"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "usage_cycle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            "period_start",
            "period_end",
            name="uq_private_usage_cycle_subscription_period",
        ),
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_user_id",
        "usage_cycle",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_source_id",
        "usage_cycle",
        ["source_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_plan_code",
        "usage_cycle",
        ["plan_code"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_status",
        "usage_cycle",
        ["status"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "usage_cycle_feature",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usage_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("limit_count", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("reserved_count", sa.Integer(), nullable=False),
        sa.Column("is_unlimited", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usage_cycle_id"], ["private.usage_cycle.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "usage_cycle_id",
            "feature_code",
            name="uq_private_usage_cycle_feature_cycle_feature",
        ),
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_feature_usage_cycle_id",
        "usage_cycle_feature",
        ["usage_cycle_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_cycle_feature_feature_code",
        "usage_cycle_feature",
        ["feature_code"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "usage_reservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("usage_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("endpoint_key", sa.String(length=128), nullable=False),
        sa.Column("reserved_count", sa.Integer(), nullable=False),
        sa.Column("consumed_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usage_cycle_id"], ["private.usage_cycle.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key"),
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_request_key",
        "usage_reservation",
        ["request_key"],
        unique=True,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_user_id",
        "usage_reservation",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_usage_cycle_id",
        "usage_reservation",
        ["usage_cycle_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_feature_code",
        "usage_reservation",
        ["feature_code"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_status",
        "usage_reservation",
        ["status"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_reservation_job_id",
        "usage_reservation",
        ["job_id"],
        unique=False,
        schema="private",
    )

    op.create_table(
        "usage_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("usage_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("endpoint_key", sa.String(length=128), nullable=False),
        sa.Column("request_key", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("quantity_requested", sa.Integer(), nullable=False),
        sa.Column("quantity_consumed", sa.Integer(), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usage_cycle_id"], ["private.usage_cycle.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_user_id",
        "usage_event",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_usage_cycle_id",
        "usage_event",
        ["usage_cycle_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_feature_code",
        "usage_event",
        ["feature_code"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_request_key",
        "usage_event",
        ["request_key"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_job_id",
        "usage_event",
        ["job_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_usage_event_result_status",
        "usage_event",
        ["result_status"],
        unique=False,
        schema="private",
    )


def downgrade() -> None:
    op.drop_index("ix_private_usage_event_result_status", table_name="usage_event", schema="private")
    op.drop_index("ix_private_usage_event_job_id", table_name="usage_event", schema="private")
    op.drop_index("ix_private_usage_event_request_key", table_name="usage_event", schema="private")
    op.drop_index("ix_private_usage_event_feature_code", table_name="usage_event", schema="private")
    op.drop_index("ix_private_usage_event_usage_cycle_id", table_name="usage_event", schema="private")
    op.drop_index("ix_private_usage_event_user_id", table_name="usage_event", schema="private")
    op.drop_table("usage_event", schema="private")

    op.drop_index("ix_private_usage_reservation_job_id", table_name="usage_reservation", schema="private")
    op.drop_index("ix_private_usage_reservation_status", table_name="usage_reservation", schema="private")
    op.drop_index("ix_private_usage_reservation_feature_code", table_name="usage_reservation", schema="private")
    op.drop_index("ix_private_usage_reservation_usage_cycle_id", table_name="usage_reservation", schema="private")
    op.drop_index("ix_private_usage_reservation_user_id", table_name="usage_reservation", schema="private")
    op.drop_index("ix_private_usage_reservation_request_key", table_name="usage_reservation", schema="private")
    op.drop_table("usage_reservation", schema="private")

    op.drop_index("ix_private_usage_cycle_feature_feature_code", table_name="usage_cycle_feature", schema="private")
    op.drop_index("ix_private_usage_cycle_feature_usage_cycle_id", table_name="usage_cycle_feature", schema="private")
    op.drop_table("usage_cycle_feature", schema="private")

    op.drop_index("ix_private_usage_cycle_status", table_name="usage_cycle", schema="private")
    op.drop_index("ix_private_usage_cycle_plan_code", table_name="usage_cycle", schema="private")
    op.drop_index("ix_private_usage_cycle_source_id", table_name="usage_cycle", schema="private")
    op.drop_index("ix_private_usage_cycle_user_id", table_name="usage_cycle", schema="private")
    op.drop_table("usage_cycle", schema="private")

    op.drop_index("ix_private_billing_notice_stripe_invoice_id", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_stripe_subscription_id", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_stripe_event_id", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_notice_key", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_status", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_notice_type", table_name="billing_notice", schema="private")
    op.drop_index("ix_private_billing_notice_user_id", table_name="billing_notice", schema="private")
    op.drop_table("billing_notice", schema="private")

    op.drop_index("ix_private_user_access_override_code", table_name="user_access_override", schema="private")
    op.drop_index("ix_private_user_access_override_user_id", table_name="user_access_override", schema="private")
    op.drop_table("user_access_override", schema="private")

    op.drop_index("ix_private_billing_webhook_event_processing_status", table_name="billing_webhook_event", schema="private")
    op.drop_index("ix_private_billing_webhook_event_stripe_invoice_id", table_name="billing_webhook_event", schema="private")
    op.drop_index("ix_private_billing_webhook_event_stripe_subscription_id", table_name="billing_webhook_event", schema="private")
    op.drop_index("ix_private_billing_webhook_event_stripe_customer_id", table_name="billing_webhook_event", schema="private")
    op.drop_index("ix_private_billing_webhook_event_event_type", table_name="billing_webhook_event", schema="private")
    op.drop_index("ix_private_billing_webhook_event_stripe_event_id", table_name="billing_webhook_event", schema="private")
    op.drop_table("billing_webhook_event", schema="private")

    op.drop_index("ix_private_billing_subscription_status", table_name="billing_subscription", schema="private")
    op.drop_index("ix_private_billing_subscription_stripe_customer_id", table_name="billing_subscription", schema="private")
    op.drop_index("ix_private_billing_subscription_stripe_subscription_id", table_name="billing_subscription", schema="private")
    op.drop_index("ix_private_billing_subscription_user_id", table_name="billing_subscription", schema="private")
    op.drop_table("billing_subscription", schema="private")

    op.drop_index("ix_private_user_billing_account_stripe_customer_id", table_name="user_billing_account", schema="private")
    op.drop_index("ix_private_user_billing_account_user_id", table_name="user_billing_account", schema="private")
    op.drop_table("user_billing_account", schema="private")

    op.drop_index("ix_private_subscription_plan_feature_limit_feature_id", table_name="subscription_plan_feature_limit", schema="private")
    op.drop_index("ix_private_subscription_plan_feature_limit_plan_id", table_name="subscription_plan_feature_limit", schema="private")
    op.drop_table("subscription_plan_feature_limit", schema="private")

    op.drop_index("ix_private_subscription_plan_code", table_name="subscription_plan", schema="private")
    op.drop_table("subscription_plan", schema="private")

    op.drop_index("ix_private_lu_billing_feature_code", table_name="lu_billing_feature", schema="private")
    op.drop_table("lu_billing_feature", schema="private")
