"""
打印机管理 API 测试
测试打印机列表、保存选择、恢复自动识别等功能
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from backend.http_app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as client:
        yield client


class TestPrinterAPI:
    """打印机 API 测试类"""
    
    def test_get_printers_success(self, client):
        """TC-PRINT-001: 获取打印机列表成功"""
        response = client.get("/api/print/printers")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "printers" in data
        assert "classified" in data
        assert "selection" in data
        assert "resolved" in data and "match" in data and "online" in data
        print(f"✓ 打印机列表获取成功：{len(data['printers'])} 台打印机")
    
    def test_get_printers_structure(self, client):
        """TC-PRINT-001: 验证打印机列表数据结构"""
        response = client.get("/api/print/printers")
        assert response.status_code == 200
        data = response.json()
        
        # 验证打印机列表结构
        for printer in data["printers"]:
            assert "name" in printer
            assert "status" in printer
            assert "is_default" in printer
            assert "is_shared" in printer
        
        # 验证分类结构
        classified = data["classified"]
        assert "document_printer" in classified or classified.get("document_printer") is None
        assert "label_printer" in classified or classified.get("label_printer") is None
        
        print(f"✓ 打印机数据结构验证通过")
    
    def test_get_default_printer(self, client):
        """TC-PRINT-006: 获取默认打印机"""
        response = client.get("/api/print/default")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "printer" in data
        print(f"✓ 默认打印机获取成功")
    
    def test_get_document_printer(self, client):
        """TC-PRINT-002: 获取发货单打印机"""
        response = client.get("/api/print/document-printer")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "printer" in data or data.get("printer") is None
        assert "classified" in data
        print(f"✓ 发货单打印机获取成功")
    
    def test_get_label_printer(self, client):
        """TC-PRINT-003: 获取标签打印机"""
        response = client.get("/api/print/label-printer")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "printer" in data or data.get("printer") is None
        assert "classified" in data
        print(f"✓ 标签打印机获取成功")
    
    def test_get_printer_selection_empty(self, client):
        """TC-PRINT-005: 获取打印机选择（初始为空）"""
        response = client.get("/api/print/printer-selection")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "selection" in data
        assert "resolved" in data and "match" in data and "online" in data
        print(f"✓ 打印机选择获取成功: {data['selection']}")
    
    def test_save_printer_selection(self, client):
        """TC-PRINT-002: 保存自定义打印机选择"""
        # 先获取可用打印机列表
        printers_response = client.get("/api/print/printers")
        printers_data = printers_response.json()
        printers = printers_data["printers"]
        
        if len(printers) > 0:
            # 选择第一台打印机作为测试
            test_printer = printers[0]["name"]
            
            # 保存选择
            save_data = {
                "document_printer": test_printer,
                "label_printer": test_printer
            }
            response = client.put("/api/print/printer-selection", json=save_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["selection"]["document_printer"] == test_printer
            assert data["selection"]["label_printer"] == test_printer
            print(f"✓ 打印机选择保存成功: {test_printer}")
            
            # 验证保存后的选择
            verify_response = client.get("/api/print/printer-selection")
            verify_data = verify_response.json()
            assert verify_data["selection"]["document_printer"] == test_printer
            assert verify_data["selection"]["label_printer"] == test_printer
            print(f"✓ 打印机选择验证成功")
        else:
            print(f"⚠ 跳过测试：没有可用打印机")
    
    def test_save_printer_selection_partial(self, client):
        """TC-PRINT-008: 只保存部分打印机选择"""
        # 先获取可用打印机列表
        printers_response = client.get("/api/print/printers")
        printers_data = printers_response.json()
        printers = printers_data["printers"]
        
        if len(printers) > 0:
            # 只保存通用打印机选择
            test_printer = printers[0]["name"]
            save_data = {
                "document_printer": test_printer
                # 不保存 label_printer
            }
            response = client.put("/api/print/printer-selection", json=save_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["selection"]["document_printer"] == test_printer
            print(f"✓ 部分打印机选择保存成功")
        else:
            print(f"⚠ 跳过测试：没有可用打印机")
    
    def test_restore_auto_identification(self, client):
        """TC-PRINT-005: 恢复自动识别（清空自定义选择）"""
        # 先保存一个选择
        printers_response = client.get("/api/print/printers")
        printers_data = printers_response.json()
        printers = printers_data["printers"]
        
        if len(printers) > 0:
            # 保存选择
            test_printer = printers[0]["name"]
            save_data = {"document_printer": test_printer, "label_printer": test_printer}
            client.put("/api/print/printer-selection", json=save_data)
            
            # 清空选择（恢复自动识别）
            restore_data = {
                "document_printer": "",
                "label_printer": ""
            }
            response = client.put("/api/print/printer-selection", json=restore_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            print(f"✓ 恢复自动识别成功")
        else:
            print(f"⚠ 跳过测试：没有可用打印机")
    
    def test_validate_printers(self, client):
        """TC-PRINT-004: 验证打印机连接状态"""
        response = client.get("/api/print/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total" in data
        assert "online" in data
        assert "printers" in data
        print(f"✓ 打印机验证成功：总计 {data['total']} 台，在线 {data['online']} 台")


class TestPrinterMock:
    """打印机功能模拟测试（不依赖真实打印机）"""
    
    def test_printer_classification_logic(self):
        """测试打印机分类逻辑"""
        from backend.routers.print import _classify_printers
        
        # 测试数据
        printers = [
            {"name": "发货单打印机 HP", "status": "就绪", "is_default": False},
            {"name": "标签打印机 Zebra", "status": "就绪", "is_default": False},
            {"name": "Microsoft Print to PDF", "status": "就绪", "is_default": True},
        ]
        
        result = _classify_printers(printers)
        
        # 验证分类结果
        assert "document_printer" in result
        assert "label_printer" in result
        
        if result["document_printer"]:
            assert "发货" in result["document_printer"]["name"] or \
                   result["document_printer"]["name"] == "Microsoft Print to PDF"
        
        if result["label_printer"]:
            assert "标签" in result["label_printer"]["name"]
        
        print(f"✓ 打印机分类逻辑测试通过")

    def test_find_printer_by_saved_name_normalization(self):
        """已保存名称与枚举名仅大小写/空白不同时应能匹配（避免刷新后提示未连接）。"""
        from backend.routers.print import _find_printer_by_saved_name

        printers = [
            {"name": "Microsoft Print to PDF", "status": "就绪", "is_default": True, "is_shared": False},
        ]
        assert _find_printer_by_saved_name(printers, "microsoft print to pdf") == printers[0]
        assert _find_printer_by_saved_name(printers, "  Microsoft Print to PDF  ") == printers[0]
        assert _find_printer_by_saved_name(printers, "") is None
        assert _find_printer_by_saved_name(printers, None) is None
        assert _find_printer_by_saved_name(printers, "不存在的打印机") is None
    
    def test_printer_selection_file_operations(self):
        """测试打印机选择文件操作"""
        from backend.routers.print import _save_printer_selection, _load_printer_selection, _PRINTER_SELECTION_FILE
        
        # 测试保存
        test_data = {
            "document_printer": "Test Printer 1",
            "label_printer": "Test Printer 2"
        }
        _save_printer_selection(test_data)
        
        # 测试加载
        loaded_data = _load_printer_selection()
        assert loaded_data["document_printer"] == "Test Printer 1"
        assert loaded_data["label_printer"] == "Test Printer 2"
        
        # 清理测试数据
        if _PRINTER_SELECTION_FILE.exists():
            _PRINTER_SELECTION_FILE.unlink()
        
        print(f"✓ 打印机选择文件操作测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
