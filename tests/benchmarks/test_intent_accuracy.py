"""
意图识别 golden set 基准（可复现 README / 营销声称中的准确率数字）。

默认门槛 INTENT_BENCHMARK_MIN_ACCURACY=0.85（与 TEST_SUMMARY 建议一致）。
若需验证「99%+」营销口径，在 workflow_dispatch 时设置 INTENT_BENCHMARK_MIN_ACCURACY=0.99。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

GOLDEN_PATH = Path(__file__).with_name("intent_golden_set.json")
REPORT_DIR = Path(__file__).resolve().parents[2] / "test_reports"


def _load_golden() -> list[dict]:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 10
    return data


def _match_case(result: dict, case: dict, text: str) -> bool:
    check = case.get("check")
    if check == "greeting":
        from app.services.intent_service import is_greeting

        return is_greeting(text)
    if check == "goodbye":
        from app.services.intent_service import is_goodbye

        return is_goodbye(text)

    exp_tool = case.get("expected_tool")
    exp_primary = case.get("expected_primary")
    tool = result.get("tool_key")
    primary = result.get("primary_intent")
    if exp_tool is not None and tool != exp_tool:
        return False
    if exp_primary is not None and primary != exp_primary:
        return False
    return True


@pytest.fixture(scope="module")
def golden_cases():
    os.environ.setdefault("XCAGI_SKIP_INTENT_LLM", "1")
    return _load_golden()


@pytest.mark.skipif(
    not os.environ.get("INTENT_BENCHMARK_RUN", "").strip(),
    reason="需要完整意图栈/DB；本地设 INTENT_BENCHMARK_RUN=1 再跑（见 intent-benchmark.yml）",
)
def test_intent_golden_set_accuracy(golden_cases):
    from app.services.intent_service import recognize_intents

    correct = 0
    failures: list[dict] = []
    for case in golden_cases:
        text = case["text"]
        result = recognize_intents(text)
        if _match_case(result, case, text):
            correct += 1
        else:
            failures.append(
                {
                    "text": text,
                    "expected_tool": case.get("expected_tool"),
                    "expected_primary": case.get("expected_primary"),
                    "got_tool": result.get("tool_key"),
                    "got_primary": result.get("primary_intent"),
                }
            )

    accuracy = correct / len(golden_cases)
    min_acc = float(os.environ.get("INTENT_BENCHMARK_MIN_ACCURACY", "0.95"))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "total": len(golden_cases),
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "min_required": min_acc,
        "failures": failures[:20],
    }
    (REPORT_DIR / "intent_benchmark_latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert accuracy >= min_acc, (
        f"Intent accuracy {accuracy:.2%} below threshold {min_acc:.2%}; "
        f"failures sample: {failures[:3]}"
    )
