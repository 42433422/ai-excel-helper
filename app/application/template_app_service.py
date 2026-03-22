"""
模板应用服务

负责模板管理相关的用例编排
"""

from typing import Any, Dict, List, Optional


class TemplateApplicationService:
    """模板应用服务 - 负责模板相关的用例编排"""

    def __init__(
        self,
        template_service=None,
    ):
        self._template_service = template_service

    def get_templates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模板列表用例

        Args:
            category: 模板分类

        Returns:
            模板列表
        """
        if category and category != 'all':
            return {'templates': self._template_service.list_by_type(category) or []}
        return {'templates': self._template_service.list_templates() or []}

    def get_template(self, template_id: int) -> Dict[str, Any]:
        """
        获取单个模板用例

        Args:
            template_id: 模板 ID

        Returns:
            模板信息
        """
        return self._template_service.get_template(template_id)

    def save_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存模板用例

        Args:
            template_data: 模板数据

        Returns:
            保存结果
        """
        return self._template_service.save_template(template_data)

    def update_template(self, template_id: int, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新模板用例

        Args:
            template_id: 模板 ID
            template_data: 模板数据

        Returns:
            更新结果
        """
        return self._template_service.update_template(template_id, template_data)

    def delete_template(self, template_id: int) -> Dict[str, Any]:
        """
        删除模板用例

        Args:
            template_id: 模板 ID

        Returns:
            删除结果
        """
        return self._template_service.delete_template(template_id)

    def decompose_template(self, file_path: str, template_type: Optional[str] = None) -> Dict[str, Any]:
        """
        分解模板用例

        Args:
            file_path: 模板文件路径
            template_type: 模板类型

        Returns:
            分解结果
        """
        return self._template_service.decompose_template(file_path, template_type)


_template_app_service: Optional[TemplateApplicationService] = None


def get_template_app_service() -> TemplateApplicationService:
    """获取模板应用服务单例 (别名)"""
    return get_template_application_service()


def get_template_application_service() -> TemplateApplicationService:
    """获取模板应用服务单例"""
    global _template_app_service
    if _template_app_service is None:
        import os

        from app.infrastructure.templates.template_store_impl import FileSystemTemplateStore
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _template_app_service = TemplateApplicationService(FileSystemTemplateStore(base_dir=base_dir))
    return _template_app_service


def init_template_app_service(
    template_service=None,
) -> TemplateApplicationService:
    """初始化模板应用服务 (用于依赖注入) (别名)"""
    return init_template_application_service(template_service)


def init_template_application_service(
    template_service=None,
) -> TemplateApplicationService:
    """初始化模板应用服务 (用于依赖注入)"""
    global _template_app_service
    _template_app_service = TemplateApplicationService(
        template_service=template_service
    )
    return _template_app_service
