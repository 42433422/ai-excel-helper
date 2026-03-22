from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.application.ports.extract_log_store import ExtractLogStorePort
from app.db.session import get_db

logger = logging.getLogger(__name__)


class SQLAlchemyExtractLogStore(ExtractLogStorePort):
    """提取日志仓储 SQLAlchemy 实现"""

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            'id': row.id,
            'file_name': row.file_name,
            'file_path': row.file_path,
            'data_type': row.data_type,
            'total_rows': row.total_rows,
            'valid_rows': row.valid_rows,
            'imported_rows': row.imported_rows,
            'skipped_rows': row.skipped_rows,
            'failed_rows': row.failed_rows,
            'status': row.status,
            'error_message': row.error_message,
            'field_mapping': json.loads(row.field_mapping) if row.field_mapping else None,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }

    def find_all(
        self,
        page: int = 1,
        per_page: int = 20,
        unit_name: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            with get_db() as db:
                query = text("SELECT * FROM extract_logs ORDER BY created_at DESC")
                result = db.execute(query)
                rows = result.fetchall()

                logs = [self._row_to_dict(row) for row in rows]

                if unit_name:
                    logs = [log for log in logs if unit_name.lower() in (log.get('file_name') or '').lower()]

                total = len(logs)
                start = (page - 1) * per_page
                end = start + per_page
                paginated_logs = logs[start:end]

                return {
                    "success": True,
                    "data": paginated_logs,
                    "total": total,
                    "page": page,
                    "per_page": per_page
                }
        except Exception as e:
            logger.error(f"获取提取日志列表失败：{e}")
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": [],
                "total": 0
            }

    def find_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                result = db.execute(
                    text("SELECT * FROM extract_logs WHERE id = :id"),
                    {'id': log_id}
                )
                row = result.fetchone()

                if not row:
                    return None

                return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"获取提取日志失败：{e}")
            return None

    def create(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with get_db() as db:
                result = db.execute(
                    text("""
                        INSERT INTO extract_logs
                        (file_name, file_path, data_type, total_rows, field_mapping, status, created_at)
                        VALUES (:file_name, :file_path, :data_type, :total_rows, :field_mapping, 'pending', :created_at)
                    """),
                    {
                        'file_name': log_data.get('file_name'),
                        'file_path': log_data.get('file_path'),
                        'data_type': log_data.get('data_type'),
                        'total_rows': log_data.get('total_rows', 0),
                        'field_mapping': json.dumps(log_data.get('field_mapping'), ensure_ascii=False) if log_data.get('field_mapping') else None,
                        'created_at': datetime.now()
                    }
                )
                log_id = result.lastrowid
                db.commit()

                return {
                    "success": True,
                    "message": "提取日志创建成功",
                    "log_id": log_id
                }
        except Exception as e:
            logger.error(f"创建提取日志失败：{e}")
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }

    def delete(self, log_id: int) -> Dict[str, Any]:
        try:
            with get_db() as db:
                db.execute(text("DELETE FROM extract_logs WHERE id = :id"), {'id': log_id})
                db.commit()
                return {
                    "success": True,
                    "message": "提取日志删除成功"
                }
        except Exception as e:
            logger.error(f"删除提取日志失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }

    def clear_old(self, days: int = 30) -> Dict[str, Any]:
        try:
            with get_db() as db:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days)

                result = db.execute(
                    text("DELETE FROM extract_logs WHERE created_at < :cutoff_date"),
                    {'cutoff_date': cutoff_date}
                )
                deleted_count = result.rowcount
                db.commit()

                return {
                    "success": True,
                    "message": f"已清理 {deleted_count} 条旧日志",
                    "deleted_count": deleted_count
                }
        except Exception as e:
            logger.error(f"清理旧日志失败：{e}")
            return {
                "success": False,
                "message": f"清理失败：{str(e)}"
            }
