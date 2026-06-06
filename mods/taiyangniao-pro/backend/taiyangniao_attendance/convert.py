from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
import math
from pathlib import Path
from typing import Any

from .mapper import (
    DayBandEntry,
    EmployeeDayTemplateData,
    EmployeeMonthTemplateData,
    TemplateEmployeeProfile,
    build_template_profiles,
    iter_detail_sheet_block_base_rows,
    open_output_workbook,
    rebuild_detail_sheet_person_blocks,
    write_detail_sheet,
    write_monthly_sheet,
)
from .parser import AttendanceDayRecord, dingtalk_work_hours_as_hours, parse_attendance_workbook
from .rules import (
    TimeRange,
    is_company_factory_group,
    is_rest_shift,
    resolve_schedule_ranges,
)

logger = logging.getLogger(__name__)


def _filter_records_to_template_roster(
    records: list[AttendanceDayRecord],
    template_profiles: dict[str, TemplateEmployeeProfile],
) -> list[AttendanceDayRecord]:
    """只保留「明细」模板里已有姓名的打卡记录，再按规则聚合；钉钉表其余人员忽略。"""
    if not template_profiles:
        return []
    allowed = {str(k).strip() for k in template_profiles.keys() if str(k).strip()}
    return [r for r in records if (r.employee_name or "").strip() in allowed]


def _retain_detail_and_monthly_sheets(workbook) -> None:
    """输出只保留「明细」与「月度统计」（后者含指向明细侧栏小计的公式，便于手改后自动重算）。"""
    keep = frozenset({"明细", "月度统计"})
    if "明细" not in workbook.sheetnames:
        workbook.active.title = "明细"
    for name in list(workbook.sheetnames):
        if name not in keep:
            del workbook[name]


def _band_windows() -> dict[str, TimeRange]:
    return {
        "morning": TimeRange(time(0, 0), time(12, 30)),
        "afternoon": TimeRange(time(12, 30), time(18, 0)),
        "night": TimeRange(time(18, 0), time(23, 59)),
    }


def _hours_between(start: datetime, end: datetime) -> float:
    return max((end - start).total_seconds() / 3600.0, 0.0)


def _overlap_hours(
    interval_start: datetime,
    interval_end: datetime,
    range_start: time,
    range_end: time,
) -> float:
    start = max(interval_start, datetime.combine(interval_start.date(), range_start))
    end = min(interval_end, datetime.combine(interval_end.date(), range_end))
    return _hours_between(start, end)


def _unique_sorted(values: list[datetime]) -> list[datetime]:
    seen: set[datetime] = set()
    result: list[datetime] = []
    for value in sorted(values):
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _round_half_hour(value: float) -> float:
    if value <= 0:
        return 0.0
    return round(round(value * 2) / 2, 2)


def _round_half_hour_with_25_minute_grace(value: float) -> float:
    if value <= 0:
        return 0.0
    whole_half_hours = math.floor(value * 2)
    remainder_hours = value - (whole_half_hours / 2)
    if remainder_hours * 60 >= 25:
        whole_half_hours += 1
    return round(whole_half_hours / 2, 2)


def _round_whole_hour(value: float) -> float:
    if value <= 0:
        return 0.0
    return float(int(math.floor(value + 0.5)))


def _time_plus_hours(t: time, hours: float) -> time:
    return (datetime.combine(date.min, t) + timedelta(hours=hours)).time()


def _profile_blocks(profile: TemplateEmployeeProfile) -> list[tuple[str, time, time, float]]:
    ms = profile.morning_work_start
    if ms is not None:
        t1 = _time_plus_hours(ms, 1.0)
        return [
            ("morning", ms, t1, profile.block_values[0]),
            ("morning", t1, time(12, 0), profile.block_values[1]),
            ("afternoon", time(13, 30), time(15, 30), profile.block_values[2]),
            ("afternoon", time(15, 30), time(17, 30), profile.block_values[3]),
        ]
    first = profile.block_values[0]
    if first <= 1.0:
        return [
            ("morning", time(9, 0), time(10, 0), profile.block_values[0]),
            ("morning", time(10, 0), time(12, 0), profile.block_values[1]),
            ("afternoon", time(13, 30), time(15, 30), profile.block_values[2]),
            ("afternoon", time(15, 30), time(17, 30), profile.block_values[3]),
        ]
    return [
        ("morning", time(8, 0), time(10, 0), profile.block_values[0]),
        ("morning", time(10, 0), time(12, 0), profile.block_values[1]),
        ("afternoon", time(13, 30), time(15, 30), profile.block_values[2]),
        ("afternoon", time(15, 30), time(17, 30), profile.block_values[3]),
    ]


