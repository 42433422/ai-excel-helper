"""
Redis 缓存策略优化模块
目标：优化缓存命中率，降低响应延迟，实现智能缓存管理
功能：
    - 自适应 TTL
    - 智能预加载
    - 缓存分层
    - 命中率优化
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import numpy as np
from datetime import datetime, timedelta


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    size: int = 0
    memory_usage_mb: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0


class AdaptiveTTLManager:
    """自适应 TTL 管理器"""
    
    def __init__(self, base_ttl: int = 3600, max_ttl: int = 7200):
        """
        初始化自适应 TTL
        Args:
            base_ttl: 基础 TTL（秒）
            max_ttl: 最大 TTL（秒）
        """
        self.base_ttl = base_ttl
        self.max_ttl = max_ttl
        self.query_frequency = {}  # query -> 访问频率
        self.last_access = {}  # query -> 最后访问时间
    
    def compute_ttl(self, query: str) -> int:
        """
        根据查询频率计算 TTL
        Args:
            query: 查询文本
        Returns:
            TTL（秒）
        """
        now = time.time()
        
        # 更新访问记录
        if query in self.query_frequency:
            self.query_frequency[query] += 1
        else:
            self.query_frequency[query] = 1
        
        # 计算访问间隔
        if query in self.last_access:
            time_since_last = now - self.last_access[query]
            # 频繁访问的查询延长 TTL
            if time_since_last < 60:  # 1 分钟内再次访问
                frequency_boost = 2.0
            elif time_since_last < 300:  # 5 分钟内
                frequency_boost = 1.5
            else:
                frequency_boost = 1.0
        else:
            frequency_boost = 1.0
        
        self.last_access[query] = now
        
        # 计算 TTL
        ttl = int(self.base_ttl * frequency_boost)
        ttl = min(ttl, self.max_ttl)
        
        return ttl
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """清理旧记录"""
        now = time.time()
        cutoff = now - max_age_seconds
        
        # 清理长时间未访问的记录
        queries_to_remove = [
            q for q, last_time in self.last_access.items()
            if last_time < cutoff
        ]
        
        for query in queries_to_remove:
            del self.last_access[query]
            if query in self.query_frequency:
                del self.query_frequency[query]


class LFUCache:
    """LFU（Least Frequently Used）缓存"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化 LFU 缓存
        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.frequency: Dict[str, int] = {}
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            self.stats.misses += 1
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if entry.ttl > 0 and (time.time() - entry.created_at) > entry.ttl:
            self._evict(key)
            self.stats.expirations += 1
            self.stats.misses += 1
            return None
        
        # 更新访问频率
        self.frequency[key] = self.frequency.get(key, 0) + 1
        entry.access_count += 1
        entry.last_accessed = time.time()
        
        # 移到末尾（最近访问）
        self.cache.move_to_end(key)
        
        self.stats.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        # 估算大小
        try:
            size_bytes = len(json.dumps(value).encode('utf-8'))
        except:
            size_bytes = 1024  # 默认估算
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
            size_bytes=size_bytes
        )
        
        if key in self.cache:
            # 更新现有条目
            self.cache[key] = entry
            self.cache.move_to_end(key)
        else:
            # 新条目，检查是否需要淘汰
            if len(self.cache) >= self.max_size:
                self._evict_lfu()
            
            self.cache[key] = entry
            self.frequency[key] = 0
        
        self.stats.size = len(self.cache)
    
    def _evict(self, key: str):
        """淘汰单个条目"""
        if key in self.cache:
            del self.cache[key]
            if key in self.frequency:
                del self.frequency[key]
            self.stats.evictions += 1
    
    def _evict_lfu(self):
        """淘汰最少使用的条目"""
        if not self.frequency:
            return
        
        # 找到访问频率最低的
        min_freq_key = min(self.frequency, key=lambda k: self.frequency[k])
        self._evict(min_freq_key)
    
    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        # 估算内存使用
        total_size = sum(entry.size_bytes for entry in self.cache.values())
        self.stats.memory_usage_mb = total_size / 1024 / 1024
        return self.stats
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.frequency.clear()
        self.stats = CacheStats()


