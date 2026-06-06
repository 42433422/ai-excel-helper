#!/usr/bin/env python3
"""
服务迁移工具 - 自动将传统服务迁移到 Neuro-DDD

用法:
    python migrate_service_to_neuro.py --service ProductAppService
    python migrate_service_to_neuro.py --service ShipmentAppService --dry-run
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple


class ServiceMigrator:
    """服务迁移器"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.changes: List[str] = []

    def migrate_app_service(self, service_name: str) -> Tuple[bool, List[str]]:
        """
        迁移 Application Service 到事件驱动版本

        Args:
            service_name: 服务类名（如 ProductAppService）

        Returns:
            (成功, 变更列表)
        """
        print(f"[MIGRATE] 开始迁移: {service_name}")

        # 1. 找到服务文件
        service_file = self._find_service_file(service_name)
        if not service_file:
            return False, [f"找不到服务文件: {service_name}"]

        print(f"[MIGRATE] 找到文件: {service_file}")

        # 2. 分析当前代码
        content = service_file.read_text(encoding="utf-8")

        # 3. 检查是否已经迁移
        if "NeuroEvent" in content or "self._bus.publish" in content:
            return False, ["该服务似乎已经迁移到 Neuro-DDD"]

        # 4. 生成迁移建议
        changes = self._generate_migration_plan(service_name, content)

        # 5. 执行迁移（如果不是 dry-run）
        if not self.dry_run:
            new_content = self._apply_migration(content, changes)

            # 保存到新文件（保留原文件）
            new_file = service_file.parent / f"{service_file.stem}_v2{service_file.suffix}"
            new_file.write_text(new_content, encoding="utf-8")
            print(f"[MIGRATE] 已生成 V2 版本: {new_file}")

        return True, changes

    def _find_service_file(self, service_name: str) -> Path:
        """查找服务文件"""
        project_root = Path("e:/FHD")

        # 可能的目录
        search_dirs = [
            project_root / "app" / "application",
            project_root / "app" / "services",
        ]

        # 可能的文件名
        possible_names = [
            f"{self._camel_to_snake(service_name)}.py",
            f"{service_name.lower()}.py",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for name in possible_names:
                file_path = search_dir / name
                if file_path.exists():
                    return file_path

                # 递归搜索
                for py_file in search_dir.rglob("*.py"):
                    if name.replace("_", "") in py_file.name.lower():
                        content = py_file.read_text(encoding="utf-8")
                        if f"class {service_name}" in content:
                            return py_file

        return None

    def _camel_to_snake(self, name: str) -> str:
        """驼峰命名转下划线命名"""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _generate_migration_plan(self, service_name: str, content: str) -> List[str]:
        """生成迁移计划"""
        changes = []

        # 1. 添加导入
        changes.append("添加 NeuroBus 导入:")
        changes.append("  from app.neuro_bus.bus import get_neuro_bus")
        changes.append("  from app.neuro_bus.events.base import EventPriority")

        # 2. 检测领域
        domain = self._detect_domain(service_name)
        changes.append(f"检测到领域: {domain}")
        changes.append(f"需要导入: from app.neuro_bus.events.{domain}_events import *")

        # 3. 分析方法
        methods = self._extract_methods(content)
        changes.append(f"检测到 {len(methods)} 个方法需要迁移:")

        for method in methods:
            if self._is_command_method(method):
                changes.append(f"  - {method['name']}: 命令方法 -> 发布事件")
            else:
                changes.append(f"  - {method['name']}: 查询方法 -> 保持直接调用")

        # 4. 生成事件定义建议
        changes.append(f"\n需要在 app/neuro_bus/events/{domain}_events.py 中定义的事件:")
        for method in methods:
            if self._is_command_method(method):
                event_name = self._method_to_event_name(method["name"])
                changes.append(f"  - {event_name}")

        return changes

    def _detect_domain(self, service_name: str) -> str:
        """检测领域"""
        service_lower = service_name.lower()

        domain_map = {
            "product": "product",
            "shipment": "shipment",
            "order": "order",
            "customer": "customer",
            "inventory": "inventory",
            "payment": "payment",
            "wechat": "wechat",
            "ocr": "ocr",
            "print": "print",
            "ai": "ai",
        }

        for key, domain in domain_map.items():
            if key in service_lower:
                return domain

        return "common"

    def _extract_methods(self, content: str) -> List[dict]:
        """提取类方法"""
        methods = []

        # 简单的正则匹配
        method_pattern = re.compile(r"def\s+(\w+)\s*\(self[^)]*\)")

        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            if not method_name.startswith("_"):
                methods.append({"name": method_name, "start": match.start()})

        return methods

    def _is_command_method(self, method: dict) -> bool:
        """判断是否为命令方法（非查询）"""
        name = method["name"].lower()

        # 查询类关键词
        query_keywords = ["get", "list", "search", "find", "query", "check", "validate"]

        for keyword in query_keywords:
            if name.startswith(keyword):
                return False

        return True

    def _method_to_event_name(self, method_name: str) -> str:
        """将方法名转换为事件名"""
        # 移除常见的命令前缀
        prefixes = ["create", "update", "delete", "import", "export", "add", "remove"]

        name_lower = method_name.lower()
        for prefix in prefixes:
            if name_lower.startswith(prefix):
                return f"{prefix}.{name_lower[len(prefix):].strip('_')}"

        return f"action.{name_lower}"

    def _apply_migration(self, content: str, changes: List[str]) -> str:
        """应用迁移"""
        # 这里应该实现实际的代码转换逻辑
        # 现在只是一个占位符
        return content + "\n# TODO: 迁移到 Neuro-DDD\n"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="迁移服务到 Neuro-DDD")
    parser.add_argument("--service", required=True, help="服务类名")
    parser.add_argument("--dry-run", action="store_true", help="只生成计划，不实际迁移")

    args = parser.parse_args()

    migrator = ServiceMigrator(dry_run=args.dry_run)
    success, changes = migrator.migrate_app_service(args.service)

    print("\n" + "=" * 60)
    if success:
        print("[OK] 迁移计划生成成功")
    else:
        print("[ERROR] 迁移失败")
    print("=" * 60)

    print("\n变更计划:")
    for change in changes:
        print(f"  {change}")

    if args.dry_run:
        print("\n[NOTE] 这是 dry-run 模式，未实际修改文件")
        print("       移除 --dry-run 参数执行实际迁移")


if __name__ == "__main__":
    main()
