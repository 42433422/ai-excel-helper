"""Tests for app.db.session query cache and get_db lifecycle."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.db import session as session_mod


@contextmanager
def _mock_session_scope():
    mock_db = MagicMock()
    try:
        yield mock_db
        mock_db.commit()
    except Exception:
        mock_db.rollback()
        raise
    finally:
        mock_db.close()


def test_query_cache_roundtrip():
    session_mod.clear_query_cache()
    key = session_mod.make_cache_key("fn", 1, page=2)
    session_mod.set_cached_query(key, {"ok": True})
    assert session_mod.get_cached_query(key) == {"ok": True}
    session_mod.clear_query_cache()
    assert session_mod.get_cached_query(key) is None


def test_timed_query_decorator_runs():
    @session_mod.timed_query("unit-test-query")
    def _work():
        return 42

    assert _work() == 42


def test_get_db_commits_on_success():
    captured = MagicMock()

    @contextmanager
    def scope():
        try:
            yield captured
            captured.commit()
        except Exception:
            captured.rollback()
            raise
        finally:
            captured.close()

    with patch.object(session_mod, "_session_scope", scope):
        with session_mod.get_db() as db:
            assert db is captured
    captured.commit.assert_called_once()
    captured.close.assert_called_once()


def test_get_db_rolls_back_on_error():
    captured = MagicMock()

    @contextmanager
    def scope():
        try:
            yield captured
            captured.commit()
        except Exception:
            captured.rollback()
            raise
        finally:
            captured.close()

    with patch.object(session_mod, "_session_scope", scope):
        with pytest.raises(RuntimeError):
            with session_mod.get_db():
                raise RuntimeError("boom")
    captured.rollback.assert_called_once()
    captured.close.assert_called_once()


def test_get_db_dependency_yields_session():
    with patch.object(session_mod, "_session_scope", _mock_session_scope):
        gen = session_mod.get_db_dependency()
        db = next(gen)
        assert isinstance(db, MagicMock)
        gen.close()
        db.close.assert_called()
