"""
数据库管理服务模块

提供数据库备份、恢复等业务逻辑。

此模块已迁移到 app/utils/
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List

from app.db.session import get_db

logger = logging.getLogger(__name__)


class DatabaseService:
    """数据库服务类"""

    def __init__(self):
        """初始化数据库服务"""
        pass

    def _get_db_path(self) -> str:
        """获取数据库文件路径"""
        from app.db.base import SQLALCHEMY_DATABASE_URI

        if SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
            db_path = SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
            return db_path
        return None

    def _get_backup_dir(self) -> str:
        """获取备份目录"""
        from app.utils.path_utils import get_data_dir
        backup_dir = os.path.join(get_data_dir(), "database_backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def backup_database(self) -> Dict[str, Any]:
        """
        备份数据库

        Returns:
            结果字典：
                - success: 是否成功
                - message: 响应消息
                - file_path: 备份文件路径
                - filename: 备份文件名
        """
        try:
            db_path = self._get_db_path()

            if not db_path:
                return {
                    "success": False,
                    "message": "仅支持 SQLite 数据库备份",
                    "file_path": None,
                    "filename": None
                }

            if not os.path.exists(db_path):
                return {
                    "success": False,
                    "message": f"数据库文件不存在：{db_path}",
                    "file_path": None,
                    "filename": None
                }

            backup_dir = self._get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_filename = os.path.basename(db_path)
            backup_filename = f"{db_filename}.{timestamp}.bak"
            backup_path = os.path.join(backup_dir, backup_filename)

            shutil.copy2(db_path, backup_path)

            logger.info(f"数据库备份成功：{backup_path}")

            return {
                "success": True,
                "message": "数据库备份成功",
                "file_path": backup_path,
                "filename": backup_filename
            }

        except Exception as e:
            logger.exception(f"数据库备份失败：{e}")
            return {
                "success": False,
                "message": f"备份失败：{str(e)}",
                "file_path": None,
                "filename": None
            }

    def restore_database(self, backup_file: str) -> Dict[str, Any]:
        """
        恢复数据库

        Args:
            backup_file: 备份文件路径或文件名

        Returns:
            结果字典
        """
        try:
            db_path = self._get_db_path()

            if not db_path:
                return {
                    "success": False,
                    "message": "仅支持 SQLite 数据库恢复"
                }

            if not os.path.isabs(backup_file):
                backup_dir = self._get_backup_dir()
                backup_path = os.path.join(backup_dir, backup_file)
            else:
                backup_path = backup_file

            if not os.path.exists(backup_path):
                return {
                    "success": False,
                    "message": f"备份文件不存在：{backup_path}"
                }

            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            shutil.copy2(backup_path, db_path)

            logger.info(f"数据库恢复成功：从 {backup_path} 恢复到 {db_path}")

            return {
                "success": True,
                "message": "数据库恢复成功"
            }

        except Exception as e:
            logger.exception(f"数据库恢复失败：{e}")
            return {
                "success": False,
                "message": f"恢复失败：{str(e)}"
            }

    def list_backups(self) -> Dict[str, Any]:
        """
        列出所有备份文件

        Returns:
            结果字典：
                - success: 是否成功
                - backups: 备份文件列表
                - count: 备份数量
        """
        try:
            backup_dir = self._get_backup_dir()

            if not os.path.exists(backup_dir):
                return {
                    "success": True,
                    "backups": [],
                    "count": 0
                }

            backups = []
            for filename in os.listdir(backup_dir):
                if filename.endswith(".bak"):
                    file_path = os.path.join(backup_dir, filename)
                    stat = os.stat(file_path)
                    backups.append({
                        "filename": filename,
                        "file_path": file_path,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                    })

            backups.sort(key=lambda x: x["created_at"], reverse=True)

            return {
                "success": True,
                "backups": backups,
                "count": len(backups)
            }

        except Exception as e:
            logger.exception(f"列出备份失败：{e}")
            return {
                "success": False,
                "message": f"列出备份失败：{str(e)}",
                "backups": [],
                "count": 0
            }

    def delete_backup(self, backup_file: str) -> Dict[str, Any]:
        """
        删除备份文件

        Args:
            backup_file: 备份文件路径或文件名

        Returns:
            结果字典
        """
        try:
            if not os.path.isabs(backup_file):
                backup_dir = self._get_backup_dir()
                backup_path = os.path.join(backup_dir, backup_file)
            else:
                backup_path = backup_file

            if not os.path.exists(backup_path):
                return {
                    "success": False,
                    "message": f"备份文件不存在：{backup_path}"
                }

            os.remove(backup_path)

            logger.info(f"备份文件删除成功：{backup_path}")

            return {
                "success": True,
                "message": "备份文件删除成功"
            }

        except Exception as e:
            logger.exception(f"删除备份失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }


def get_database_service() -> DatabaseService:
    """获取数据库服务实例"""
    return DatabaseService()
