"""生成代码校验与受限 pandas 执行辅助。

Phase 3B 从 ``app.legacy.excel_text_to_pandas`` 吸收。
"""

from __future__ import annotations

import ast
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 2000

_ALLOWED_AST_NODES = (
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.Return,
    ast.If,
    ast.For,
    ast.While,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Lambda,
    ast.IfExp,
    ast.Dict,
    ast.Set,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Compare,
    ast.Call,
    ast.Constant,
    ast.Name,
    ast.List,
    ast.Tuple,
    ast.Subscript,
    ast.Index,
    ast.Slice,
    ast.ExtSlice,
    ast.Starred,
    ast.Num,
    ast.Str,
    ast.FormattedValue,
    ast.JoinedStr,
)

SAFE_BUILTINS: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "len": len,
    "range": range,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "sorted": sorted,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "isinstance": isinstance,
    "type": type,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "any": any,
    "all": all,
    "hasattr": hasattr,
    "getattr": getattr,
    "True": True,
    "False": False,
    "None": None,
    "print": lambda *a, **kw: None,
}


def _validate_generated_code(code: str) -> str | None:
    if not code or not code.strip():
        return "empty code"
    if len(code) > MAX_CODE_LENGTH:
        return f"code exceeds maximum length ({len(code)} > {MAX_CODE_LENGTH})"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            attr_name = node.attr
            if attr_name.startswith("_"):
                return f"access to private attribute '{attr_name}' is forbidden"
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            return "import statements are forbidden"
        if not isinstance(node, _ALLOWED_AST_NODES):
            node_type = type(node).__name__
            logger.debug("restricted AST node rejected: %s", node_type)

    return None


def _safe_exec_pandas(code: str, df: pd.DataFrame) -> pd.DataFrame:
    err = _validate_generated_code(code)
    if err:
        raise ValueError(f"code validation failed: {err}")
    env: dict[str, Any] = {
        "df": df.copy(),
        "pd": pd,
        "result": None,
        "__builtins__": SAFE_BUILTINS,
    }
    exec(code, env, env)
    result = env.get("result")
    if isinstance(result, pd.DataFrame):
        return result
    if isinstance(result, pd.Series):
        return result.to_frame()
    return df.head(0)


__all__ = ["_validate_generated_code", "_safe_exec_pandas"]
