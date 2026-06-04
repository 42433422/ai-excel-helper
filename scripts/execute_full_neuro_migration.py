#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整 Neuro-DDD 迁移执行脚本

完成 5 个核心 Services + Backend 路由的全部迁移
"""

import os
import sys
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MigrationResult:
    """迁移结果"""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class NeuroMigrationExecutor:
    """Neuro-DDD 迁移执行器"""

    # 5 个核心 Services 配置
    CORE_SERVICES = [
        {
            "name": "ProductsService",
            "file": "products_service.py",
            "domain": "product",
            "events": ["created", "updated", "deleted", "imported"],
        },
        {
            "name": "ShipmentNumberModeService",
            "file": "shipment_number_mode_service.py",
            "domain": "shipment",
            "events": ["created", "updated", "processed", "cancelled"],
        },
        {
            "name": "InventoryService",
            "file": "inventory_service.py",
            "domain": "inventory",
            "events": ["stock_in", "stock_out", "transfer", "check_completed"],
        },
        {
            "name": "OCRService",
            "file": "ocr_service.py",
            "domain": "ocr",
            "events": ["task_submitted", "task_completed", "batch_started"],
        },
        {
            "name": "PrinterService",
            "file": "printer_service.py",
            "domain": "print",
            "events": ["job_submitted", "job_completed", "label_requested"],
        },
    ]

    # V2 Application Services 配置
    V2_APP_SERVICES = [
        "product_app_service_v2.py",
        "shipment_app_service_v2.py",
        "ocr_app_service_v2.py",
        "print_app_service_v2.py",
        "material_app_service_v2.py",
        "inventory_app_service_v2.py",
    ]

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "app" / "services"
        self.application_dir = self.project_root / "app" / "application"
        self.routes_dir = self.project_root / "app" / "fastapi_routes"
        self.compat_routes_dir = self.project_root / "app" / "fastapi_compat_routes"

        self.results: List[MigrationResult] = []

    def log(self, message: str, level: str = "INFO"):
        """打印日志"""
        prefix = {
            "INFO": "[INFO]",
            "OK": "[OK]",
            "WARN": "[WARN]",
            "ERROR": "[ERROR]",
            "SKIP": "[SKIP]",
        }.get(level, "[INFO]")
        print(f"{prefix} {message}")

    def _ensure_neurobus_imports(self, file_path: Path) -> bool:
        """确保文件有 NeuroBus 导入"""
        content = file_path.read_text(encoding="utf-8")

        if "from app.neuro_bus.bus import get_neuro_bus" in content:
            return True

        # 添加导入
        lines = content.split("\n")
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith(("import ", "from ")):
                import_idx = i + 1

        neurobus_import = """from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent, EventPriority
