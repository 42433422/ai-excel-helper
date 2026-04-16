"""
持久化集成模块
目标：将向量索引持久化集成到 ExcelVectorAppService
功能：
    - 自动保存/加载索引
    - 增量更新
    - 版本管理
    - 缓存优化
"""

from __future__ import annotations

import os
import json
import pickle
import time
from pathlib import Path
from typing import Any, Optional, List, Dict
from datetime import datetime
import numpy as np

from backend.excel_vector_app_service import ExcelVectorAppService, SentenceTransformerEmbedder, _Chunk


class PersistedExcelVectorService(ExcelVectorAppService):
    """
    支持持久化的 Excel 向量检索服务
    继承自 ExcelVectorAppService，添加持久化能力
    """
    
    def __init__(self, workspace_root: str, 
                 persist_dir: Optional[str] = None,
                 auto_save: bool = True,
                 embedder: Optional[SentenceTransformerEmbedder] = None):
        """
        初始化持久化服务
        Args:
            workspace_root: 工作目录
            persist_dir: 持久化目录（默认在 workspace_root/.vector_index）
            auto_save: 是否自动保存
            embedder: 嵌入模型
        """
        super().__init__(workspace_root=workspace_root, embedder=embedder)
        
        # 持久化目录
        if persist_dir is None:
            self.persist_dir = Path(workspace_root) / ".vector_index"
        else:
            self.persist_dir = Path(persist_dir)
        
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 持久化文件路径
        self.index_file = self.persist_dir / "chunks.pkl"
        self.metadata_file = self.persist_dir / "metadata.json"
        self.version_file = self.persist_dir / "version.json"
        
        # 自动保存
        self.auto_save = auto_save
        
        # 版本信息
        self.version = 0
        self.last_saved = None
        
        # 尝试加载已有索引
        self._load_if_exists()
    
    def _load_if_exists(self):
        """如果存在持久化索引则加载"""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self._load_index()
                print(f"已加载持久化索引：{self.persist_dir}")
            except Exception as e:
                print(f"加载索引失败：{e}，将创建新索引")
    
    def index_excel(self,
                   file_path: str,
                   *,
                   sheet_name: str | int | None = None,
                   columns: list[str] | None = None,
                   header_row: int = 0,
                   max_rows: int | None = None,
                   extra_prefix: str = "",
                   force_rebuild: bool = False) -> dict[str, Any]:
        """
        索引 Excel 文件（支持持久化）
        Args:
            force_rebuild: 是否强制重建索引
        """
        # 检查是否已索引该文件
        file_key = self._get_file_key(file_path)
        
        if not force_rebuild and self._is_file_indexed(file_key):
            print(f"文件已索引：{file_path}，使用缓存")
            return self._get_indexed_result(file_key)
        
        # 调用父类方法索引
        result = super().index_excel(
            file_path,
            sheet_name=sheet_name,
            columns=columns,
            header=header_row,
            max_rows=max_rows,
            extra_prefix=extra_prefix
        )
        
        # 更新版本
        self.version += 1
        
        # 自动保存
        if self.auto_save:
            self._save_index()
        
        return result
    
    def _get_file_key(self, file_path: str) -> str:
        """生成文件唯一键"""
        return str(Path(file_path).resolve())
    
    def _is_file_indexed(self, file_key: str) -> bool:
        """检查文件是否已索引"""
        # 简单实现：检查是否有任何 chunk 包含该文件路径
        for chunk in self._chunks:
            if chunk.meta.get('file_path') == file_key:
                return True
        return False
    
    def _get_indexed_result(self, file_key: str) -> dict[str, Any]:
        """获取已索引文件的结果"""
        count = sum(1 for c in self._chunks if c.meta.get('file_path') == file_key)
        return {
            'indexed': count,
            'file_path': file_key,
            'total_chunks': len(self._chunks),
            'cached': True
        }
    
    def _save_index(self):
        """保存索引到磁盘"""
        try:
            # 保存 chunks
            with open(self.index_file, 'wb') as f:
                # 序列化 chunks（排除向量以节省空间，向量单独存储）
                chunks_data = []
                vectors = []
                
                for chunk in self._chunks:
                    chunks_data.append({
                        'text': chunk.text,
                        'meta': chunk.meta,
                        'vector_index': len(vectors)
                    })
                    vectors.append(chunk.vector)
                
                pickle.dump({
                    'chunks': chunks_data,
                    'vectors': np.array(vectors, dtype=np.float32)
                }, f)
            
            # 保存元数据
            metadata = {
                'version': self.version,
                'chunk_count': len(self._chunks),
                'saved_at': datetime.now().isoformat(),
                'workspace_root': self.workspace_root
            }
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 保存版本信息
            version_info = {
                'version': self.version,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'chunk_count': len(self._chunks)
            }
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
            
            self.last_saved = time.time()
            
            print(f"索引已保存：{len(self._chunks)} chunks, 版本 {self.version}")
        
        except Exception as e:
            print(f"保存索引失败：{e}")
            raise
    
    def _load_index(self):
        """从磁盘加载索引"""
        try:
            # 加载 chunks
            with open(self.index_file, 'rb') as f:
                data = pickle.load(f)
                chunks_data = data['chunks']
                vectors = data['vectors']
            
            # 重建 chunks
            self._chunks = []
            for chunk_data in chunks_data:
                vector = vectors[chunk_data['vector_index']]
                self._chunks.append(_Chunk(
                    text=chunk_data['text'],
                    vector=vector,
                    meta=chunk_data['meta']
                ))
            
            # 加载元数据
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                self.version = metadata.get('version', 0)
            
            print(f"索引已加载：{len(self._chunks)} chunks, 版本 {self.version}")
        
        except Exception as e:
            print(f"加载索引失败：{e}")
            raise
    
    def incremental_update(self, new_chunks: List[_Chunk]) -> dict[str, Any]:
        """
        增量更新索引
        Args:
            new_chunks: 新增的 chunks
        Returns:
            更新结果
        """
        old_count = len(self._chunks)
        
        # 添加新 chunks
        self._chunks.extend(new_chunks)
        new_count = len(self._chunks)
        
        # 更新版本
        self.version += 1
        
        # 自动保存
        if self.auto_save:
            self._save_index()
        
        return {
            'old_count': old_count,
            'new_count': new_count,
            'added': new_count - old_count,
            'version': self.version
        }
    
    def get_version_info(self) -> Dict[str, Any]:
        """获取版本信息"""
        if self.version_file.exists():
            with open(self.version_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        stats = {
            'chunk_count': len(self._chunks),
            'version': self.version,
            'persist_dir': str(self.persist_dir),
            'last_saved': self.last_saved,
            'files_indexed': len(set(c.meta.get('file_path') for c in self._chunks if c.meta.get('file_path')))
        }
        
        # 估算内存使用
        if self._chunks:
            vector_size = self._chunks[0].vector.nbytes
            total_vector_memory = len(self._chunks) * vector_size
            stats['estimated_memory_mb'] = total_vector_memory / 1024 / 1024
        
        return stats
    
    def clear_index(self):
        """清空索引"""
        self._chunks.clear()
        self.version = 0
        self.last_saved = None
        
        # 删除持久化文件
        for file in [self.index_file, self.metadata_file, self.version_file]:
            if file.exists():
                file.unlink()
        
        print("索引已清空")
    
    def backup_index(self, backup_dir: Optional[str] = None) -> str:
        """
        备份索引
        Args:
            backup_dir: 备份目录（默认在 persist_dir/backups/）
        Returns:
            备份目录路径
        """
        if backup_dir is None:
            backup_dir = self.persist_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            backup_dir = Path(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制所有文件
        import shutil
        for file in [self.index_file, self.metadata_file, self.version_file]:
            if file.exists():
                shutil.copy2(file, backup_dir / file.name)
        
        print(f"索引已备份到：{backup_dir}")
        return str(backup_dir)
    
    def restore_from_backup(self, backup_dir: str):
        """
        从备份恢复
        Args:
            backup_dir: 备份目录
        """
        backup_path = Path(backup_dir)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份不存在：{backup_dir}")
        
        # 备份当前索引
        if self.index_file.exists():
            self.backup_index()
        
        # 复制备份文件
        import shutil
        for file in backup_path.glob("*"):
            if file.name.endswith('.pkl') or file.name.endswith('.json'):
                shutil.copy2(file, self.persist_dir / file.name)
        
        # 重新加载
        self._load_index()
        
        print(f"索引已从备份恢复：{backup_dir}")


class CacheablePersistedService(PersistedExcelVectorService):
    """
    支持缓存的持久化服务
    在 PersistedExcelVectorService 基础上添加查询缓存
    """
    
    def __init__(self, workspace_root: str,
                 persist_dir: Optional[str] = None,
                 cache_size: int = 1000,
                 **kwargs):
        """
        初始化缓存服务
        Args:
            cache_size: 缓存大小
        """
        super().__init__(workspace_root, persist_dir, **kwargs)
        
        self.cache_size = cache_size
        self.query_cache = {}  # query -> (results, timestamp)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def search(self, query: str, top_k: int = 5, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        搜索（支持缓存）
        Args:
            use_cache: 是否使用缓存
        """
        # 生成缓存键
        cache_key = f"{query}:{top_k}"
        
        # 尝试从缓存获取
        if use_cache and cache_key in self.query_cache:
            results, timestamp = self.query_cache[cache_key]
            
            # 检查是否过期（10 分钟）
            if time.time() - timestamp < 600:
                self.cache_hits += 1
                return results
            else:
                # 过期删除
                del self.query_cache[cache_key]
        
        self.cache_misses += 1
        
        # 执行搜索
        results = super().search(query, top_k)
        
        # 缓存结果
        if use_cache:
            # 如果缓存满了，删除最旧的
            if len(self.query_cache) >= self.cache_size:
                oldest_key = min(self.query_cache, key=lambda k: self.query_cache[k][1])
                del self.query_cache[oldest_key]
            
            self.query_cache[cache_key] = (results, time.time())
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        
        return {
            'cache_size': len(self.query_cache),
            'max_size': self.cache_size,
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.query_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0


def create_persisted_service(workspace_root: str,
                            persist_dir: Optional[str] = None,
                            use_cache: bool = True,
                            cache_size: int = 1000,
                            auto_save: bool = True) -> CacheablePersistedService:
    """
    创建持久化服务工厂函数
    Args:
        workspace_root: 工作目录
        persist_dir: 持久化目录
        use_cache: 是否使用缓存
        cache_size: 缓存大小
        auto_save: 是否自动保存
    Returns:
        服务实例
    """
    if use_cache:
        return CacheablePersistedService(
            workspace_root=workspace_root,
            persist_dir=persist_dir,
            cache_size=cache_size,
            auto_save=auto_save
        )
    else:
        return PersistedExcelVectorService(
            workspace_root=workspace_root,
            persist_dir=persist_dir,
            auto_save=auto_save
        )


if __name__ == "__main__":
    # 示例：使用持久化服务
    print("持久化集成示例\n")
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建持久化服务
        service = create_persisted_service(
            workspace_root=tmpdir,
            use_cache=True,
            cache_size=100
        )
        
        print(f"初始版本：{service.get_version_info()}")
        
        # 模拟索引操作
        # 实际应该调用 index_excel
        
        # 查看统计
        stats = service.get_index_stats()
        print(f"\n索引统计：{stats}")
        
        # 缓存统计
        cache_stats = service.get_cache_stats()
        print(f"\n缓存统计：{cache_stats}")
        
        # 备份
        backup_path = service.backup_index()
        print(f"\n备份路径：{backup_path}")
