#!/usr/bin/env python3
"""
批量更新路由文件使用 V2 服务

警告: 此脚本会直接修改路由文件，请确保已备份！
"""

import re
from pathlib import Path

# V1 到 V2 的导入映射
IMPORT_MAPPING = {
    "from app.application.product_app_service import get_product_app_service": "from app.application.product_app_service_v2 import get_product_app_service_v2",
    "from app.application.shipment_app_service import get_shipment_application_service": "from app.application.shipment_app_service_v2 import get_shipment_app_service_v2",
    "from app.application.auth_app_service import get_auth_app_service": "from app.application.auth_app_service_v2 import get_auth_app_service_v2",
    "from app.application.user_app_service import get_user_app_service": "from app.application.user_app_service_v2 import get_user_app_service_v2",
    "from app.application.customer_app_service import get_customer_app_service": "from app.application.customer_app_service_v2 import get_customer_app_service_v2",
    "from app.application.print_app_service import get_print_app_service": "from app.application.print_app_service_v2 import get_print_app_service_v2",
    "from app.application.ocr_app_service import get_ocr_app_service": "from app.application.ocr_app_service_v2 import get_ocr_app_service_v2",
    "from app.application.ai_chat_app_service import get_ai_chat_app_service": "from app.application.ai_chat_app_service_v2 import get_ai_chat_app_service_v2",
    "from app.application.conversation_app_service import get_conversation_app_service": "from app.application.conversation_app_service_v2 import get_conversation_app_service_v2",
    "from app.application.wechat_task_app_service import get_wechat_task_app_service": "from app.application.wechat_task_app_service_v2 import get_wechat_task_app_service_v2",
    "from app.application.wechat_contact_app_service import get_wechat_contact_app_service": "from app.application.wechat_contact_app_service_v2 import get_wechat_contact_app_service_v2",
    "from app.application.material_app_service import get_material_app_service": "from app.application.material_app_service_v2 import get_material_app_service_v2",
}

# 函数名替换映射
FUNC_MAPPING = {
    "get_product_app_service()": "get_product_app_service_v2()",
    "get_shipment_application_service()": "get_shipment_app_service_v2()",
    "get_auth_app_service()": "get_auth_app_service_v2()",
    "get_user_app_service()": "get_user_app_service_v2()",
    "get_customer_app_service()": "get_customer_app_service_v2()",
    "get_print_app_service()": "get_print_app_service_v2()",
    "get_ocr_app_service()": "get_ocr_app_service_v2()",
    "get_ai_chat_app_service()": "get_ai_chat_app_service_v2()",
    "get_conversation_app_service()": "get_conversation_app_service_v2()",
    "get_wechat_task_app_service()": "get_wechat_task_app_service_v2()",
    "get_wechat_contact_app_service()": "get_wechat_contact_app_service_v2()",
    "get_material_app_service()": "get_material_app_service_v2()",
}


def update_route_file(file_path: Path) -> bool:
    """更新单个路由文件"""
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 替换导入
    for old_import, new_import in IMPORT_MAPPING.items():
        content = content.replace(old_import, new_import)

    # 替换函数调用
    for old_func, new_func in FUNC_MAPPING.items():
        content = content.replace(old_func, new_func)

    if content != original_content:
        # 创建备份
        backup_path = file_path.with_suffix(".py.v1_backup")
        backup_path.write_text(original_content, encoding="utf-8")

        # 写入新内容
        file_path.write_text(content, encoding="utf-8")
        return True

    return False


def main():
    """主函数"""
    print("=" * 60)
    print("批量更新路由文件到 V2 版本")
    print("=" * 60)

    project_root = Path("e:/FHD")
    routes_dirs = [
        project_root / "app" / "fastapi_routes",
        project_root / "app" / "fastapi_compat_routes",
    ]

    updated_count = 0

    for routes_dir in routes_dirs:
        if not routes_dir.exists():
            continue

        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("__"):
                continue

            print(f"[PROCESSING] {route_file.name}")

            try:
                if update_route_file(route_file):
                    updated_count += 1
                    print(f"  [UPDATED] {route_file.name}")
                else:
                    print(f"  [SKIP] 无需更新")
            except Exception as e:
                print(f"  [ERROR] {e}")

    print("\n" + "=" * 60)
    print(f"更新完成: {updated_count} 个文件")
    print("=" * 60)
    print("\n备份文件后缀: .py.v1_backup")
    print("如需回滚，请使用备份文件恢复")


if __name__ == "__main__":
    # 安全确认
    print("警告: 此脚本会直接修改路由文件！")
    response = input("是否继续? (yes/no): ")

    if response.lower() == "yes":
        main()
    else:
        print("操作已取消")
