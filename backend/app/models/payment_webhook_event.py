"""
NEXORA — Payment Webhook Event Model

Tracks incoming webhooks from Razorpay to ensure idempotency.
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utcnow


class PaymentWebhookEvent(Base):
    """
    Stores webhook events received from Razorpay.
    Used for deduplication and audit trailing.
    """
    __tablename__ = "payment_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # Razorpay event ID (X-Razorpay-Event-Id header or payload id)
    event_id: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
    )

    # Status of processing the event
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="RECEIVED",
        server_default=sa.text("'RECEIVED'"),
    )

    payload_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_payment_webhook_events_event_id", "event_id"),
        sa.Index("idx_payment_webhook_events_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<PaymentWebhookEvent id={self.id} event_id={self.event_id!r} status={self.status!r}>"
