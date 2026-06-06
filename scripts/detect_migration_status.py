#!/usr/bin/env python3
"""
Neuro-DDD 迁移状态全面检测脚本

功能：
1. 扫描所有服务类，检测是否已 instrument
2. 扫描 Application Services，检测是否使用事件驱动
3. 扫描路由文件，检测是否发布 NeuroEvent
4. 生成详细的迁移状态报告
"""

import os
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict


@dataclass
class ServiceStatus:
    """服务迁移状态"""

    name: str
    file_path: str
    line_number: int
    has_instrumentation: bool = False
    has_event_publish: bool = False
    has_event_handler: bool = False
    direct_service_calls: List[str] = field(default_factory=list)
    event_types_used: List[str] = field(default_factory=list)


@dataclass
class MigrationReport:
    """迁移状态报告"""

    total_services: int = 0
    instrumented_services: int = 0
    event_driven_services: int = 0
    total_app_services: int = 0
    event_driven_app_services: int = 0
    total_routes: int = 0
    event_driven_routes: int = 0
    services: List[ServiceStatus] = field(default_factory=list)
    app_services: List[ServiceStatus] = field(default_factory=list)
    routes: List[ServiceStatus] = field(default_factory=list)

    @property
    def service_migration_rate(self) -> float:
        if self.total_services == 0:
            return 0.0
        return (self.event_driven_services / self.total_services) * 100

    @property
    def app_service_migration_rate(self) -> float:
        if self.total_app_services == 0:
            return 0.0
        return (self.event_driven_app_services / self.total_app_services) * 100

    @property
    def routes_migration_rate(self) -> float:
        if self.total_routes == 0:
            return 0.0
        return (self.event_driven_routes / self.total_routes) * 100


