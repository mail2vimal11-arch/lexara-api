"""Database session management."""

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# Base for ORM models
Base = declarative_base()


def reconcile_schema(bind=None):
    """Add mapped columns that are missing from existing live tables.

    create_all() creates missing tables but never alters existing ones, and
    the repo carries no Alembic migrations — so every column added to a model
    after a table's first deploy silently never reaches production. That
    drift made INSERTs into `users` 500 in prod while the full test suite
    (fresh schema) stayed green.

    Strictly additive and idempotent: columns are added nullable (no table
    rewrite, no lock pain), then backfilled once when the model declares a
    scalar default. Never drops, renames, or retypes anything.
    """
    bind = bind or engine
    inspector = inspect(bind)
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue  # create_all handles brand-new tables
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                col_type = col.type.compile(bind.dialect)
                conn.execute(text(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'
                ))
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    conn.execute(
                        text(f'UPDATE "{table.name}" SET "{col.name}" = :v '
                             f'WHERE "{col.name}" IS NULL'),
                        {"v": col.default.arg},
                    )
                logger.warning("schema reconcile: added column %s.%s (%s)",
                               table.name, col.name, col_type)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    try:
        reconcile_schema()
    except Exception:
        # A failed repair must not stop boot — the app worked (partially)
        # without it. Loudly logged so the operator sees it.
        logger.exception("schema reconciliation failed — live schema may "
                         "still be missing model columns")


def get_db():
    """Get database session (dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
