"""
Mod Schema Router for PostgreSQL Multi-Tenancy

Implements schema-per-Mod isolation using PostgreSQL search_path.
This provides true FK constraints across tables within the same schema while isolating data per Mod.

Usage in engine setup:
    - On connect: SET search_path TO xcagi_mod_{normalized_mod_id},public
    - All queries in that connection see only the Mod's schema
    - Row Level Security (RLS) can be added for extra protection

This fulfills the postgres-foundation todo and solves cross-database FK and concurrency issues.
"""

import logging

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.sqlite_mod_paths import mod_suffix_token
from app.request_active_mod_ctx import get_request_active_mod_id

logger = logging.getLogger(__name__)


def normalize_schema_name(mod_id: str) -> str:
    """Convert Mod ID to valid PostgreSQL schema name (lowercase, alphanumeric + underscore)."""
    if not mod_id:
        return "public"
    suffix = mod_suffix_token(mod_id)
    return f"xcagi_mod_{suffix}" if suffix else "public"


def set_search_path(dbapi_connection, connection_record):
    """Event listener to set search_path based on active Mod for PostgreSQL connections."""
    active_mod_id = get_request_active_mod_id()
    if not active_mod_id:
        return

    schema_name = normalize_schema_name(active_mod_id)

    try:
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_name}, public")
        cursor.close()
        logger.debug(f"Set search_path to {schema_name} for Mod {active_mod_id}")
    except Exception as e:
        logger.warning(f"Failed to set search_path for Mod {active_mod_id}: {e}")


def setup_mod_schema_routing(engine: Engine) -> None:
    """Register event listeners for Mod-aware schema routing on PostgreSQL engines."""
    # Only for PostgreSQL
    if engine.dialect.name == "postgresql":
        event.listen(engine, "connect", set_search_path)
        logger.info("Mod schema routing (search_path) enabled for PostgreSQL engine")
    else:
        logger.debug("Mod schema routing skipped (not PostgreSQL)")


def ensure_mod_schema(db: Session, mod_id: str) -> bool:
    """Ensure the schema for a Mod exists (idempotent)."""
    if not mod_id:
        return True

    schema_name = normalize_schema_name(mod_id)
    try:
        db.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        db.commit()
        logger.info(f"Ensured schema {schema_name} for Mod {mod_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create schema {schema_name}: {e}")
        db.rollback()
        return False


def get_current_schema(db: Session) -> str:
    """Get the current search_path schema (for debugging)."""
    try:
        result = db.execute("SHOW search_path").scalar()
        return str(result)
    except Exception:
        return "unknown"


# Register globally if imported
def init_mod_schema_routing():
    """Call this during app startup to enable Mod schema routing."""
    from app.db import engine

    if hasattr(engine, "sync_engine") and engine.sync_engine is not None:  # Some engines wrap
        setup_mod_schema_routing(engine.sync_engine)
    elif hasattr(engine, "engine"):
        setup_mod_schema_routing(engine.engine)
    else:
        # The proxy engine
        try:
            setup_mod_schema_routing(engine)
        except Exception as e:
            logger.warning(f"Could not setup schema routing on engine proxy: {e}")