def _default_profile(record: AttendanceDayRecord) -> TemplateEmployeeProfile:
    return TemplateEmployeeProfile(
        employee_name=record.employee_name,
        base_row=-1,
        department=record.department,
        nature_text="",
        block_values=(2.0, 2.0, 2.0, 2.0),
        overtime_start=time(18, 0),
        morning_work_start=None,
    )


def _primary_interval(punches: list[datetime]) -> tuple[datetime, datetime] | None:
    if len(punches) < 2:
        return None
    start = punches[0]
    end = punches[-1]
    return (start, end) if end > start else None


def _work_intervals(punches: list[datetime]) -> list[tuple[datetime, datetime]]:
    """按相邻两卡拆成多段在岗时间（钉钉常见「上班1/下班1/上班2/下班2」）。

    偶数次打卡依次两两配对，午休落在两段之间，不会被单段「首末卡」吞进正班重叠。
    奇数次打卡无法可靠配对，退回首尾单段，与历史 `_primary_interval` 行为一致。
    """
    n = len(punches)
    if n < 2:
        return []
    if n % 2 == 1:
        span = _primary_interval(punches)
        return [span] if span else []
    intervals: list[tuple[datetime, datetime]] = []
    for i in range(0, n, 2):
        start, end = punches[i], punches[i + 1]
        if end > start:
            intervals.append((start, end))
    return intervals


def _clip_work_intervals_to_schedule(
    work_date: date,
    work_intervals: list[tuple[datetime, datetime]],
    schedule_ranges: tuple[TimeRange, ...],
) -> list[tuple[datetime, datetime]]:
    """把实际上班区间与「应计正班的日历时段」求交（如周六配置班段仅 13:30–16:00）。"""
    clipped: list[tuple[datetime, datetime]] = []
    for wi_start, wi_end in work_intervals:
        for sr in schedule_ranges:
            cs = max(wi_start, datetime.combine(work_date, sr.start))
            ce = min(wi_end, datetime.combine(work_date, sr.end))
            if ce > cs:
                clipped.append((cs, ce))
    return clipped


def _saturday_factory_outside_regular_hours(
    work_date: date,
    work_intervals: list[tuple[datetime, datetime]],
    schedule_ranges: tuple[TimeRange, ...],
    *,
    group_name: str | None,
    shift_name: str | None,
) -> float:
    """公司/工厂周六：正班以解析/回退日程为准，窗口外时长计平常加班。"""
    if work_date.weekday() != 5 or not is_company_factory_group(group_name, shift_name):
        return 0.0
    if not schedule_ranges:
        return 0.0
    clipped = _clip_work_intervals_to_schedule(work_date, work_intervals, schedule_ranges)
    total = sum(_hours_between(a, b) for a, b in work_intervals)
    inside = sum(_hours_between(a, b) for a, b in clipped)
    return max(0.0, total - inside)


def _build_full_day_entries(profile: TemplateEmployeeProfile, symbol: str) -> tuple[list[DayBandEntry], list[DayBandEntry]]:
    morning: list[DayBandEntry] = []
    afternoon: list[DayBandEntry] = []
    blocks = _profile_blocks(profile)
    for band, _start, _end, credit in blocks:
        if credit <= 0:
            continue
        entry = DayBandEntry(symbol=symbol, value=credit)
        if band == "morning":
            morning.append(entry)
        else:
            afternoon.append(entry)
    return morning, afternoon


