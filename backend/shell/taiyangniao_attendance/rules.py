"""考勤规则模块 - 实现大小周等考勤规则。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd


class WeekType(Enum):
    """周类型：大周或小周。"""
    BIG = "大周"
    SMALL = "小周"


@dataclass
class AttendanceRule:
    """考勤规则配置。"""
    # 考勤组名称
    group_name: str = ""
    # 大小周规则
    enable_big_small_week: bool = True
    # 周六有效打卡窗口（上班不晚于此时刻、下班不早于此时刻，见 check_saturday_work_time）
    saturday_start_hour: int = 13
    saturday_start_minute: int = 30
    saturday_end_hour: int = 16
    saturday_end_minute: int = 30
    # 小周周六可以选择休息
    small_week_saturday_can_rest: bool = True
    # 大周周六必须工作
    big_week_saturday_must_work: bool = True
    # 工作日上班时间
    weekday_start_hour: int = 9
    weekday_start_minute: int = 0
    weekday_end_hour: int = 17
    weekday_end_minute: int = 30


# 预定义的考勤组规则（键名与钉钉「考勤组」名称一致或去空白后一致）
ATTENDANCE_GROUP_RULES: dict[str, AttendanceRule] = {
    "惠州工厂-正班": AttendanceRule(
        group_name="惠州工厂-正班",
        enable_big_small_week=True,
        # 周六与工作日同为工厂正班，有效覆盖时段取整日窗
        saturday_start_hour=8,
        saturday_start_minute=0,
        saturday_end_hour=17,
        saturday_end_minute=30,
        big_week_saturday_must_work=True,
        small_week_saturday_can_rest=True,
        weekday_start_hour=8,
        weekday_start_minute=0,
        weekday_end_hour=17,
        weekday_end_minute=30,
    ),
    "公司-考勤": AttendanceRule(
        group_name="公司-考勤",
        enable_big_small_week=True,
        saturday_start_hour=9,
        saturday_start_minute=0,
        saturday_end_hour=16,
        saturday_end_minute=0,
        big_week_saturday_must_work=True,
        small_week_saturday_can_rest=True,
        weekday_start_hour=9,
        weekday_start_minute=0,
        weekday_end_hour=17,
        weekday_end_minute=30,
    ),
    "食堂员工": AttendanceRule(
        group_name="食堂员工",
        enable_big_small_week=True,
        saturday_start_hour=7,
        saturday_start_minute=30,
        saturday_end_hour=18,
        saturday_end_minute=0,
        big_week_saturday_must_work=True,
        small_week_saturday_can_rest=True,
        weekday_start_hour=7,
        weekday_start_minute=30,
        weekday_end_hour=18,
        weekday_end_minute=0,
    ),
}

# 钉钉后台「固定班制」展示文案（与界面一致，仅供前端对照；逻辑以 ATTENDANCE_GROUP_RULES 为准）
ATTENDANCE_GROUP_SCHEDULES: list[dict[str, Any]] = [
    {
        "name": "惠州工厂-正班",
        "headcount": "65人",
        "shift_type": "固定班制",
        "lines": [
            "周日 休息",
            "周一、周二、周三、周四、周五、周六 工厂正班: 08:00-12:00 13:30-17:30",
        ],
    },
    {
        "name": "公司-考勤",
        "headcount": "17人",
        "shift_type": "固定班制",
        "lines": [
            "周日 休息",
            "周六 公司周六考勤: 09:00-16:00",
            "周一、周二、周三、周四、周五 公司正班: 09:00-17:30",
        ],
    },
    {
        "name": "食堂员工",
        "headcount": "1人",
        "shift_type": "固定班制",
        "lines": [
            "周日 休息",
            "周一、周二、周三、周四、周五、周六 工厂食堂员工: 07:30-18:00",
        ],
    },
]


def _normalize_group_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "").strip())


def get_rule_for_group(group_name: str) -> AttendanceRule:
    """根据考勤组名称获取对应的规则（忽略空白差异，如「惠州工厂 - 正班」）。"""
    raw = str(group_name or "").strip()
    if raw in ATTENDANCE_GROUP_RULES:
        return ATTENDANCE_GROUP_RULES[raw]
    compact = _normalize_group_name(raw)
    if not compact:
        return AttendanceRule()
    for key, rule in ATTENDANCE_GROUP_RULES.items():
        if _normalize_group_name(key) == compact:
            return rule
    return AttendanceRule()


@dataclass
class AttendanceCheckResult:
    """考勤检查结果。"""
    employee_name: str
    employee_id: str
    date: str
    week_type: Optional[WeekType] = None
    is_saturday: bool = False
    has_check_in: bool = False
    has_check_out: bool = False
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    saturday_work_valid: bool = False
    rule_violation: Optional[str] = None
    remarks: str = ""


def determine_week_type(date_str: str, base_date: Optional[str] = None) -> WeekType:
    """根据日期确定是大周还是小周。
    
    Args:
        date_str: 日期字符串，格式为 YYYY-MM-DD
        base_date: 基准日期，用于确定大小周起始点
    
    Returns:
        WeekType: 大周或小周
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return WeekType.BIG
    
    if base_date:
        try:
            base = datetime.strptime(base_date, "%Y-%m-%d")
        except ValueError:
            base = datetime(2024, 1, 1)
    else:
        base = datetime(2024, 1, 1)
    
    days_diff = (date - base).days
    week_num = days_diff // 7
    
    if week_num % 2 == 0:
        return WeekType.BIG
    else:
        return WeekType.SMALL


