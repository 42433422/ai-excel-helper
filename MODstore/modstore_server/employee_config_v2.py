"""员工包 ``employee_config_v2`` 校验；可选 ``metadata.daily_brief_seed`` / ``daily_brief_research_focus`` 供每日摘要调研 brief。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from modstore_server.models import Workflow
from modstore_server.workflow_sandbox_state import validate_workflow_sandbox_ready


def _to_str(v: Any) -> str:
    return str(v or "").strip()


def _to_workflow_id(v: Any) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def upgrade_legacy_manifest_to_v2(legacy: Dict[str, Any]) -> Dict[str, Any]:
    item = legacy if isinstance(legacy, dict) else {}
    wf_rows = item.get("workflow_employees")
    wf0 = wf_rows[0] if isinstance(wf_rows, list) and wf_rows else {}
    wf_id = _to_workflow_id((wf0 or {}).get("workflow_id") if isinstance(wf0, dict) else 0)
    price = 0.0
    try:
        price = float((item.get("commerce") or {}).get("price") or 0.0)
    except (TypeError, ValueError, AttributeError):
        price = 0.0
    return {
        "identity": {
            "id": _to_str(item.get("id")),
            "version": _to_str(item.get("version")) or "1.0.0",
            "artifact": _to_str(item.get("artifact")) or "employee_pack",
            "name": _to_str(item.get("name")),
            "description": _to_str(item.get("description")),
        },
        "cognition": {
            "agent": {
                "system_prompt": _to_str(item.get("panel_summary")),
                "role": {
                    "name": _to_str(item.get("name")),
                    "persona": "",
                    "tone": "professional",
                    "expertise": [],
                },
                "behavior_rules": [],
                "few_shot_examples": [],
                "model": {
                    "provider": "auto",
                    "model_name": "auto",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "top_p": 0.9,
                },
            },
            "skills": [],
        },
        "collaboration": {"workflow": {"workflow_id": wf_id}},
        "commerce": {"industry": _to_str(item.get("industry")) or "通用", "price": max(price, 0.0)},
        "workflow_employees": wf_rows if isinstance(wf_rows, list) else [],
        "metadata": {"framework_version": "2.0.0", "created_by": "migration", "migration_from": "v1"},
    }


def extract_or_upgrade_v2_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    v2 = payload.get("employee_config_v2")
    if isinstance(v2, dict):
        return v2
    return upgrade_legacy_manifest_to_v2(payload)


def validate_v2_config(
    config: Dict[str, Any],
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    require_workflow_heart: bool = True,
    require_workflow_sandbox: bool = False,
) -> List[str]:
    c = config if isinstance(config, dict) else {}
    errs: List[str] = []
    if not _to_str(((c.get("identity") or {}).get("id"))):
        errs.append("缺少 identity.id")
    if not _to_str(((c.get("identity") or {}).get("name"))):
        errs.append("缺少 identity.name")
    if not _to_str(((c.get("identity") or {}).get("version"))):
        errs.append("缺少 identity.version")
    wf_id = _to_workflow_id((((c.get("collaboration") or {}).get("workflow") or {}).get("workflow_id")))
    if require_workflow_heart and wf_id <= 0:
        errs.append("工作流心脏必填：collaboration.workflow.workflow_id")
    if wf_id > 0 and db is not None:
        q = db.query(Workflow).filter(Workflow.id == wf_id)
        if user_id is not None:
            q = q.filter(Workflow.user_id == user_id)
        hit = q.first()
        if not hit:
            errs.append(f"workflow_id={wf_id} 不存在或无权限")
        elif require_workflow_sandbox:
            errs.extend(
                validate_workflow_sandbox_ready(
                    db,
                    workflow_id=wf_id,
                    user_id=user_id,
                )
            )
    elif wf_id > 0 and require_workflow_sandbox:
        errs.append("无法验证 workflow 沙箱状态：缺少数据库上下文")
    perception = c.get("perception") or {}
    actions = c.get("actions") or {}
    memory = c.get("memory") or {}
    cognition = c.get("cognition") or {}
    asr_enabled = bool((((perception.get("audio") or {}).get("asr") or {}).get("enabled")))
    if asr_enabled and not isinstance(actions.get("voice_output"), dict):
        errs.append("启用 ASR 需要配置 actions.voice_output")
    long_term_enabled = bool((memory.get("long_term") or {}).get("enabled"))
    if long_term_enabled and not isinstance(cognition.get("agent"), dict):
        errs.append("启用知识库需要配置 cognition.agent")
    return errs
