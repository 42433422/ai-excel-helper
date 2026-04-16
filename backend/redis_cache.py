"""
Redis 缓存集成模块
目标：实现热点查询缓存，加速高频查询响应
功能：
    - 查询结果缓存
    - 向量缓存
    - 热点检测
    - 自动过期
"""

import json
import time
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0


class RedisCacheManager:
    """Redis 缓存管理器"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 default_ttl: int = 3600):
        """
        初始化 Redis 缓存
        Args:
            host: Redis 主机
            port: Redis 端口
            db: Redis 数据库
            password: 密码
            default_ttl: 默认过期时间（秒）
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        
        self.redis_client = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接 Redis"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            # 测试连接
            self.redis_client.ping()
            self._connected = True
            print(f"Redis 连接成功：{self.host}:{self.port}")
            return True
        except ImportError:
            print("警告：redis-py 未安装，使用内存缓存降级")
            self._use_memory_cache = True
            self._connected = True
            return True
        except Exception as e:
            print(f"Redis 连接失败：{e}，使用内存缓存降级")
            self._use_memory_cache = True
            self._connected = True
            return False
    
    def _generate_key(self, query: str, cache_type: str = "query") -> str:
        """生成缓存键"""
        # 使用 MD5 哈希
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        return f"{cache_type}:{query_hash}"
    
    def set(self, query: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = "query"):
        """设置缓存"""
        if not self._connected:
            return
        
        key = self._generate_key(query, cache_type)
        
        if hasattr(self, '_use_memory_cache') and self._use_memory_cache:
            # 内存缓存降级
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
            self._memory_cache[key] = {
                'value': value,
                'expires_at': time.time() + (ttl or self.default_ttl)
            }
            return
        
        try:
            ttl = ttl or self.default_ttl
            data = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(key, ttl, data)
        except Exception as e:
            print(f"Redis SET 错误：{e}")
    
    def get(self, query: str, cache_type: str = "query") -> Optional[Any]:
        """获取缓存"""
        if not self._connected:
            return None
        
        key = self._generate_key(query, cache_type)
        
        if hasattr(self, '_use_memory_cache') and self._use_memory_cache:
            # 内存缓存降级
            memory_cache = getattr(self, '_memory_cache', {})
            if key in memory_cache:
                entry = memory_cache[key]
                # 检查是否过期
                if entry.get('expires_at', 0) > time.time():
                    return entry.get('value')
                else:
                    # 过期删除
                    del memory_cache[key]
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Redis GET 错误：{e}")
            return None
    
    def delete(self, query: str, cache_type: str = "query"):
        """删除缓存"""
        if not self._connected:
            return
        
        key = self._generate_key(query, cache_type)
        
        if hasattr(self, '_use_memory_cache') and self._use_memory_cache:
            if hasattr(self, '_memory_cache'):
                self._memory_cache.pop(key, None)
            return
        
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Redis DELETE 错误：{e}")
    
    def clear(self, cache_type: str = "query"):
        """清空缓存"""
        if not self._connected:
            return
        
        if hasattr(self, '_use_memory_cache') and self._use_memory_cache:
            if hasattr(self, '_memory_cache'):
                self._memory_cache.clear()
            return
        
        try:
            # 查找所有匹配的键
            pattern = f"{cache_type}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis CLEAR 错误：{e}")
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        if not self._connected:
            return {'status': 'disconnected'}
        
        if hasattr(self, '_use_memory_cache') and self._use_memory_cache:
            memory_cache = getattr(self, '_memory_cache', {})
            now = time.time()
            valid_count = sum(1 for v in memory_cache.values() 
                            if v.get('expires_at', 0) > now)
            return {
                'status': 'memory_fallback',
                'cache_size': valid_count,
                'max_size': 'unlimited'
            }
        
        try:
            info = self.redis_client.info('stats')
            return {
                'status': 'connected',
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': info.get('keyspace_hits', 0) / 
                           (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1))
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class HotQueryDetector:
    """热点查询检测器"""
    
    def __init__(self, window_size: int = 100, threshold: int = 5):
        """
        初始化热点检测器
        Args:
            window_size: 滑动窗口大小
            threshold: 热点阈值（窗口内出现次数）
        """
        self.window_size = window_size
        self.threshold = threshold
        self.query_window = []
        self.query_counts = {}
    
    def record_query(self, query: str):
        """记录查询"""
        # 添加到窗口
        self.query_window.append((time.time(), query))
        
        # 维护窗口大小
        if len(self.query_window) > self.window_size:
            self.query_window.pop(0)
        
        # 更新计数
        self.query_counts[query] = self.query_counts.get(query, 0) + 1
    
    def is_hot_query(self, query: str) -> bool:
        """判断是否为热点查询"""
        count = self.query_counts.get(query, 0)
        return count >= self.threshold
    
    def get_hot_queries(self) -> List[str]:
        """获取热点查询列表"""
        return [q for q, count in self.query_counts.items() 
                if count >= self.threshold]
    
    def reset(self):
        """重置检测器"""
        self.query_window.clear()
        self.query_counts.clear()