def _interval_entries(
    intervals: list[tuple[datetime, datetime]],
    profile: TemplateEmployeeProfile,
    symbol: str,
) -> tuple[list[DayBandEntry], list[DayBandEntry]]:
    if not intervals:
        return [], []
    morning: list[DayBandEntry] = []
    afternoon: list[DayBandEntry] = []
    for band, block_start, block_end, credit in _profile_blocks(profile):
        total_hours = 0.0
        for start, end in intervals:
            total_hours += _overlap_hours(start, end, block_start, block_end)
        rounded = min(_round_whole_hour(total_hours), credit)
        if rounded <= 0:
            continue
        entry = DayBandEntry(symbol=symbol, value=rounded)
        if band == "morning":
            morning.append(entry)
        else:
            afternoon.append(entry)
    return morning, afternoon


def _night_overtime_entry(
    work_date: date,
    last_punch: datetime | None,
    *,
    symbol: str,
    overtime_start: time,
) -> DayBandEntry | None:
    if last_punch is None:
        return None
    base_dt = datetime.combine(work_date, overtime_start)
    if last_punch <= base_dt:
        return None
    rounded = _round_half_hour(_hours_between(base_dt, last_punch))
    if rounded <= 0:
        return None
    if rounded < 1:
        rounded = 1.0
    return DayBandEntry(symbol=symbol, value=rounded)


def _fixed_night_overtime_entry(
    work_date: date,
    last_punch: datetime | None,
    *,
    symbol: str,
) -> DayBandEntry | None:
    """晚上加班固定从 18:00 起，按最后一次打卡时间结算；零头满 25 分钟进 0.5 小时。"""
    if last_punch is None:
        return None
    base_dt = datetime.combine(work_date, time(18, 0))
    if last_punch <= base_dt:
        return None
    rounded = _round_half_hour_with_25_minute_grace(_hours_between(base_dt, last_punch))
    if rounded <= 0:
        return None
    return DayBandEntry(symbol=symbol, value=rounded)


def _absence_symbol(record: AttendanceDayRecord, absent_streak: int) -> str | None:
    if record.leave_hours > 0:
        return "〇"
    if not record.absent_days:
        return None
    if absent_streak >= 5:
        return "〇"
    if absent_streak >= 3:
        return "〇"
    return None


def _regular_symbol(record: AttendanceDayRecord) -> str:
    shift_text = record.shift_name
    if is_rest_shift(shift_text):
        return "★"
    is_factory_person = (
        "惠州工厂" in record.department
        or "工厂" in record.attendance_group
        or "工厂" in shift_text
    )
    if "公司" in shift_text and is_factory_person and "远程" not in record.attendance_group and "公司-考勤" not in record.attendance_group:
        return "☆"
    return "√"


def _resolved_day_symbol(record: AttendanceDayRecord) -> str:
    """写入明细用的班次符号。周日不计正班：原为正班 √ 或交叉 ☆ 的一律按星期天加班 ★（可关）。"""
    from . import rules as _att_rules

    s = _regular_symbol(record)
    if not _att_rules.ACTIVE_POLICY.get("sunday_map_sqrt_to_star", True):
        return s
    if record.work_date.weekday() == 6 and s in ("√", "☆"):
        return "★"
    return s


def _install_attendance_policy_from_host() -> None:
    try:
        from resources.config.approval_config import get_approval_config

        pol = getattr(get_approval_config(), "attendance_policy", None) or {}
    except Exception:
        pol = {}
    from . import rules as _att_rules

    _att_rules.set_attendance_policy(pol if isinstance(pol, dict) else {})


def _clear_attendance_policy() -> None:
    from . import rules as _att_rules

    _att_rules.set_attendance_policy({})


def _symbol_entry(symbol: str, value: float) -> DayBandEntry | None:
    if value <= 0:
        return None
    return DayBandEntry(symbol=symbol, value=round(value, 2))


def _append_entry(entries: list[DayBandEntry], symbol: str, value: float) -> None:
    entry = _symbol_entry(symbol, value)
    if entry is not None:
        entries.append(entry)


