"""
打印应用服务

负责标签打印相关的用例编排
"""

from typing import Any

from app.services.printer_service import PrinterService

# Avoid importing from services.__init__ to prevent circular imports
# get_printer_service is defined in services/__init__.py


class PrintApplicationService:
    """打印应用服务 - 负责打印相关的用例编排"""

    def __init__(
        self,
        printer_service: PrinterService | None = None,
    ):
        self._printer_service = printer_service or get_printer_service()  # type: ignore

    def print_labels(self, label_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        打印标签用例

        Args:
            label_data: 标签数据列表

        Returns:
            打印结果
        """
        if not label_data:
            return {"success": False, "message": "没有要打印的标签"}

        return self._printer_service.print_labels(label_data)

    def print_single_label(
        self,
        product_name: str,
        model_number: str | None = None,
        specification: str | None = None,
        unit: str = "个",
        quantity: int = 1,
    ) -> dict[str, Any]:
        """
        打印单个标签用例

        Args:
            product_name: 产品名称
            model_number: 型号
            specification: 规格
            unit: 单位
            quantity: 数量

        Returns:
            打印结果
        """
        label_data = [
            {
                "product_name": product_name,
                "model_number": model_number,
                "specification": specification,
                "unit": unit,
                "quantity": quantity,
            }
        ]

        return self.print_labels(label_data)

    def get_printer_status(self) -> dict[str, Any]:
        """
        获取打印机状态用例

        Returns:
            打印机状态
        """
        return self._printer_service.get_printer_status()

    def test_print(self) -> dict[str, Any]:
        """
        测试打印用例

        Returns:
            测试打印结果
        """
        test_label = [
            {
                "product_name": "测试标签",
                "model_number": "TEST-001",
                "specification": "测试规格",
                "unit": "个",
                "quantity": 1,
            }
        ]

        return self._printer_service.print_labels(test_label)


from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(PrintApplicationService)

_print_app_service: PrintApplicationService | None = None


def get_print_app_service() -> PrintApplicationService:
    """获取打印应用服务单例 (别名)"""
    return get_print_application_service()


def get_print_application_service() -> PrintApplicationService:
    """获取打印应用服务单例"""
    global _print_app_service
    if _print_app_service is None:
        _print_app_service = PrintApplicationService()
    return _print_app_service


def init_print_app_service(
    printer_service: PrinterService,
) -> PrintApplicationService:
    """初始化打印应用服务 (用于依赖注入) (别名)"""
    return init_print_application_service(printer_service)


def init_print_application_service(
    printer_service: PrinterService,
) -> PrintApplicationService:
    """初始化打印应用服务 (用于依赖注入)"""
    global _print_app_service
    _print_app_service = PrintApplicationService(printer_service=printer_service)
    return _print_app_service
