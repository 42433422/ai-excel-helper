from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import re
from typing import Any


TIME_RANGE_RE = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})")

# 由 ``convert`` 在每次转换前注入 ``resources/config/approval_config.yaml`` 中的 ``attendance_policy``。
ACTIVE_POLICY: dict[str, Any] = {}


def set_attendance_policy(policy: dict[str, Any] | None) -> None:
    """用毕可传 ``{}`` 清空，避免测试间串味。"""
    global ACTIVE_POLICY
    ACTIVE_POLICY = dict(policy or {})


@dataclass(frozen=True)
class TimeRange:
    start: time
    end: time

    def hours(self) -> float:
        start_dt = datetime.combine(date.min, self.start)
        end_dt = datetime.combine(date.min, self.end)
        return max((end_dt - start_dt).total_seconds() / 3600.0, 0.0)


COMPANY_FACTORY_GROUP_KEYWORDS = (
    "公司-考勤",
    "公司正班",
    "惠州工厂-正班",
    "工厂正班",
)

DEFAULT_WEEKDAY_SEGMENTS = (
    TimeRange(time(8, 0), time(12, 0)),
    TimeRange(time(13, 30), time(17, 30)),
)


def parse_hhmm(value: str) -> time:
    hour_str, minute_str = value.split(":", 1)
    return time(int(hour_str), int(minute_str))


def normalize_group_text(*values: str | None) -> str:
    return " ".join(str(v or "").strip() for v in values if str(v or "").strip())


def _policy_company_keywords() -> tuple[str, ...]:
    k = ACTIVE_POLICY.get("company_factory_group_keywords")
    if isinstance(k, list) and k:
        return tuple(str(x).strip() for x in k if str(x).strip())
    return COMPANY_FACTORY_GROUP_KEYWORDS


def is_company_factory_group(group_name: str | None, shift_name: str | None = None) -> bool:
    text = normalize_group_text(group_name, shift_name)
    return any(keyword in text for keyword in _policy_company_keywords())


def _segment_strings_to_ranges(segments: Any) -> tuple[TimeRange, ...] | None:
    if not isinstance(segments, list) or not segments:
        return None
    out: list[TimeRange] = []
    for s in segments:
        if not isinstance(s, str):
            continue
        m = TIME_RANGE_RE.search(s.replace("—", "-").replace("–", "-"))
        if not m:
            continue
        start, end = parse_hhmm(m.group(1)), parse_hhmm(m.group(2))
        if end > start:
            out.append(TimeRange(start, end))
    return tuple(out) if out else None


def _policy_weekday_segments() -> tuple[TimeRange, ...]:
    got = _segment_strings_to_ranges(ACTIVE_POLICY.get("weekday_segments"))
    return got if got is not None else DEFAULT_WEEKDAY_SEGMENTS


def parse_shift_ranges(shift_name: str | None) -> tuple[TimeRange, ...]:
    text = str(shift_name or "").strip()
    matches = TIME_RANGE_RE.findall(text)
    ranges: list[TimeRange] = []
    for start_raw, end_raw in matches:
        start = parse_hhmm(start_raw)
        end = parse_hhmm(end_raw)
        if end > start:
            ranges.append(TimeRange(start, end))
    return tuple(ranges)


def is_rest_shift(shift_name: str | None) -> bool:
    text = str(shift_name or "").strip()
    return (not text) or ("休息" in text)


def resolve_schedule_ranges(
    work_date: date,
    *,
    group_name: str | None,
    shift_name: str | None,
    has_any_punch: bool,
) -> tuple[TimeRange, ...]:
    parsed = parse_shift_ranges(shift_name)
    weekday = work_date.weekday()

    if weekday == 6:
        if ACTIVE_POLICY.get("sunday_empty_schedule", True):
            return ()
        return _policy_weekday_segments()

    if weekday == 5:
        if not has_any_punch:
            return ()
        if parsed:
            return parsed
        return _policy_weekday_segments()

    if parsed:
        return parsed

    return _policy_weekday_segments()


def regular_hours_for_ranges(ranges: tuple[TimeRange, ...]) -> float:
    return round(sum(r.hours() for r in ranges), 2)
