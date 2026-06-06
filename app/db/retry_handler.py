"""
SQLite Database Retry Handler

Provides retry logic for SQLite database operations to handle "database is locked" errors
that occur under concurrent write scenarios.
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default retry configuration
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 0.5  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier


def is_database_locked_error(error: Exception) -> bool:
    """
    Check if an exception is a database locked error.

    Args:
        error: The exception to check

    Returns:
        True if the error indicates a database lock issue
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    locked_indicators = [
        "database is locked",
        "database locked",
        "sqlite3.operationalerror",
        "operationalerror",
        "locked",
    ]

    return any(indicator in error_str for indicator in locked_indicators) or any(
        indicator in error_type for indicator in locked_indicators
    )


def with_sqlite_retry(
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    on_retry: Callable[[Exception, int], None] | None = None,
    reraise_original: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for SQLite database operations with automatic retry on lock errors.

    This addresses the SQLite concurrency issue where concurrent writes cause
    "database is locked" errors. The retry logic uses exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        backoff: Exponential backoff multiplier (default: 2.0)
        on_retry: Optional callback function called on each retry with (error, attempt_number)
        reraise_original: If True, re-raise the original error instead of wrapping it

    Returns:
        Decorated function with retry logic

    Usage:
        @with_sqlite_retry(max_attempts=3, base_delay=0.5)
        def create_shipment_record(db, data):
            # This will retry up to 3 times if database is locked
            record = ShipmentRecord(**data)
            db.add(record)
            db.commit()
            return record

        @with_sqlite_retry()
        def bulk_import_products(products_data):
            for data in products_data:
                create_product(data)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            delay = base_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if this is a retryable database lock error
                    if not is_database_locked_error(e):
                        # Not a lock error, re-raise immediately
                        raise

                    # Database locked - retry with backoff
                    if attempt < max_attempts:
                        logger.warning(
                            "Database locked in %s (attempt %d/%d): %s. " "Retrying in %.2fs...",
                            func.__name__,
                            attempt,
                            max_attempts,
                            e,
                            delay,
                        )

                        if on_retry:
                            try:
                                on_retry(e, attempt)
                            except Exception:
                                pass  # Ignore callback errors

                        time.sleep(delay)
                        delay *= backoff
                    else:
                        # Final attempt failed
                        logger.error(
                            "Database locked in %s after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )

                        if reraise_original:
                            raise

                        # Wrap the error with context
                        raise RuntimeError(
                            f"Database is locked after {max_attempts} retry attempts. "
                            f"Original error: {e}"
                        ) from e

            # Should not reach here, but just in case
            if last_exception:
                if reraise_original:
                    raise last_exception
                raise RuntimeError("Unexpected retry loop exit") from last_exception

            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def execute_with_retry(
    operation: Callable[..., T],
    *args: Any,
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    **kwargs: Any,
) -> T:
    """
    Execute a database operation with retry logic.

    This is the non-decorator version for dynamic retry logic.

    Args:
        operation: The function to execute
        *args: Positional arguments for the operation
        max_attempts: Maximum retry attempts
        base_delay: Initial retry delay
        backoff: Exponential backoff multiplier
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation

    Raises:
        RuntimeError: If all retry attempts fail

    Usage:
        result = execute_with_retry(
            db_session.commit,
            max_attempts=3,
            base_delay=0.5
        )
    """
    last_exception: Exception | None = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if not is_database_locked_error(e):
                raise

            if attempt < max_attempts:
                logger.warning(
                    "Database locked (attempt %d/%d): %s. Retrying in %.2fs...",
                    attempt,
                    max_attempts,
                    e,
                    delay,
                )
                time.sleep(delay)
                delay *= backoff
            else:
                logger.error("Database locked after %d attempts: %s", max_attempts, e)
                raise RuntimeError(
                    f"Database is locked after {max_attempts} retry attempts: {e}"
                ) from e

    raise RuntimeError("Unexpected retry loop exit")


# Session commit wrapper with retry


def safe_commit(session, max_attempts: int = DEFAULT_RETRY_ATTEMPTS) -> None:
    """
    Commit a SQLAlchemy session with automatic retry on database lock.

    Args:
        session: SQLAlchemy session to commit
        max_attempts: Maximum retry attempts

    Raises:
        RuntimeError: If commit fails after all retries
    """
    execute_with_retry(
        session.commit,
        max_attempts=max_attempts,
        base_delay=DEFAULT_RETRY_DELAY,
        backoff=DEFAULT_RETRY_BACKOFF,
    )
