#!/usr/bin/env python3
"""
执行完整的 Neuro-DDD 迁移

一键完成所有迁移步骤：
1. 验证所有事件定义
2. 验证所有 V2 服务
3. 注册所有领域处理器
4. 更新路由层到 V2
5. 验证迁移完成
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"[STEP] {description}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd, cwd="e:/FHD", capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )

        if result.returncode == 0:
            print(f"[OK] {description} 完成")
            if result.stdout:
                print(result.stdout[-1000:])
            return True
        else:
            print(f"[ERROR] {description} 失败")
            if result.stderr:
                print(result.stderr[-500:])
            return False

    except Exception as e:
        print(f"[ERROR] {description} 异常: {e}")
        return False


def execute_migration():
    """执行完整迁移"""
    print("=" * 60)
    print("Neuro-DDD 完整迁移执行器")
    print("=" * 60)
    print("\n此脚本将执行以下步骤:")
    print("  1. 检测当前迁移状态")
    print("  2. 验证事件定义")
    print("  3. 验证 V2 服务")
    print("  4. 注册所有领域处理器")
    print("  5. 更新路由层到 V2")
    print("  6. 最终验证")

    # 确认
    print("\n" + "=" * 60)
    response = input("确认执行完整迁移? (yes/no): ")

    if response.lower() != "yes":
        print("操作已取消")
        return

    results = {}

    # 1. 检测当前状态
    results["detect"] = run_command(
        [sys.executable, "scripts/detect_migration_status.py"], "检测迁移状态"
    )

    # 2. 批量修复
    results["fix"] = run_command([sys.executable, "scripts/batch_migration_fix.py"], "批量修复")

    # 3. 验证迁移
    results["validate"] = run_command([sys.executable, "scripts/validate_migration.py"], "验证迁移")

    # 4. 更新路由（可选）
    print(f"\n{'='*60}")
    print("[STEP] 更新路由层")
    print("=" * 60)
    response = input("是否更新路由层到 V2? (yes/no): ")

    if response.lower() == "yes":
        results["update_routes"] = run_command(
            [sys.executable, "scripts/update_routes_to_v2.py"], "更新路由层"
        )
    else:
        print("[SKIP] 跳过路由层更新")
        results["update_routes"] = None

    # 打印总结
    print("\n" + "=" * 60)
    print("迁移执行总结")
    print("=" * 60)

    for step, success in results.items():
        if success is None:
            status = "[SKIP]"
        elif success:
            status = "[OK]"
        else:
            status = "[FAIL]"
        print(f"  {status} {step}")

    success_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)

    print(f"\n成功率: {success_count}/{total_count}")

    if success_count == total_count:
        print("\n[OK] 所有步骤成功完成！")
        print("\n下一步:")
        print("  1. 测试所有功能")
        print("  2. 运行应用")
        print("  3. 监控事件流")
    else:
        print("\n[WARNING] 部分步骤失败，请检查日志")


if __name__ == "__main__":
    execute_migration()