class TieredCacheManager:
    """分层缓存管理器"""
    
    def __init__(self, 
                 l1_size: int = 100,
                 l2_size: int = 1000,
                 redis_client=None):
        """
        初始化分层缓存
        Args:
            l1_size: L1 缓存大小（内存，最快）
            l2_size: L2 缓存大小（内存，中等）
            redis_client: Redis 客户端（可选，最慢）
        """
        self.l1_cache = LFUCache(max_size=l1_size)
        self.l2_cache = LFUCache(max_size=l2_size)
        self.redis_client = redis_client
        self.ttl_manager = AdaptiveTTLManager()
        
        self.stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'redis_hits': 0,
            'misses': 0
        }
    
    def get(self, key: str, cache_type: str = "query") -> Optional[Any]:
        """
        分层获取缓存
        Args:
            key: 缓存键
            cache_type: 缓存类型
        Returns:
            缓存值
        """
        # L1 缓存（最快）
        value = self.l1_cache.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value
        
        # L2 缓存
        value = self.l2_cache.get(key)
        if value is not None:
            self.stats['l1_hits'] += 0  # L1 miss
            self.stats['l2_hits'] += 1
            # 提升到 L1
            self.l1_cache.set(key, value, ttl=300)  # L1 TTL 较短
            return value
        
        # Redis 缓存（如果有）
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    value = json.loads(data)
                    self.stats['redis_hits'] += 1
                    # 提升到 L2
                    self.l2_cache.set(key, value, ttl=600)
                    return value
            except:
                pass
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = "query"):
        """
        分层设置缓存
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
            cache_type: 缓存类型
        """
        # 计算自适应 TTL
        if ttl is None:
            ttl = self.ttl_manager.compute_ttl(key)
        
        # 所有层级都存储
        self.l1_cache.set(key, value, ttl=min(ttl, 300))  # L1 短 TTL
        self.l2_cache.set(key, value, ttl=min(ttl, 600))  # L2 中 TTL
        
        # Redis 存储（如果有）
        if self.redis_client and ttl > 0:
            try:
                data = json.dumps(value, ensure_ascii=False)
                self.redis_client.setex(key, ttl, data)
            except:
                pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()
        
        total_hits = (self.stats['l1_hits'] + self.stats['l2_hits'] + 
                     self.stats['redis_hits'])
        total_requests = total_hits + self.stats['misses']
        
        return {
            'l1_hit_rate': self.stats['l1_hits'] / total_requests if total_requests > 0 else 0,
            'l2_hit_rate': self.stats['l2_hits'] / total_requests if total_requests > 0 else 0,
            'redis_hit_rate': self.stats['redis_hits'] / total_requests if total_requests > 0 else 0,
            'overall_hit_rate': total_hits / total_requests if total_requests > 0 else 0,
            'l1_size': l1_stats.size,
            'l2_size': l2_stats.size,
            'l1_memory_mb': l1_stats.memory_usage_mb,
            'l2_memory_mb': l2_stats.memory_usage_mb,
            'total_hits': total_hits,
            'misses': self.stats['misses']
        }


