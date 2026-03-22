"""
服务层测试 - 最简化版
"""

import pytest


class TestProductsService:
    """产品服务测试"""

    def test_service_import(self):
        """测试服务类可以导入"""
        from app.services.products_service import ProductsService
        service = ProductsService()
        assert service is not None


class TestShipmentService:
    """发货单服务测试"""

    def test_service_import(self):
        """测试应用服务类可以导入"""
        from app.application.shipment_app_service import ShipmentApplicationService
        assert ShipmentApplicationService is not None


class TestOCRService:
    """OCR服务测试"""

    def test_service_import(self):
        """测试服务类可以导入"""
        from app.services.ocr_service import OCRService
        service = OCRService()
        assert service is not None


class TestWechatTaskService:
    """微信任务服务测试"""

    def test_service_import(self):
        """测试服务类可以导入"""
        from app.services.wechat_task_service import WechatTaskService
        service = WechatTaskService()
        assert service is not None


class TestPrinterService:
    """打印服务测试"""

    def test_service_import(self):
        """测试服务类可以导入"""
        from app.services.printer_service import PrinterService
        service = PrinterService()
        assert service is not None
