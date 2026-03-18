# -*- coding: utf-8 -*-
"""
蒸馏模型版本 API
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

distillation_bp = Blueprint('distillation', __name__)


def _get_distillation_checkpoints_dir():
    """蒸馏模型 checkpoints 目录"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "distillation", "checkpoints")


@distillation_bp.route('/api/distillation/versions', methods=['GET'])
def get_distillation_versions():
    """查看蒸馏模型版本（last.pt / best.pt / vocab.json 及修改时间）"""
    try:
        ckpt_dir = _get_distillation_checkpoints_dir()
        versions = []

        for name in ("last.pt", "best.pt", "vocab.json"):
            path = os.path.join(ckpt_dir, name)
            if os.path.isfile(path):
                try:
                    mtime = os.path.getmtime(path)
                    versions.append({
                        "name": name,
                        "label": "最新训练" if name == "last.pt" else ("当前最优" if name == "best.pt" else "词表"),
                        "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                        "size_kb": round(os.path.getsize(path) / 1024, 1),
                    })
                except OSError:
                    versions.append({"name": name, "label": name, "modified": "-", "size_kb": 0})

        db_path = _get_distillation_db_path()
        count = 0
        if os.path.exists(db_path):
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.execute("SELECT COUNT(*) FROM distillation_log")
                count = cur.fetchone()[0]
                conn.close()
            except Exception as e:
                logger.debug(f"读取蒸馏数据库失败: {e}")

        return jsonify({
            "success": True,
            "versions": versions,
            "distillation_samples": count,
        })
    except Exception as e:
        logger.error(f"获取蒸馏版本失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def _get_distillation_db_path():
    """蒸馏数据库路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "distillation", "distillation.db")
