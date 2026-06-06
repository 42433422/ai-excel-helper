"""COVERAGE_RAMP Phase 55: finance_app_service, app.db pool/health, rate_limiter redis client,
security_headers, user_memory_service (mocked I/O)."""

from __future__ import annotations

import json
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import Engine

import app.db as db_mod
import app.services.user_memory_service as ums
import app.utils.rate_limiter as redis_client_mod
from app.application.finance_app_service import FinanceAppService, _parse_dt, _to_float
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.user_memory_service import (
    ActionPattern,
    ContextSummary,
    FeedbackRecord,
    UserMemory,
    UserMemoryService,
    UserMemoryStore,
    get_user_memory_service,
    reset_user_memory_service,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_user_memory_singletons() -> None:
    UserMemoryStore._instance = None
    UserMemoryService._instance = None
    reset_user_memory_service()
    yield
    UserMemoryStore._instance = None
    UserMemoryService._instance = None
    reset_user_memory_service()


@pytest.fixture(autouse=True)
def _reset_rate_limiter_state() -> None:
    redis_client_mod._redis_client = None
    redis_client_mod._redis_init_attempted = False
    redis_client_mod._rate_limiters.clear()
    redis_client_mod._circuit_breakers.clear()
    yield
    redis_client_mod._redis_client = None
    redis_client_mod._redis_init_attempted = False
    redis_client_mod._rate_limiters.clear()
    redis_client_mod._circuit_breakers.clear()


@pytest.fixture(autouse=True)
def _reset_db_engine_cache() -> None:
    with db_mod._engine_cache_lock:
        db_mod._engine_cache.clear()
        db_mod._session_local_cache.clear()
    yield
    with db_mod._engine_cache_lock:
        db_mod._engine_cache.clear()
        db_mod._session_local_cache.clear()


@pytest.fixture
def memory_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    mem_dir = tmp_path / "user_memory"
    mem_dir.mkdir()
    json_path = mem_dir / "memory_store.json"
    monkeypatch.setattr(ums, "MEMORY_DIR", str(mem_dir))
    monkeypatch.setattr(ums, "JSON_MEMORY_PATH", str(json_path))
    return json_path


def _mock_get_db(mock_db: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = mock_db
    cm.__exit__.return_value = None
    return cm


def _query_chain(
    *,
    scalar: float | Decimal | None = None,
    count: int = 0,
    all_items: list | None = None,
    first: MagicMock | None = None,
) -> MagicMock:
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.notin_.return_value = q
    q.in_.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.scalar.return_value = scalar
    q.count.return_value = count
    q.all.return_value = all_items or []
    q.first.return_value = first
    return q


def _http_scope(
    path: str = "/",
    *,
    query_string: bytes = b"",
    scheme: str = "http",
) -> dict:
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": query_string,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": scheme,
        "root_path": "",
    }


# ---------------------------------------------------------------------------
# finance_app_service
# ---------------------------------------------------------------------------


def test_finance_to_float_variants() -> None:
    assert _to_float(None) is None
    assert _to_float(Decimal("12.5")) == 12.5
    assert _to_float(7) == 7.0


@patch("app.application.finance_app_service.get_db")
def test_finance_dashboard_zero_revenue_margin(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    mock_db.query.return_value = _query_chain(scalar=None)
    out = FinanceAppService().get_dashboard()
    assert out["success"] is True
    assert out["data"]["gross_margin_pct"] == 0.0


@patch("app.application.finance_app_service.get_db")
def test_finance_list_transactions_filters(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    row = MagicMock()
    row.to_dict.return_value = {"id": 2, "transaction_type": "payment"}
    mock_db.query.return_value = _query_chain(count=1, all_items=[row])
    out = FinanceAppService().list_transactions(
        transaction_type="payment",
        status="completed",
        page=1,
        per_page=10,
    )
    assert out["success"] is True
    assert out["data"][0]["transaction_type"] == "payment"


@patch("app.application.finance_app_service.get_db")
def test_finance_update_transaction_success(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    txn = MagicMock()
    txn.to_dict.return_value = {"id": 5, "amount": "99"}
    mock_db.query.return_value = _query_chain(first=txn)
    out = FinanceAppService().update_transaction(
        5,
        {"amount": "99", "transaction_date": "2026-06-01", "due_date": "2026-07-01"},
    )
    assert out["success"] is True
    mock_db.commit.assert_called_once()


@patch("app.application.finance_app_service.get_db")
def test_finance_delete_transaction_success(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    mock_db.query.return_value = _query_chain(first=MagicMock())
    out = FinanceAppService().delete_transaction(3)
    assert out["success"] is True
    mock_db.delete.assert_called_once()


@patch("app.application.finance_app_service.get_db")
def test_finance_create_transaction_rollback(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    mock_db.add.side_effect = RuntimeError("constraint")
    with patch(
        "app.application.finance_app_service.FinancialTransaction", return_value=MagicMock()
    ):
        out = FinanceAppService().create_transaction(
            {"transaction_type": "receipt", "amount": "10"},
        )
    assert out["success"] is False
    mock_db.rollback.assert_called_once()


@patch("app.application.finance_app_service.get_db")
def test_finance_monthly_trend_twelve_months(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    mock_db.query.return_value = _query_chain(scalar=Decimal("100"))
    out = FinanceAppService().get_monthly_trend(year=2025)
    assert out["success"] is True
    assert out["year"] == 2025
    assert len(out["data"]) == 12
    assert out["data"][0]["month"] == "2025-01"


@patch("app.application.finance_app_service.get_db")
def test_finance_get_receivables_with_dates(mock_get_db: MagicMock) -> None:
    mock_db = MagicMock()
    mock_get_db.return_value = _mock_get_db(mock_db)
    mock_db.query.return_value = _query_chain(count=0, all_items=[])
    start = datetime(2026, 1, 1)
    end = datetime(2026, 12, 31)
    out = FinanceAppService().get_receivables(start_date=start, end_date=end, status="pending")
    assert out["success"] is True
    assert out["total"] == 0


def test_finance_parse_dt_invalid_string() -> None:
    assert _parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# app.db — pool / session health
# ---------------------------------------------------------------------------


def test_db_get_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///phase55.db")
    with patch.object(db_mod, "_database_url_for_active_mod", side_effect=lambda u: u):
        assert db_mod._get_database_url() == "sqlite:///phase55.db"


def test_db_get_database_url_test_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_db = tmp_path / "test_runtime.db"
    mgr = MagicMock()
    mgr.is_enabled.return_value = True
    mgr.resolved_test_db_path.return_value = str(test_db)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with patch.object(db_mod, "_get_test_db_manager", return_value=mgr):
        url = db_mod._get_database_url()
    assert url == f"sqlite:///{test_db}"


def test_db_engine_cache_reuses_instance() -> None:
    url = "sqlite:///:memory:"
    e1 = db_mod._get_engine_for_url(url)
    e2 = db_mod._get_engine_for_url(url)
    assert e1 is e2
    assert isinstance(e1, Engine)


def test_db_session_local_factory_cached() -> None:
    url = "sqlite:///:memory:"
    with patch.object(db_mod, "_get_database_url", return_value=url):
        f1 = db_mod._get_session_local()
        f2 = db_mod._get_session_local()
    assert f1 is f2


def test_db_session_local_callable_returns_session() -> None:
    with patch.object(db_mod, "_get_database_url", return_value="sqlite:///:memory:"):
        session = db_mod.SessionLocal()
    try:
        assert session is not None
        session.close()
    except Exception:
        session.close()


def test_db_get_db_closes_session() -> None:
    from contextlib import contextmanager

    mock_session = MagicMock()

    @contextmanager
    def fake_transaction(url, mod_id=None):
        try:
            yield mock_session
            mock_session.commit()
        except Exception:
            mock_session.rollback()
            raise
        finally:
            mock_session.close()

    with patch("app.db.db_consistency.get_consistency_manager") as mgr:
        mgr.return_value.transaction.side_effect = fake_transaction
        gen = db_mod.get_db()
        db = next(gen)
        assert db is mock_session
        with pytest.raises(StopIteration):
            gen.send(None)
    mock_session.close.assert_called_once()


def test_db_close_old_connections_clears_pool() -> None:
    from app.db.db_consistency import get_consistency_manager

    url = "sqlite:///:memory:"
    mgr = get_consistency_manager()
    db_mod._get_engine_for_url(url)
    assert mgr._engines
    db_mod.close_old_connections()
    assert not mgr._engines


def test_db_engine_proxy_delegates_dialect() -> None:
    with patch.object(db_mod, "_get_engine") as mock_eng:
        mock_eng.return_value.dialect.name = "sqlite"
        assert db_mod.engine.dialect.name == "sqlite"


def test_db_dispose_and_recreate_engine_clears_cache() -> None:
    db_mod._get_engine_for_url("sqlite:///:memory:")
    db_mod.dispose_and_recreate_engine()
    assert not db_mod._engine_cache


def test_db_mod_isolated_databases_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XCAGI_MOD_ISOLATED_DATABASES", "true")
    assert db_mod._mod_isolated_databases_enabled() is True


# ---------------------------------------------------------------------------
# rate_limiter — redis client helper (redis_client.py role)
# ---------------------------------------------------------------------------


def test_redis_client_no_url_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("XCAGI_REDIS_URL", raising=False)
    assert redis_client_mod._get_redis_client() is None


def test_redis_client_success_from_cache_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = MagicMock()
    fake.ping.return_value = True
    monkeypatch.setenv("CACHE_REDIS_URL", "redis://localhost:6379/0")
    with patch("redis.from_url", return_value=fake) as from_url:
        client = redis_client_mod._get_redis_client()
    assert client is fake
    from_url.assert_called_once()


def test_redis_client_ping_failure_falls_back_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    broken = MagicMock()
    broken.ping.side_effect = ConnectionError("down")
    with patch("redis.from_url", return_value=broken):
        assert redis_client_mod._get_redis_client() is None


def test_redis_client_second_call_uses_cached_attempt_flag() -> None:
    redis_client_mod._redis_init_attempted = True
    sentinel = MagicMock()
    redis_client_mod._redis_client = sentinel
    assert redis_client_mod._get_redis_client() is sentinel


def test_in_memory_rate_limiter_blocks_over_max() -> None:
    limiter = redis_client_mod._InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.is_allowed("k") is True
    assert limiter.is_allowed("k") is True
    assert limiter.is_allowed("k") is False
    assert limiter.get_remaining("k") == 0


def test_in_memory_rate_limiter_reset_time() -> None:
    limiter = redis_client_mod._InMemoryRateLimiter(max_requests=5, window_seconds=10)
    limiter.is_allowed("user:1")
    reset = limiter.get_reset_time("user:1")
    assert reset is not None
    assert reset > time.time()


def test_redis_rate_limiter_allows_when_no_client() -> None:
    limiter = redis_client_mod._RedisRateLimiter(max_requests=5, window_seconds=60)
    limiter._redis = None
    assert limiter.is_allowed("k") is True
    assert limiter.get_remaining("k") == 5


def test_redis_rate_limiter_pipeline_counts() -> None:
    fake_redis = MagicMock()
    pipe = MagicMock()
    pipe.execute.return_value = (3, True)
    fake_redis.pipeline.return_value = pipe
    limiter = redis_client_mod._RedisRateLimiter(max_requests=5, window_seconds=60)
    limiter._redis = fake_redis
    assert limiter.is_allowed("endpoint:user") is True
    pipe.incr.assert_called_once()


def test_redis_rate_limiter_get_remaining_handles_error() -> None:
    fake_redis = MagicMock()
    fake_redis.get.side_effect = RuntimeError("redis read fail")
    limiter = redis_client_mod._RedisRateLimiter(max_requests=10, window_seconds=30)
    limiter._redis = fake_redis
    assert limiter.get_remaining("k") == 0


def test_circuit_breaker_opens_after_threshold() -> None:
    cb = redis_client_mod._CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    def boom():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        cb.call(boom)
    with pytest.raises(ValueError):
        cb.call(boom)
    assert cb.state == "open"
    with pytest.raises(Exception, match="open"):
        cb.call(lambda: "ok")


def test_circuit_breaker_half_open_recovers() -> None:
    cb = redis_client_mod._CircuitBreaker(failure_threshold=1, recovery_timeout=0)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError("x")))
    time.sleep(0.01)
    assert cb.state == "half-open"
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == "closed"


def test_check_rate_limit_denied_returns_retry_after() -> None:
    limiter = redis_client_mod._InMemoryRateLimiter(max_requests=1, window_seconds=30)
    with patch.object(redis_client_mod, "get_rate_limiter", return_value=limiter):
        first = redis_client_mod.check_rate_limit("u1", "api", max_requests=1, window_seconds=30)
        second = redis_client_mod.check_rate_limit("u1", "api", max_requests=1, window_seconds=30)
    assert first["allowed"] is True
    assert second["allowed"] is False
    assert second["retry_after"] is not None


def test_get_rate_limiter_uses_redis_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_client_mod, "_get_redis_client", lambda: MagicMock())
    lim = redis_client_mod.get_rate_limiter("phase55", max_requests=3, window_seconds=10)
    assert isinstance(lim, redis_client_mod._RedisRateLimiter)


def test_reset_circuit_breaker_clears_state() -> None:
    cb = redis_client_mod.get_circuit_breaker("phase55-cb", failure_threshold=1)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
    redis_client_mod.reset_circuit_breaker("phase55-cb")
    assert cb.state == "closed"


# ---------------------------------------------------------------------------
# security_headers middleware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_headers_https_adds_hsts() -> None:
    captured: dict = {}

    async def _app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def capture_send(message):
        if message["type"] == "http.response.start":
            captured["headers"] = dict(message.get("headers", []))

    mw = SecurityHeadersMiddleware(_app)
    await mw(_http_scope(scheme="https"), lambda: None, capture_send)
    assert b"strict-transport-security" in captured["headers"]


@pytest.mark.asyncio
async def test_security_headers_sandbox_query_flag_1() -> None:
    captured: dict = {}

    async def _app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def capture_send(message):
        if message["type"] == "http.response.start":
            captured["headers"] = dict(message.get("headers", []))

    mw = SecurityHeadersMiddleware(_app)
    await mw(_http_scope(query_string=b"sandbox=1"), lambda: None, capture_send)
    csp = captured["headers"].get(b"content-security-policy", b"").decode()
    assert "unsafe-eval" in csp


@pytest.mark.asyncio
async def test_security_headers_websocket_passthrough() -> None:
    called = {"inner": False}

    async def inner(scope, receive, send):
        called["inner"] = True

    mw = SecurityHeadersMiddleware(inner)
    await mw({"type": "websocket"}, MagicMock(), MagicMock())
    assert called["inner"] is True


# ---------------------------------------------------------------------------
# user_memory_service
# ---------------------------------------------------------------------------


def test_user_memory_store_load_invalid_json(memory_paths: Path) -> None:
    memory_paths.write_text("not-json", encoding="utf-8")
    store = UserMemoryStore(storage_type="json")
    assert store._memory_cache == {}


def test_user_memory_store_non_json_storage_skips_persist() -> None:
    store = UserMemoryStore(storage_type="memory")
    mem = UserMemory(user_id="u55")
    store.save_memory("u55", mem)
    store._should_persist()


def test_user_memory_preference_roundtrip(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    svc.add_preference("u55", "favorite_customer", "七彩乐园")
    assert svc.get_preference("u55", "favorite_customer") == "七彩乐园"
    assert svc.get_all_preferences("u55")["favorite_customer"] == "七彩乐园"


def test_user_memory_record_action_increments_frequency(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    slots = {"unit_name": "甲", "product_name": "底漆"}
    svc.record_action("u55", "shipment", slots)
    svc.record_action("u55", "shipment", slots)
    actions = svc.get_recent_actions("u55", limit=5, intent_filter="shipment")
    assert actions[0]["frequency"] == 2


def test_user_memory_get_similar_pattern_none_when_empty(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    assert svc.get_similar_pattern("new-user", "shipment", {}) is None


def test_user_memory_feedback_stats_error_rates(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    for _ in range(4):
        svc.add_feedback("u55", "msg", "products_query", "negated")
    stats = svc.get_feedback_stats("u55")
    assert stats["negated"] == 4
    assert "products_query" in stats.get("error_rates", {})


def test_user_memory_apply_preference_fills_slots(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    svc.add_preference("u55", "favorite_customer", "默认客户")
    svc.add_preference("u55", "default_template", "tpl-a")
    filled = svc.apply_preference_to_slots("u55", "shipment", {})
    assert filled["unit_name"] == "默认客户"
    assert filled["template"] == "tpl-a"


def test_user_memory_summary_has_memory_flag(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    svc.record_action("u55", "inventory_query", {"unit_name": "甲"})
    summary = svc.get_memory_summary("u55")
    assert summary["has_memory"] is True
    assert summary["action_count"] >= 1


def test_user_memory_summary_empty_user(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    assert svc.get_memory_summary("ghost")["has_memory"] is True


def test_get_user_memory_service_singleton() -> None:
    a = get_user_memory_service()
    b = get_user_memory_service()
    assert a is b


def test_user_memory_dataclass_roundtrip() -> None:
    ap = ActionPattern(pattern="p", intent="i", slots={"a": 1})
    assert ActionPattern.from_dict(ap.to_dict()).intent == "i"
    fr = FeedbackRecord(
        timestamp="t",
        message="m",
        recognized_intent="ri",
        user_feedback="confirmed",
    )
    assert FeedbackRecord.from_dict(fr.to_dict()).user_feedback == "confirmed"
    cs = ContextSummary(timestamp="t", intent="i", slots={}, message="m")
    assert ContextSummary.from_dict(cs.to_dict()).intent == "i"


def test_user_memory_calculate_similarity_both_empty() -> None:
    svc = UserMemoryService(storage_type="json")
    assert svc._calculate_similarity({}, {}) == 1.0


def test_user_memory_negated_feedback_lowers_confidence(memory_paths: Path) -> None:
    svc = UserMemoryService(storage_type="json")
    svc.record_action("u55", "shipment", {"unit_name": "甲"})
    before = svc._store.get_memory("u55").frequent_actions[0]["confidence"]
    svc.add_feedback("u55", "不对", "shipment", "negated")
    after = svc._store.get_memory("u55").frequent_actions[0]["confidence"]
    assert after < before


def test_user_memory_store_persists_json(memory_paths: Path) -> None:
    store = UserMemoryStore(storage_type="json")
    store.get_memory("persist-user")
    store._cache_dirty["persist-user"] = True
    store._save_all_memories()
    assert memory_paths.exists()
    data = json.loads(memory_paths.read_text(encoding="utf-8"))
    assert "persist-user" in data
