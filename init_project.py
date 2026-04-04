# -*- coding: utf-8 -*-
"""
初始化项目必要的目录和数据库表

运行此脚本可修复以下 API 错误:
- /api/distillation/versions (502)
- /api/preferences (502)
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR

def init_distillation_dirs():
    """初始化蒸馏相关目录"""
    distillation_root = os.path.join(BASE_DIR, "distillation")
    checkpoints_dir = os.path.join(distillation_root, "checkpoints")
    logs_dir = os.path.join(distillation_root, "logs")

    for d in [distillation_root, checkpoints_dir, logs_dir]:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            print(f"创建目录: {d}")

    training_data = os.path.join(distillation_root, "training_data.jsonl")
    if not os.path.exists(training_data):
        with open(training_data, 'w', encoding='utf-8') as f:
            pass
        print(f"创建文件: {training_data}")

def init_user_memory_dir():
    """初始化用户记忆目录"""
    memory_dir = os.path.join(BASE_DIR, "user_memory")
    if not os.path.exists(memory_dir):
        os.makedirs(memory_dir, exist_ok=True)
        print(f"创建目录: {memory_dir}")

    memory_store = os.path.join(memory_dir, "memory_store.json")
    if not os.path.exists(memory_store):
        with open(memory_store, 'w', encoding='utf-8') as f:
            f.write("{}")
        print(f"创建文件: {memory_store}")

def init_db_tables():
    """初始化数据库表"""
    try:
        from app.db import engine
        from app.db.init_db import init_distillation_tables, initialize_databases

        print("初始化数据库...")
        initialize_databases()
        init_distillation_tables(engine)
        print("数据库表初始化完成")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        print("注意: 如果数据库已存在此操作是安全的")

if __name__ == "__main__":
    print("=" * 50)
    print("XCAGI 项目初始化")
    print(f"基础目录: {BASE_DIR}")
    print("=" * 50)

    print("\n1. 初始化蒸馏目录...")
    init_distillation_dirs()

    print("\n2. 初始化用户记忆目录...")
    init_user_memory_dir()

    print("\n3. 初始化数据库表...")
    init_db_tables()

    print("\n" + "=" * 50)
    print("初始化完成!")
    print("=" * 50)