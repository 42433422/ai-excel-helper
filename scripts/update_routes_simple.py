#!/usr/bin/env python3
"""
简化版路由层更新脚本

直接更新 backend 路由使用 V2 服务
"""

import re
from pathlib import Path


# 导入替换映射
IMPORT_MAP = {
    # Products
    "from app.application.product_app_service import get_product_app_service": "from app.application.product_app_service_v2 import get_product_app_service_v2",
    # Shipment
    "from app.application.shipment_app_service import get_shipment_application_service": "from app.application.shipment_app_service_v2 import get_shipment_app_service_v2",
    # OCR
    "from app.application.ocr_app_service import get_ocr_app_service": "from app.application.ocr_app_service_v2 import get_ocr_app_service_v2",
    # Print
    "from app.application.print_app_service import get_print_app_service": "from app.application.print_app_service_v2 import get_print_app_service_v2",
    # Material/Inventory
    "from app.application.material_app_service import get_material_app_service": "from app.application.material_app_service_v2 import get_material_app_service_v2",
    # AI
    "from app.application.ai_chat_app_service import get_ai_chat_app_service": "from app.application.ai_chat_app_service_v2 import get_ai_chat_app_service_v2",
    # WeChat
    "from app.application.wechat_task_app_service import get_wechat_task_app_service": "from app.application.wechat_task_app_service_v2 import get_wechat_task_app_service_v2",
    "from app.application.wechat_contact_app_service import get_wechat_contact_app_service": "from app.application.wechat_contact_app_service_v2 import get_wechat_contact_app_service_v2",
}

# 函数调用替换
FUNC_MAP = {
    "get_product_app_service()": "get_product_app_service_v2()",
    "get_shipment_application_service()": "get_shipment_app_service_v2()",
    "get_ocr_app_service()": "get_ocr_app_service_v2()",
    "get_print_app_service()": "get_print_app_service_v2()",
    "get_material_app_service()": "get_material_app_service_v2()",
    "get_ai_chat_app_service()": "get_ai_chat_app_service_v2()",
    "get_wechat_task_app_service()": "get_wechat_task_app_service_v2()",
    "get_wechat_contact_app_service()": "get_wechat_contact_app_service_v2()",
}


def update_file(file_path: Path) -> bool:
    """更新单个文件"""
    content = file_path.read_text(encoding="utf-8")
    original = content

    # 替换导入
    for old, new in IMPORT_MAP.items():
        content = content.replace(old, new)

    # 替换函数调用
    for old, new in FUNC_MAP.items():
        content = content.replace(old, new)

    if content != original:
        # 备份
        backup = file_path.with_suffix(".py.backup")
        backup.write_text(original, encoding="utf-8")
        # 写入
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("更新 Backend 路由层到 V2")
    print("=" * 60)

    project = Path("e:/FHD")
    routes_dirs = [
        project / "app" / "fastapi_routes",
        project / "app" / "fastapi_compat_routes",
    ]

    updated = 0
    for routes_dir in routes_dirs:
        if not routes_dir.exists():
            continue

        for py_file in routes_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            if update_file(py_file):
                updated += 1
                print(f"[UPDATED] {py_file.name}")

    print(f"\n[SUMMARY] 更新了 {updated} 个文件")
    print("\n备份文件后缀: .py.backup")


if __name__ == "__main__":
    main()
