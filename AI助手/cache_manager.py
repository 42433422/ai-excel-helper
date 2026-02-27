# 缓存管理器
import time
import hashlib
import json
from typing import Any, Optional, Dict
from functools import wraps

class CacheManager:
    """API响应缓存管理器"""
    
    def __init__(self, default_ttl: int = 30):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            cache_entry = self.cache[key]
            if time.time() < cache_entry['expires_at']:
                return cache_entry['data']
            else:
                # 过期删除
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        expires_at = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            'data': data,
            'expires_at': expires_at,
            'created_at': time.time()
        }
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = len(self.cache)
        valid = sum(1 for entry in self.cache.values() if time.time() < entry['expires_at'])
        expired = total - valid
        
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': expired,
            'cache_size': sum(len(str(v['data'])) for v in self.cache.values())
        }

# 全局缓存实例
cache_manager = CacheManager(default_ttl=60)  # 默认60秒缓存

def cached_endpoint(ttl: int = 60, key_prefix: str = None):
    """API缓存装饰器"""
    def decorator(f):
        prefix = key_prefix if key_prefix is not None else f.__name__
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        return decorated_function
    return decorator

class StatusCache:
    """状态缓存管理器"""
    
    def __init__(self):
        self.status_cache = {}
        self.last_update = {}
    
    def get_status(self, module: str) -> Optional[Dict]:
        """获取模块状态"""
        if module in self.status_cache:
            last_update = self.last_update.get(module, 0)
            # 如果在5秒内，不重新获取
            if time.time() - last_update < 5:
                return self.status_cache[module]
        return None
    
    def set_status(self, module: str, status: Dict) -> None:
        """设置模块状态"""
        self.status_cache[module] = status
        self.last_update[module] = time.time()

# 全局状态缓存
status_cache = StatusCache()