def _build_day_template_data(
    record: AttendanceDayRecord,
    profile: TemplateEmployeeProfile,
    *,
    absent_streak: int,
) -> tuple[EmployeeDayTemplateData, dict[str, float], list[str]]:
    punches = _unique_sorted(record.all_punch_times())
    day_payload = EmployeeDayTemplateData(work_date=record.work_date, notes=list(record.notes))
    work_intervals = _work_intervals(punches)
    symbol = _resolved_day_symbol(record)
    dingtalk_hours = dingtalk_work_hours_as_hours(record.work_duration_raw)
    late_count = 0.0
    early_count = 0.0
    absent_hours = 0.0

    if not punches:
        fill_from_aggregate = (
            not is_rest_shift(record.shift_name)
            and record.leave_hours <= 0
            and (dingtalk_hours >= 6.5 or record.attendance_day_hint >= 1.0)
        )
        if fill_from_aggregate:
            reg = _resolved_day_symbol(record)
            morning, afternoon = _build_full_day_entries(profile, reg)
            day_payload.morning.extend(morning)
            day_payload.afternoon.extend(afternoon)
            day_payload.notes.append(
                f"dingtalk_aggregate_fill hours≈{dingtalk_hours:g} 出勤={record.attendance_day_hint:g}"
            )
        else:
            absence_symbol = _absence_symbol(record, absent_streak)
            if absence_symbol:
                morning, afternoon = _build_full_day_entries(profile, absence_symbol)
                day_payload.morning.extend(morning)
                day_payload.afternoon.extend(afternoon)
                absent_hours = round(sum(e.value for e in morning + afternoon), 2)
    else:
        schedule_ranges: tuple[TimeRange, ...] = ()
        if len(punches) == 1:
            if is_rest_shift(record.shift_name) and record.leave_hours <= 0:
                morning, afternoon = [], []
            else:
                morning, afternoon = _build_full_day_entries(profile, symbol)
        elif not work_intervals:
            morning, afternoon = _build_full_day_entries(profile, symbol)
        else:
            schedule_ranges = resolve_schedule_ranges(
                record.work_date,
                group_name=record.attendance_group,
                shift_name=record.shift_name,
                has_any_punch=True,
            )
            effective_intervals = (
                _clip_work_intervals_to_schedule(record.work_date, work_intervals, schedule_ranges)
                if schedule_ranges
                else work_intervals
            )
            morning, afternoon = _interval_entries(effective_intervals, profile, symbol)
            if not morning and not afternoon:
                if schedule_ranges:
                    pass
                else:
                    morning, afternoon = _build_full_day_entries(profile, symbol)
        day_payload.morning.extend(morning)
        day_payload.afternoon.extend(afternoon)

        night_symbol = "★" if symbol == "★" else "☆"
        night_entry = _fixed_night_overtime_entry(
            record.work_date,
            punches[-1],
            symbol=night_symbol,
        )
        night_total = night_entry.value if night_entry is not None else 0.0
        if night_total > 0:
            day_payload.night.append(DayBandEntry(symbol=night_symbol, value=night_total))

    metrics = {
        "normal_hours": round(
            sum(e.value for e in day_payload.morning + day_payload.afternoon if e.symbol == "√"),
            2,
        ),
        "weekday_overtime_hours": round(
            sum(e.value for e in day_payload.morning + day_payload.afternoon + day_payload.night if e.symbol == "☆"),
            2,
        ),
        "sunday_overtime_hours": round(
            sum(e.value for e in day_payload.morning + day_payload.afternoon + day_payload.night if e.symbol == "★"),
            2,
        ),
        "leave_hours": round(
            sum(e.value for e in day_payload.morning + day_payload.afternoon if e.symbol == "〇"),
            2,
        ),
        "absent_hours": round(absent_hours, 2),
        "late_count": late_count,
        "early_count": early_count,
    }
    warning_notes: list[str] = []
    if record.missing_card_count:
        warning_notes.append(f"缺卡{record.missing_card_count:g}次")
    if (
        not punches
        and dingtalk_hours < 6.5
        and record.attendance_day_hint < 1.0
        and not record.leave_hours
        and not record.absent_days
    ):
        warning_notes.append("无有效打卡")
    if len(punches) >= 3:
        warning_notes.append(f"去重后打卡{len(punches)}次")
    return day_payload, metrics, warning_notes


