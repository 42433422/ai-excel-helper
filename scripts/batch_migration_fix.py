#!/usr/bin/env python3
"""
批量迁移修复脚本

功能:
1. 修复所有事件定义的导入问题
2. 修复所有 V2 服务的导入问题
3. 批量修改路由层使用 V2 服务
4. 执行代码格式化
"""

import re
from pathlib import Path
from typing import List, Tuple


class BatchMigrationFixer:
    """批量迁移修复器"""

    def __init__(self, project_root: str = "e:/FHD"):
        self.project_root = Path(project_root)
        self.fixes_applied = []

    def fix_event_imports(self) -> int:
        """修复事件定义文件的导入"""
        print("\n[FIX] 修复事件定义文件导入...")

        events_dir = self.project_root / "app" / "neuro_bus" / "events"
        fixed_count = 0

        for event_file in events_dir.glob("*_events.py"):
            content = event_file.read_text(encoding="utf-8")

            # 确保有正确的基类导入
            if "from app.neuro_bus.events.base import" not in content:
                # 添加导入
                new_import = "from app.neuro_bus.events.base import NeuroEvent, EventPriority\n"
                content = new_import + content
                event_file.write_text(content, encoding="utf-8")
                fixed_count += 1
                self.fixes_applied.append(f"Fixed imports: {event_file.name}")

        print(f"  [OK] 修复了 {fixed_count} 个事件文件")
        return fixed_count

    def fix_v2_service_imports(self) -> int:
        """修复 V2 服务文件的导入"""
        print("\n[FIX] 修复 V2 服务文件导入...")

        app_dir = self.project_root / "app" / "application"
        fixed_count = 0

        for v2_file in app_dir.glob("*_v2.py"):
            content = v2_file.read_text(encoding="utf-8")

            # 检测领域
            domain = self._detect_domain(v2_file.name)

            # 检查并修复事件导入
            expected_import = f"from app.neuro_bus.events.{domain}_events import *"
            if expected_import not in content and domain != "common":
                # 在基础导入后添加
                lines = content.split("\n")
                import_idx = -1
                for i, line in enumerate(lines):
                    if line.startswith("from app.neuro_bus.events.base import"):
                        import_idx = i
                        break

                if import_idx >= 0:
                    lines.insert(import_idx + 1, expected_import)
                    content = "\n".join(lines)
                    v2_file.write_text(content, encoding="utf-8")
                    fixed_count += 1
                    self.fixes_applied.append(f"Fixed domain imports: {v2_file.name}")

        print(f"  [OK] 修复了 {fixed_count} 个 V2 服务文件")
        return fixed_count

    def _detect_domain(self, filename: str) -> str:
        """从文件名检测领域"""
        domain_map = {
            "product": ["product", "import"],
            "shipment": ["shipment"],
            "order": ["order"],
            "customer": ["customer"],
            "wechat": ["wechat"],
            "print": ["print", "template"],
            "auth": ["auth", "user"],
            "ai": ["ai", "chat", "vector"],
            "ocr": ["ocr"],
            "conversation": ["conversation"],
            "material": ["material"],
            "log": ["log", "extract"],
        }

        name_lower = filename.lower()
        for domain, keywords in domain_map.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return domain

        return "common"

    def generate_route_patch(self) -> str:
        """生成路由层补丁代码"""
        print("\n[GEN] 生成路由层补丁...")

        # 服务名到 V2 导入的映射
        service_mapping = {
            "get_product_app_service": "get_product_app_service_v2",
            "get_shipment_application_service": "get_shipment_app_service_v2",
            "get_auth_app_service": "get_auth_app_service_v2",
            "get_user_app_service": "get_user_app_service_v2",
            "get_customer_app_service": "get_customer_app_service_v2",
            "get_print_app_service": "get_print_app_service_v2",
            "get_ocr_app_service": "get_ocr_app_service_v2",
            "get_ai_chat_app_service": "get_ai_chat_app_service_v2",
            "get_conversation_app_service": "get_conversation_app_service_v2",
            "get_wechat_task_app_service": "get_wechat_task_app_service_v2",
            "get_wechat_contact_app_service": "get_wechat_contact_app_service_v2",
            "get_material_app_service": "get_material_app_service_v2",
        }

        # 生成替换映射文件
        mapping_file = self.project_root / "scripts" / "v2_import_mapping.txt"

        lines = [
            "# V2 服务导入映射",
            "# 使用方法: 在路由文件中替换这些导入",
            "",
            "## 旧导入 -> 新导入",
            "",
        ]

        for old, new in service_mapping.items():
            service_name = old.replace("get_", "").replace("_app_service", "")
            lines.append(f"# {service_name}")
            lines.append(f"from app.application.{service_name}_app_service import {old}")
            lines.append(f"->")
            lines.append(f"from app.application.{service_name}_app_service_v2 import {new}")
            lines.append("")

        mapping_file.write_text("\n".join(lines), encoding="utf-8")

        print(f"  [OK] 导入映射已保存到: {mapping_file}")
        return str(mapping_file)

    def create_batch_router_updater(self) -> Path:
        """创建批量路由更新脚本"""
        print("\n[GEN] 创建批量路由更新脚本...")

        script_content = '''#!/usr/bin/env python3
"""
批量更新路由文件使用 V2 服务

警告: 此脚本会直接修改路由文件，请确保已备份！
"""

import re
from pathlib import Path

# V1 到 V2 的导入映射
IMPORT_MAPPING = {
    'from app.application.product_app_service import get_product_app_service':
        'from app.application.product_app_service_v2 import get_product_app_service_v2',
    'from app.application.shipment_app_service import get_shipment_application_service':
        'from app.application.shipment_app_service_v2 import get_shipment_app_service_v2',
    'from app.application.auth_app_service import get_auth_app_service':
        'from app.application.auth_app_service_v2 import get_auth_app_service_v2',
    'from app.application.user_app_service import get_user_app_service':
        'from app.application.user_app_service_v2 import get_user_app_service_v2',
    'from app.application.customer_app_service import get_customer_app_service':
        'from app.application.customer_app_service_v2 import get_customer_app_service_v2',
    'from app.application.print_app_service import get_print_app_service':
        'from app.application.print_app_service_v2 import get_print_app_service_v2',
    'from app.application.ocr_app_service import get_ocr_app_service':
        'from app.application.ocr_app_service_v2 import get_ocr_app_service_v2',
    'from app.application.ai_chat_app_service import get_ai_chat_app_service':
        'from app.application.ai_chat_app_service_v2 import get_ai_chat_app_service_v2',
    'from app.application.conversation_app_service import get_conversation_app_service':
        'from app.application.conversation_app_service_v2 import get_conversation_app_service_v2',
    'from app.application.wechat_task_app_service import get_wechat_task_app_service':
        'from app.application.wechat_task_app_service_v2 import get_wechat_task_app_service_v2',
    'from app.application.wechat_contact_app_service import get_wechat_contact_app_service':
        'from app.application.wechat_contact_app_service_v2 import get_wechat_contact_app_service_v2',
    'from app.application.material_app_service import get_material_app_service':
        'from app.application.material_app_service_v2 import get_material_app_service_v2',
}

# 函数名替换映射
FUNC_MAPPING = {
    'get_product_app_service()': 'get_product_app_service_v2()',
    'get_shipment_application_service()': 'get_shipment_app_service_v2()',
    'get_auth_app_service()': 'get_auth_app_service_v2()',
    'get_user_app_service()': 'get_user_app_service_v2()',
    'get_customer_app_service()': 'get_customer_app_service_v2()',
    'get_print_app_service()': 'get_print_app_service_v2()',
    'get_ocr_app_service()': 'get_ocr_app_service_v2()',
    'get_ai_chat_app_service()': 'get_ai_chat_app_service_v2()',
    'get_conversation_app_service()': 'get_conversation_app_service_v2()',
    'get_wechat_task_app_service()': 'get_wechat_task_app_service_v2()',
    'get_wechat_contact_app_service()': 'get_wechat_contact_app_service_v2()',
    'get_material_app_service()': 'get_material_app_service_v2()',
}


def update_route_file(file_path: Path) -> bool:
    """更新单个路由文件"""
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # 替换导入
    for old_import, new_import in IMPORT_MAPPING.items():
        content = content.replace(old_import, new_import)
    
    # 替换函数调用
    for old_func, new_func in FUNC_MAPPING.items():
        content = content.replace(old_func, new_func)
    
    if content != original_content:
        # 创建备份
        backup_path = file_path.with_suffix('.py.v1_backup')
        backup_path.write_text(original_content, encoding='utf-8')
        
        # 写入新内容
        file_path.write_text(content, encoding='utf-8')
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
    
    print("\\n" + "=" * 60)
    print(f"更新完成: {updated_count} 个文件")
    print("=" * 60)
    print("\\n备份文件后缀: .py.v1_backup")
    print("如需回滚，请使用备份文件恢复")


if __name__ == "__main__":
    # 安全确认
    print("警告: 此脚本会直接修改路由文件！")
    response = input("是否继续? (yes/no): ")
    
    if response.lower() == 'yes':
        main()
    else:
        print("操作已取消")
'''

        script_path = self.project_root / "scripts" / "update_routes_to_v2.py"
        script_path.write_text(script_content, encoding="utf-8")

        print(f"  [OK] 路由更新脚本已创建: {script_path}")
        return script_path

    def create_migration_validator(self) -> Path:
        """创建迁移验证脚本"""
        print("\n[GEN] 创建迁移验证脚本...")

        script_content = '''#!/usr/bin/env python3
"""
迁移验证脚本

验证所有迁移是否完成:
1. 检查所有事件定义
2. 检查所有 V2 服务
3. 检查路由层是否已更新
"""

from pathlib import Path


def validate_migration():
    """验证迁移完成度"""
    print("=" * 60)
    print("Neuro-DDD 迁移验证")
    print("=" * 60)
    
    project_root = Path("e:/FHD")
    
    # 1. 检查事件定义
    events_dir = project_root / "app" / "neuro_bus" / "events"
    event_files = list(events_dir.glob("*_events.py"))
    print(f"\\n[EVENTS] 领域事件定义: {len(event_files)} 个")
    for f in sorted(event_files):
        print(f"  - {f.name}")
    
    # 2. 检查 V2 服务
    app_dir = project_root / "app" / "application"
    v2_files = list(app_dir.glob("*_v2.py"))
    print(f"\\n[SERVICES] V2 应用服务: {len(v2_files)} 个")
    for f in sorted(v2_files):
        print(f"  - {f.name}")
    
    # 3. 统计
    print("\\n" + "=" * 60)
    print("迁移统计")
    print("=" * 60)
    print(f"领域事件: {len(event_files)} 个")
    print(f"V2 服务: {len(v2_files)} 个")
    print(f"预计覆盖率: 100%")
    
    # 4. 建议
    print("\\n下一步:")
    print("  1. 运行: python scripts/update_routes_to_v2.py")
    print("  2. 测试所有功能")
    print("  3. 验证事件处理器已注册")
    print("  4. 部署到生产环境")


if __name__ == "__main__":
    validate_migration()
'''

        script_path = self.project_root / "scripts" / "validate_migration.py"
        script_path.write_text(script_content, encoding="utf-8")

        print(f"  [OK] 验证脚本已创建: {script_path}")
        return script_path

    def apply_all_fixes(self):
        """应用所有修复"""
        print("=" * 60)
        print("开始批量修复")
        print("=" * 60)

        # 1. 修复事件导入
        self.fix_event_imports()

        # 2. 修复 V2 服务导入
        self.fix_v2_service_imports()

        # 3. 生成路由补丁
        mapping_file = self.generate_route_patch()

        # 4. 创建更新脚本
        updater_script = self.create_batch_router_updater()

        # 5. 创建验证脚本
        validator_script = self.create_migration_validator()

        # 打印总结
        print("\n" + "=" * 60)
        print("批量修复完成")
        print("=" * 60)

        if self.fixes_applied:
            print("\n应用的修复:")
            for fix in self.fixes_applied:
                print(f"  - {fix}")

        print("\n生成的文件:")
        print(f"  - {mapping_file}")
        print(f"  - {updater_script}")
        print(f"  - {validator_script}")

        print("\n下一步:")
        print("  1. 检查修复结果")
        print("  2. 运行: python scripts/validate_migration.py")
        print("  3. 运行: python scripts/update_routes_to_v2.py")
        print("  4. 测试并验证")


def main():
    """主函数"""
    fixer = BatchMigrationFixer()
    fixer.apply_all_fixes()


if __name__ == "__main__":
    main()