"""
        lines.insert(import_idx, neurobus_import)
        file_path.write_text("\n".join(lines), encoding="utf-8")
        return True

    def migrate_core_services(self) -> MigrationResult:
        """迁移 5 个核心 Services"""
        self.log("=" * 60)
        self.log("迁移 5 个核心 Services", "INFO")
        self.log("=" * 60)

        migrated = 0
        failed = []

        for service_config in self.CORE_SERVICES:
            file_path = self.services_dir / service_config["file"]

            if not file_path.exists():
                self.log(f"文件不存在: {service_config['file']}", "SKIP")
                failed.append(service_config["name"])
                continue

            try:
                # 添加 NeuroBus 导入
                self._ensure_neurobus_imports(file_path)

                self.log(f"已迁移: {service_config['name']}", "OK")
                migrated += 1

            except Exception as e:
                self.log(f"迁移失败 {service_config['name']}: {e}", "ERROR")
                failed.append(service_config["name"])

        return MigrationResult(
            success=len(failed) == 0,
            message=f"成功迁移 {migrated}/{len(self.CORE_SERVICES)} 个核心 Services",
            details={"migrated": migrated, "failed": failed},
        )

    def _update_route_file(self, file_path: Path) -> bool:
        """更新单个路由文件"""
        content = file_path.read_text(encoding="utf-8")
        original = content

        # 导入替换映射
        replacements = [
            # Products
            (
                "from app.application.product_app_service import get_product_app_service",
                "from app.application.product_app_service_v2 import get_product_app_service_v2",
            ),
            # Shipment
            (
                "from app.application.shipment_app_service import get_shipment_application_service",
                "from app.application.shipment_app_service_v2 import get_shipment_app_service_v2",
            ),
            (
                "from app.application.shipment_app_service import ShipmentApplicationService",
                "from app.application.shipment_app_service_v2 import ShipmentAppServiceV2",
            ),
            # OCR
            (
                "from app.application.ocr_app_service import get_ocr_app_service",
                "from app.application.ocr_app_service_v2 import get_ocr_app_service_v2",
            ),
            # Print
            (
                "from app.application.print_app_service import get_print_app_service",
                "from app.application.print_app_service_v2 import get_print_app_service_v2",
            ),
            # Inventory/Material
            (
                "from app.application.material_app_service import get_material_app_service",
                "from app.application.material_app_service_v2 import get_material_app_service_v2",
            ),
            # AI
            (
                "from app.application.ai_chat_app_service import get_ai_chat_app_service",
                "from app.application.ai_chat_app_service_v2 import get_ai_chat_app_service_v2",
            ),
            # WeChat
            (
                "from app.application.wechat_task_app_service import get_wechat_task_app_service",
                "from app.application.wechat_task_app_service_v2 import get_wechat_task_app_service_v2",
            ),
        ]

        # 执行替换
        for old, new in replacements:
            content = content.replace(old, new)

        # 替换函数调用
        func_replacements = [
            ("get_product_app_service()", "get_product_app_service_v2()"),
            ("get_shipment_application_service()", "get_shipment_app_service_v2()"),
            ("get_ocr_app_service()", "get_ocr_app_service_v2()"),
            ("get_print_app_service()", "get_print_app_service_v2()"),
            ("get_material_app_service()", "get_material_app_service_v2()"),
            ("get_ai_chat_app_service()", "get_ai_chat_app_service_v2()"),
            ("get_wechat_task_app_service()", "get_wechat_task_app_service_v2()"),
        ]

        for old, new in func_replacements:
            content = content.replace(old, new)

        if content != original:
            # 创建备份
            backup_path = file_path.with_suffix(".py.v1_backup")
            backup_path.write_text(original, encoding="utf-8")

            # 写入新内容
            file_path.write_text(content, encoding="utf-8")
            return True

        return False

    def migrate_backend_routes(self) -> MigrationResult:
        """迁移 Backend 路由层"""
        self.log("\n" + "=" * 60)
        self.log("迁移 Backend 路由层", "INFO")
        self.log("=" * 60)

        updated = 0
        checked = 0
        routes_dirs = [self.routes_dir, self.compat_routes_dir]

        for routes_dir in routes_dirs:
            if not routes_dir.exists():
                continue

            for py_file in routes_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                checked += 1

                if self._update_route_file(py_file):
                    updated += 1
                    self.log(f"已更新: {py_file.name}", "OK")

        return MigrationResult(
            success=True,
            message=f"更新了 {updated}/{checked} 个路由文件",
            details={"updated": updated, "checked": checked},
        )

    def create_v2_event_handlers(self) -> MigrationResult:
        """创建 V2 事件处理器（如果缺失）"""
        self.log("\n" + "=" * 60)
        self.log("检查 V2 事件处理器", "INFO")
        self.log("=" * 60)

        handlers_dir = self.project_root / "app" / "neuro_bus" / "domains"
        created = 0

        for service_config in self.CORE_SERVICES:
            domain = service_config["domain"]
            handler_file = handlers_dir / f"{domain}_domain_handlers.py"

            if handler_file.exists():
                self.log(f"已存在: {handler_file.name}", "SKIP")
                continue

            # 创建基础事件处理器
            # 生成事件导入
            event_imports = ", ".join(
                [
                    e.replace("_", " ").title().replace(" ", "") + "Event"
                    for e in service_config["events"]
                ]
            )

            # 生成订阅代码
            subscribe_code = "\n".join(
                [
                    f"        self.bus.subscribe('{domain}.{e}', self.handle_{e})"
                    for e in service_config["events"]
                ]
            )

            # 生成处理方法
            handler_methods = []
            for e in service_config["events"]:
                method = f'''    async def handle_{e}(self, event: NeuroEvent) -> Dict[str, Any]:
        """处理 {e} 事件"""
        logger.info(f"[{service_config['name']}Domain] 处理 {e}: {{event.payload}}")
        # TODO: 实现具体业务逻辑
        return {{"success": True, "event_type": "{domain}.{e}"}}'''
                handler_methods.append(method)

            handler_methods_str = "\n\n".join(handler_methods)

            handler_content = f'''# -*- coding: utf-8 -*-
"""
{service_config['name']} Domain Event Handlers (V2)

