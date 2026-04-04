"""
蒸馏功能统一路径定义。

集中维护 distillation 目录相关路径，避免不同模块使用不一致的相对层级。
"""

from __future__ import annotations

import os

from app.utils.path_utils import get_base_dir


def get_distillation_root_dir() -> str:
    """返回蒸馏根目录。"""
    return os.path.join(get_base_dir(), "distillation")


def get_distillation_checkpoints_dir() -> str:
    """返回蒸馏模型 checkpoints 目录。"""
    return os.path.join(get_distillation_root_dir(), "checkpoints")


def get_distillation_logs_dir() -> str:
    """返回蒸馏日志目录。"""
    return os.path.join(get_distillation_root_dir(), "logs")


def get_distillation_db_path() -> str:
    """返回蒸馏 sqlite 数据库路径。"""
    return os.path.join(get_distillation_root_dir(), "distillation.db")


def get_distillation_training_data_path() -> str:
    """返回蒸馏训练数据文件路径。"""
    return os.path.join(get_distillation_root_dir(), "training_data.jsonl")
