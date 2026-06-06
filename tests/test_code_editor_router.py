"""code-editor 路由单测（不依赖 backend/tests 的 PostgreSQL conftest）。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.fastapi_routes.code_editor import router as code_editor_router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(code_editor_router)
    with TestClient(app) as c:
        yield c


def test_code_editor_status(client: TestClient) -> None:
    r = client.get("/api/code-editor/status")
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is True
    assert j.get("phase") == "edit_diff_apply"
    assert "analyze_readonly" in (j.get("capabilities") or [])
    assert "apply_p2" in (j.get("capabilities") or [])
    assert "propose_new_file" in (j.get("capabilities") or [])
    assert "draft_p2" in (j.get("capabilities") or [])
    assert j.get("version") == 4


def test_code_editor_analyze_no_path(client: TestClient) -> None:
    r = client.post("/api/code-editor/analyze", json={"message": "x"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("kind") == "noop"


def test_code_editor_analyze_text_preview(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "note.txt").write_text("hello brain", encoding="utf-8")
    r = client.post("/api/code-editor/analyze", json={"path": "note.txt", "message": "peek"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("kind") == "text_preview"
    assert "hello brain" in (body.get("preview") or "")


def test_code_editor_analyze_escape_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    r = client.post("/api/code-editor/analyze", json={"path": "../outside.txt"})
    assert r.status_code == 400


def test_code_editor_edit_diff_apply_flow(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    (tmp_path / "x.txt").write_text("line1\n", encoding="utf-8")
    r_edit = client.post(
        "/api/code-editor/edit", json={"path": "x.txt", "new_content": "line1\nline2\n"}
    )
    assert r_edit.status_code == 200
    body = r_edit.json()
    assert body.get("success") is True
    edit_id = body.get("edit_id")
    assert isinstance(edit_id, str) and edit_id
    assert "line2" in (body.get("unified_diff") or "")

    r_diff = client.get(f"/api/code-editor/diff/{edit_id}")
    assert r_diff.status_code == 200
    assert "line2" in (r_diff.json().get("unified_diff") or "")

    r_apply_bad = client.post(f"/api/code-editor/apply/{edit_id}", json={})
    assert r_apply_bad.status_code == 403

    r_apply = client.post(
        f"/api/code-editor/apply/{edit_id}",
        json={},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "sekrit"},
    )
    assert r_apply.status_code == 200
    assert r_apply.json().get("created") is False
    assert (tmp_path / "x.txt").read_text(encoding="utf-8") == "line1\nline2\n"

    r_apply_again = client.post(
        f"/api/code-editor/apply/{edit_id}",
        json={},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "sekrit"},
    )
    assert r_apply_again.status_code == 404


def test_code_editor_apply_conflict_restores_proposal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    (tmp_path / "y.txt").write_text("a", encoding="utf-8")
    r_edit = client.post("/api/code-editor/edit", json={"path": "y.txt", "new_content": "b"})
    edit_id = r_edit.json()["edit_id"]
    (tmp_path / "y.txt").write_text("changed", encoding="utf-8")
    r_apply = client.post(
        f"/api/code-editor/apply/{edit_id}",
        json={},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "sekrit"},
    )
    assert r_apply.status_code == 409
    r_diff = client.get(f"/api/code-editor/diff/{edit_id}")
    assert r_diff.status_code == 200


def test_code_editor_edit_missing_path_without_flag_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "dir").mkdir()
    r = client.post(
        "/api/code-editor/edit",
        json={"path": "dir/missing.txt", "new_content": "x"},
    )
    assert r.status_code == 404


def test_code_editor_create_if_missing_apply(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    (tmp_path / "nest").mkdir()
    r_edit = client.post(
        "/api/code-editor/edit",
        json={
            "path": "nest/new_file.md",
            "new_content": "# hi\n",
            "create_if_missing": True,
        },
    )
    assert r_edit.status_code == 200
    assert r_edit.json().get("is_new_file") is True
    edit_id = r_edit.json()["edit_id"]
    r_apply = client.post(
        f"/api/code-editor/apply/{edit_id}",
        json={},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "sekrit"},
    )
    assert r_apply.status_code == 200
    assert r_apply.json().get("created") is True
    assert (tmp_path / "nest" / "new_file.md").read_text(encoding="utf-8") == "# hi\n"


def test_code_editor_create_if_missing_bad_extension(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "nest").mkdir()
    r = client.post(
        "/api/code-editor/edit",
        json={
            "path": "nest/blob.dat",
            "new_content": "x",
            "create_if_missing": True,
        },
    )
    assert r.status_code == 400


def test_code_editor_apply_new_file_conflict_when_path_appears(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    (tmp_path / "nest").mkdir()
    r_edit = client.post(
        "/api/code-editor/edit",
        json={
            "path": "nest/collision.txt",
            "new_content": "from proposal\n",
            "create_if_missing": True,
        },
    )
    edit_id = r_edit.json()["edit_id"]
    (tmp_path / "nest" / "collision.txt").write_text("race", encoding="utf-8")
    r_apply = client.post(
        f"/api/code-editor/apply/{edit_id}",
        json={},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "sekrit"},
    )
    assert r_apply.status_code == 409
    r_diff = client.get(f"/api/code-editor/diff/{edit_id}")
    assert r_diff.status_code == 200


def test_code_editor_draft_requires_p2(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    r = client.post("/api/code-editor/draft", json={"path": "a.py", "instruction": "add y"})
    assert r.status_code == 403


def test_code_editor_draft_mock_llm(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "tok")
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")

    def _fake(messages: list, **kw: object) -> str:
        return "x=1\ny=2\n"

    monkeypatch.setattr("app.fastapi_routes.code_editor.chat_completion_no_tools", _fake)
    r = client.post(
        "/api/code-editor/draft",
        json={"path": "a.py", "instruction": "append y"},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "tok"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is True
    assert j.get("proposed_new_content") == "x=1\ny=2\n"
    assert j.get("is_new_file") is False


def test_code_editor_draft_model_error_line(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "tok")
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")

    monkeypatch.setattr(
        "app.fastapi_routes.code_editor.chat_completion_no_tools",
        lambda messages, **kw: "ERROR: cannot comply",
    )
    r = client.post(
        "/api/code-editor/draft",
        json={"path": "a.py", "instruction": "do impossible"},
        headers={"X-XCAGI-AI-Tier": "p2", "X-XCAGI-Elevated-Token": "tok"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is False
    assert "ERROR" in (j.get("message") or "")
