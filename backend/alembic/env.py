"""
Alembic Migration Environment

This env.py:
  - Reads the database URL from app.config.settings (not from alembic.ini)
  - Supports both offline (--sql) and online (live DB) migration modes
  - Imports the SQLAlchemy Base so autogenerate can detect model changes

To create a new migration:
    alembic revision --autogenerate -m "short description"

To apply migrations:
    alembic upgrade head

To rollback one step:
    alembic downgrade -1
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Load Alembic logging config ───────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import Base and all models so autogenerate sees them ─────────────────────
# As models are added in later phases, import them here so Alembic detects changes.
from app.database.base import Base  # noqa: E402

# Future phase models — uncomment as each phase implements models:
# from app.models.merchant import Merchant        # Phase 2
# from app.models.buyer import Buyer              # Phase 2
# from app.models.product import Product          # Phase 2
# from app.models.negotiation import Negotiation  # Phase 2
# from app.models.agreement import Agreement      # Phase 2
# from app.models.payment import Payment          # Phase 2
# from app.models.audit import AuditEvent         # Phase 2
# from app.models.approval import ApprovalRequest # Phase 2
# from app.models.webhook_event import WebhookEvent # Phase 2

target_metadata = Base.metadata

# ── Inject DATABASE_URL from settings ─────────────────────────────────────────
from app.config import settings  # noqa: E402

# Convert asyncpg DSN to sync psycopg2 DSN for Alembic's offline mode
# (Alembic's offline mode runs synchronously; online mode uses asyncio)
_sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2", 1)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ── Offline mode ──────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — emit SQL to stdout without a DB connection.
    Useful for review and production deployment scripts.
    """
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Detect column type changes, not just add/drop
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async database connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
