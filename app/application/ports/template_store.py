from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class TemplateStorePort(ABC):
    """模板库端口（Port）。

    单一来源：所有模板的“列出/取文件/保存”都必须通过这个端口完成。
    """

    @abstractmethod
    def list_templates(self) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def resolve_template_file(self, template_id: str) -> Optional[str]:
        """根据 template_id 返回模板文件路径（不存在返回 None）。"""
        raise NotImplementedError

    @abstractmethod
    def save_template_file(self, source_name: str, target_name: str, overwrite: bool) -> Dict:
        """把某个源文件保存成目标模板文件（用于“保存发货单模板.xlsx”）。"""
        raise NotImplementedError

    @abstractmethod
    def list_by_type(self, template_type: str, active_only: bool = True) -> List[Dict]:
        """按 template_type 查询模板列表（可选只看 is_active=1）。"""
        raise NotImplementedError

    @abstractmethod
    def get_default_for_type(self, template_type: str) -> Optional[Dict]:
        """返回某个类型当前默认模板（例如最新 is_active=1 且 original_file_path 存在的那条）。"""
        raise NotImplementedError

