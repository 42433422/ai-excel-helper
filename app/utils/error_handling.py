"""
Structured Error Handling Utilities

Provides specific exception types and decorators for proper error handling,
replacing broad `except Exception:` patterns throughout the codebase.
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


# Specific Exception Types for Structured Error Handling


class WorkflowError(Exception):
    """Base class for workflow-related errors."""

    pass


class ServiceUnavailableError(WorkflowError):
    """Raised when a required service is unavailable."""

    pass


class DataValidationError(WorkflowError):
    """Raised when data validation fails."""

    pass


class ModAccessDeniedError(WorkflowError):
    """Raised when Mod access is denied."""

    pass


class DatabaseLockError(WorkflowError):
    """Raised when database is locked (SQLite concurrency issue)."""

    pass


class ForeignKeyViolationError(WorkflowError):
    """Raised when a foreign key constraint is violated."""

    pass


# Retry Configuration for Database Operations

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 0.5  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier


def with_error_handling(
    fallback: Callable | None = None,
    log_level: str = "error",
    reraise: tuple[type[Exception], ...] = (),
    error_code_prefix: str = "",
) -> Callable:
    """
    Decorator for structured error handling.

    Replaces broad `except Exception:` with specific error handling and logging.

    Args:
        fallback: Optional fallback function to call on error
        log_level: Logging level ("debug", "info", "warning", "error")
        reraise: Tuple of exception types to re-raise without handling
        error_code_prefix: Prefix for error codes in return values

    Usage:
        @with_error_handling(log_level="warning", reraise=(KeyboardInterrupt, SystemExit))
        def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except reraise:
                raise
            except ImportError as e:
                # Service unavailable due to missing dependency
                log_func = getattr(logger, log_level)
                log_func("Service unavailable [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": f"Service unavailable: {e}",
                    "error_code": f"{error_code_prefix}service_unavailable",
                }
            except (ValueError, TypeError) as e:
                # Data validation error
                log_func = getattr(logger, log_level if log_level != "error" else "warning")
                log_func("Validation error [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": f"Validation error: {e}",
                    "error_code": f"{error_code_prefix}validation_error",
                }
            except DatabaseLockError as e:
                # Database concurrency issue
                logger.error("Database locked [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": "Database is busy, please retry",
                    "error_code": f"{error_code_prefix}database_busy",
                }
            except ForeignKeyViolationError as e:
                # Foreign key constraint violation
                logger.error("Foreign key violation [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": f"Data integrity error: {e}",
                    "error_code": f"{error_code_prefix}fk_violation",
                }
            except ModAccessDeniedError as e:
                # Mod access control error
                logger.warning("Mod access denied [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": f"Access denied: {e}",
                    "error_code": f"{error_code_prefix}access_denied",
                }
            except WorkflowError as e:
                # Generic workflow error
                log_func = getattr(logger, log_level)
                log_func("Workflow error [%s]: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": str(e),
                    "error_code": f"{error_code_prefix}workflow_error",
                }
            except Exception as e:
                # Unexpected error - this is the last resort
                logger.exception("Unexpected error in %s: %s", func.__name__, e)
                if fallback:
                    return fallback(*args, **kwargs)
                return {
                    "success": False,
                    "message": f"Unexpected error: {type(e).__name__}",
                    "error_code": f"{error_code_prefix}unexpected_error",
                }

        return wrapper

    return decorator


def with_sqlite_retry(
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    retryable_errors: tuple[type[Exception], ...] = (),
) -> Callable:
    """
    Decorator for SQLite database operations with retry logic.

    Handles "database is locked" errors by retrying with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        backoff: Exponential backoff multiplier
        retryable_errors: Additional exception types to retry

    Usage:
        @with_sqlite_retry(max_attempts=3, base_delay=0.5)
        def my_database_operation():
            ...
    """
    default_retryable = (DatabaseLockError,)
    all_retryable = default_retryable + retryable_errors

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            delay = base_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except all_retryable as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            "Database operation failed (attempt %d/%d): %s. Retrying in %.2fs...",
                            attempt,
                            max_attempts,
                            e,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            "Database operation failed after %d attempts: %s", max_attempts, e
                        )
                        raise DatabaseLockError(
                            f"Database locked after {max_attempts} attempts: {e}"
                        ) from e
                except Exception:
                    # Non-retryable error
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def is_database_locked_error(error: Exception) -> bool:
    """
    Check if an exception is a database locked error.

    Handles various forms of SQLite database locked errors.
    """
    error_str = str(error).lower()
    locked_indicators = [
        "database is locked",
        "sqlite3.operationalerror",
        "operationalerror",
        "locked",
    ]
    return any(indicator in error_str for indicator in locked_indicators)


def handle_database_error(
    error: Exception, operation: str = "database operation"
) -> dict[str, Any]:
    """
    Handle database errors and return structured error response.

    Args:
        error: The exception that occurred
        operation: Description of the operation being performed

    Returns:
        Structured error dictionary
    """
    if is_database_locked_error(error):
        logger.error("Database locked during %s: %s", operation, error)
        return {
            "success": False,
            "message": "Database is busy. Please retry the operation.",
            "error_code": "database_locked",
            "retryable": True,
        }

    if "foreign key" in str(error).lower():
        logger.error("Foreign key violation during %s: %s", operation, error)
        return {
            "success": False,
            "message": "Data integrity error: referenced data does not exist.",
            "error_code": "foreign_key_violation",
            "retryable": False,
        }

    if "unique constraint" in str(error).lower() or "duplicate" in str(error).lower():
        logger.warning("Duplicate data error during %s: %s", operation, error)
        return {
            "success": False,
            "message": "Duplicate data: the record already exists.",
            "error_code": "duplicate_error",
            "retryable": False,
        }

    logger.exception("Database error during %s", operation)
    return {
        "success": False,
        "message": f"Database error: {type(error).__name__}",
        "error_code": "database_error",
        "retryable": False,
    }
