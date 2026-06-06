#!/usr/bin/env python3
"""
批量生成所有 Application Service 的 V2 版本

自动将现有的 App Service 转换为事件驱动版本。
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


class V2ServiceGenerator:
    """V2 服务生成器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.app_dir = self.project_root / "app" / "application"
        self.generated_count = 0

        # 领域映射
        self.domain_mapping = {
            "product": ["product", "import", "unit_products_import"],
            "shipment": ["shipment"],
            "order": ["order"],
            "customer": ["customer"],
            "wechat": ["wechat_contact", "wechat_task"],
            "print": ["print", "template"],
            "auth": ["auth", "user", "user_preference", "user_memory"],
            "ai": ["ai_chat", "file_analysis", "excel_vector"],
            "ocr": ["ocr"],
            "conversation": ["conversation"],
            "material": ["material"],
            "log": ["extract_log"],
        }

    def detect_domain(self, service_name: str) -> str:
        """根据服务名检测领域"""
        service_lower = service_name.lower()

        for domain, keywords in self.domain_mapping.items():
            for keyword in keywords:
                if keyword in service_lower:
                    return domain

        return "common"

    def generate_v2_header(self, service_name: str, domain: str) -> str:
        """生成 V2 文件头部"""
        return f'''"""
{service_name} V2 - 事件驱动版本

基于 Neuro-DDD 架构的事件驱动实现。

与 V1 的区别：
- V1: 直接调用 Services 层方法
- V2: 发布事件到 NeuroBus，由事件处理器执行实际业务

生成时间: 自动生成
"""

import logging
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.events.{domain}_events import *

if TYPE_CHECKING:
    pass  # 根据实际需要添加类型引用

logger = logging.getLogger(__name__)


'''

    def generate_v2_class(self, service_name: str, domain: str) -> str:
        """生成 V2 类定义"""
        class_name = service_name.replace("_", " ").title().replace(" ", "")

        return f'''
class {class_name}V2:
    """
    {class_name} V2 - 事件驱动版本
    """
    
    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "{domain}"
    
    def _create_correlation_id(self) -> str:
        """创建事件关联 ID"""
        return f"{{self._correlation_prefix}}-{{datetime.now().strftime('%Y%m%d%H%M%S')}}-{{id(self)}}"
    
    async def execute_command(self, command_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用命令执行方法
        
        Args:
            command_type: 命令类型 (对应事件类型)
            payload: 命令数据
        
        Returns:
            执行结果
        """
        try:
            correlation_id = self._create_correlation_id()
            
            # 构建事件类型
            event_type = f"{domain}.{{command_type}}"
            
            # 创建事件
            from app.neuro_bus.events.base import NeuroEvent
            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="{class_name.lower()}_v2",
                correlation_id=correlation_id
            )
            
            # 发布事件
            self._bus.publish(event)
            
            logger.info(f"[{class_name}V2] 命令已发布: {{command_type}} (event_id={{event.metadata.event_id}})")
            
            return {{
                "success": True,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": f"{{command_type}} 命令已提交"
            }}
            
        except Exception as e:
            logger.exception(f"[{class_name}V2] 执行命令失败: {{e}}")
            return {{"success": False, "message": str(e)}}
'''

    def generate_v2_footer(self, service_name: str) -> str:
        """生成 V2 文件尾部"""
        class_name = service_name.replace("_", " ").title().replace(" ", "")

        return f'''

# 注册到 instrumentation
from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class({class_name}V2, service_name="{class_name}V2")

# 单例管理
_{class_name.lower()}_v2_instance = None


def get_{service_name}_v2() -> {class_name}V2:
    """获取 {class_name}V2 单例"""
    global _{class_name.lower()}_v2_instance
    if _{class_name.lower()}_v2_instance is None:
        _{class_name.lower()}_v2_instance = {class_name}V2()
    return _{class_name.lower()}_v2_instance
'''

    def generate_v2_service(self, original_file: Path) -> Path:
        """生成单个服务的 V2 版本"""
        service_name = original_file.stem  # e.g., "product_app_service"
        v2_file_name = f"{service_name}_v2.py"
        v2_file_path = original_file.parent / v2_file_name

        # 检测领域
        domain = self.detect_domain(service_name)

        # 生成内容
        content = (
            self.generate_v2_header(service_name, domain)
            + self.generate_v2_class(service_name, domain)
            + self.generate_v2_footer(service_name)
        )

        # 写入文件
        v2_file_path.write_text(content, encoding="utf-8")

        self.generated_count += 1
        print(f"  [GENERATED] {v2_file_name}")

        return v2_file_path

    def generate_all_v2_services(self) -> List[Path]:
        """生成所有服务的 V2 版本"""
        print("=" * 60)
        print("开始生成所有 App Service V2 版本")
        print("=" * 60)

        generated_files = []

        # 遍历所有 App Service 文件
        for py_file in sorted(self.app_dir.glob("*_app_service.py")):
            # 跳过已有的 V2 文件
            if py_file.name.endswith("_v2.py"):
                continue

            # 跳过特殊文件
            if py_file.name in ["__init__.py", "ports.py"]:
                continue

            print(f"\n[PROCESSING] {py_file.name}")

            try:
                v2_file = self.generate_v2_service(py_file)
                generated_files.append(v2_file)
            except Exception as e:
                print(f"  [ERROR] 生成失败: {e}")

        return generated_files

    def print_summary(self, generated_files: List[Path]):
        """打印生成摘要"""
        print("\n" + "=" * 60)
        print("生成完成摘要")
        print("=" * 60)
        print(f"总共生成: {len(generated_files)} 个 V2 服务")
        print("\n生成的文件:")
        for f in generated_files:
            print(f"  - {f.name}")

        print("\n下一步:")
        print("  1. 检查生成的 V2 服务文件")
        print("  2. 根据实际业务需求完善 execute_command 方法")
        print("  3. 在路由层切换到 V2 版本")
        print("  4. 测试并验证功能")


def main():
    """主函数"""
    generator = V2ServiceGenerator()
    generated_files = generator.generate_all_v2_services()
    generator.print_summary(generated_files)


if __name__ == "__main__":
    main()
