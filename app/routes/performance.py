# -*- coding: utf-8 -*-
"""
性能监控和优化 API 路由

提供：
- 性能指标查询
- 缓存状态查看
- 健康检查
- 优化配置管理
- Prometheus 指标导出
"""

import logging
import time
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

performance_bp = Blueprint("performance", __name__, url_prefix="/api/performance")


@performance_bp.route("/status", methods=["GET"])
def get_performance_status():
    """
    获取性能优化系统状态

    Returns:
        各组件状态、统计信息
    """
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer._initialized:
            return jsonify({
                "success": False,
                "message": "性能优化系统未初始化",
                "data": None
            }), 503

        status = optimizer.get_status()

        return jsonify({
            "success": True,
            "data": status,
            "timestamp": time.time()
        })

    except Exception as e:
        logger.error(f"获取性能状态失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": None
        }), 500


@performance_bp.route("/health", methods=["GET"])
def health_check():
    """
    健康检查端点

    用于监控探针（Kubernetes liveness/readiness probe）
    """
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        health = optimizer.get_health_check()

        status_code = 200 if health["status"] == "healthy" else (503 if health["status"] == "degraded" else 500)

        response = {
            "status": health["status"],
            "timestamp": health["timestamp"],
            "checks": health.get("checks", {}),
        }

        if "issues" in health:
            response["issues"] = health["issues"]

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500


@performance_bp.route("/metrics/summary", methods=["GET"])
def get_metrics_summary():
    """
    获取性能指标摘要

    Query Parameters:
        - minutes: 统计时间窗口（分钟），默认 5
    """
    try:
        minutes = request.args.get("minutes", 5, type=int)
        minutes = max(1, min(minutes, 60))

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.performance_monitor:
            return jsonify({
                "success": False,
                "message": "性能监控未启用",
                "data": None
            }), 503

        summary = optimizer.performance_monitor.get_metrics_summary(minutes=minutes)

        return jsonify({
            "success": True,
            "data": summary
        })

    except Exception as e:
        logger.error(f"获取指标摘要失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": None
        }), 500


@performance_bp.route("/metrics/prometheus", methods=["GET"])
def get_prometheus_metrics():
    """
    导出 Prometheus 格式指标

    用于 Prometheus 抓取
    """
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.performance_monitor:
            return "# XCAGI metrics unavailable\n", 503

        metrics_text = optimizer.performance_monitor.get_prometheus_metrics()

        return metrics_text, 200, {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"}

    except Exception as e:
        logger.error(f"导出 Prometheus 指标失败: {e}")
        return f"# Error: {str(e)}\n", 500


@performance_bp.route("/cache/stats", methods=["GET"])
def get_cache_stats():
    """获取缓存统计信息"""
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.redis_cache:
            return jsonify({
                "success": False,
                "message": "Redis 缓存未初始化",
                "data": None
            }), 503

        stats = optimizer.redis_cache.stats

        return jsonify({
            "success": True,
            "data": stats
        })

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": None
        }), 500


