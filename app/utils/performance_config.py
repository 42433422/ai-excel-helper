# -*- coding: utf-8 -*-
"""
XCAGI 性能优化配置

所有性能相关的环境变量和默认值都在这里定义。
"""

import os


class PerformanceConfig:
    """性能优化配置"""

    # ========== 缓存配置 ==========
    # Redis 缓存前缀
    REDIS_CACHE_PREFIX: str = os.environ.get("XCAGI_REDIS_CACHE_PREFIX", "xcagi:")

    # 默认缓存 TTL（秒）
    DEFAULT_CACHE_TTL: int = int(os.environ.get("XCAGI_DEFAULT_CACHE_TTL", "300"))

    # 空值缓存 TTL（防止穿透）
    CACHE_NULL_TTL: int = int(os.environ.get("XCAGI_CACHE_NULL_TTL", "60"))

    # 本地 L1 缓存大小
    LOCAL_CACHE_SIZE: int = int(os.environ.get("XCAGI_LOCAL_CACHE_SIZE", "1000"))

    # 本地 L1 缓存 TTL（秒）
    LOCAL_CACHE_TTL: int = int(os.environ.get("XCAGI_LOCAL_CACHE_TTL", "10"))

    # 产品缓存 TTL
    PRODUCT_CACHE_TTL: int = int(os.environ.get("XCAGI_PRODUCT_CACHE_TTL", "300"))

    # 产品列表缓存 TTL
    PRODUCT_LIST_CACHE_TTL: int = int(os.environ.get("XCAGI_PRODUCT_LIST_CACHE_TTL", "60"))

    # AI 响应缓存 TTL
    AI_RESPONSE_CACHE_TTL: int = int(os.environ.get("XCAGI_AI_RESPONSE_CACHE_TTL", "300"))

    # 意图识别缓存 TTL
    INTENT_CACHE_TTL: int = int(os.environ.get("XCAGI_INTENT_CACHE_TTL", "300"))

    # 客户数据缓存 TTL
    CUSTOMER_CACHE_TTL: int = int(os.environ.get("XCAGI_CUSTOMER_CACHE_TTL", "600"))

    # ========== 查询优化配置 ==========
    # 慢查询阈值（秒）
    SLOW_QUERY_THRESHOLD: float = float(os.environ.get("XCAGI_SLOW_QUERY_THRESHOLD", "0.5"))

    # 批量操作最大大小
    MAX_BATCH_SIZE: int = int(os.environ.get("XCAGI_MAX_BATCH_SIZE", "100"))

    # ========== 异步任务配置 ==========
    # 默认任务超时（秒）
    TASK_DEFAULT_TIMEOUT: int = int(os.environ.get("XCAGI_TASK_DEFAULT_TIMEOUT", "300"))

    # 最大重试次数
    TASK_MAX_RETRIES: int = int(os.environ.get("XCAGI_TASK_MAX_RETRIES", "3"))

    # 重试延迟（秒）
    TASK_RETRY_DELAY: int = int(os.environ.get("XCAGI_TASK_RETRY_DELAY", "5"))

    # 强制同步模式（调试用）
    FORCE_SYNC_TASKS: bool = os.environ.get("XCAGI_FORCE_SYNC_TASKS", "0") == "1"

    # ========== 请求去重配置 ==========
    # 去重时间窗口（秒）
    DEDUP_WINDOW: int = int(os.environ.get("XCAGI_DEDUP_WINDOW", "60"))

    # 最大去重键数
    DEDUP_MAX_KEYS: int = int(os.environ.get("XCAGI_DEDUP_MAX_KEYS", "10000"))

    # ========== 性能监控配置 ==========
    # 性能历史记录大小
    PERF_HISTORY_SIZE: int = int(os.environ.get("XCAGI_PERF_HISTORY_SIZE", "1000"))

    # 慢 API 阈值（毫秒）
    SLOW_API_THRESHOLD_MS: float = float(os.environ.get("XCAGI_SLOW_API_THRESHOLD", "1000"))

    # 内存警告阈值（MB）
    MEMORY_WARNING_MB: int = int(os.environ.get("XCAGI_MEMORY_WARNING", "512"))

    # ========== 限流配置 ==========
    # 默认每用户每分钟请求数
    DEFAULT_RATE_LIMIT: int = int(os.environ.get("XCAGI_DEFAULT_RATE_LIMIT", "100"))

    # AI 接口限流
    AI_RATE_LIMIT: int = int(os.environ.get("XCAGI_AI_RATE_LIMIT", "30"))

    # 文件上传接口限流
    UPLOAD_RATE_LIMIT: int = int(os.environ.get("XCAGI_UPLOAD_RATE_LIMIT", "10"))

    # ========== 熔断配置 ==========
    # 默认失败阈值
    CIRCUIT_FAILURE_THRESHOLD: int = int(os.environ.get("XCAGI_CIRCUIT_FAILURE_THRESHOLD", "5"))

    # 恢复超时（秒）
    CIRCUIT_RECOVERY_TIMEOUT: int = int(os.environ.get("XCAGI_CIRCUIT_RECOVERY_TIMEOUT", "60"))

    @classmethod
    def get_all_configs(cls) -> dict:
        """获取所有配置项"""
        return {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith("_") and attr.isupper()
        }

    @classmethod
    def validate(cls) -> list:
        """验证配置有效性，返回问题列表"""
        issues = []

        if cls.LOCAL_CACHE_SIZE < 10:
            issues.append("LOCAL_CACHE_SIZE 过小 (< 10)")

        if cls.DEFAULT_CACHE_TTL < 1:
            issues.append("DEFAULT_CACHE_TTL 过小 (< 1s)")

        if cls.SLOW_QUERY_THRESHOLD <= 0:
            issues.append("SLOW_QUERY_THRESHOLD 必须为正数")

        if cls.MAX_BATCH_SIZE < 1:
            issues.append("MAX_BATCH_SIZE 必须为正数")

        return issues

    @classmethod
    def print_config(cls) -> None:
        """打印当前配置"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info("=" * 50)
        logger.info("📊 XCAGI 性能优化配置")
        logger.info("=" * 50)

        for key, value in cls.get_all_configs().items():
            display_key = key.replace("_", " ").title()
            logger.info(f"  {display_key}: {value}")

        issues = cls.validate()
        if issues:
            logger.warning(f"⚠️  配置问题 ({len(issues)}):")
            for issue in issues:
                logger.warning(f"    - {issue}")
        else:
            logger.info("✅ 所有配置有效")

        logger.info("=" * 50)


def get_performance_config() -> PerformanceConfig:
    """获取性能配置单例"""
    return PerformanceConfig()
