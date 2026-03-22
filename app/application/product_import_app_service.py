"""
产品导入应用服务

负责产品导入相关的用例编排
"""

from typing import Any, Dict, List, Optional

from app.services import ProductImportService, get_product_import_service


class ProductImportApplicationService:
    """产品导入应用服务 - 负责产品导入相关的用例编排"""

    def __init__(
        self,
        product_import_service: Optional[ProductImportService] = None,
    ):
        self._product_import_service = product_import_service or get_product_import_service()

    def import_from_file(self, file_path: str, unit_name: str) -> Dict[str, Any]:
        """
        从文件导入产品用例

        Args:
            file_path: 文件路径
            unit_name: 单位名称

        Returns:
            导入结果
        """
        return self._product_import_service.import_products_from_excel(file_path, unit_name)

    def import_from_data(self, products: List[Dict[str, Any]], unit_name: str) -> Dict[str, Any]:
        """
        从数据导入产品用例

        Args:
            products: 产品数据列表
            unit_name: 单位名称

        Returns:
            导入结果
        """
        return self._product_import_service.batch_add_products(products, unit_name)

    def validate_import_data(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证导入数据用例

        Args:
            products: 产品数据列表

        Returns:
            验证结果
        """
        return self._product_import_service.validate_products(products)

    def get_import_history(
        self,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取导入历史用例

        Args:
            page: 页码
            per_page: 每页数量

        Returns:
            导入历史和分页信息
        """
        return self._product_import_service.get_import_history(
            page=page,
            per_page=per_page
        )


_product_import_app_service: Optional[ProductImportApplicationService] = None


def get_product_import_app_service() -> ProductImportApplicationService:
    """获取产品导入应用服务单例 (别名)"""
    return get_product_import_application_service()


def get_product_import_application_service() -> ProductImportApplicationService:
    """获取产品导入应用服务单例"""
    global _product_import_app_service
    if _product_import_app_service is None:
        _product_import_app_service = ProductImportApplicationService()
    return _product_import_app_service


def init_product_import_app_service(
    product_import_service: ProductImportService,
) -> ProductImportApplicationService:
    """初始化产品导入应用服务 (用于依赖注入) (别名)"""
    return init_product_import_application_service(product_import_service)


def init_product_import_application_service(
    product_import_service: ProductImportService,
) -> ProductImportApplicationService:
    """初始化产品导入应用服务 (用于依赖注入)"""
    global _product_import_app_service
    _product_import_app_service = ProductImportApplicationService(
        product_import_service=product_import_service
    )
    return _product_import_app_service
