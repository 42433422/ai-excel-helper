#!/usr/bin/env python3
"""
迁移 5 个核心 Services + Backend 路由

5 个核心 Services:
1. ProductsService - 产品管理
2. ShipmentNumberModeService - 发货单核心
3. InventoryService - 库存管理
4. OCRService - OCR 识别
5. PrinterService - 打印服务
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional


class CoreServiceMigrator:
    """核心 Services 迁移器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "app" / "services"
        self.routes_dir = self.project_root / "app" / "fastapi_routes"
        self.compat_routes_dir = self.project_root / "app" / "fastapi_compat_routes"

        # 5 个核心 Services
        self.core_services = [
            "products_service.py",
            "shipment_number_mode_service.py",
            "inventory_service.py",
            "ocr_service.py",
            "printer_service.py",
        ]

        # 对应的事件类型
        self.service_event_mapping = {
            "products_service.py": {
                "create": "product.created",
                "update": "product.updated",
                "delete": "product.deleted",
                "import": "product.imported",
            },
            "shipment_number_mode_service.py": {
                "create": "shipment.created",
                "update": "shipment.updated",
                "delete": "shipment.deleted",
                "process": "shipment.processed",
            },
            "inventory_service.py": {
                "stock_in": "inventory.stock_in",
                "stock_out": "inventory.stock_out",
                "transfer": "inventory.transfer",
                "check": "inventory.check_completed",
            },
            "ocr_service.py": {
                "recognize": "ocr.task_submitted",
                "batch": "ocr.batch_completed",
            },
            "printer_service.py": {
                "print": "print.job_submitted",
                "print_label": "print.label_requested",
            },
        }

    def add_event_publishing_to_service(self, service_file: str) -> bool:
        """为 Service 添加事件发布能力"""
        file_path = self.services_dir / service_file

        if not file_path.exists():
            print(f"  [SKIP] 文件不存在: {service_file}")
            return False

        print(f"\n[PROCESSING] {service_file}")

        content = file_path.read_text(encoding="utf-8")

        # 检查是否已有 NeuroBus 导入
        if "from app.neuro_bus.bus import get_neuro_bus" in content:
            print(f"  [SKIP] 已有 NeuroBus 导入")
            return False

        # 在文件顶部添加导入
        import_section = """from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent, EventPriority

"""

        # 找到第一个 import 的位置
        lines = content.split("\n")
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_idx = i + 1

        lines.insert(import_idx, import_section.strip())

        # 添加 publish_event 方法到类
        publish_method = '''
    def _publish_event(self, event_type: str, payload: dict, priority: EventPriority = EventPriority.NORMAL):
        """发布领域事件"""
        try:
            bus = get_neuro_bus()
            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source=self.__class__.__name__,
                priority=priority
            )
            bus.publish(event)
            return event.metadata.event_id
        except Exception as e:
            logger.warning(f"发布事件失败 {event_type}: {e}")
            return None
'''

        # 找到类定义并在第一个方法前插入 publish_event 方法
        class_pattern = r"(class \w+.*?\n)"
        match = re.search(class_pattern, content)
        if match:
            # 找到类中的第一个 def
            class_start = match.end()
            after_class = content[class_start:]
            first_def = re.search(r"\n    def ", after_class)
            if first_def:
                insert_pos = class_start + first_def.start()
                content = content[:insert_pos] + publish_method + content[insert_pos:]

        # 写回文件
        file_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  [OK] 已添加事件发布能力")
        return True

    def migrate_all_core_services(self) -> int:
        """迁移所有核心 Services"""
        print("=" * 60)
        print("迁移 5 个核心 Services")
        print("=" * 60)

        migrated_count = 0
        for service_file in self.core_services:
            if self.add_event_publishing_to_service(service_file):
                migrated_count += 1

        print(f"\n[SUMMARY] 成功迁移 {migrated_count}/{len(self.core_services)} 个核心 Services")
        return migrated_count

    def update_routes_to_v2(self) -> int:
        """更新 Backend 路由层到 V2"""
        print("\n" + "=" * 60)
        print("更新 Backend 路由层到 V2")
        print("=" * 60)

        updated_count = 0

        # 导入替换映射
        import_replacements = {
            # Products
            "from app.application.product_app_service import get_product_app_service": "from app.application.product_app_service_v2 import get_product_app_service_v2",
            "get_product_app_service()": "get_product_app_service_v2()",
            # Shipment
            "from app.application.shipment_app_service import get_shipment_application_service": "from app.application.shipment_app_service_v2 import get_shipment_app_service_v2",
            "get_shipment_application_service()": "get_shipment_app_service_v2()",
            # OCR
            "from app.application.ocr_app_service import get_ocr_app_service": "from app.application.ocr_app_service_v2 import get_ocr_app_service_v2",
            "get_ocr_app_service()": "get_ocr_app_service_v2()",
            # Print
            "from app.application.print_app_service import get_print_app_service": "from app.application.print_app_service_v2 import get_print_app_service_v2",
            "get_print_app_service()": "get_print_app_service_v2()",
            # Inventory (通过 Material)
            "from app.application.material_app_service import get_material_app_service": "from app.application.material_app_service_v2 import get_material_app_service_v2",
            "get_material_app_service()": "get_material_app_service_v2()",
        }

        # 遍历路由文件
        routes_dirs = [self.routes_dir, self.compat_routes_dir]

        for routes_dir in routes_dirs:
            if not routes_dir.exists():
                continue

            for route_file in routes_dir.glob("*.py"):
                if route_file.name.startswith("__"):
                    continue

                print(f"\n[PROCESSING] {route_file.name}")

                content = route_file.read_text(encoding="utf-8")
                original_content = content

                # 执行替换
                for old, new in import_replacements.items():
                    content = content.replace(old, new)

                # 检查是否有变化
                if content != original_content:
                    # 创建备份
                    backup_path = route_file.with_suffix(".py.v1_backup")
                    backup_path.write_text(original_content, encoding="utf-8")

                    # 写入新内容
                    route_file.write_text(content, encoding="utf-8")

                    updated_count += 1
                    print(f"  [UPDATED] 已更新到 V2")
                else:
                    print(f"  [SKIP] 无需更新")

        print(f"\n[SUMMARY] 成功更新 {updated_count} 个路由文件")
        return updated_count

    def add_async_await_to_routes(self) -> int:
        """为路由添加 async/await 支持"""
        print("\n" + "=" * 60)
        print("为路由添加 async/await 支持")
        print("=" * 60)

        fixed_count = 0
        routes_dirs = [self.routes_dir, self.compat_routes_dir]

        for routes_dir in routes_dirs:
            if not routes_dir.exists():
                continue

            for route_file in routes_dir.glob("*.py"):
                if route_file.name.startswith("__"):
                    continue

                content = route_file.read_text(encoding="utf-8")
                original_content = content

                # 为使用了 V2 服务的函数添加 async
                # 查找调用 V2 服务的模式
                v2_patterns = [
                    r"(def (\w+)\([^)]*\)):",
                    r"get_\w+_v2\(\)",
                ]

                # 简单处理：如果文件包含 V2 导入，添加 async
                if "_v2" in content and "async def" not in content:
                    # 将 def 改为 async def
                    content = re.sub(r"\ndef (\w+)\(", "\nasync def \1(", content)

                    # 为 V2 服务调用添加 await
                    content = re.sub(
                        r"((\w+) = get_\w+_v2\(\))", r"\2 = await get_\w+_v2()", content
                    )

                if content != original_content:
                    route_file.write_text(content, encoding="utf-8")
                    fixed_count += 1
                    print(f"  [FIXED] {route_file.name}")

        print(f"\n[SUMMARY] 修复了 {fixed_count} 个文件")
        return fixed_count

    def create_v2_wrapper_for_core_services(self) -> int:
        """为核心 Services 创建 V2 包装器"""
        print("\n" + "=" * 60)
        print("创建核心 Services V2 包装器")
        print("=" * 60)

        created_count = 0

        v2_wrapper_template = '''"""
{service_class} V2 - 事件驱动包装器

自动生成的事件驱动版本
"""

import logging
from typing import Dict, Any, Optional

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent, EventPriority
from app.services import {service_class}

logger = logging.getLogger(__name__)


class {service_class}V2:
    """
    {service_class} V2 - 事件驱动版本
    
    包装原有服务，添加事件发布能力
    """
    
    def __init__(self, original_service: Optional[{service_class}] = None):
        self._service = original_service or {service_class}()
        self._bus = get_neuro_bus()
    
    def _publish_event(self, event_type: str, payload: dict, priority: EventPriority = EventPriority.NORMAL):
        """发布领域事件"""
        try:
            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="{service_class}V2",
                priority=priority
            )
            self._bus.publish(event)
            return event.metadata.event_id
        except Exception as e:
            logger.warning(f"发布事件失败 {{event_type}}: {{e}}")
            return None
    
    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        通用执行方法
        
        Args:
            operation: 操作类型
            **kwargs: 操作参数
        
        Returns:
            执行结果
        """
        # 发布操作事件
        event_id = self._publish_event(
            f"{self._get_domain()}.{{operation}}",
            {{"operation": operation, "params": kwargs}}
        )
        
        # 调用原始服务方法
        method = getattr(self._service, operation, None)
        if method:
            if asyncio.iscoroutinefunction(method):
                result = await method(**kwargs)
            else:
                result = method(**kwargs)
        else:
            result = {{"success": False, "error": f"Unknown operation: {{operation}}"}}
        
        # 添加事件 ID 到结果
        if isinstance(result, dict):
            result["event_id"] = event_id
        
        return result
    
    def _get_domain(self) -> str:
        """获取领域名称"""
        return "{domain}"


# 单例管理
_{instance_name} = None


def get_{instance_name}() -> {service_class}V2:
    """获取 V2 服务单例"""
    global _{instance_name}
    if _{instance_name} is None:
        _{instance_name} = {service_class}V2()
    return _{instance_name}


# 导入 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class
instrument_service_layer_class({service_class}V2, "app.services.{module_name}_v2")
'''

        service_configs = [
            ("ProductsService", "product", "products_service"),
            ("ShipmentNumberModeService", "shipment", "shipment_number_mode_service"),
            ("InventoryService", "inventory", "inventory_service"),
            ("OCRService", "ocr", "ocr_service"),
            ("PrinterService", "print", "printer_service"),
        ]

        for service_class, domain, module_name in service_configs:
            # 创建 V2 文件
            v2_filename = f"{module_name}_v2.py"
            v2_filepath = self.services_dir / v2_filename

            content = v2_wrapper_template.format(
                service_class=service_class,
                domain=domain,
                module_name=module_name,
                instance_name=f"{service_class.lower()}_v2",
            )

            v2_filepath.write_text(content, encoding="utf-8")
            created_count += 1
            print(f"  [CREATED] {v2_filename}")

        print(f"\n[SUMMARY] 创建了 {created_count} 个 V2 包装器")
        return created_count

    def execute_full_migration(self):
        """执行完整迁移"""
        print("=" * 60)
        print("开始执行完整迁移")
        print("=" * 60)

        results = {}

        # 1. 迁移核心 Services
        results["core_services"] = self.migrate_all_core_services()

        # 2. 创建 V2 包装器
        results["v2_wrappers"] = self.create_v2_wrapper_for_core_services()

        # 3. 更新路由层
        results["routes"] = self.update_routes_to_v2()

        # 4. 添加 async 支持
        results["async"] = self.add_async_await_to_routes()

        # 打印总结
        self._print_summary(results)

    def _print_summary(self, results: dict):
        """打印总结"""
        print("\n" + "=" * 60)
        print("迁移完成总结")
        print("=" * 60)

        print(f"\n核心 Services 迁移: {results.get('core_services', 0)} 个")
        print(f"V2 包装器创建: {results.get('v2_wrappers', 0)} 个")
        print(f"路由文件更新: {results.get('routes', 0)} 个")
        print(f"Async 支持添加: {results.get('async', 0)} 个")

        print("\n下一步:")
        print("  1. 测试核心 Services 事件发布")
        print("  2. 测试路由层 V2 调用")
        print("  3. 运行验证脚本")
        print("  4. 部署到生产环境")


def main():
    """主函数"""
    migrator = CoreServiceMigrator()
    migrator.execute_full_migration()


if __name__ == "__main__":
    main()