class SmartCacheManager:
    """智能缓存管理器"""
    
    def __init__(self, redis_config: Optional[Dict] = None):
        """
        初始化智能缓存
        Args:
            redis_config: Redis 配置
        """
        # 尝试连接 Redis
        self.redis_client = None
        if redis_config:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    password=redis_config.get('password'),
                    decode_responses=True
                )
                self.redis_client.ping()
                print("Redis 连接成功")
            except Exception as e:
                print(f"Redis 连接失败：{e}，使用内存缓存")
        
        # 分层缓存
        self.tiered_cache = TieredCacheManager(
            l1_size=100,
            l2_size=1000,
            redis_client=self.redis_client
        )
        
        # 查询模式分析
        self.query_patterns = {}
        self.hot_queries = set()
        
        # 预加载列表
        self.prefetch_list = []
    
    def analyze_query_pattern(self, query: str) -> str:
        """
        分析查询模式
        Args:
            query: 查询文本
        Returns:
            模式类型
        """
        # 简单模式识别
        if any(word in query for word in ['销售额', '营收', '销量']):
            return 'sales_metric'
        elif any(word in query for word in ['地区', '区域', '城市']):
            return 'geographic'
        elif any(word in query for word in ['时间', '日期', '月', '年']):
            return 'temporal'
        elif any(word in query for word in ['对比', '比较', 'vs']):
            return 'comparison'
        else:
            return 'general'
    
    def get_or_compute(self, query: str, compute_fn: Callable, 
                      use_cache: bool = True) -> Any:
        """
        获取或计算（智能缓存）
        Args:
            query: 查询文本
            compute_fn: 计算函数
            use_cache: 是否使用缓存
        Returns:
            结果
        """
        # 生成缓存键
        key = f"query:{hashlib.md5(query.encode('utf-8')).hexdigest()}"
        
        # 尝试从缓存获取
        if use_cache:
            cached = self.tiered_cache.get(key)
            if cached is not None:
                return cached
        
        # 计算结果
        result = compute_fn(query)
        
        # 分析查询模式
        pattern = self.analyze_query_pattern(query)
        
        # 更新模式统计
        if pattern not in self.query_patterns:
            self.query_patterns[pattern] = {'count': 0, 'queries': []}
        self.query_patterns[pattern]['count'] += 1
        self.query_patterns[pattern]['queries'].append(query)
        
        # 识别热点查询
        if len(self.query_patterns[pattern]['queries']) >= 5:
            self.hot_queries.add(query)
        
        # 缓存结果
        if use_cache:
            # 热点查询使用更长 TTL
            if query in self.hot_queries:
                ttl = 7200  # 2 小时
            else:
                ttl = None  # 自适应 TTL
            
            self.tiered_cache.set(key, result, ttl=ttl)
        
        return result
    
    def prefetch(self, queries: List[str], compute_fn: Callable):
        """
        预加载缓存
        Args:
            queries: 查询列表
            compute_fn: 计算函数
        """
        print(f"预加载 {len(queries)} 个查询...")
        
        for query in queries:
            try:
                self.get_or_compute(query, compute_fn, use_cache=True)
            except Exception as e:
                print(f"预加载失败 {query}: {e}")
        
        print("预加载完成")
    
    def get_optimization_report(self) -> Dict:
        """获取优化报告"""
        stats = self.tiered_cache.get_stats()
        
        # 热点查询统计
        hot_query_count = len(self.hot_queries)
        
        # 模式分布
        pattern_distribution = {
            pattern: data['count'] 
            for pattern, data in self.query_patterns.items()
        }
        
        return {
            **stats,
            'hot_queries_count': hot_query_count,
            'pattern_distribution': pattern_distribution,
            'recommendations': self._generate_recommendations(stats)
        }
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if stats['l1_hit_rate'] < 0.3:
            recommendations.append("建议增加 L1 缓存大小或优化查询局部性")
        
        if stats['overall_hit_rate'] < 0.7:
            recommendations.append("整体命中率较低，建议分析查询模式并预加载")
        
        if stats['l1_memory_mb'] < 1:
            recommendations.append("L1 缓存利用率低，可适当减小")
        
        if len(self.hot_queries) > 0:
            recommendations.append(f"检测到 {len(self.hot_queries)} 个热点查询，建议专门优化")
        
        return recommendations


def create_optimized_cache(redis_host: str = 'localhost', 
                          redis_port: int = 6379) -> SmartCacheManager:
    """
    创建优化的缓存管理器
    Args:
        redis_host: Redis 主机
        redis_port: Redis 端口
    Returns:
        SmartCacheManager 实例
    """
    redis_config = {
        'host': redis_host,
        'port': redis_port
    }
    
    return SmartCacheManager(redis_config=redis_config)


if __name__ == "__main__":
    # 示例：智能缓存使用
    print("智能缓存优化示例\n")
    
    # 创建缓存管理器
    cache = create_optimized_cache()
    
    # 模拟计算函数
    def mock_compute(query):
        time.sleep(0.01)  # 模拟计算延迟
        return {'query': query, 'result': 'mock_data'}
    
    # 模拟查询
    queries = ["销售额"] * 10 + ["销量"] * 5 + ["营收"] * 3
    
    for i, query in enumerate(queries):
        result = cache.get_or_compute(query, mock_compute)
        
        if (i + 1) % 5 == 0:
            stats = cache.get_optimization_report()
            print(f"\n查询 {i+1} 次后统计:")
            print(f"  命中率：{stats['overall_hit_rate']:.2%}")
            print(f"  L1 命中：{stats['l1_hit_rate']:.2%}")
            print(f"  L2 命中：{stats['l2_hit_rate']:.2%}")
            print(f"  热点查询数：{stats['hot_queries_count']}")
    
    # 优化建议
    print("\n优化建议:")
    for rec in stats['recommendations']:
        print(f"  - {rec}")
