"""
MOD Metadata Index Service - MOD 元数据索引与搜索服务

提供 MOD 元数据的持久化存储、索引构建、搜索查询功能。
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Optional

from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class ModIndexDatabase:
    """MOD 索引数据库管理"""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            base_dir = os.environ.get("XCAGI_MOD_STORE_DIR", "")
            if not base_dir:
                base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mod_store")
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "mod_index.db")

        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_metadata (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT,
                    description TEXT,
                    package_file TEXT,
                    package_hash TEXT,
                    file_size INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    download_count INTEGER DEFAULT 0,
                    is_installed INTEGER DEFAULT 0,
                    manifest_json TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_dependencies (
                    mod_id TEXT,
                    dependency_id TEXT,
                    version_spec TEXT,
                    dep_type TEXT,
                    PRIMARY KEY (mod_id, dependency_id),
                    FOREIGN KEY (mod_id) REFERENCES mod_metadata(id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mod_id TEXT NOT NULL,
                    user_id TEXT,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TEXT,
                    FOREIGN KEY (mod_id) REFERENCES mod_metadata(id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_statistics (
                    mod_id TEXT PRIMARY KEY,
                    total_downloads INTEGER DEFAULT 0,
                    total_installs INTEGER DEFAULT 0,
                    total_uninstalls INTEGER DEFAULT 0,
                    total_updates INTEGER DEFAULT 0,
                    avg_rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    last_updated TEXT,
                    FOREIGN KEY (mod_id) REFERENCES mod_metadata(id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mod_name ON mod_metadata(name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mod_author ON mod_metadata(author)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mod_installed ON mod_metadata(is_installed)
            """
            )

            logger.info(f"MOD index database initialized: {self.db_path}")

    def upsert_mod(self, metadata: dict[str, Any], package_file: str) -> bool:
        """插入或更新 MOD 元数据"""
        try:
            with self.get_connection() as conn:
                now = utc_now_naive().isoformat()

                conn.execute(
                    """
                    INSERT OR REPLACE INTO mod_metadata 
                    (id, name, version, author, description, package_file, 
                     file_size, created_at, updated_at, manifest_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metadata.get("id", ""),
                        metadata.get("name", ""),
                        metadata.get("version", ""),
                        metadata.get("author", ""),
                        metadata.get("description", ""),
                        package_file,
                        metadata.get("file_size", 0),
                        now,
                        now,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )

                mod_id = metadata.get("id", "")

                conn.execute("DELETE FROM mod_dependencies WHERE mod_id = ?", (mod_id,))

                dependencies = metadata.get("dependencies", {})
                for dep_id, version_spec in dependencies.items():
                    dep_type = "core" if dep_id == "xcagi" else "mod"
                    conn.execute(
                        """
                        INSERT INTO mod_dependencies 
                        (mod_id, dependency_id, version_spec, dep_type)
                        VALUES (?, ?, ?, ?)
                    """,
                        (mod_id, dep_id, version_spec, dep_type),
                    )

                logger.info(f"MOD metadata indexed: {mod_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to index MOD metadata: {e}")
            return False

    def get_mod(self, mod_id: str) -> dict[str, Any] | None:
        """获取 MOD 元数据"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM mod_metadata WHERE id = ?", (mod_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return dict(row)

    def get_all_mods(self) -> list[dict[str, Any]]:
        """获取所有 MOD 元数据"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM mod_metadata ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def search_mods(
        self,
        query: str | None = None,
        author: str | None = None,
        installed_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """搜索 MOD"""
        conditions = []
        params = []

        if query:
            conditions.append("(name LIKE ? OR description LIKE ? OR author LIKE ?)")
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])

        if author:
            conditions.append("author LIKE ?")
            params.append(f"%{author}%")

        if installed_only:
            conditions.append("is_installed = 1")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"""
                    SELECT * FROM mod_metadata 
                    WHERE {where_clause}
                    ORDER BY name
                    LIMIT ?
                """,
                params + [limit],
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_install_status(self, mod_id: str, is_installed: bool):
        """更新 MOD 安装状态"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE mod_metadata SET is_installed = ?, updated_at = ? WHERE id = ?",
                (1 if is_installed else 0, utc_now_naive().isoformat(), mod_id),
            )

    def increment_download_count(self, mod_id: str):
        """增加下载计数"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE mod_metadata 
                SET download_count = download_count + 1, 
                    updated_at = ?
                WHERE id = ?
            """,
                (utc_now_naive().isoformat(), mod_id),
            )

    def add_rating(self, mod_id: str, user_id: str, rating: int, comment: str = "") -> bool:
        """添加 MOD 评分"""
        try:
            with self.get_connection() as conn:
                now = utc_now_naive().isoformat()

                conn.execute(
                    """
                    INSERT INTO mod_ratings (mod_id, user_id, rating, comment, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (mod_id, user_id, rating, comment, now),
                )

                self._recalculate_statistics(conn, mod_id)

                return True
        except Exception as e:
            logger.error(f"Failed to add rating: {e}")
            return False

    def get_ratings(self, mod_id: str) -> list[dict[str, Any]]:
        """获取 MOD 评分列表"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM mod_ratings WHERE mod_id = ? ORDER BY created_at DESC", (mod_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self, mod_id: str) -> dict[str, Any] | None:
        """获取 MOD 统计信息"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM mod_statistics WHERE mod_id = ?", (mod_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def _recalculate_statistics(self, conn: sqlite3.Connection, mod_id: str):
        """重新计算 MOD 统计信息"""
        cursor = conn.execute(
            """
            SELECT 
                COUNT(*) as rating_count,
                AVG(rating) as avg_rating
            FROM mod_ratings
            WHERE mod_id = ?
        """,
            (mod_id,),
        )

        row = cursor.fetchone()
        rating_count = row["rating_count"] or 0
        avg_rating = row["avg_rating"] or 0.0

        conn.execute(
            """
            INSERT OR REPLACE INTO mod_statistics 
            (mod_id, rating_count, avg_rating, last_updated)
            VALUES (?, ?, ?, ?)
        """,
            (mod_id, rating_count, avg_rating, utc_now_naive().isoformat()),
        )

    def get_popular_mods(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取热门 MOD（按下载量）"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT m.*, s.total_downloads, s.avg_rating
                FROM mod_metadata m
                LEFT JOIN mod_statistics s ON m.id = s.mod_id
                ORDER BY s.total_downloads DESC, s.avg_rating DESC
                LIMIT ?
            """,
                [limit],
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_mods(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最新 MOD"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM mod_metadata
                ORDER BY created_at DESC
                LIMIT ?
            """,
                [limit],
            )
            return [dict(row) for row in cursor.fetchall()]


class ModIndexService:
    """MOD 索引服务"""

    _instance: Optional["ModIndexService"] = None

    def __init__(self):
        self.db = ModIndexDatabase()

    @classmethod
    def get_instance(cls) -> "ModIndexService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def index_mod_package(self, package_path: str, package_file: str) -> bool:
        """索引 MOD 包"""
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager

            mm = get_mod_manager()
            is_valid, msg, info = mm.validate_mod_package(package_path)

            if not is_valid:
                logger.warning(f"Cannot index invalid MOD: {msg}")
                return False

            info["file_size"] = os.path.getsize(package_path)

            return self.db.upsert_mod(info, package_file)

        except Exception as e:
            logger.error(f"Failed to index MOD package: {e}")
            return False

    def rebuild_index(self, store_dir: str | None = None) -> tuple[int, int]:
        """
        重建 MOD 索引

        Returns:
            (成功索引数，失败数)
        """
        if store_dir is None:
            store_dir = os.environ.get("XCAGI_MOD_STORE_DIR", "")
            if not store_dir:
                store_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mod_store")

        if not os.path.isdir(store_dir):
            logger.warning(f"Store directory does not exist: {store_dir}")
            return 0, 0

        success_count = 0
        fail_count = 0

        logger.info(f"Rebuilding MOD index from: {store_dir}")

        for entry in os.listdir(store_dir):
            if entry.endswith(".xcmod") or entry.endswith(".xcemp"):
                package_path = os.path.join(store_dir, entry)

                if self.index_mod_package(package_path, entry):
                    success_count += 1
                else:
                    fail_count += 1

        logger.info(f"MOD index rebuilt: {success_count} success, {fail_count} failed")
        return success_count, fail_count

    def search(
        self,
        query: str | None = None,
        author: str | None = None,
        installed_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """搜索 MOD"""
        return self.db.search_mods(query, author, installed_only, limit)

    def get_mod(self, mod_id: str) -> dict[str, Any] | None:
        """获取 MOD 详情"""
        return self.db.get_mod(mod_id)

    def get_all_mods(self) -> list[dict[str, Any]]:
        """获取所有 MOD"""
        return self.db.get_all_mods()

    def get_popular_mods(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取热门 MOD"""
        return self.db.get_popular_mods(limit)

    def get_recent_mods(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最新 MOD"""
        return self.db.get_recent_mods(limit)

    def add_rating(
        self,
        mod_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> bool:
        """添加评分"""
        if rating < 1 or rating > 5:
            logger.error(f"Invalid rating: {rating}")
            return False

        return self.db.add_rating(mod_id, user_id, rating, comment)

    def get_ratings(self, mod_id: str) -> list[dict[str, Any]]:
        """获取评分列表"""
        return self.db.get_ratings(mod_id)

    def get_statistics(self, mod_id: str) -> dict[str, Any] | None:
        """获取统计信息"""
        return self.db.get_statistics(mod_id)


def get_mod_index_service() -> ModIndexService:
    """获取 MOD 索引服务单例"""
    return ModIndexService.get_instance()
