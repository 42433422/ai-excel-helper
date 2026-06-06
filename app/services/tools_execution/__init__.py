"""工具执行与订单解析服务。

Phase 4 由 ``app.services.archive_tools_legacy`` 更名而来,内容不变,
只是摆脱 "archive_" 命名噪音。后续 (Phase 4B) 计划与 ``app.legacy.tools``
去重合并到 ``app.application.tools.*``。
"""

from __future__ import annotations

from app.services.tools_execution.context import (
    _hdr,
    _j,
    _tool_execute_headers,
    set_tool_execute_headers,
)
from app.services.tools_execution.executor import (
    _execute_tool_from_payload_inner,
    execute_tool_from_payload,
)
from app.services.tools_execution.order_parser import _parse_order_text
from app.services.tools_execution.order_parser_helpers import (
    ASR_MODEL_SEGMENT_MAP,
    CHINESE_DIGIT_MAP,
    build_missing_prompt,
    cleanup_unit_name,
    normalize_chinese_digits,
    normalize_model_number_token,
    normalize_quantity_token,
    normalize_trailing_unit_name,
    parse_cn_number,
)
from app.services.tools_execution.registry import (
    ACTION_ALIASES,
    CANONICAL_ACTIONS,
    REQUIRED_PARAMS_BY_TOOL_ACTION,
    _normalize_action,
    _validate_required_params,
    get_workflow_tool_registry,
)
from app.services.tools_workflow_registered import execute_registered_workflow_tool

__all__ = [
    "set_tool_execute_headers",
    "execute_tool_from_payload",
    "execute_registered_workflow_tool",
    "_execute_tool_from_payload_inner",
    "_parse_order_text",
    "get_workflow_tool_registry",
    "_normalize_action",
    "_validate_required_params",
    "CANONICAL_ACTIONS",
    "ACTION_ALIASES",
    "REQUIRED_PARAMS_BY_TOOL_ACTION",
    "_hdr",
    "_j",
    "_tool_execute_headers",
    "parse_cn_number",
    "cleanup_unit_name",
    "build_missing_prompt",
    "normalize_trailing_unit_name",
    "normalize_chinese_digits",
    "normalize_quantity_token",
    "normalize_model_number_token",
    "CHINESE_DIGIT_MAP",
    "ASR_MODEL_SEGMENT_MAP",
]
