"""
Email 值对象

表示邮箱地址，包含格式验证。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """
    邮箱值对象

    自动验证邮箱格式。

    Examples:
        >>> email = Email("user@example.com")
        >>> email.domain  # "example.com"
    """

    address: str

    # 简单邮箱验证正则
    _EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __post_init__(self):
        # 标准化：小写并去除空格
        normalized = self.address.strip().lower()
        object.__setattr__(self, "address", normalized)

        # 验证格式
        if not self._EMAIL_REGEX.match(normalized):
            raise ValueError(f"Invalid email format: {self.address}")

    @property
    def domain(self) -> str:
        """获取域名部分"""
        return self.address.split("@")[1]

    @property
    def local_part(self) -> str:
        """获取用户名部分"""
        return self.address.split("@")[0]

    @classmethod
    def is_valid(cls, address: str) -> bool:
        """验证邮箱格式是否有效"""
        if not address:
            return False
        return bool(cls._EMAIL_REGEX.match(address.strip().lower()))

    def to_dict(self) -> dict:
        return {"address": self.address, "domain": self.domain, "local_part": self.local_part}

    @classmethod
    def from_dict(cls, data: dict) -> Email:
        return cls(data["address"])

    def __str__(self) -> str:
        return self.address

    def __repr__(self) -> str:
        return f"Email(address={self.address})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Email):
            return False
        return self.address == other.address

    def __hash__(self) -> int:
        return hash(self.address)