def _employee_absent_streaks(records: list[AttendanceDayRecord]) -> dict[tuple[str, date], int]:
    streaks: dict[tuple[str, date], int] = {}
    by_name: dict[str, list[AttendanceDayRecord]] = {}
    for record in records:
        by_name.setdefault(record.employee_name, []).append(record)
    for name, items in by_name.items():
        streak = 0
        for record in sorted(items, key=lambda r: r.work_date):
            if not record.all_punch_times() and record.absent_days:
                streak += 1
            else:
                streak = 0
            streaks[(name, record.work_date)] = streak
    return streaks


def _lookup_employee(
    employees: dict[str, EmployeeMonthTemplateData], name: str
) -> EmployeeMonthTemplateData | None:
    key = (name or "").strip()
    if not key:
        return None
    if key in employees:
        return employees[key]
    for ek, ev in employees.items():
        if str(ek).strip() == key:
            return ev
    return None


def _monthly_row_dict_from_payload(payload: EmployeeMonthTemplateData) -> dict[str, object]:
    return {
        "姓名": payload.employee_name,
        "考勤组": payload.attendance_group,
        "部门": payload.department,
        "工号": payload.employee_no,
        "正常上班": round(payload.normal_hours, 2),
        "平常加班": round(payload.weekday_overtime_hours, 2),
        "星期天加班": round(payload.sunday_overtime_hours, 2),
        "请假": round(payload.leave_hours, 2),
        "旷工": round(payload.absent_hours, 2),
        "迟到": round(payload.late_count, 2),
        "早退": round(payload.early_count, 2),
        "警告": "；".join(sorted(set(payload.warnings))),
    }


def _empty_monthly_row(name: str, dept: str = "", group: str = "") -> dict[str, object]:
    return {
        "姓名": name,
        "考勤组": group,
        "部门": dept,
        "工号": "",
        "正常上班": 0.0,
        "平常加班": 0.0,
        "星期天加班": 0.0,
        "请假": 0.0,
        "旷工": 0.0,
        "迟到": 0.0,
        "早退": 0.0,
        "警告": "",
    }


def _build_monthly_rows_for_template(
    employees: dict[str, EmployeeMonthTemplateData],
    personnel_roster: list[tuple[str, str, str]] | None,
    detail_ws,
) -> list[dict[str, object]]:
    """与「明细」每人块顺序一致：按人员管理名单或模板块自上而下；无钉钉汇总仍输出一行（零值），避免月度统计主表与夜班侧栏断行。"""
    if personnel_roster:
        out: list[dict[str, object]] = []
        for dept, _nature, name in personnel_roster:
            raw_name = str(name).strip() if name is not None else ""
            p = _lookup_employee(employees, raw_name)
            if p is not None:
                out.append(_monthly_row_dict_from_payload(p))
            else:
                out.append(_empty_monthly_row(raw_name, dept=str(dept or "").strip()))
        return out

    out: list[dict[str, object]] = []
    for br in iter_detail_sheet_block_base_rows(detail_ws):
        raw = detail_ws.cell(br, 3).value
        raw_name = str(raw).strip() if raw not in (None, "") else ""
        dept = str(detail_ws.cell(br, 1).value or "").strip()
        p = _lookup_employee(employees, raw_name) if raw_name else None
        if p is not None:
            out.append(_monthly_row_dict_from_payload(p))
        elif raw_name:
            out.append(_empty_monthly_row(raw_name, dept=dept))
        else:
            out.append(_empty_monthly_row("", dept=dept))
    return out


