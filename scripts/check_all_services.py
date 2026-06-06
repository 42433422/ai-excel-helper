#!/usr/bin/env python3
"""检查所有 Services 的迁移状态"""

from pathlib import Path

services_dir = Path("app/services")
services = [f for f in services_dir.glob("*.py") if not f.name.startswith("__")]

migrated = []
need_migration = []

for svc in sorted(services):
    content = svc.read_text(encoding="utf-8")
    has_neuro = "get_neuro_bus" in content or "NeuroEvent" in content
    if has_neuro:
        migrated.append(svc.name)
    else:
        need_migration.append(svc.name)

print("=" * 60)
print(f"Services 总数: {len(services)}")
print(f"已迁移: {len(migrated)}")
print(f"待迁移: {len(need_migration)}")
print("=" * 60)

print("\n已迁移 Services:")
for name in migrated:
    print(f"  [OK] {name}")

print("\n待迁移 Services:")
for name in need_migration:
    print(f"  [NEED] {name}")
