"""
Neuro-DDD 使用率统计分析脚本

量化分析项目中 Neuro-DDD 架构的实际使用情况
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# 定义 Neuro-DDD 核心标识
NEURO_PATTERNS = [
    r"get_neuro_bus\(\)",
    r"publish_event\s*\(",
    r"NeuroEvent\s*\(",
    r"subscribe_event\s*\(",
    r"neuro_bus\.publish",
    r"neuro_bus\.subscribe",
    r"from app\.neuro_bus",
    r"import.*neuro_bus",
    r"NeuroDomain",
    r"DomainChannel",
]

# 传统架构标识
TRADITIONAL_PATTERNS = [
    r"@app\.route\s*\(",
    r"@router\.(get|post|put|delete)\s*\(",
    r"db\.session\.",
    r"SessionLocal\(\)",
    r"from app\.services\.",
    r"from app\.utils\.",
]


def analyze_file(file_path):
    """分析单个文件的 Neuro-DDD 使用情况"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        neuro_matches = []
        traditional_matches = []

        for pattern in NEURO_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                neuro_matches.extend(matches)

        for pattern in TRADITIONAL_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                traditional_matches.extend(matches)

        return {
            "neuro_count": len(neuro_matches),
            "traditional_count": len(traditional_matches),
            "neuro_patterns": list(set(neuro_matches)),
            "traditional_patterns": list(set(traditional_matches)),
        }
    except Exception as e:
        return None


def scan_directory(root_dir, extensions=None):
    """扫描目录并统计"""
    if extensions is None:
        extensions = [".py", ".vue", ".ts", ".js"]

    stats = defaultdict(lambda: {"neuro": 0, "traditional": 0, "files": []})

    for root, dirs, files in os.walk(root_dir):
        # 跳过特定目录
        if any(
            skip in root
            for skip in ["node_modules", "__pycache__", ".git", "venv", "dist", "build"]
        ):
            continue

        for file in files:
            if not any(file.endswith(ext) for ext in extensions):
                continue

            file_path = os.path.join(root, file)
            result = analyze_file(file_path)

            if result and (result["neuro_count"] > 0 or result["traditional_count"] > 0):
                rel_path = os.path.relpath(file_path, root_dir)

                # 按模块分类
                module = rel_path.split(os.sep)[0] if os.sep in rel_path else "root"

                stats[module]["files"].append(
                    {
                        "path": rel_path,
                        "neuro": result["neuro_count"],
                        "traditional": result["traditional_count"],
                        "neuro_patterns": result["neuro_patterns"],
                    }
                )

                stats[module]["neuro"] += result["neuro_count"]
                stats[module]["traditional"] += result["traditional_count"]

    return stats


def print_report(stats):
    """打印统计报告"""
    print("\n" + "=" * 80)
    print("Neuro-DDD 使用率统计报告")
    print("=" * 80)

    total_neuro = 0
    total_traditional = 0
    total_files = 0

    module_stats = []

    for module, data in sorted(stats.items(), key=lambda x: x[1]["neuro"], reverse=True):
        neuro_count = data["neuro"]
        traditional_count = data["traditional"]
        file_count = len(data["files"])
        total = neuro_count + traditional_count

        if total == 0:
            continue

        neuro_ratio = (neuro_count / total * 100) if total > 0 else 0

        module_stats.append(
            {
                "module": module,
                "neuro": neuro_count,
                "traditional": traditional_count,
                "total": total,
                "ratio": neuro_ratio,
                "files": file_count,
            }
        )

        total_neuro += neuro_count
        total_traditional += traditional_count
        total_files += file_count

    # 按模块打印
    print(
        f"\n{'模块':<25} {'Neuro':>8} {'Traditional':>12} {'Total':>8} {'Neuro%':>10} {'Files':>8}"
    )
    print("-" * 80)

    for stat in module_stats:
        print(
            f"{stat['module']:<25} {stat['neuro']:>8} {stat['traditional']:>12} "
            f"{stat['total']:>8} {stat['ratio']:>9.1f}% {stat['files']:>8}"
        )

    print("-" * 80)
    grand_total = total_neuro + total_traditional
    overall_ratio = (total_neuro / grand_total * 100) if grand_total > 0 else 0
    print(
        f"{'TOTAL':<25} {total_neuro:>8} {total_traditional:>12} "
        f"{grand_total:>8} {overall_ratio:>9.1f}% {total_files:>8}"
    )

    print("\n" + "=" * 80)
    print("关键发现")
    print("=" * 80)

    # 找出 Neuro 使用率最高的文件
    all_files = []
    for module, data in stats.items():
        for file_info in data["files"]:
            if file_info["neuro"] > 0:
                all_files.append(
                    {
                        "module": module,
                        "path": file_info["path"],
                        "neuro": file_info["neuro"],
                        "traditional": file_info["traditional"],
                    }
                )

    all_files.sort(key=lambda x: x["neuro"], reverse=True)

    print("\nNeuro-DDD 使用最多的 Top 10 文件:")
    for i, file_info in enumerate(all_files[:10], 1):
        total = file_info["neuro"] + file_info["traditional"]
        ratio = (file_info["neuro"] / total * 100) if total > 0 else 0
        print(f"{i:2}. [{file_info['module']}] {file_info['path']}")
        print(
            f"    Neuro: {file_info['neuro']}, Traditional: {file_info['traditional']}, Ratio: {ratio:.1f}%"
        )

    # 分析核心业务模块
    print("\n" + "=" * 80)
    print("核心业务模块分析")
    print("=" * 80)

    core_modules = ["application", "services", "routes"]
    for module in core_modules:
        if module in stats:
            data = stats[module]
            total = data["neuro"] + data["traditional"]
            ratio = (data["neuro"] / total * 100) if total > 0 else 0
            print(f"\n{module.upper()} 层:")
            print(f"  Neuro-DDD 调用：{data['neuro']} 次")
            print(f"  传统调用：{data['traditional']} 次")
            print(f"  Neuro 使用率：{ratio:.1f}%")
            print(f"  涉及文件数：{len(data['files'])}")

    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)

    if overall_ratio < 30:
        print(f"\n⚠️  Neuro-DDD 整体使用率仅为 {overall_ratio:.1f}%，大部分业务仍使用传统架构")
    elif overall_ratio < 50:
        print(f"\n📊 Neuro-DDD 使用率为 {overall_ratio:.1f}%，与传统架构并存")
    else:
        print(f"\n✅ Neuro-DDD 已成为主流架构，使用率达 {overall_ratio:.1f}%")

    print("\n建议:")
    print("1. 核心业务逻辑应优先迁移至 Neuro-DDD 架构")
    print("2. 新增功能应使用 Neuro-DDD 模式")
    print("3. 建立架构迁移路线图，逐步提升使用率")


if __name__ == "__main__":
    # 分析 app 目录
    app_dir = r"e:\FHD\app"
    print(f"\n分析目录：{app_dir}")

    stats = scan_directory(app_dir)
    print_report(stats)

    # 分析 backend 目录
    backend_dir = r"e:\FHD\backend"
    print(f"\n\n分析目录：{backend_dir}")

    backend_stats = scan_directory(backend_dir)
    print_report(backend_stats)
