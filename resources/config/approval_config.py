from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

import yaml

# 钉钉→太阳鸟明细：与 ``taiyangniao_attendance.rules`` 默认值对齐；在太阳鸟 Mod「考勤设置」页修改。
DEFAULT_ATTENDANCE_POLICY: Dict[str, Any] = {
    "company_factory_group_keywords": [
        "公司-考勤",
        "公司正班",
        "惠州工厂-正班",
        "工厂正班",
    ],
    "weekday_segments": ["08:00-12:00", "13:30-17:30"],
    "sunday_empty_schedule": True,
    "sunday_map_sqrt_to_star": True,
}


_NESTED_ATTENDANCE_KEYS = frozenset()


def _merge_attendance_policy(raw: Any) -> Dict[str, Any]:
    base = copy.deepcopy(DEFAULT_ATTENDANCE_POLICY)
    if not isinstance(raw, dict):
        return base
    for k, v in raw.items():
        if k not in base or v is None:
            continue
        if k in _NESTED_ATTENDANCE_KEYS and isinstance(v, dict) and isinstance(base.get(k), dict):
            inner = copy.deepcopy(DEFAULT_ATTENDANCE_POLICY[k])
            inner.update(v)
            base[k] = inner
        else:
            base[k] = v
    return base


def normalize_attendance_policy(raw: Any) -> Dict[str, Any]:
    """供 API 写入前归一化，丢弃未知键、补默认。"""
    return _merge_attendance_policy(raw if isinstance(raw, dict) else {})


class ApprovalConfig:
    def __init__(
        self,
        rules: List[Dict[str, Any]],
        enabled: bool = True,
        attendance_policy: Optional[Dict[str, Any]] = None,
    ):
        self.rules = rules
        self.enabled = enabled
        self.attendance_policy = _merge_attendance_policy(attendance_policy)

    @staticmethod
    def _get_config_path() -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "resources", "config", "approval_config.yaml")

    @classmethod
    def load(cls) -> "ApprovalConfig":
        config_path = cls._get_config_path()
        if not os.path.exists(config_path):
            return cls._default_config()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(
                rules=data.get("approval_rules", []),
                enabled=data.get("enabled", True),
                attendance_policy=data.get("attendance_policy"),
            )
        except Exception:
            return cls._default_config()

    @classmethod
    def _default_config(cls) -> "ApprovalConfig":
        return cls(
            enabled=True,
            attendance_policy=copy.deepcopy(DEFAULT_ATTENDANCE_POLICY),
            rules=[
                {
                    "tool_id": "shipment_generate",
                    "action": "execute",
                    "trigger": "always",
                    "description": "发货单生成需要审批",
                    "conditions": {},
                },
                {
                    "tool_id": "print",
                    "action": "execute",
                    "trigger": "always",
                    "description": "打印操作需要审批",
                    "conditions": {},
                },
                {
                    "tool_id": "products",
                    "action": "create",
                    "trigger": "always",
                    "description": "创建产品需要审批",
                    "conditions": {},
                },
                {
                    "tool_id": "products",
                    "action": "delete",
                    "trigger": "always",
                    "description": "删除产品需要审批",
                    "conditions": {},
                },
                {
                    "tool_id": "customers",
                    "action": "create",
                    "trigger": "always",
                    "description": "创建客户需要审批",
                    "conditions": {},
                },
            ],
        )

    def save(self) -> None:
        config_path = self._get_config_path()
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = {
            "enabled": self.enabled,
            "approval_rules": self.rules,
            "attendance_policy": self.attendance_policy,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


_approval_config: Optional[ApprovalConfig] = None


def get_approval_config() -> ApprovalConfig:
    global _approval_config
    if _approval_config is None:
        _approval_config = ApprovalConfig.load()
    return _approval_config


def reload_approval_config() -> ApprovalConfig:
    global _approval_config
    _approval_config = ApprovalConfig.load()
    return _approval_config
