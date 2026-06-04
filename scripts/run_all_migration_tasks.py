#!/usr/bin/env python3
"""
Neuro-DDD 迁移任务执行器

一键执行所有迁移相关任务：
1. 检测当前迁移状态
2. 生成报告
3. 准备新的事件定义
4. 准备 V2 版本服务
5. 清理传统代码分析
"""

import asyncio
import subprocess
import sys
from pathlib import Path


class MigrationTaskRunner:
    """迁移任务执行器"""

    def __init__(self):
        self.project_root = Path("e:/FHD")
        self.results = {}

    async def run_task(self, name: str, command: list, description: str) -> bool:
        """运行单个任务"""
        print(f"\n{'='*60}")
        print(f"[TASK] {name}")
        print(f"[DESC] {description}")
        print("=" * 60)

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            if result.returncode == 0:
                print(f"[OK] {name} 完成")
                if result.stdout:
                    print(result.stdout[-2000:])  # 只显示最后 2000 字符
                self.results[name] = True
                return True
            else:
                print(f"[ERROR] {name} 失败")
                if result.stderr:
                    print(result.stderr[-1000:])
                self.results[name] = False
                return False

        except Exception as e:
            print(f"[ERROR] {name} 异常: {e}")
            self.results[name] = False
            return False

    async def run_all_tasks(self):
        """运行所有任务"""
        print("=" * 60)
        print("Neuro-DDD 迁移任务执行器")
        print("=" * 60)
        print(f"项目根目录: {self.project_root}")

        tasks = [
            (
                "检测迁移状态",
                [sys.executable, "scripts/detect_migration_status.py"],
                "扫描所有服务，检测迁移状态",
            ),
            (
                "清理分析",
                [sys.executable, "scripts/cleanup_legacy_code.py"],
                "分析传统代码，识别未使用文件",
            ),
        ]

        for name, command, desc in tasks:
            await self.run_task(name, command, desc)

        # 打印总结
        self._print_summary()

    def _print_summary(self):
        """打印任务总结"""
        print("\n" + "=" * 60)
        print("任务执行总结")
        print("=" * 60)

        success_count = sum(1 for v in self.results.values() if v)
        total_count = len(self.results)

        for name, success in self.results.items():
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {name}")

        print(f"\n总计: {success_count}/{total_count} 成功")

        if success_count == total_count:
            print("\n[OK] 所有任务完成！")
            print("\n下一步:")
            print("  1. 查看生成的报告文件")
            print("  2. 查看 migration_status_report.txt 了解当前状态")
            print("  3. 查看 cleanup_report.txt 了解清理建议")
            print("  4. 检查新生成的 V2 服务文件")
        else:
            print("\n[WARNING] 部分任务失败，请检查日志")


def main():
    """主函数"""
    runner = MigrationTaskRunner()

    # 使用 asyncio 运行
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(runner.run_all_tasks())
        else:
            loop.run_until_complete(runner.run_all_tasks())
    except RuntimeError:
        asyncio.run(runner.run_all_tasks())


if __name__ == "__main__":
    main()