def is_saturday(date_str: str) -> bool:
    """判断是否为周六。"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date.weekday() == 5
    except ValueError:
        return False


def check_saturday_work_time(
    check_in: Optional[datetime],
    check_out: Optional[datetime],
    rule: Optional[AttendanceRule] = None,
) -> bool:
    """检查周六工作时间是否符合要求（13:30-16:30）。
    
    Args:
        check_in: 上班打卡时间
        check_out: 下班打卡时间
        rule: 考勤规则
    
    Returns:
        bool: 是否符合要求
    """
    if rule is None:
        rule = AttendanceRule()
    
    if check_in is None or check_out is None:
        return False
    
    start_time = check_in.replace(
        hour=rule.saturday_start_hour,
        minute=rule.saturday_start_minute,
        second=0,
        microsecond=0
    )
    end_time = check_out.replace(
        hour=rule.saturday_end_hour,
        minute=rule.saturday_end_minute,
        second=0,
        microsecond=0
    )
    
    check_in_time = check_in.replace(year=1900, month=1, day=1)
    check_out_time = check_out.replace(year=1900, month=1, day=1)
    start_cmp = start_time.replace(year=1900, month=1, day=1)
    end_cmp = end_time.replace(year=1900, month=1, day=1)
    
    return check_in_time <= start_cmp and check_out_time >= end_cmp


def check_attendance_record(
    record: dict[str, Any],
    rule: Optional[AttendanceRule] = None,
    base_date: Optional[str] = None,
) -> AttendanceCheckResult:
    """检查单条考勤记录是否符合规则。
    
    Args:
        record: 考勤记录字典
        rule: 考勤规则（如果提供则优先使用）
        base_date: 基准日期
    
    Returns:
        AttendanceCheckResult: 检查结果
    """
    date_str = str(record.get("日期", ""))
    emp_name = str(record.get("姓名", ""))
    emp_id = str(record.get("工号", ""))
    group_key = str(record.get("考勤组") or record.get("部门") or "").strip()

    # 如果没有提供规则，则根据考勤组 / 部门列自动选择
    if rule is None:
        rule = get_rule_for_group(group_key)
    
    result = AttendanceCheckResult(
        employee_name=emp_name,
        employee_id=emp_id,
        date=date_str,
    )
    
    if rule.enable_big_small_week:
        result.week_type = determine_week_type(date_str, base_date)
    
    result.is_saturday = is_saturday(date_str)
    
    check_in = record.get("上班打卡")
    check_out = record.get("下班打卡")
    
    result.has_check_in = check_in is not None and pd.notna(check_in)
    result.has_check_out = check_out is not None and pd.notna(check_out)
    
    if result.has_check_in:
        result.check_in_time = check_in
    if result.has_check_out:
        result.check_out_time = check_out
    
    if result.is_saturday and result.has_check_in and result.has_check_out:
        result.saturday_work_valid = check_saturday_work_time(
            result.check_in_time,
            result.check_out_time,
            rule
        )
    
    if rule.enable_big_small_week and result.is_saturday:
        if result.week_type == WeekType.BIG and rule.big_week_saturday_must_work:
            if not result.saturday_work_valid:
                sh = f"{rule.saturday_start_hour:02d}:{rule.saturday_start_minute:02d}"
                eh = f"{rule.saturday_end_hour:02d}:{rule.saturday_end_minute:02d}"
                result.rule_violation = f"大周周六必须在{sh}-{eh}之间工作"
                result.remarks = "不符合大周周六工作要求"
        elif result.week_type == WeekType.SMALL and rule.small_week_saturday_can_rest:
            if not result.has_check_in or not result.has_check_out:
                result.remarks = "小周周六可以休息"
    
    return result


def process_attendance_dataframe(
    df: pd.DataFrame,
    rule: Optional[AttendanceRule] = None,
    base_date: Optional[str] = None,
) -> pd.DataFrame:
    """处理整个考勤 DataFrame，添加规则检查结果。
    
    Args:
        df: 考勤数据 DataFrame
        rule: 考勤规则（如果提供则对所有记录使用此规则）
        base_date: 基准日期
    
    Returns:
        pd.DataFrame: 添加了规则检查结果的 DataFrame
    """
    results = []
    for _, record in df.iterrows():
        # 如果提供了 rule 参数，则使用提供的规则；否则让 check_attendance_record 自动选择
        check_result = check_attendance_record(record.to_dict(), rule=rule, base_date=base_date)
        gkey = str(record.get("考勤组") or record.get("部门") or "").strip()
        results.append({
            "考勤组": gkey,
            "周类型": check_result.week_type.value if check_result.week_type else "",
            "是否周六": "是" if check_result.is_saturday else "否",
            "周六工作有效": "是" if check_result.saturday_work_valid else "否",
            "规则违规": check_result.rule_violation or "",
            "备注": check_result.remarks,
        })
    
    result_df = pd.DataFrame(results)
    return pd.concat([df, result_df], axis=1)