class VectorCacheManager:
    """向量缓存管理器"""
    
    def __init__(self, redis_config: Optional[Dict] = None):
        """
        初始化向量缓存
        Args:
            redis_config: Redis 配置
        """
        self.redis_cache = RedisCacheManager(
            host=redis_config.get('host', 'localhost') if redis_config else 'localhost',
            port=redis_config.get('port', 6379) if redis_config else 6379,
            default_ttl=redis_config.get('ttl', 3600) if redis_config else 3600
        )
        
        self.hot_detector = HotQueryDetector()
        self.query_history = []
    
    def connect(self):
        """连接缓存"""
        self.redis_cache.connect()
    
    def get_or_compute(self, query: str, compute_fn, use_cache: bool = True):
        """
        获取或计算查询结果
        Args:
            query: 查询文本
            compute_fn: 计算函数
            use_cache: 是否使用缓存
        Returns:
            查询结果
        """
        # 记录查询用于热点检测
        self.hot_detector.record_query(query)
        
        # 检查是否为热点查询
        is_hot = self.hot_detector.is_hot_query(query)
        
        # 尝试从缓存获取
        if use_cache and is_hot:
            cached = self.redis_cache.get(query, cache_type="vector")
            if cached is not None:
                return cached
        
        # 计算结果
        result = compute_fn(query)
        
        # 缓存热点查询结果
        if use_cache and is_hot:
            self.redis_cache.set(query, result, cache_type="vector")
        
        return result
    
    def cache_vector(self, query: str, vector: List[float], ttl: int = 3600):
        """缓存向量"""
        self.redis_cache.set(query, vector, ttl=ttl, cache_type="vector")
    
    def get_cached_vector(self, query: str) -> Optional[List[float]]:
        """获取缓存的向量"""
        return self.redis_cache.get(query, cache_type="vector")
    
    def cache_search_results(self, query: str, results: List[Dict], ttl: int = 600):
        """缓存搜索结果"""
        self.redis_cache.set(query, results, ttl=ttl, cache_type="search")
    
    def get_cached_search_results(self, query: str) -> Optional[List[Dict]]:
        """获取缓存的搜索结果"""
        return self.redis_cache.get(query, cache_type="search")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        cache_stats = self.redis_cache.get_stats()
        hot_queries = self.hot_detector.get_hot_queries()
        
        return {
            **cache_stats,
            'hot_queries_count': len(hot_queries),
            'hot_queries': hot_queries[:10]  # 返回 top 10
        }


if __name__ == "__main__":
    # 测试缓存管理器
    print("测试 Redis 缓存管理器...")
    
    # 创建缓存管理器
    cache_manager = VectorCacheManager()
    cache_manager.connect()
    
    # 模拟查询
    def mock_compute(query):
        print(f"计算查询：{query}")
        return {'query': query, 'result': 'mock_result'}
    
    # 第一次查询（未缓存）
    result1 = cache_manager.get_or_compute("销售额", mock_compute)
    print(f"结果 1: {result1}")
    
    # 重复查询（热点）
    for i in range(5):
        result2 = cache_manager.get_or_compute("销售额", mock_compute)
        print(f"结果 2-{i}: {result2}")
    
    # 获取统计
    stats = cache_manager.get_stats()
    print(f"\n缓存统计：{stats}")
    
    # 热点查询
    hot_queries = cache_manager.hot_detector.get_hot_queries()
    print(f"热点查询：{hot_queries}")
