# -*- coding: utf-8 -*-
"""
蒸馏模型版本 API
"""
import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.db import SessionLocal
from app.utils.distillation_paths import (
    get_distillation_checkpoints_dir,
)

logger = logging.getLogger(__name__)

distillation_bp = Blueprint('distillation', __name__)


def _get_distillation_checkpoints_dir():
    """蒸馏模型 checkpoints 目录。"""
    return get_distillation_checkpoints_dir()


@distillation_bp.route('/api/distillation/versions', methods=['GET'])
def get_distillation_versions():
    """查看蒸馏模型版本（last.pt / best.pt / vocab.json 及修改时间）"""
    try:
        ckpt_dir = _get_distillation_checkpoints_dir()
        versions = []
        sample_count_error = None

        for name in ("last.pt", "best.pt", "vocab.json"):
            path = os.path.join(ckpt_dir, name)
            exists = os.path.exists(path)
            path_type = "missing"
            if exists:
                if os.path.isdir(path):
                    path_type = "directory"
                elif os.path.isfile(path):
                    path_type = "file"
                else:
                    path_type = "other"

            if exists:
                label = "最新训练" if name == "last.pt" else ("当前最优" if name == "best.pt" else "词表")
                entry = {
                    "name": name,
                    "label": label,
                    "exists": True,
                    "type": path_type,
                    "modified": "-",
                    "size_kb": 0,
                }
                try:
                    mtime = os.path.getmtime(path)
                    entry["modified"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    if os.path.isfile(path):
                        entry["size_kb"] = round(os.path.getsize(path) / 1024, 1)
                except OSError:
                    pass
                versions.append(entry)

        count = 0
        try:
            with SessionLocal() as db:
                result = db.execute(text("SELECT COUNT(*) FROM distillation_log"))
                count = int(result.scalar() or 0)
        except Exception as e:
            sample_count_error = str(e)
            logger.debug(f"读取蒸馏数据库失败: {e}")

        response = {
            "success": True,
            "versions": versions,
            "distillation_samples": count,
        }
        if sample_count_error:
            response["sample_count_error"] = sample_count_error
        return jsonify(response)
    except Exception as e:
        logger.error(f"获取蒸馏版本失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