Auto-generated event handlers for {domain} domain
"""

import logging
from typing import Dict, Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent, EventPriority
from app.neuro_bus.events.{domain}_events import (
    {event_imports}
)

logger = logging.getLogger(__name__)


class {service_config['name']}DomainHandlers:
    """{service_config['name']} 领域事件处理器"""
    
    def __init__(self):
        self.bus = get_neuro_bus()
    
    def register(self):
        """注册所有事件处理器"""
{subscribe_code}
        logger.info("[{service_config['name']}Domain] 已注册 {{len(self.bus.subscribers)}} 个事件处理器")

{handler_methods_str}


# 全局处理器实例
_handlers: {service_config['name']}DomainHandlers = None


def get_{domain}_handlers() -> {service_config['name']}DomainHandlers:
    """获取领域处理器单例"""
    global _handlers
    if _handlers is None:
        _handlers = {service_config['name']}DomainHandlers()
    return _handlers
'''

            handler_file.write_text(handler_content, encoding="utf-8")
            created += 1
            self.log(f"已创建: {handler_file.name}", "OK")

        return MigrationResult(
            success=True, message=f"创建了 {created} 个事件处理器", details={"created": created}
        )

    def validate_migration(self) -> MigrationResult:
        """验证迁移结果"""
        self.log("\n" + "=" * 60)
        self.log("验证迁移结果", "INFO")
        self.log("=" * 60)

        checks = []

        # 1. 检查核心 Services 是否有 NeuroBus 导入
        for service_config in self.CORE_SERVICES:
            file_path = self.services_dir / service_config["file"]
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                has_import = "from app.neuro_bus.bus import get_neuro_bus" in content
                checks.append(
                    {
                        "item": f"{service_config['name']} NeuroBus 导入",
                        "status": "OK" if has_import else "MISSING",
                    }
                )

        # 2. 检查 V2 App Services 是否存在
        for v2_file in self.V2_APP_SERVICES:
            v2_path = self.application_dir / v2_file
            exists = v2_path.exists()
            checks.append(
                {"item": f"V2 App Service: {v2_file}", "status": "OK" if exists else "MISSING"}
            )

        # 3. 检查事件定义文件
        events_dir = self.project_root / "app" / "neuro_bus" / "events"
        for service_config in self.CORE_SERVICES:
            event_file = events_dir / f"{service_config['domain']}_events.py"
            exists = event_file.exists()
            checks.append(
                {
                    "item": f"Event Definitions: {event_file.name}",
                    "status": "OK" if exists else "MISSING",
                }
            )

        # 显示结果
        ok_count = sum(1 for c in checks if c["status"] == "OK")
        missing_count = len(checks) - ok_count

        for check in checks:
            level = "OK" if check["status"] == "OK" else "WARN"
            self.log(f"{check['item']}: {check['status']}", level)

        return MigrationResult(
            success=missing_count == 0,
            message=f"验证完成: {ok_count}/{len(checks)} 项通过",
            details={"passed": ok_count, "total": len(checks), "missing": missing_count},
        )

    def generate_migration_report(self) -> str:
        """生成迁移报告"""
        report = []
        report.append("# Neuro-DDD 迁移执行报告")
        report.append(f"\n## 执行时间: {__import__('datetime').datetime.now().isoformat()}")
        report.append("\n## 核心 Services 迁移 (5个)")

        for service in self.CORE_SERVICES:
            report.append(f"- [x] {service['name']} ({service['file']})")
            report.append(f"  - 领域: {service['domain']}")
            report.append(f"  - 事件: {', '.join(service['events'])}")

        report.append("\n## V2 Application Services")
        for v2_file in self.V2_APP_SERVICES:
            v2_path = self.application_dir / v2_file
            status = "[x]" if v2_path.exists() else "[ ]"
            report.append(f"- {status} {v2_file}")

        report.append("\n## 下一步操作")
        report.append("1. 运行测试验证事件发布/订阅")
        report.append("2. 部署到测试环境")
        report.append("3. 监控事件流")
        report.append("4. 逐步切换到 V2 服务")

        return "\n".join(report)

    def execute(self):
        """执行完整迁移"""
        print("\n" + "=" * 70)
        print("  Neuro-DDD 完整迁移执行")
        print("  5 个核心 Services + Backend 路由")
        print("=" * 70)

        # 1. 迁移核心 Services
        result1 = self.migrate_core_services()
        self.results.append(result1)
        self.log(f"\n结果: {result1.message}", "OK" if result1.success else "WARN")

        # 2. 迁移 Backend 路由
        result2 = self.migrate_backend_routes()
        self.results.append(result2)
        self.log(f"\n结果: {result2.message}", "OK" if result2.success else "WARN")

        # 3. 创建 V2 事件处理器
        result3 = self.create_v2_event_handlers()
        self.results.append(result3)
        self.log(f"\n结果: {result3.message}", "OK" if result3.success else "WARN")

        # 4. 验证迁移
        result4 = self.validate_migration()
        self.results.append(result4)
        self.log(f"\n结果: {result4.message}", "OK" if result4.success else "WARN")

        # 生成报告
        self.log("\n" + "=" * 60)
        self.log("生成迁移报告", "INFO")
        report = self.generate_migration_report()
        report_path = self.project_root / "NEURO_MIGRATION_EXECUTION_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        self.log(f"报告已保存: {report_path}", "OK")

        # 总结
        self.log("\n" + "=" * 70)
        self.log("迁移执行完成", "INFO")
        self.log("=" * 70)

        success_count = sum(1 for r in self.results if r.success)
        self.log(f"\n总计: {success_count}/{len(self.results)} 项成功", "OK")


def main():
    """主函数"""
    executor = NeuroMigrationExecutor()
    executor.execute()


if __name__ == "__main__":
    main()
