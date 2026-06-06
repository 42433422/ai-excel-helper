#!/usr/bin/env python3
"""
传统代码清理工具

功能:
1. 识别未使用的代码
2. 标记可以清理的文件
3. 生成清理报告
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Set, Dict
from collections import defaultdict


@dataclass
class CodeUsage:
    """代码使用统计"""

    file_path: str
    total_functions: int = 0
    used_functions: int = 0
    unused_functions: List[str] = field(default_factory=list)
    import_count: int = 0
    is_legacy: bool = False


class LegacyCodeCleaner:
    """传统代码清理器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.usage_stats: Dict[str, CodeUsage] = {}

    def analyze_codebase(self) -> None:
        """分析代码库使用状况"""
        print("[ANALYZE] 开始分析代码库...")

        # 1. 扫描所有 Python 文件
        all_py_files = list(self.project_root.rglob("*.py"))
        print(f"[ANALYZE] 找到 {len(all_py_files)} 个 Python 文件")

        # 2. 构建导入图谱
        import_graph = self._build_import_graph(all_py_files)

        # 3. 识别未使用的文件
        self._identify_unused_files(all_py_files, import_graph)

        # 4. 识别未使用的函数
        self._identify_unused_functions(all_py_files)

        print("[ANALYZE] 分析完成")

    def _build_import_graph(self, py_files: List[Path]) -> Dict[str, Set[str]]:
        """构建导入关系图"""
        import_graph = defaultdict(set)

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")

                # 解析导入语句
                import_pattern = re.compile(r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")

                for match in import_pattern.finditer(content):
                    from_import = match.group(1)
                    direct_import = match.group(2)

                    imported = from_import or direct_import
                    if imported:
                        import_graph[str(py_file)].add(imported)

            except Exception as e:
                print(f"[WARN] 分析文件失败 {py_file}: {e}")

        return import_graph

    def _identify_unused_files(self, py_files: List[Path], import_graph: Dict) -> None:
        """识别未被导入的文件"""
        print("[ANALYZE] 识别未使用的文件...")

        # 计算每个文件被导入的次数
        import_counts = defaultdict(int)

        for file_path, imports in import_graph.items():
            for imported in imports:
                # 转换导入路径为文件路径
                possible_paths = [
                    imported.replace(".", "/") + ".py",
                    imported.replace(".", "/") + "/__init__.py",
                ]

                for path_suffix in possible_paths:
                    full_path = str(self.project_root / path_suffix)
                    if full_path in [str(f) for f in py_files]:
                        import_counts[full_path] += 1

        # 标记未使用的文件
        for py_file in py_files:
            file_str = str(py_file)

            # 排除明显的入口文件
            if any(x in file_str for x in ["__main__", "main", "fastapi_app", "config"]):
                continue

            if import_counts.get(file_str, 0) == 0:
                # 检查是否真的没有导入
                self.usage_stats[file_str] = CodeUsage(
                    file_path=file_str, import_count=0, is_legacy=True
                )

    def _identify_unused_functions(self, py_files: List[Path]) -> None:
        """识别未使用的函数"""
        print("[ANALYZE] 识别未使用的函数...")

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                file_str = str(py_file)

                # 提取所有函数定义
                func_pattern = re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE)
                all_functions = [m.group(1) for m in func_pattern.finditer(content)]

                if not all_functions:
                    continue

                # 统计函数被调用次数
                used_functions = []
                for func in all_functions:
                    # 排除自己定义处的匹配
                    call_count = len(re.findall(rf"\b{func}\s*\(", content))

                    # 减 1 因为定义本身匹配一次
                    if call_count > 1:
                        used_functions.append(func)

                unused = [f for f in all_functions if f not in used_functions]

                if file_str in self.usage_stats:
                    self.usage_stats[file_str].total_functions = len(all_functions)
                    self.usage_stats[file_str].unused_functions = unused
                    self.usage_stats[file_str].used_functions = len(used_functions)

            except Exception as e:
                print(f"[WARN] 分析函数失败 {py_file}: {e}")

    def generate_cleanup_report(self) -> str:
        """生成清理报告"""
        lines = [
            "=" * 80,
            "传统代码清理报告",
            "=" * 80,
            "",
            f"统计文件数: {len(self.usage_stats)}",
            "",
            "-" * 80,
            "可清理文件列表",
            "-" * 80,
        ]

        legacy_files = [stat for stat in self.usage_stats.values() if stat.is_legacy]

        if not legacy_files:
            lines.append("未发现明显未使用的文件")
        else:
            for stat in sorted(legacy_files, key=lambda x: x.file_path):
                lines.append(f"\n文件: {stat.file_path}")
                lines.append(f"  被导入次数: {stat.import_count}")
                lines.append(f"  总函数: {stat.total_functions}")
                lines.append(f"  未使用函数: {len(stat.unused_functions)}")
                if stat.unused_functions:
                    for func in stat.unused_functions[:5]:
                        lines.append(f"    - {func}")
                    if len(stat.unused_functions) > 5:
                        lines.append(f"    ... 还有 {len(stat.unused_functions) - 5} 个")

        lines.extend(
            [
                "",
                "=" * 80,
                "清理建议",
                "=" * 80,
                "",
                "1. 对于确认未使用的文件:",
                "   - 移动到 legacy/ 目录",
                "   - 或添加 deprecation 警告",
                "   - 或在 3 个月后删除",
                "",
                "2. 对于未使用的函数:",
                "   - 检查是否是公共 API",
                "   - 如果不是，标记为内部使用",
                "   - 添加单元测试覆盖",
                "",
                "3. 注意事项:",
                "   - 不要删除入口文件",
                "   - 不要删除配置相关文件",
                "   - 删除前确保有备份",
                "",
                "=" * 80,
            ]
        )

        return "\n".join(lines)

    def save_report(self, output_path: str = "e:/FHD/cleanup_report.txt") -> None:
        """保存报告"""
        report = self.generate_cleanup_report()
        Path(output_path).write_text(report, encoding="utf-8")
        print(f"\n[SAVE] 报告已保存: {output_path}")

    def mark_legacy_files(self) -> None:
        """标记传统文件"""
        for file_path, stat in self.usage_stats.items():
            if stat.is_legacy:
                self._add_deprecation_notice(Path(file_path))

    def _add_deprecation_notice(self, file_path: Path) -> None:
        """添加废弃警告到文件"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 检查是否已有警告
            if "DEPRECATED" in content or "LEGACY" in content:
                return

            # 在文件头部添加警告
            notice = '''\
"""
[DEPRECATED] 此文件已被标记为传统代码

状态: 未使用或即将迁移
建议: 
  1. 检查是否有其他代码依赖此文件
  2. 如果有依赖，规划迁移路径
  3. 如果没有依赖，考虑删除

标记日期: 2026-04-18
预计清理日期: 2026-07-18 (3个月后)
"""

'''
            new_content = notice + content

            # 实际修改
            file_path.write_text(new_content, encoding="utf-8")
            print(f"[MARK] 已标记: {file_path}")

        except Exception as e:
            print(f"[ERROR] 标记失败 {file_path}: {e}")


def main():
    """主函数"""
    print("[START] 启动传统代码清理分析")
    print("=" * 60)

    cleaner = LegacyCodeCleaner()

    # 执行分析
    cleaner.analyze_codebase()

    # 生成报告
    print("\n" + cleaner.generate_cleanup_report())
    cleaner.save_report()

    # 询问是否标记文件
    print("\n" + "=" * 60)
    response = input("是否标记传统文件为 DEPRECATED? (y/n): ")

    if response.lower() == "y":
        cleaner.mark_legacy_files()
        print("[DONE] 标记完成")
    else:
        print("[SKIP] 跳过标记")

    print("\n[DONE] 清理分析完成")


if __name__ == "__main__":
    main()
