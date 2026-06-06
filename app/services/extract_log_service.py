"""
提取日志服务

记录和管理 Excel 数据提取操作的日志。
"""

import json
import logging
from datetime import datetime
from typing import Any

from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin

logger = logging.getLogger(__name__)


class ExtractLogService(NeuroEventPublisherMixin):
    """提取日志服务类"""

    def __init__(self):
        """初始化提取日志服务"""
        pass

    def create_log(
        self,
        file_name: str,
        data_type: str,
        file_path: str | None = None,
        total_rows: int = 0,
        field_mapping: dict | None = None,
    ) -> int:
        """
        创建提取日志记录

        Args:
            file_name: 文件名
            data_type: 数据类型 (products/customers/orders)
            file_path: 文件路径
            total_rows: 总行数
            field_mapping: 字段映射

        Returns:
            日志 ID
        """
        try:
            with get_db() as db:
                from sqlalchemy import text

                result = db.execute(
                    text(
                        """
                        INSERT INTO extract_logs 
                        (file_name, file_path, data_type, total_rows, field_mapping, status, created_at)
                        VALUES (:file_name, :file_path, :data_type, :total_rows, :field_mapping, 'pending', :created_at)
                    """
                    ),
                    {
                        "file_name": file_name,
                        "file_path": file_path,
                        "data_type": data_type,
                        "total_rows": total_rows,
                        "field_mapping": (
                            json.dumps(field_mapping, ensure_ascii=False) if field_mapping else None
                        ),
                        "created_at": datetime.now(),
                    },
                )
                log_id = result.lastrowid
                db.commit()
                logger.info(f"创建提取日志：id={log_id}, file={file_name}")
                return log_id

        except Exception as e:
            logger.error(f"创建提取日志失败：{e}")
            return -1

    def update_log(
        self,
        log_id: int,
        status: str,
        valid_rows: int | None = None,
        imported_rows: int | None = None,
        skipped_rows: int | None = None,
        failed_rows: int | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        更新日志记录

        Args:
            log_id: 日志 ID
            status: 状态 (pending/completed/failed)
            valid_rows: 有效行数
            imported_rows: 导入行数
            skipped_rows: 跳过行数
            failed_rows: 失败行数
            error_message: 错误消息

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                from sqlalchemy import text

                updates = ["status = :status"]
                params = {"log_id": log_id, "status": status}

                if valid_rows is not None:
                    updates.append("valid_rows = :valid_rows")
                    params["valid_rows"] = valid_rows

                if imported_rows is not None:
                    updates.append("imported_rows = :imported_rows")
                    params["imported_rows"] = imported_rows

                if skipped_rows is not None:
                    updates.append("skipped_rows = :skipped_rows")
                    params["skipped_rows"] = skipped_rows

                if failed_rows is not None:
                    updates.append("failed_rows = :failed_rows")
                    params["failed_rows"] = failed_rows

                if error_message is not None:
                    updates.append("error_message = :error_message")
                    params["error_message"] = error_message

                params["log_id"] = log_id

                sql = f"UPDATE extract_logs SET {', '.join(updates)} WHERE id = :log_id"
                db.execute(text(sql), params)
                db.commit()

                logger.info(f"更新提取日志：id={log_id}, status={status}")
                return True

        except Exception as e:
            logger.error(f"更新提取日志失败：{e}")
            return False

    def get_log(self, log_id: int) -> dict[str, Any] | None:
        """
        获取日志记录

        Args:
            log_id: 日志 ID

        Returns:
            日志记录字典
        """
        try:
            with get_db() as db:
                from sqlalchemy import text

                result = db.execute(
                    text("SELECT * FROM extract_logs WHERE id = :id"), {"id": log_id}
                )
                row = result.fetchone()

                if row:
                    return {
                        "id": row.id,
                        "file_name": row.file_name,
                        "file_path": row.file_path,
                        "data_type": row.data_type,
                        "total_rows": row.total_rows,
                        "valid_rows": row.valid_rows,
                        "imported_rows": row.imported_rows,
                        "skipped_rows": row.skipped_rows,
                        "failed_rows": row.failed_rows,
                        "status": row.status,
                        "error_message": row.error_message,
                        "field_mapping": (
                            json.loads(row.field_mapping) if row.field_mapping else None
                        ),
                        "created_at": row.created_at,
                    }
                return None

        except Exception as e:
            logger.error(f"获取提取日志失败：{e}")
            return None

    def get_logs(
        self,
        data_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        获取日志列表

        Args:
            data_type: 数据类型过滤
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            日志列表
        """
        try:
            with get_db() as db:
                from sqlalchemy import text

                conditions = []
                params = {"limit": limit, "offset": offset}

                if data_type:
                    conditions.append("data_type = :data_type")
                    params["data_type"] = data_type

                if status:
                    conditions.append("status = :status")
                    params["status"] = status

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                sql = f"""
                    SELECT * FROM extract_logs 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """

                result = db.execute(text(sql), params)
                rows = result.fetchall()

                logs = []
                for row in rows:
                    logs.append(
                        {
                            "id": row.id,
                            "file_name": row.file_name,
                            "file_path": row.file_path,
                            "data_type": row.data_type,
                            "total_rows": row.total_rows,
                            "valid_rows": row.valid_rows,
                            "imported_rows": row.imported_rows,
                            "skipped_rows": row.skipped_rows,
                            "failed_rows": row.failed_rows,
                            "status": row.status,
                            "created_at": row.created_at,
                        }
                    )

                return logs

        except Exception as e:
            logger.error(f"获取提取日志列表失败：{e}")
            return []


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(ExtractLogService, "app.services.extract_log_service")
