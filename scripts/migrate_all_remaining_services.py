#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量迁移所有剩余的 Services 到 Neuro-DDD

为每个 Service 添加:
- NeuroBus 导入
- Event 基类导入
- _publish_event() 方法
"""

import os
from pathlib import Path
from typing import List, Tuple


class BulkServiceMigrator:
    """批量 Service 迁移器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "app" / "services"

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

    def is_service_migrated(self, file_path: Path) -> bool:
        """检查 Service 是否已迁移"""
        try:
            content = file_path.read_text(encoding="utf-8")
            return "get_neuro_bus" in content or "NeuroEvent" in content
        except:
            return False

    def migrate_service(self, file_path: Path) -> bool:
        """迁移单个 Service"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 找到最后一个 import 的位置
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith(("import ", "from ")):
                    import_idx = i + 1

            # 插入 NeuroBus 导入
            neuro_imports = [
                "from app.neuro_bus.bus import get_neuro_bus\n",
                "from app.neuro_bus.events.base import NeuroEvent, EventPriority\n",
                "\n",
            ]

            # 在最后一个 import 后插入
            for imp in reversed(neuro_imports):
                lines.insert(import_idx, imp)

            # 找到类定义行
            class_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("class ") and "Service" in line:
                    class_idx = i
                    break

            if class_idx:
                # 找到类中的第一个方法
                first_method_idx = None
                for i in range(class_idx + 1, len(lines)):
                    if lines[i].strip().startswith("def ") and not lines[i].strip().startswith(
                        "def __"
                    ):
                        first_method_idx = i
                        break

                if first_method_idx:
                    # 插入 _publish_event 方法
                    publish_method = [
                        "\n",
                        "    def _publish_event(self, event_type: str, payload: dict, priority: 'EventPriority' = None) -> str:\n",
                        '        """发布领域事件"""\n',
                        "        if priority is None:\n",
                        "            priority = EventPriority.NORMAL\n",
                        "        try:\n",
                        "            bus = get_neuro_bus()\n",
                        "            event = NeuroEvent(\n",
                        "                event_type=event_type,\n",
                        "                payload=payload,\n",
                        "                source=self.__class__.__name__,\n",
                        "                priority=priority\n",
                        "            )\n",
                        "            bus.publish(event)\n",
                        "            return event.metadata.event_id\n",
                        "        except Exception as e:\n",
                        '            logger.warning(f"发布事件失败 {event_type}: {e}")\n',
                        '            return ""\n',
                        "\n",
                    ]

                    for line in reversed(publish_method):
                        lines.insert(first_method_idx, line)

            # 创建备份
            backup_path = file_path.with_suffix(".py.v1_backup")
            with open(backup_path, "w", encoding="utf-8") as f:
                f.writelines(
                    lines[:import_idx] + lines[import_idx + len(neuro_imports) :]
                )  # 原始内容

            # 实际备份 - 重新读取原始文件
            original_content = file_path.read_text(encoding="utf-8")
            backup_path.write_text(original_content, encoding="utf-8")

            # 写入新内容
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return True

        except Exception as e:
            self.log(f"迁移失败 {file_path.name}: {e}", "ERROR")
            return False

    def execute(self):
        """执行批量迁移"""
        print("=" * 70)
        print("批量迁移剩余 Services 到 Neuro-DDD")
        print("=" * 70)

        # 获取所有需要迁移的 Services
        services = [f for f in self.services_dir.glob("*.py") if not f.name.startswith("__")]

        to_migrate = []
        already_migrated = []

        for svc in sorted(services):
            if self.is_service_migrated(svc):
                already_migrated.append(svc)
            else:
                to_migrate.append(svc)

        self.log(f"总计 Services: {len(services)}")
        self.log(f"已迁移: {len(already_migrated)}")
        self.log(f"待迁移: {len(to_migrate)}")
        print()

        # 执行迁移
        success = 0
        failed = 0

        for svc in to_migrate:
            if self.migrate_service(svc):
                self.log(f"已迁移: {svc.name}", "OK")
                success += 1
            else:
                failed += 1

        print()
        print("=" * 70)
        print("迁移结果")
        print("=" * 70)
        self.log(f"成功: {success}", "OK")
        self.log(f"失败: {failed}", "ERROR" if failed > 0 else "INFO")
        self.log(f"总计: {success + len(already_migrated)}/{len(services)}", "OK")


def main():
    migrator = BulkServiceMigrator()
    migrator.execute()


if __name__ == "__main__":
    main()