def _aggregate_employee_records(
    records: list[AttendanceDayRecord],
    *,
    template_profiles: dict[str, TemplateEmployeeProfile],
) -> tuple[dict[str, EmployeeMonthTemplateData], list[dict[str, object]]]:
    employees: dict[str, EmployeeMonthTemplateData] = {}
    analysis_rows: list[dict[str, object]] = []
    absent_streaks = _employee_absent_streaks(records)

    for record in sorted(records, key=lambda r: (r.employee_name, r.work_date)):
        profile = template_profiles.get(record.employee_name) or _default_profile(record)
        punches = _unique_sorted(record.all_punch_times())
        month_payload = employees.setdefault(
            record.employee_name,
            EmployeeMonthTemplateData(
                employee_name=record.employee_name,
                attendance_group=record.attendance_group,
                department=record.department,
                employee_no=record.employee_no,
            ),
        )
        day_payload, metrics, warnings = _build_day_template_data(
            record,
            profile,
            absent_streak=absent_streaks.get((record.employee_name, record.work_date), 0),
        )
        month_payload.days[record.work_date.day] = day_payload
        month_payload.normal_hours += metrics["normal_hours"]
        month_payload.weekday_overtime_hours += metrics["weekday_overtime_hours"]
        month_payload.sunday_overtime_hours += metrics["sunday_overtime_hours"]
        month_payload.leave_hours += metrics["leave_hours"]
        month_payload.absent_hours += metrics["absent_hours"]
        month_payload.late_count += metrics["late_count"]
        month_payload.early_count += metrics["early_count"]
        month_payload.warnings.extend(warnings)

        analysis_rows.append(
            {
                "姓名": record.employee_name,
                "考勤组": record.attendance_group,
                "部门": record.department,
                "日期": record.work_date.isoformat(),
                "班次": record.shift_name,
                "打卡时间": ", ".join(dt.strftime("%H:%M") for dt in punches),
                "正班工时": round(metrics["normal_hours"], 2),
                "平常加班": round(metrics["weekday_overtime_hours"], 2),
                "星期天加班": round(metrics["sunday_overtime_hours"], 2),
                "请假工时": round(metrics["leave_hours"], 2),
                "旷工工时": round(metrics["absent_hours"], 2),
                "迟到次数": round(metrics["late_count"], 2),
                "早退次数": round(metrics["early_count"], 2),
                "备注": "；".join(record.notes + warnings),
            }
        )

    return employees, analysis_rows


