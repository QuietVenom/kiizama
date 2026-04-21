"""add scheduled cancellation fields to billing subscriptions

Revision ID: 20260417_0001
Revises: 20260412_0001
Create Date: 2026-04-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260417_0001"
down_revision = "20260412_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "billing_subscription",
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        schema="private",
    )
    op.add_column(
        "billing_subscription",
        sa.Column("cancellation_reason", sa.String(length=64), nullable=True),
        schema="private",
    )

    op.execute(
        """
        WITH latest_events AS (
            SELECT DISTINCT ON (event.stripe_subscription_id)
                event.stripe_subscription_id,
                CASE
                    WHEN event.payload_json->'data'->'object'->>'cancel_at' ~ '^[0-9]+$'
                    THEN to_timestamp(
                        (event.payload_json->'data'->'object'->>'cancel_at')::bigint
                    )
                    ELSE NULL
                END AS cancel_at,
                NULLIF(
                    event.payload_json->'data'->'object'->'cancellation_details'->>'reason',
                    ''
                ) AS cancellation_reason
            FROM private.billing_webhook_event AS event
            WHERE event.processing_status = 'processed'
              AND event.stripe_subscription_id IS NOT NULL
              AND event.event_type LIKE 'customer.subscription.%'
            ORDER BY
                event.stripe_subscription_id,
                CASE
                    WHEN event.payload_json->>'created' ~ '^[0-9]+$'
                    THEN (event.payload_json->>'created')::bigint
                    ELSE NULL
                END DESC NULLS LAST,
                event.created_at DESC
        )
        UPDATE private.billing_subscription AS subscription
        SET
            cancel_at = latest_events.cancel_at,
            cancellation_reason = latest_events.cancellation_reason
        FROM latest_events
        WHERE subscription.stripe_subscription_id = latest_events.stripe_subscription_id
        """
    )


def downgrade() -> None:
    op.drop_column("billing_subscription", "cancellation_reason", schema="private")
    op.drop_column("billing_subscription", "cancel_at", schema="private")
