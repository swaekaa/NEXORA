"""
NEXORA Backend — SQLAlchemy Declarative Base

All ORM models must inherit from `Base`.

IMPORTANT monetary field rules (enforced in every model):
    - Use:  sa.Numeric(precision=18, scale=2, asdecimal=True)
    - NOT:  sa.Float or sa.Double
    - In Python: always use Decimal, never float

Convention helpers:
    - All primary keys: UUID (server-side gen_random_uuid())
    - All timestamps: TIMESTAMPTZ (UTC)
    - Every table has: created_at, updated_at
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all NEXORA ORM models."""

    # ── Shared column helpers ────────────────────────────────────────────────

    # Subclasses can use these as Mapped annotations:
    #   id: Mapped[uuid.UUID] = mapped_column(
    #       sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    #   )
    pass


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


# ── Reusable column factories ──────────────────────────────────────────────────

def uuid_pk() -> sa.Column:  # type: ignore[type-arg]
    """Primary key column: UUID generated server-side."""
    return mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def timestamp_col(*, nullable: bool = False, server_default: bool = False) -> sa.Column:  # type: ignore[type-arg]
    """TIMESTAMPTZ column, timezone-aware."""
    kwargs: dict = {"nullable": nullable}
    if server_default:
        kwargs["server_default"] = sa.func.now()
    return mapped_column(sa.TIMESTAMP(timezone=True), **kwargs)


def money_col(*, nullable: bool = False) -> sa.Column:  # type: ignore[type-arg]
    """NUMERIC(18, 2) column for monetary values. asdecimal=True returns Decimal objects."""
    return mapped_column(sa.Numeric(precision=18, scale=2, asdecimal=True), nullable=nullable)
