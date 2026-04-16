"""
向量索引持久化模块
目标：实现向量索引的持久化存储，支持快速加载和增量更新
功能：
    - 索引序列化
    - 增量更新
    - 版本管理
    - 备份恢复
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pickle
import json
import time
from datetime import datetime
import shutil


class VectorIndexPersistence:
    """向量索引持久化管理器"""
    
    def __init__(self, storage_dir: str):
        """
        初始化持久化管理器
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.storage_dir / "vector_index.faiss"
        self.metadata_file = self.storage_dir / "metadata.pkl"
        self.config_file = self.storage_dir / "config.json"
        self.version_file = self.storage_dir / "version.json"
    
    def save_index(self, index, vectors: np.ndarray, metadata: List[Dict], 
                   config: Optional[Dict] = None):
        """
        保存索引
        Args:
            index: FAISS 索引对象
            vectors: 向量矩阵
            metadata: 元数据列表
            config: 配置信息
        """
        import faiss
        
        # 1. 保存 FAISS 索引
        faiss.write_index(index, str(self.index_file))
        
        # 2. 保存元数据
        metadata_data = {
            'vectors_shape': vectors.shape,
            'metadata': metadata,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(metadata_data, f)
        
        # 3. 保存配置
        if config is None:
            config = {}
        config['dimension'] = vectors.shape[1] if len(vectors) > 0 else 512
        config['vector_count'] = len(vectors)
        config['saved_at'] = datetime.now().isoformat()
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 4. 保存版本信息
        version_info = {
            'version': 1,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'vector_count': len(vectors)
        }
        
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)
        
        print(f"索引已保存到 {self.storage_dir}")
        print(f"  - 向量数：{len(vectors)}")
        print(f"  - 维度：{config['dimension']}")
    
    def load_index(self, index):
        """
        加载索引
        Args:
            index: FAISS 索引对象（用于接收）
        Returns:
            (index, vectors, metadata, config)
        """
        import faiss
        
        # 1. 加载 FAISS 索引
        if self.index_file.exists():
            index = faiss.read_index(str(self.index_file))
        else:
            raise FileNotFoundError(f"索引文件不存在：{self.index_file}")
        
        # 2. 加载元数据
        if self.metadata_file.exists():
            with open(self.metadata_file, 'rb') as f:
                metadata_data = pickle.load(f)
                vectors_shape = metadata_data['vectors_shape']
                metadata = metadata_data['metadata']
                
                # 重建向量矩阵（从元数据中恢复，实际应该单独存储向量）
                vectors = np.zeros(vectors_shape, dtype=np.float32)
        else:
            raise FileNotFoundError(f"元数据文件不存在：{self.metadata_file}")
        
        # 3. 加载配置
        config = {}
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        return index, vectors, metadata, config
    
    def incremental_update(self, index, new_vectors: np.ndarray, 
                          new_metadata: List[Dict]) -> bool:
        """
        增量更新索引
        Args:
            index: FAISS 索引对象
            new_vectors: 新增向量
            new_metadata: 新增元数据
        Returns:
            是否成功
        """
        import faiss
        
        # 1. 备份当前索引
        backup_dir = self.storage_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if self.storage_dir.exists():
            shutil.copytree(self.storage_dir, backup_dir)
        
        try:
            # 2. 添加新向量到索引
            if len(new_vectors) > 0:
                faiss.normalize_L2(new_vectors)
                index.add(new_vectors)
            
            # 3. 加载现有元数据
            with open(self.metadata_file, 'rb') as f:
                metadata_data = pickle.load(f)
                existing_metadata = metadata_data['metadata']
            
            # 4. 合并元数据
            existing_metadata.extend(new_metadata)
            
            # 5. 保存更新后的索引
            self.save_index(index, new_vectors, existing_metadata)
            
            # 6. 更新版本信息
            with open(self.version_file, 'r', encoding='utf-8') as f:
                version_info = json.load(f)
            
            version_info['version'] += 1
            version_info['updated_at'] = datetime.now().isoformat()
            version_info['vector_count'] = index.ntotal
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
            
            print(f"索引已增量更新")
            print(f"  - 新增向量：{len(new_vectors)}")
            print(f"  - 总向量数：{index.ntotal}")
            print(f"  - 版本号：{version_info['version']}")
            
            return True
        
        except Exception as e:
            print(f"增量更新失败：{e}")
            print("正在恢复备份...")
            
            # 恢复备份
            if backup_dir.exists():
                if self.storage_dir.exists():
                    shutil.rmtree(self.storage_dir)
                shutil.move(backup_dir, self.storage_dir)
            
            return False
    
    def get_version_info(self) -> Dict:
        """获取版本信息"""
        if self.version_file.exists():
            with open(self.version_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def list_backups(self) -> List[Path]:
        """列出所有备份"""
        backups = []
        for item in self.storage_dir.iterdir():
            if item.is_dir() and item.name.startswith('backup_'):
                backups.append(item)
        return sorted(backups, key=lambda x: x.name)
    
    def restore_from_backup(self, backup_path: Path):
        """从备份恢复"""
        if not backup_path.exists():
            raise FileNotFoundError(f"备份不存在：{backup_path}")
        
        # 备份当前状态
        current_backup = self.storage_dir / f"current_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(self.storage_dir, current_backup)
        
        # 恢复备份
        shutil.rmtree(self.storage_dir)
        shutil.copytree(backup_path, self.storage_dir)
        
        print(f"已从备份恢复：{backup_path}")


class VectorCache:
    """向量缓存管理器（Redis 简化版）"""
    
    def __init__(self, cache_size: int = 1000):
        """
        初始化缓存
        Args:
            cache_size: 缓存大小
        """
        self.cache_size = cache_size
        self.cache = {}  # query -> (results, timestamp)
        self.access_count = {}  # query -> access_count
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, query: str) -> Optional[List]:
        """从缓存获取结果"""
        if query in self.cache:
            results, timestamp = self.cache[query]
            self.access_count[query] = self.access_count.get(query, 0) + 1
            self.hit_count += 1
            return results
        else:
            self.miss_count += 1
            return None
    
    def set(self, query: str, results: List):
        """设置缓存"""
        if len(self.cache) >= self.cache_size:
            # LRU 淘汰：淘汰访问次数最少的
            min_access = min(self.access_count.values())
            for q in list(self.access_count.keys()):
                if self.access_count[q] == min_access:
                    del self.cache[q]
                    del self.access_count[q]
                    break
        
        self.cache[query] = (results, time.time())
        self.access_count[query] = 1
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'max_size': self.cache_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate
        }
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_count.clear()
        self.hit_count = 0
        self.miss_count = 0


