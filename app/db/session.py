import hashlib
import logging
import time
import traceback
from contextlib import contextmanager
from functools import lru_cache, wraps

from app.db import SessionLocal

logger = logging.getLogger(__name__)

_query_cache = {}
_CACHE_MAX_SIZE = 128
_CACHE_TTL_SECONDS = 300

_SLOW_QUERY_THRESHOLD = 1.0


def _make_cache_key(query_func_name: str, *args, **kwargs) -> str:
    key_str = f"{query_func_name}:{str(args)}:{str(kwargs)}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached_query(cache_key: str):
    return _query_cache.get(cache_key)


def set_cached_query(cache_key: str, value, ttl: int = _CACHE_TTL_SECONDS):
    if len(_query_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_query_cache))
        del _query_cache[oldest_key]
    _query_cache[cache_key] = value


def clear_query_cache():
    global _query_cache
    _query_cache = {}
    logger.info("Query cache cleared")


def _log_slow_query(query_name: str, duration: float, details: str = ""):
    if duration >= _SLOW_QUERY_THRESHOLD:
        logger.warning(
            f"Slow query detected: {query_name} took {duration:.3f}s. {details}"
        )


class _QueryTimer:
    def __init__(self, query_name: str):
        self.query_name = query_name
        self.start_time: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        _log_slow_query(self.query_name, duration)
        return False


def timed_query(query_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with _QueryTimer(query_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def get_db():
    db = SessionLocal()
    query_count = [0]
    def _count_query():
        query_count[0] += 1
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败，已回滚: {e}")
        raise
    finally:
        db.close()


def get_db_dependency():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败，已回滚: {e}")
        raise
    finally:
        db.close()
