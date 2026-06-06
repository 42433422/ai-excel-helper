"""
Address 和 ContactInfo 值对象

用于表示地址和联系信息。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    """
    地址值对象

    包含完整的地理位置信息。
    """

    province: str  # 省/直辖市
    city: str  # 市
    district: str | None = None  # 区/县
    street: str | None = None  # 街道
    detail: str | None = None  # 详细地址
    zip_code: str | None = None  # 邮编

    def __post_init__(self):
        # 标准化：去除空格
        object.__setattr__(self, "province", self.province.strip() if self.province else "")
        object.__setattr__(self, "city", self.city.strip() if self.city else "")
        object.__setattr__(self, "district", self.district.strip() if self.district else None)
        object.__setattr__(self, "street", self.street.strip() if self.street else None)
        object.__setattr__(self, "detail", self.detail.strip() if self.detail else None)
        object.__setattr__(self, "zip_code", self.zip_code.strip() if self.zip_code else None)

    @classmethod
    def from_string(cls, address_str: str) -> Address:
        """从字符串解析地址（简化版）"""
        parts = address_str.split()
        if len(parts) >= 2:
            return cls(province=parts[0], city=parts[1])
        return cls(province=address_str, city="")

    def to_full_string(self) -> str:
        """转换为完整地址字符串"""
        parts = [self.province, self.city]
        if self.district:
            parts.append(self.district)
        if self.street:
            parts.append(self.street)
        if self.detail:
            parts.append(self.detail)
        return "".join(parts)

    def to_short_string(self) -> str:
        """转换为简短地址"""
        parts = [self.province, self.city]
        if self.district:
            parts.append(self.district)
        return "".join(parts)

    def to_dict(self) -> dict:
        return {
            "province": self.province,
            "city": self.city,
            "district": self.district,
            "street": self.street,
            "detail": self.detail,
            "zip_code": self.zip_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Address:
        return cls(
            province=data.get("province", ""),
            city=data.get("city", ""),
            district=data.get("district"),
            street=data.get("street"),
            detail=data.get("detail"),
            zip_code=data.get("zip_code"),
        )

    def __str__(self) -> str:
        return self.to_full_string()

    def __repr__(self) -> str:
        return f"Address(province={self.province}, city={self.city})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Address):
            return False
        return (
            self.province == other.province
            and self.city == other.city
            and self.district == other.district
            and self.street == other.street
            and self.detail == other.detail
        )

    def __hash__(self) -> int:
        return hash((self.province, self.city, self.district, self.street, self.detail))


@dataclass(frozen=True)
class ContactInfo:
    """
    联系信息值对象

    整合地址、联系人、电话、邮箱等信息。
    """

    name: str  # 联系人姓名
    phone: str | None = None  # 电话
    email: str | None = None  # 邮箱
    address: Address | None = None  # 地址
    company: str | None = None  # 公司名称

    def __post_init__(self):
        object.__setattr__(self, "name", self.name.strip() if self.name else "")
        object.__setattr__(self, "phone", self.phone.strip() if self.phone else None)
        object.__setattr__(self, "email", self.email.strip() if self.email else None)
        object.__setattr__(self, "company", self.company.strip() if self.company else None)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "address": self.address.to_dict() if self.address else None,
            "company": self.company,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContactInfo:
        address = None
        if data.get("address"):
            address = Address.from_dict(data["address"])
        return cls(
            name=data.get("name", ""),
            phone=data.get("phone"),
            email=data.get("email"),
            address=address,
            company=data.get("company"),
        )

    def __str__(self) -> str:
        parts = [self.name]
        if self.phone:
            parts.append(f"电话:{self.phone}")
        if self.email:
            parts.append(f"邮箱:{self.email}")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"ContactInfo(name={self.name}, phone={self.phone})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, ContactInfo):
            return False
        return self.name == other.name and self.phone == other.phone and self.email == other.email

    def __hash__(self) -> int:
        return hash((self.name, self.phone, self.email))
