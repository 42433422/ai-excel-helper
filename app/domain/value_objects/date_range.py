"""
DateRange 值对象

表示日期时间范围，用于报表、查询等场景。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class DateRange:
    """
    日期范围值对象

    包含开始和结束日期，确保结束日期不早于开始日期。
    """

    start: date
    end: date

    def __post_init__(self):
        # 确保 start 和 end 是 date 类型
        if isinstance(self.start, datetime):
            object.__setattr__(self, "start", self.start.date())
        if isinstance(self.end, datetime):
            object.__setattr__(self, "end", self.end.date())

        # 验证：结束日期不能早于开始日期
        if self.end < self.start:
            raise ValueError(f"End date {self.end} cannot be before start date {self.start}")

    @classmethod
    def from_datetime(cls, start: datetime, end: datetime) -> DateRange:
        """从 datetime 创建"""
        return cls(start.date(), end.date())

    @classmethod
    def from_strings(cls, start_str: str, end_str: str, fmt: str = "%Y-%m-%d") -> DateRange:
        """从字符串创建"""
        start = datetime.strptime(start_str, fmt).date()
        end = datetime.strptime(end_str, fmt).date()
        return cls(start, end)

    @classmethod
    def today(cls) -> DateRange:
        """今天"""
        today = date.today()
        return cls(today, today)

    @classmethod
    def this_week(cls) -> DateRange:
        """本周"""
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return cls(start, end)

    @classmethod
    def this_month(cls) -> DateRange:
        """本月"""
        today = date.today()
        start = today.replace(day=1)
        # 下月第一天减一天
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return cls(start, end)

    @classmethod
    def this_year(cls) -> DateRange:
        """本年"""
        today = date.today()
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
        return cls(start, end)

    @classmethod
    def last_n_days(cls, n: int) -> DateRange:
        """最近 N 天"""
        end = date.today()
        start = end - timedelta(days=n - 1)
        return cls(start, end)

    @property
    def days(self) -> int:
        """天数（包含首尾）"""
        return (self.end - self.start).days + 1

    @property
    def is_single_day(self) -> bool:
        """是否为单日"""
        return self.start == self.end

    def contains(self, target: date) -> bool:
        """是否包含指定日期"""
        return self.start <= target <= self.end

    def overlaps(self, other: DateRange) -> bool:
        """是否与另一个范围重叠"""
        return not (self.end < other.start or self.start > other.end)

    def intersection(self, other: DateRange) -> DateRange | None:
        """求交集"""
        if not self.overlaps(other):
            return None
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return DateRange(start, end)

    def union(self, other: DateRange) -> DateRange:
        """求并集（最小范围包含两者）"""
        start = min(self.start, other.start)
        end = max(self.end, other.end)
        return DateRange(start, end)

    def extend(self, days: int) -> DateRange:
        """向后延长 N 天"""
        new_end = self.end + timedelta(days=days)
        return DateRange(self.start, new_end)

    def shift(self, days: int) -> DateRange:
        """整体平移 N 天"""
        new_start = self.start + timedelta(days=days)
        new_end = self.end + timedelta(days=days)
        return DateRange(new_start, new_end)

    def split_by_month(self) -> list[DateRange]:
        """按月分割"""
        ranges = []
        current = self.start.replace(day=1)

        while current <= self.end:
            # 当月最后一天
            if current.month == 12:
                month_end = current.replace(year=current.year + 1, month=1, day=1) - timedelta(
                    days=1
                )
            else:
                month_end = current.replace(month=current.month + 1, day=1) - timedelta(days=1)

            # 裁剪到原始范围
            range_start = max(current, self.start)
            range_end = min(month_end, self.end)

            if range_start <= range_end:
                ranges.append(DateRange(range_start, range_end))

            # 下月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

        return ranges

    def to_datetime_range(self) -> tuple[datetime, datetime]:
        """转换为 datetime 范围（开始到结束当天的23:59:59）"""
        start = datetime.combine(self.start, datetime.min.time())
        end = datetime.combine(self.end, datetime.max.time().replace(microsecond=0))
        return start, end

    def to_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "days": self.days}

    @classmethod
    def from_dict(cls, data: dict) -> DateRange:
        return cls(start=date.fromisoformat(data["start"]), end=date.fromisoformat(data["end"]))

    def __str__(self) -> str:
        return f"{self.start} ~ {self.end}"

    def __repr__(self) -> str:
        return f"DateRange(start={self.start}, end={self.end})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, DateRange):
            return False
        return self.start == other.start and self.end == other.end

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __len__(self) -> int:
        return self.days
