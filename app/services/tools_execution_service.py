"""兼容性 shim — 原始模块已拆分为 ``app.services.tools_execution`` 包。

所有公共符号从此包重新导出，现有 import 无需修改。
"""

from __future__ import annotations

from app.services.tools_execution import (  # noqa: F401
    ACTION_ALIASES,
    ASR_MODEL_SEGMENT_MAP,
    CANONICAL_ACTIONS,
    CHINESE_DIGIT_MAP,
    REQUIRED_PARAMS_BY_TOOL_ACTION,
    _execute_tool_from_payload_inner,
    _hdr,
    _j,
    _normalize_action,
    _parse_order_text,
    _tool_execute_headers,
    _validate_required_params,
    build_missing_prompt,
    cleanup_unit_name,
    execute_tool_from_payload,
    get_workflow_tool_registry,
    normalize_chinese_digits,
    normalize_model_number_token,
    normalize_quantity_token,
    normalize_trailing_unit_name,
    parse_cn_number,
    set_tool_execute_headers,
)
from app.services.tools_workflow_registered import execute_registered_workflow_tool  # noqa: F401
