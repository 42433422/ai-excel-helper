"""
Natural language → pandas code (LLM) → restricted execution. Result must be assigned to `result`.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from openai import OpenAI

from backend.llm_config import get_llm_client, resolve_chat_model

_FORBIDDEN_SUBSTRINGS = (
    "__",
    "import ",
    "\nimport",
    "eval(",
    "exec(",
    "compile(",
    "open(",
    "globals(",
    "locals(",
    "input(",
    "subprocess",
    "os.",
    "sys.",
    " pathlib",
    "Path(",
    " shutil",
    " socket",
    " requests",
)


def _validate_generated_code(code: str) -> str | None:
    if not code or len(code) > 4000:
        return "invalid_or_too_long_code"
    low = code.lower()
    for bad in _FORBIDDEN_SUBSTRINGS:
        if bad.lower() in low:
            return f"forbidden_pattern:{bad}"
    return None


def _safe_exec_pandas(code: str, df: pd.DataFrame) -> Any:
    err = _validate_generated_code(code)
    if err:
        raise ValueError(err)
    safe_builtins: dict[str, Any] = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "enumerate": enumerate,
        "range": range,
        "isinstance": isinstance,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
    }
    ns: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "pd": pd,
        "np": np,
        "df": df,
        "result": None,
    }
    exec(compile(code, "<nl_pandas>", "exec"), ns, ns)
    return ns.get("result")


def generate_pandas_code(
    *,
    client: OpenAI,
    model: str,
    df: pd.DataFrame,
    natural_language: str,
    schema_hint: dict[str, Any] | None = None,
) -> str:
    from backend.excel_schema_understanding_service import dataframe_schema_snapshot

    snap = schema_hint or dataframe_schema_snapshot(df, sample_rows=4)
    system = (
        "你是资深 pandas 工程师。用户会用自然语言描述对表格的查询或分析。"
        "变量 df 已存在，是 pandas.DataFrame。你必须只输出合法 JSON 对象，键 code 的值为"
        "一段 Python 代码字符串：代码中应使用 df 与 pd/np，并把最终答案赋给变量 result。"
        "result 应为 DataFrame、Series 或标量。禁止 import、文件、网络、eval/exec、双下划线名。"
        "列名必须与快照中的 columns 一致（区分大小写）。"
    )
    user = json.dumps(
        {
            "natural_language": natural_language,
            "schema_snapshot": snap,
        },
        ensure_ascii=False,
        default=str,
    )
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = json.loads(raw)
    code = data.get("code")
    if not isinstance(code, str):
        raise ValueError("llm_missing_code_key")
    return code.strip()


def run_natural_language_pandas(
    df: pd.DataFrame,
    natural_language: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    schema_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """LLM generates code; execute in restricted env. Returns JSON-serializable dict."""
    cli = client or get_llm_client()
    mdl = model or resolve_chat_model()
    try:
        code = generate_pandas_code(
            client=cli,
            model=mdl,
            df=df,
            natural_language=natural_language,
            schema_hint=schema_hint,
        )
    except Exception as e:
        return {"error": "code_generation_failed", "message": str(e)}

    try:
        out = _safe_exec_pandas(code, df)
    except Exception as e:
        return {
            "error": "execution_failed",
            "generated_code": code,
            "message": str(e),
        }

    if out is None:
        return {"error": "result_was_none", "generated_code": code}

    if isinstance(out, pd.DataFrame):
        return {
            "generated_code": code,
            "result_kind": "dataframe",
            **_df_result_records(out, max_rows=500),
        }
    if isinstance(out, pd.Series):
        fr = out.reset_index()
        return {
            "generated_code": code,
            "result_kind": "series",
            **_df_result_records(fr, max_rows=500),
        }
    return {
        "generated_code": code,
        "result_kind": "scalar",
        "value": out,
    }


def _df_result_records(df: pd.DataFrame, max_rows: int) -> dict[str, Any]:
    total = len(df)
    head = df.head(max_rows).replace({np.nan: None})
    records = json.loads(head.to_json(orient="records", date_format="iso"))
    return {
        "row_count": total,
        "truncated": total > max_rows,
        "returned_rows": len(head),
        "columns": list(df.columns.astype(str)),
        "records": records,
    }
