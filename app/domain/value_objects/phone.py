"""
PhoneNumber 值对象

表示电话号码，支持中国和国际号码格式。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class PhoneType(Enum):
    """电话类型"""

    MOBILE = "mobile"  # 手机号
    LANDLINE = "landline"  # 固定电话
    UNKNOWN = "unknown"  # 未知


@dataclass(frozen=True)
class PhoneNumber:
    """
    电话号码值对象

    支持中国大陆手机号和部分固定电话格式。
    自动标准化为纯数字格式。

    Examples:
        >>> phone = PhoneNumber("138-1234-5678")
        >>> phone.formatted  # "13812345678"
        >>> phone.masked    # "138****5678"
    """

    number: str
    country_code: str | None = None  # 国家码，如 "+86"

    # 手机号正则
    _MOBILE_REGEX = re.compile(r"^1[3-9]\d{9}$")
    # 固定电话正则（简化版）
    _LANDLINE_REGEX = re.compile(r"^(0\d{2,3})?-?\d{7,8}$")

    def __post_init__(self):
        # 标准化：去除所有非数字字符
        cleaned = re.sub(r"\D", "", self.number)

        # 处理国家码
        country_code = self.country_code
        if cleaned.startswith("86") and len(cleaned) == 13:
            # 自动识别国家码
            country_code = "+86"
            cleaned = cleaned[2:]

        object.__setattr__(self, "number", cleaned)
        if country_code:
            object.__setattr__(self, "country_code", country_code)

        # 验证长度
        if len(cleaned) not in [7, 8, 11]:
            raise ValueError(f"Invalid phone number length: {len(cleaned)}")

    @property
    def phone_type(self) -> PhoneType:
        """判断电话类型"""
        if self._MOBILE_REGEX.match(self.number):
            return PhoneType.MOBILE
        elif self._LANDLINE_REGEX.match(self.number):
            return PhoneType.LANDLINE
        return PhoneType.UNKNOWN

    @property
    def is_mobile(self) -> bool:
        """是否为手机号"""
        return self.phone_type == PhoneType.MOBILE

    @property
    def is_landline(self) -> bool:
        """是否为固定电话"""
        return self.phone_type == PhoneType.LANDLINE

    @property
    def formatted(self) -> str:
        """格式化显示"""
        if self.is_mobile and len(self.number) == 11:
            # 138-1234-5678
            return f"{self.number[:3]}-{self.number[3:7]}-{self.number[7:]}"
        return self.number

    @property
    def masked(self) -> str:
        """脱敏显示（如 138****5678）"""
        if self.is_mobile and len(self.number) == 11:
            return f"{self.number[:3]}****{self.number[7:]}"
        elif len(self.number) >= 7:
            return f"{self.number[:3]}****{self.number[-3:]}"
        return "****"

    @property
    def full_number(self) -> str:
        """带国家码的完整号码"""
        if self.country_code:
            return f"{self.country_code}{self.number}"
        return self.number

    @classmethod
    def is_valid(cls, number: str) -> bool:
        """验证号码格式是否有效"""
        if not number:
            return False
        cleaned = re.sub(r"\D", "", number)
        # 去除可能的国家码前缀
        if cleaned.startswith("86") and len(cleaned) == 13:
            cleaned = cleaned[2:]
        return bool(cls._MOBILE_REGEX.match(cleaned) or cls._LANDLINE_REGEX.match(cleaned))

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "country_code": self.country_code,
            "formatted": self.formatted,
            "type": self.phone_type.value,
            "is_mobile": self.is_mobile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PhoneNumber:
        return cls(number=data["number"], country_code=data.get("country_code"))

    def __str__(self) -> str:
        return self.formatted

    def __repr__(self) -> str:
        return f"PhoneNumber(number={self.number})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, PhoneNumber):
            return False
        return self.number == other.number

    def __hash__(self) -> int:
        return hash(self.number)