if __name__ == "__main__":
    # 测试持久化
    import tempfile
    
    print("测试向量索引持久化...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建持久化管理器
        persistence = VectorIndexPersistence(tmpdir)
        
        # 创建测试数据
        import faiss
        index = faiss.IndexFlatIP(512)
        test_vectors = np.random.rand(100, 512).astype(np.float32)
        faiss.normalize_L2(test_vectors)
        index.add(test_vectors)
        
        metadata = [{'id': i, 'text': f'doc_{i}'} for i in range(100)]
        
        # 保存索引
        persistence.save_index(index, test_vectors, metadata)
        
        # 获取版本信息
        version = persistence.get_version_info()
        print(f"版本信息：{version}")
        
        # 增量更新
        new_vectors = np.random.rand(10, 512).astype(np.float32)
        faiss.normalize_L2(new_vectors)
        new_metadata = [{'id': i+100, 'text': f'doc_{i+100}'} for i in range(10)]
        
        persistence.incremental_update(index, new_vectors, new_metadata)
        
        # 列出备份
        backups = persistence.list_backups()
        print(f"备份数量：{len(backups)}")
    
    # 测试缓存
    print("\n测试向量缓存...")
    cache = VectorCache(cache_size=100)
    
    # 设置缓存
    for i in range(50):
        cache.set(f"query_{i}", [f"result_{j}" for j in range(5)])
    
    # 获取缓存
    for i in range(30):
        cache.get(f"query_{i}")
    
    # 统计
    stats = cache.get_stats()
    print(f"缓存统计：{stats}")