@performance_bp.route("/cache/clear", methods=["POST"])
def clear_cache():
    """
    清除缓存

    Query Parameters:
        - pattern: 要清除的缓存模式（可选，默认清除所有）
    """
    try:
        pattern = request.args.get("pattern")

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.redis_cache:
            return jsonify({
                "success": False,
                "message": "Redis 缓存未初始化"
            }), 503

        if pattern:
            cleared = optimizer.redis_cache.clear_pattern(pattern)
            message = f"已清除模式 '{pattern}' 的缓存 ({cleared} 个键)"
        else:
            optimizer.redis_cache.clear_local_cache()
            message = "已清除本地缓存"

        logger.info(message)

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@performance_bp.route("/cache/invalidate", methods=["POST"])
def invalidate_cache():
    """
    使指定缓存失效

    Body JSON:
        - keys: 要失效的键列表
    """
    try:
        data = request.get_json() or {}
        keys = data.get("keys", [])

        if not keys:
            return jsonify({
                "success": False,
                "message": "请提供要失效的键列表"
            }), 400

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.redis_cache:
            return jsonify({
                "success": False,
                "message": "Redis 缓存未初始化"
            }), 503

        deleted = optimizer.redis_cache.delete(*keys)

        return jsonify({
            "success": True,
            "data": {
                "deleted_count": deleted,
                "requested_keys": len(keys)
            },
            "message": f"已删除 {deleted} 个缓存键"
        })

    except Exception as e:
        logger.error(f"缓存失效失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@performance_bp.route("/tasks/status", methods=["GET"])
def get_tasks_status():
    """获取异步任务状态"""
    try:
        task_id = request.args.get("task_id")

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.async_task_manager:
            return jsonify({
                "success": False,
                "message": "异步任务管理未启用",
                "data": None
            }), 503

        if task_id:
            result = optimizer.async_task_manager.get_status(task_id)
            if result is None:
                return jsonify({
                    "success": False,
                    "message": "任务不存在",
                    "data": None
                }), 404

            return jsonify({
                "success": True,
                "data": {
                    "task_id": result.task_id,
                    "status": result.status.value,
                    "progress": result.progress,
                    "duration_ms": round(result.duration_ms, 2) if result.duration_ms else None,
                    "error": result.error,
                    "metadata": result.metadata,
                }
            })

        active_tasks = optimizer.async_task_manager.active_tasks
        stats = optimizer.async_task_manager.stats

        return jsonify({
            "success": True,
            "data": {
                "active_tasks": {
                    tid: {
                        "task_id": t.task_id,
                        "status": t.status.value,
                        "progress": t.progress,
                        "name": t.metadata.get("task_name", ""),
                    }
                    for tid, t in active_tasks.items()
                } if active_tasks else {},
                "stats": stats,
            }
        })

    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": None
        }), 500


@performance_bp.route("/alerts", methods=["GET"])
def get_alerts():
    """
    获取性能告警列表

    Query Parameters:
        - level: 告警级别过滤 (warning/critical)
        - limit: 返回数量限制，默认 20
    """
    try:
        level = request.args.get("level")
        limit = request.args.get("limit", 20, type=int)

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.performance_monitor:
            return jsonify({
                "success": False,
                "message": "性能监控未启用",
                "data": []
            }), 503

        alerts = optimizer.performance_monitor.get_alerts(level=level, limit=limit)

        return jsonify({
            "success": True,
            "data": alerts,
            "count": len(alerts)
        })

    except Exception as e:
        logger.error(f"获取告警列表失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": []
        }), 500


@performance_bp.route("/slow-queries", methods=["GET"])
def get_slow_queries():
    """
    获取慢查询列表

    Query Parameters:
        - limit: 返回数量限制，默认 20
    """
    try:
        limit = request.args.get("limit", 20, type=int)

        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if not optimizer.query_optimizer:
            return jsonify({
                "success": False,
                "message": "查询优化器未启用",
                "data": []
            }), 503

        slow_queries = optimizer.query_optimizer.get_slow_queries(limit=limit)

        return jsonify({
            "success": True,
            "data": slow_queries,
            "count": len(slow_queries)
        })

    except Exception as e:
        logger.error(f"获取慢查询列表失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": []
        }), 500


@performance_bp.route("/optimize/reinitialize", methods=["POST"])
def reinitialize_optimizer():
    """重新初始化性能优化系统"""
    try:
        from app.utils.performance_initializer import init_performance_optimization
        from app import create_app
        from app.config import DevelopmentConfig

        app = create_app(DevelopmentConfig)
        with app.app_context():
            optimizer = init_performance_optimization(app)

        return jsonify({
            "success": True,
            "message": "性能优化系统已重新初始化",
            "data": optimizer.get_status()
        })

    except Exception as e:
        logger.error(f"重新初始化失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


def register_performance_blueprint(app):
    """注册性能监控蓝图"""
    app.register_blueprint(performance_bp)
    logger.info("✅ 性能监控 API 已注册 (/api/performance/*)")