def convert_attendance_records(
    records: list[AttendanceDayRecord],
    output_path: str | Path,
    *,
    template_path: str | Path,
    month_label: str,
    personnel_roster: list[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """将已解析的 ``AttendanceDayRecord`` 列表（如从 SQLite 还原）按与 ``convert_attendance_file`` 相同规则写入明细模板。"""
    out = Path(output_path)
    template = Path(template_path)
    if not records:
        return {"success": False, "error": "no attendance records"}
    _install_attendance_policy_from_host()
    try:
        workbook = open_output_workbook(out, template)
        detail_ws = workbook["明细"] if "明细" in workbook.sheetnames else workbook.active
        if personnel_roster:
            rebuild_detail_sheet_person_blocks(detail_ws, personnel_roster)
        template_profiles = build_template_profiles(detail_ws)
        if not template_profiles:
            return {"success": False, "error": "明细页未解析到任何员工块，请检查固定模板或人员管理名单"}
        filtered = _filter_records_to_template_roster(records, template_profiles)
        if not filtered and not personnel_roster:
            return {
                "success": False,
                "error": "钉钉数据与模板明细中的姓名无交集：请核对模板人员名单与「每日统计」姓名列是否一致（含空格/全半角）。",
            }
        employees, analysis_rows = _aggregate_employee_records(
            filtered,
            template_profiles=template_profiles,
        )
        monthly_rows = _build_monthly_rows_for_template(employees, personnel_roster, detail_ws)
        template_result = write_detail_sheet(
            workbook,
            employees,
            month_label=month_label,
        )
        write_monthly_sheet(workbook, monthly_rows, link_detail_side_totals=True)
        _retain_detail_and_monthly_sheets(workbook)
        output_sheet_names = list(workbook.sheetnames)

        out.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(out)
        workbook.close()

        return {
            "success": True,
            "input": "database",
            "output": str(out),
            "month": month_label,
            "rows_in": len(records),
            "rows_used_for_template": len(filtered),
            "rows_stats": len(analysis_rows),
            "employees_total": len(employees),
            "employees_matched": template_result.matched_employee_count,
            "unmatched_names": template_result.unmatched_employee_names,
            "header_info": None,
            "used_llm": False,
            "personnel_roster_count": len(personnel_roster) if personnel_roster else 0,
            "output_sheet_names": output_sheet_names,
        }
    except Exception as exc:
        logger.exception("Attendance conversion from record list failed")
        return {"success": False, "error": str(exc)}
    finally:
        _clear_attendance_policy()


def convert_attendance_file(
    input_path: str,
    output_path: str | None = None,
    *,
    template_path: str | None = None,
    month: str | None = None,
    header_row: int = 0,
    use_llm: bool | None = None,
    personnel_roster: list[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """把钉钉考勤导出 xlsx 转换为太阳鸟明细模板。

    ``header_row`` 是用户在前端填写的表头所在行（1-based），``0`` 代表自动识别。
    ``use_llm`` 为真时允许在本地规则无法识别必需列时调用 LLM 兜底；
    ``None`` 代表尊重环境变量 ``FHD_ATTENDANCE_LLM``。
    """
    from .header_resolver import llm_enabled_by_env

    if use_llm is None:
        use_llm = llm_enabled_by_env()

    src = Path(input_path)
    if not src.exists():
        return {"success": False, "error": "input file not found"}

    out = Path(output_path) if output_path else src.with_name(src.stem + "_converted.xlsx")
    template = Path(template_path) if template_path else (out if out.exists() else None)

    try:
        parsed = parse_attendance_workbook(
            src,
            month=month,
            header_row=max(0, int(header_row or 0)),
            use_llm=bool(use_llm),
        )
        workbook = open_output_workbook(out, template)
        detail_ws = workbook["明细"] if "明细" in workbook.sheetnames else workbook.active
        if personnel_roster:
            rebuild_detail_sheet_person_blocks(detail_ws, personnel_roster)
        template_profiles = build_template_profiles(detail_ws)
        if not template_profiles:
            return {"success": False, "error": "明细页未解析到任何员工块，请检查固定模板或人员管理名单"}
        filtered = _filter_records_to_template_roster(parsed.records, template_profiles)
        if not filtered and not personnel_roster:
            return {
                "success": False,
                "error": "钉钉数据与模板明细中的姓名无交集：请核对模板人员名单与「每日统计」姓名列是否一致（含空格/全半角）。",
            }
        employees, analysis_rows = _aggregate_employee_records(
            filtered,
            template_profiles=template_profiles,
        )
        monthly_rows = _build_monthly_rows_for_template(employees, personnel_roster, detail_ws)
        template_result = write_detail_sheet(
            workbook,
            employees,
            month_label=month or parsed.month,
        )
        write_monthly_sheet(workbook, monthly_rows, link_detail_side_totals=True)
        _retain_detail_and_monthly_sheets(workbook)
        output_sheet_names = list(workbook.sheetnames)

        out.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(out)
        workbook.close()

        daily_header = parsed.daily_header
        header_info: dict[str, Any] | None = None
        if daily_header is not None:
            header_info = {
                "header_row": daily_header.header_row,
                "data_start_row": daily_header.data_start_row,
                "source": daily_header.source,
                "columns": daily_header.columns,
                "clock_time_columns": daily_header.clock_time_columns,
                "leave_columns": daily_header.leave_columns,
            }

        return {
            "success": True,
            "input": str(src),
            "output": str(out),
            "month": month or parsed.month,
            "rows_in": parsed.rows_in,
            "rows_used_for_template": len(filtered),
            "rows_stats": len(analysis_rows),
            "employees_total": len(employees),
            "employees_matched": template_result.matched_employee_count,
            "unmatched_names": template_result.unmatched_employee_names,
            "header_info": header_info,
            "used_llm": bool(use_llm),
            "personnel_roster_count": len(personnel_roster) if personnel_roster else 0,
            "output_sheet_names": output_sheet_names,
        }
    except Exception as exc:
        logger.exception("Attendance conversion failed")
        return {"success": False, "error": str(exc)}
    finally:
        _clear_attendance_policy()
