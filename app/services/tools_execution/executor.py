from __future__ import annotations

import logging

from app.services.tools_execution.context import _hdr, _j
from app.services.tools_execution.order_parser import _parse_order_text
from app.services.tools_execution.registry import (
    _normalize_action,
    _validate_required_params,
    get_workflow_tool_registry,
)
from app.services.tools_payload_legacy import dispatch_legacy_tool_payload
from app.services.tools_workflow_registered import execute_registered_workflow_tool

logger = logging.getLogger(__name__)


def execute_tool_from_payload(data):
    return _execute_tool_from_payload_inner(data)


def _execute_tool_from_payload_inner(data):
    try:
        logger.info(f"[DEBUG] /api/tools/execute 收到请求 - data: {data}")

        if not data:
            logger.error("[DEBUG] /api/tools/execute 请求数据为空")
            return _j({"success": False, "message": "未收到数据"}, 400)

        tool_id = data.get("tool_id")
        action = _normalize_action(data.get("action", "view"), data.get("params") or {})
        params = data.get("params") or {}

        valid, err_msg = _validate_required_params(str(tool_id or "").strip(), action, params)
        if not valid:
            return _j(
                {
                    "success": False,
                    "error_code": "missing_required_params",
                    "message": err_msg,
                },
                400,
            )

        registry = get_workflow_tool_registry()
        if tool_id in registry and action in registry[tool_id].get("actions", {}):
            routed = execute_registered_workflow_tool(tool_id=tool_id, action=action, params=params)
            status_code = 200 if routed.get("success") else 400
            return _j(routed, status_code)

        logger.info(
            f"[DEBUG] tool_id={tool_id}, action={action}, params_keys={list(params.keys())}"
        )
        if "order_text" in params:
            logger.info(
                f"[DEBUG] order_text={params.get('order_text')[:200] if params.get('order_text') else None}"
            )

        return dispatch_legacy_tool_payload(
            tool_id,
            action,
            params,
            json_response_fn=_j,
            hdr_getter=_hdr,
            parse_order_text_fn=_parse_order_text,
        )

    except Exception as e:
        logger.error(f"执行工具失败: {e}")
        return _j({"success": False, "message": str(e)}, 500)
