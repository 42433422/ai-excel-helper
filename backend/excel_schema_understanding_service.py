"""
Upload / analyze Excel: call LLM to produce table summary, data dictionary, and semantic labels.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from openai import OpenAI

from backend.llm_config import get_llm_client, resolve_chat_model


def dataframe_schema_snapshot(df: pd.DataFrame, *, sample_rows: int = 5) -> dict[str, Any]:
    """Compact, LLM-facing snapshot: dtypes, nulls, and sample values (no full data)."""
    nulls = {str(c): int(v) for c, v in df.isnull().sum().items()}
    dtypes = {str(c): str(t) for c, t in df.dtypes.items()}
    head = df.head(sample_rows).replace({np.nan: None})
    sample_records = json.loads(head.to_json(orient="records", date_format="iso"))
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(map(str, df.columns)),
        "dtypes": dtypes,
        "null_counts": nulls,
        "sample_rows": sample_records,
    }


class ExcelSchemaUnderstandingService:
    """
    After an Excel file is available under the workspace, builds a schema snapshot and
    asks the LLM for: what the table is, field-level dictionary, and business semantics.
    """

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str | None = None,
    ) -> None:
        self._client = client or get_llm_client()
        self._model = model or resolve_chat_model()

    def understand_dataframe(
        self,
        df: pd.DataFrame,
        *,
        file_path: str,
        sheet_name: str | int | None = None,
    ) -> dict[str, Any]:
        snapshot = dataframe_schema_snapshot(df)
        sheet_note = "" if sheet_name is None else f"\n工作表: {sheet_name!r}\n"
        user_payload = {
            "file_path": file_path,
            "sheet": sheet_name,
            "snapshot": snapshot,
        }
        system = (
            "你是数据分析与业务建模助手。根据给定的表格结构快照（列名、类型、缺失、样例行），"
            "输出一个 JSON 对象（不要 Markdown），键必须包含：\n"
            "table_summary: string，用中文概括这张表是什么、可能用途；\n"
            "business_domain: string，推断业务域（如销售、人力、库存等）；\n"
            "columns: 数组，每项含 name, dtype, data_dictionary_zh（字段含义说明）, "
            "semantic_tag（如 维度/度量/标识/时间）, example_values（来自样例的简短数组）。\n"
            "还可选 data_quality_notes: string，简述明显数据质量问题。"
        )
        resp = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": sheet_note
                    + "以下为表格快照 JSON，请生成理解与数据字典：\n"
                    + json.dumps(user_payload, ensure_ascii=False, default=str),
                },
            ],
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "error": "llm_json_parse_failed",
                "raw": raw[:2000],
                "snapshot": snapshot,
            }
        return {
            "file_path": file_path,
            "sheet_name": sheet_name,
            "snapshot": snapshot,
            "llm_understanding": parsed,
        }