class MigrationDetector:
    """迁移状态检测器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.report = MigrationReport()

        # 定义扫描模式
        self.patterns = {
            "instrument_service": re.compile(r"instrument_service_layer_class\s*\(\s*(\w+)"),
            "instrument_app": re.compile(r"instrument_application_service_class\s*\(\s*(\w+)"),
            "event_publish": re.compile(r"(?:publish|emit)\s*\(\s*(\w+)\s*Event|NeuroEvent\s*\("),
            "event_handler": re.compile(
                r"@\s*(?:on_event|handler|subscribe)|def\s+handle_\w+.*event"
            ),
            "direct_call": re.compile(
                r"self\._(\w+)_service\.(\w+)\(|get_(\w+)_service\(\)\.(\w+)\("
            ),
            "class_definition": re.compile(r"^class\s+(\w+Service)\s*(?:\(|:)"),
            "route_decorator": re.compile(r"@\s*(?:router|app)\.(?:get|post|put|delete|patch)"),
        }

    def scan_services(self) -> None:
        """扫描 Services 层"""
        services_dir = self.project_root / "app" / "services"
        if not services_dir.exists():
            print(f"[ERROR] Services 目录不存在: {services_dir}")
            return

        print(f"[SCAN] 扫描 Services 层: {services_dir}")

        for py_file in services_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            self._analyze_service_file(py_file)

    def _analyze_service_file(self, file_path: Path) -> None:
        """分析单个服务文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            # 查找类定义
            for i, line in enumerate(lines, 1):
                match = self.patterns["class_definition"].search(line)
                if match:
                    class_name = match.group(1)
                    status = ServiceStatus(
                        name=class_name,
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=i,
                    )

                    # 检测是否有 instrumentation
                    if self.patterns["instrument_service"].search(content):
                        status.has_instrumentation = True

                    # 检测是否发布事件
                    if self.patterns["event_publish"].search(content):
                        status.has_event_publish = True

                    # 检测是否有事件处理器
                    if self.patterns["event_handler"].search(content):
                        status.has_event_handler = True

                    # 检测直接服务调用
                    for call_match in self.patterns["direct_call"].finditer(content):
                        status.direct_service_calls.append(call_match.group(0))

                    self.report.services.append(status)
                    self.report.total_services += 1

                    if status.has_instrumentation:
                        self.report.instrumented_services += 1

                    if status.has_event_publish or status.has_event_handler:
                        self.report.event_driven_services += 1

        except Exception as e:
            print(f"[WARN] 分析文件失败 {file_path}: {e}")

    def scan_application_services(self) -> None:
        """扫描 Application Services 层"""
        app_dir = self.project_root / "app" / "application"
        if not app_dir.exists():
            print(f"[ERROR] Application 目录不存在: {app_dir}")
            return

        print(f"[SCAN] 扫描 Application 层: {app_dir}")

        for py_file in app_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            self._analyze_app_service_file(py_file)

    def _analyze_app_service_file(self, file_path: Path) -> None:
        """分析应用服务文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # 查找 AppService 类定义
                if "class" in line and "AppService" in line and not line.strip().startswith("#"):
                    match = re.search(r"class\s+(\w+)", line)
                    if match:
                        class_name = match.group(1)
                        status = ServiceStatus(
                            name=class_name,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=i,
                        )

                        # 检测 instrumentation
                        if self.patterns["instrument_app"].search(content):
                            status.has_instrumentation = True

                        # 检测事件发布
                        if self.patterns["event_publish"].search(content):
                            status.has_event_publish = True

                        # 检测直接服务调用
                        for call_match in self.patterns["direct_call"].finditer(content):
                            status.direct_service_calls.append(call_match.group(0))

                        self.report.app_services.append(status)
                        self.report.total_app_services += 1

                        if status.has_event_publish:
                            self.report.event_driven_app_services += 1

        except Exception as e:
            print(f"[WARN] 分析文件失败 {file_path}: {e}")

    def scan_routes(self) -> None:
        """扫描路由文件"""
        routes_dirs = [
            self.project_root / "app" / "fastapi_routes",
            self.project_root / "app" / "fastapi_compat_routes",
        ]

        for routes_dir in routes_dirs:
            if not routes_dir.exists():
                continue

                print(f"[SCAN] 扫描 Routes: {routes_dir}")

            for py_file in routes_dir.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                self._analyze_route_file(py_file)

    def _analyze_route_file(self, file_path: Path) -> None:
        """分析路由文件"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 查找路由函数
            route_matches = list(self.patterns["route_decorator"].finditer(content))

            for match in route_matches:
                # 找到对应的路由函数名
                line_num = content[: match.start()].count("\n") + 1
                status = ServiceStatus(
                    name=f"route_{file_path.stem}_{line_num}",
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                )

                # 检测是否发布事件
                if self.patterns["event_publish"].search(content):
                    status.has_event_publish = True

                self.report.routes.append(status)
                self.report.total_routes += 1

                if status.has_event_publish:
                    self.report.event_driven_routes += 1

        except Exception as e:
            print(f"[WARN] 分析文件失败 {file_path}: {e}")

    def generate_report(self) -> str:
        """生成文本报告"""
        lines = [
            "=" * 80,
            "Neuro-DDD 迁移状态检测报告",
            "=" * 80,
            "",
            f"[SUMMARY] 总体统计",
            f"  Services 层:",
            f"    总服务数: {self.report.total_services}",
            f"    已 Instrument: {self.report.instrumented_services} ({self.report.instrumented_services/self.report.total_services*100:.1f}%)",
            f"    事件驱动: {self.report.event_driven_services} ({self.report.service_migration_rate:.1f}%)",
            f"",
            f"  Application 层:",
            f"    总服务数: {self.report.total_app_services}",
            f"    事件驱动: {self.report.event_driven_app_services} ({self.report.app_service_migration_rate:.1f}%)",
            f"",
            f"  Routes 层:",
            f"    总路由数: {self.report.total_routes}",
            f"    事件驱动: {self.report.event_driven_routes} ({self.report.routes_migration_rate:.1f}%)",
            f"",
            "-" * 80,
            f"[DETAIL] Services 层详情",
            "-" * 80,
        ]

        # Services 详情
        sorted_services = sorted(
            self.report.services,
            key=lambda s: (not s.has_event_publish, not s.has_instrumentation, s.name),
        )

        for s in sorted_services:
            status_symbol = (
                "[OK]"
                if s.has_event_publish
                else ("[PARTIAL]" if s.has_instrumentation else "[NO]")
            )
            lines.append(
                f"  {status_symbol} {s.name:40s} (instrument={s.has_instrumentation}, event={s.has_event_publish})"
            )
            if s.direct_service_calls:
                lines.append(f"      直接调用: {len(s.direct_service_calls)} 处")

        lines.extend(
            [
                "",
                "-" * 80,
                f"[DETAIL] Application Services 详情",
                "-" * 80,
            ]
        )

        # App Services 详情
        sorted_app_services = sorted(
            self.report.app_services, key=lambda s: (not s.has_event_publish, s.name)
        )

        for s in sorted_app_services:
            status_symbol = "[OK]" if s.has_event_publish else "[NO]"
            lines.append(f"  {status_symbol} {s.name:40s} (event={s.has_event_publish})")

        lines.extend(
            [
                "",
                "=" * 80,
                f"[PRIORITY] 迁移优先级建议",
                "=" * 80,
                "",
                "P0 (立即迁移):",
            ]
        )

        # 找出高频且未迁移的服务
        p0_candidates = [
            s
            for s in self.report.app_services
            if not s.has_event_publish and s.direct_service_calls
        ]

        for s in p0_candidates[:5]:
            lines.append(f"  - {s.name} - 调用次数: {len(s.direct_service_calls)}")

        lines.extend(
            [
                "",
                "P1 (近期迁移):",
                "  - 其他高频业务服务",
                "",
                "P2 (排期迁移):",
                "  - 低频/后台任务服务",
                "",
                "=" * 80,
            ]
        )

        return "\n".join(lines)

    def save_report(self, output_path: str = "e:/FHD/migration_status_report.txt") -> None:
        """保存报告到文件"""
        report = self.generate_report()
        Path(output_path).write_text(report, encoding="utf-8")
        print(f"\n[SAVE] 报告已保存: {output_path}")


def main():
    """主函数"""
    print("[START] 启动 Neuro-DDD 迁移状态全面检测")
    print("=" * 60)

    detector = MigrationDetector()

    # 执行扫描
    detector.scan_services()
    detector.scan_application_services()
    detector.scan_routes()

    # 生成并保存报告
    print("\n" + detector.generate_report())
    detector.save_report()

    # 打印摘要
    print("\n" + "=" * 60)
    print("[SUMMARY] 检测完成摘要")
    print("=" * 60)
    print(
        f"  Services: {detector.report.event_driven_services}/{detector.report.total_services} 事件驱动"
    )
    print(
        f"  Application: {detector.report.event_driven_app_services}/{detector.report.total_app_services} 事件驱动"
    )
    print(
        f"  Routes: {detector.report.event_driven_routes}/{detector.report.total_routes} 事件驱动"
    )
    print("\n[DONE] 检测完成")


if __name__ == "__main__":
    main()
