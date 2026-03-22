"""
产品应用服务

负责产品管理相关的用例编排，包括产品查询、创建、更新、删除、导入等
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.services import PrinterService, ProductsService


class ProductApplicationService:
    """产品应用服务 - 负责产品相关的用例编排"""

    def __init__(
        self,
        products_service: Optional["ProductsService"] = None,
        printer_service: Optional["PrinterService"] = None,
    ):
        from app.services import get_printer_service, get_products_service
        self._products_service = products_service or get_products_service()
        self._printer_service = printer_service or get_printer_service()

    def get_product_units(self) -> Dict[str, Any]:
        """
        获取产品单位列表用例

        Returns:
            单位列表
        """
        return self._products_service.get_product_units()

    def get_products(
        self,
        unit: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取产品列表用例

        Args:
            unit: 单位名称筛选
            keyword: 搜索关键词
            page: 页码
            per_page: 每页数量

        Returns:
            产品列表和分页信息
        """
        return self._products_service.get_products(
            unit_name=unit,
            keyword=keyword,
            page=page,
            per_page=per_page
        )

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        获取单个产品用例

        Args:
            product_id: 产品 ID

        Returns:
            产品信息
        """
        return self._products_service.get_product(product_id)

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建产品用例

        Args:
            data: 产品数据，包含：
                - unit_name: 单位名称
                - product_name: 产品名称
                - price: 价格
                - description: 描述（可选）

        Returns:
            创建结果
        """
        product_name = data.get("product_name") or data.get("name")

        if not product_name:
            return {
                "success": False,
                "message": "产品名称不能为空"
            }

        if "price" in data and data["price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        result = self._products_service.create_product(data)

        if result.get("success"):
            self._log_action("create_product", product_id=result.get("product_id"), data=data)

        return result

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新产品用例

        Args:
            product_id: 产品 ID
            data: 更新数据

        Returns:
            更新结果
        """
        if "price" in data and data["price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        result = self._products_service.update_product(product_id, data)

        if result.get("success"):
            self._log_action("update_product", product_id=product_id, data=data)

        return result

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """
        删除产品用例 (软删除)

        Args:
            product_id: 产品 ID

        Returns:
            删除结果
        """
        result = self._products_service.delete_product(product_id)

        if result.get("success"):
            self._log_action("delete_product", product_id=product_id)

        return result

    def import_products_from_excel(self, file_path: str, unit_name: str) -> Dict[str, Any]:
        """
        从 Excel 导入产品用例

        Args:
            file_path: Excel 文件路径
            unit_name: 单位名称

        Returns:
            导入结果
        """
        result = self._products_service.import_products_from_excel(file_path, unit_name)

        if result.get("success"):
            self._log_action("import_products", count=result.get("count", 0), unit_name=unit_name)

        return result

    def get_product_labels(
        self,
        product_id: int,
        quantity: int = 1,
        label_type: str = "default"
    ) -> Dict[str, Any]:
        """
        获取产品标签用例

        Args:
            product_id: 产品 ID
            quantity: 标签数量
            label_type: 标签类型

        Returns:
            标签数据
        """
        product_result = self._products_service.get_product(product_id)

        if not product_result.get("success"):
            return product_result

        product = product_result.get("data")

        label_data = {
            "product_id": product_id,
            "product_name": product.get("name"),
            "model_number": product.get("model_number"),
            "specification": product.get("specification"),
            "unit": product.get("unit"),
            "quantity": quantity,
            "label_type": label_type
        }

        return {
            "success": True,
            "data": label_data
        }

    def print_product_labels(
        self,
        product_id: int,
        quantity: int = 1,
        label_type: str = "default"
    ) -> Dict[str, Any]:
        """
        打印产品标签用例

        Args:
            product_id: 产品 ID
            quantity: 标签数量
            label_type: 标签类型

        Returns:
            打印结果
        """
        label_result = self.get_product_labels(product_id, quantity, label_type)

        if not label_result.get("success"):
            return label_result

        label_data = label_result.get("data")

        return self._printer_service.print_labels([label_data])

    def search_products(
        self,
        keyword: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        高级产品搜索用例

        Args:
            keyword: 搜索关键词
            filters: 额外筛选条件

        Returns:
            搜索结果
        """
        filters = filters or {}

        return self._products_service.get_products(
            unit=filters.get("unit"),
            keyword=keyword,
            page=filters.get("page", 1),
            per_page=filters.get("per_page", 20)
        )

    def get_product_statistics(self, unit: Optional[str] = None) -> Dict[str, Any]:
        """
        获取产品统计信息用例

        Args:
            unit: 单位名称筛选

        Returns:
            统计信息
        """
        result = self._products_service.get_products(unit_name=unit, page=1, per_page=1)
        total = result.get("total", 0)

        return {
            "success": True,
            "data": {
                "total_products": total,
                "unit": unit or "全部",
                "statistics_time": datetime.now().isoformat()
            }
        }

    def _log_action(self, action: str, **kwargs):
        """
        记录操作审计日志

        Args:
            action: 操作名称
            **kwargs: 操作相关参数
        """
        pass


_product_app_service: Optional[ProductApplicationService] = None


def get_product_app_service() -> ProductApplicationService:
    """获取产品应用服务单例 (别名)"""
    return get_product_application_service()


def get_product_application_service() -> ProductApplicationService:
    """获取产品应用服务单例"""
    global _product_app_service
    if _product_app_service is None:
        _product_app_service = ProductApplicationService()
    return _product_app_service


def init_product_application_service(
    products_service: "ProductsService",
    printer_service: Optional["PrinterService"] = None
) -> "ProductApplicationService":
    """初始化产品应用服务 (用于依赖注入)"""
    global _product_app_service
    _product_app_service = ProductApplicationService(
        products_service=products_service,
        printer_service=printer_service
    )
    return _product_app_service


def init_product_app_service(
    products_service: "ProductsService",
    printer_service: Optional["PrinterService"] = None
) -> "ProductApplicationService":
    """初始化产品应用服务 (用于依赖注入) (别名)"""
    return init_product_application_service(products_service, printer_service)
