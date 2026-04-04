"""
深圳奇士美定制 PRO Mod - 蓝图注册
"""

import json
import logging
import os
import sys
import importlib.util
from datetime import datetime
from flask import Blueprint, Response, jsonify, request

logger = logging.getLogger(__name__)

_example_bp = None
_qa_manager_module = None
_PHONE_AGENT_LAST_STATUS_BY_CHANNEL = {}


def _phone_agent_status_ok_response(data: dict) -> Response:
    """
    GET /phone-agent/status 始终返回 HTTP 200 + JSON。
    避免 get_status/jsonify 抛错时前端只显示「HTTP 500」且响应体非 JSON。
    """
    try:
        payload = {"success": True, "data": data if isinstance(data, dict) else {}}
        body = json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False)
    except Exception:
        try:
            body = json.dumps(
                {
                    "success": True,
                    "data": {
                        "running": False,
                        "phone_agent_status_json_dump_failed": True,
                    },
                },
                ensure_ascii=False,
                default=str,
                allow_nan=False,
            )
        except Exception:
            body = '{"success":true,"data":{"running":false,"phone_agent_status_json_dump_failed":true}}'
    return Response(body, status=200, mimetype="application/json; charset=utf-8")


def _load_qa_manager():
    """动态加载问答包管理器"""
    global _qa_manager_module
    if _qa_manager_module is not None:
        return _qa_manager_module
    
    try:
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        qa_manager_path = os.path.join(current_dir, 'qa_package_manager.py')
        
        logger.info(f"[奇士美 PRO] 尝试从 {qa_manager_path} 加载问答包管理器")
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location("qa_package_manager", qa_manager_path)
        if spec is None or spec.loader is None:
            logger.error(f"[奇士美 PRO] 无法创建模块spec")
            return None
        
        _qa_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_qa_manager_module)
        
        logger.info(f"[奇士美 PRO] 问答包管理器加载成功")
        return _qa_manager_module
    except Exception as e:
        import traceback
        logger.error(f"[奇士美 PRO] 加载问答包管理器失败: {e}")
        logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
        return None


def create_blueprint(mod_id: str):
    """创建专业版定制蓝图"""
    bp = Blueprint(mod_id, __name__, url_prefix=f"/api/mod/{mod_id}")

    @bp.route("/dashboard", methods=["GET"])
    def get_dashboard():
        """获取专业版仪表盘数据"""
        return jsonify({
            "success": True,
            "data": {
                "company": "深圳奇士美",
                "version": "PRO",
                "features": [
                    "高级数据分析",
                    "自定义报表",
                    "批量处理",
                    "智能推荐"
                ],
                "stats": {
                    "total_orders": 1234,
                    "total_products": 567,
                    "total_customers": 890,
                    "today_revenue": 99999.99
                },
                "last_updated": datetime.now().isoformat()
            }
        })

    @bp.route("/advanced-settings", methods=["GET"])
    def get_advanced_settings():
        """获取高级设置"""
        return jsonify({
            "success": True,
            "data": {
                "pro_features_enabled": True,
                "custom_theme": "qsm-pro",
                "auto_backup": True,
                "smart_recommendations": True,
                "batch_processing": True
            }
        })

    @bp.route("/advanced-settings", methods=["POST"])
    def update_advanced_settings():
        """更新高级设置"""
        data = request.get_json()
        logger.info(f"更新专业版设置：{data}")
        
        return jsonify({
            "success": True,
            "message": "设置已保存",
            "data": data
        })

    @bp.route("/batch-process", methods=["POST"])
    def batch_process():
        """批量处理接口"""
        data = request.get_json()
        items = data.get("items", [])
        
        processed = len(items)
        success = processed
        
        logger.info(f"批量处理完成：{processed} 项")
        
        return jsonify({
            "success": True,
            "message": f"批量处理完成，成功 {success}/{processed}",
            "data": {
                "total": processed,
                "success": success,
                "failed": 0
            }
        })

    @bp.route("/smart-recommend", methods=["POST"])
    def smart_recommend():
        """智能推荐接口"""
        data = request.get_json()
        context = data.get("context", {})
        
        # 这里可以实现智能推荐逻辑
        recommendations = [
            {"type": "product", "id": 1, "reason": "热销产品"},
            {"type": "product", "id": 2, "reason": "库存充足"},
            {"type": "customer", "id": 3, "reason": "高价值客户"}
        ]
        
        return jsonify({
            "success": True,
            "data": {
                "recommendations": recommendations,
                "algorithm": "qsm-pro-v1"
            }
        })

    # 问答包管理API
    @bp.route("/qa-packages", methods=["GET"])
    def get_qa_packages():
        """获取所有问答包"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            packages = manager.get_all_packages()
            logger.info(f"[奇士美 PRO] 获取 {len(packages)} 个问答包")
            
            return jsonify({
                "success": True,
                "data": packages
            })
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 获取问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @bp.route("/qa-packages/&lt;package_id&gt;", methods=["GET"])
    def get_qa_package(package_id):
        """获取单个问答包"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            package = manager.get_package(package_id)
            if package:
                return jsonify({
                    "success": True,
                    "data": package
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "问答包不存在"
                }), 404
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 获取问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @bp.route("/qa-packages", methods=["POST"])
    def create_qa_package():
        """创建问答包"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            data = request.get_json()
            package = manager.create_package(data)
            return jsonify({
                "success": True,
                "message": "问答包创建成功",
                "data": package
            })
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 创建问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @bp.route("/qa-packages/&lt;package_id&gt;", methods=["PUT"])
    def update_qa_package(package_id):
        """更新问答包"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            data = request.get_json()
            package = manager.update_package(package_id, data)
            if package:
                return jsonify({
                    "success": True,
                    "message": "问答包更新成功",
                    "data": package
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "问答包不存在"
                }), 404
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 更新问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @bp.route("/qa-packages/&lt;package_id&gt;", methods=["DELETE"])
    def delete_qa_package(package_id):
        """删除问答包"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            success = manager.delete_package(package_id)
            if success:
                return jsonify({
                    "success": True,
                    "message": "问答包删除成功"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "问答包不存在"
                }), 404
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 删除问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @bp.route("/qa-packages/&lt;package_id&gt;/reset", methods=["POST"])
    def reset_qa_package(package_id):
        """重置问答包为默认"""
        try:
            qa_module = _load_qa_manager()
            if not qa_module:
                return jsonify({
                    "success": False,
                    "message": "问答包管理器加载失败"
                }), 500
            
            get_manager = getattr(qa_module, 'get_qa_package_manager', None)
            if not get_manager:
                return jsonify({
                    "success": False,
                    "message": "找不到问答包管理器函数"
                }), 500
            
            manager = get_manager()
            package = manager.reset_package(package_id)
            if package:
                return jsonify({
                    "success": True,
                    "message": "问答包重置成功",
                    "data": package
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "无法重置此问答包"
                }), 400
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 重置问答包失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    def _phone_agent_status_response():
        """GET /phone-agent/status（及拼写别名 /statu）共用：恒 200 + JSON。"""
        ch = (request.args.get("channel") or "").strip().lower()
        if ch not in ("wechat", "adb"):
            ch = "wechat"
        manager_down = {
            "running": False,
            "window_monitor_available": False,
            "audio_capture_available": False,
            "asr_available": False,
            "intent_handler_available": False,
            "tts_available": False,
            "vb_cable_available": False,
            "phone_agent_manager_load_failed": True,
            "phone_agent_manager_load_message": "电话业务员管理器加载失败（见后端日志：import_mod_backend_py services）",
        }
        try:
            manager = _load_phone_agent_manager()
            if not manager:
                cached = _PHONE_AGENT_LAST_STATUS_BY_CHANNEL.get(ch)
                if isinstance(cached, dict) and cached:
                    return _phone_agent_status_ok_response(
                        {
                            **cached,
                            "phone_agent_status_from_cache": True,
                            "phone_agent_manager_load_failed": True,
                            "phone_agent_manager_load_message": manager_down.get("phone_agent_manager_load_message"),
                        }
                    )
                return _phone_agent_status_ok_response(manager_down)
            if ch in ("wechat", "adb") and hasattr(manager, "set_phone_channel"):
                manager.set_phone_channel(ch)

            try:
                status = manager.get_status()
            except Exception as e:
                import traceback

                logger.error(f"[奇士美 PRO] get_status 失败: {e}")
                logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
                return _phone_agent_status_ok_response(
                    {
                        "running": False,
                        "window_monitor_available": False,
                        "audio_capture_available": False,
                        "asr_available": False,
                        "intent_handler_available": False,
                        "tts_available": False,
                        "vb_cable_available": False,
                        "phone_agent_get_status_failed": True,
                        "phone_agent_get_status_message": str(e)[:800],
                    }
                )

            if not isinstance(status, dict):
                status = {"running": False, "status_non_dict": True, "status_repr": str(status)[:500]}
            _PHONE_AGENT_LAST_STATUS_BY_CHANNEL[ch] = dict(status)
            return _phone_agent_status_ok_response(status)
        except Exception as e:
            import traceback

            logger.error(f"[奇士美 PRO] 获取电话业务员状态失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            cached = _PHONE_AGENT_LAST_STATUS_BY_CHANNEL.get(ch)
            if isinstance(cached, dict) and cached:
                return _phone_agent_status_ok_response(
                    {
                        **cached,
                        "phone_agent_status_from_cache": True,
                        "phone_agent_status_route_failed": True,
                        "phone_agent_status_route_message": str(e)[:800],
                    }
                )
            return _phone_agent_status_ok_response(
                {
                    **manager_down,
                    "phone_agent_manager_load_failed": False,
                    "phone_agent_status_route_failed": True,
                    "phone_agent_status_route_message": str(e)[:800],
                }
            )

    @bp.route("/phone-agent/status", methods=["GET"])
    def get_phone_agent_status():
        """获取电话业务员状态"""
        return _phone_agent_status_response()

    @bp.route("/phone-agent/statu", methods=["GET"])
    def get_phone_agent_status_typo():
        """兼容 URL 拼写错误（少写 s）；请优先使用 /phone-agent/status。"""
        return _phone_agent_status_response()

    @bp.route("/phone-agent/start", methods=["POST"])
    def start_phone_agent():
        """启动电话业务员（业务失败统一 HTTP 200 + success:false，便于前端解析 JSON）"""
        try:
            manager = _load_phone_agent_manager()
            if not manager:
                return jsonify({
                    "success": False,
                    "message": "电话业务员管理器加载失败"
                }), 200

            body = request.get_json(silent=True) or {}
            ch = (
                request.args.get("channel")
                or body.get("channel")
                or ""
            )
            ch = str(ch).strip().lower()
            if ch in ("wechat", "adb") and hasattr(manager, "set_phone_channel"):
                manager.set_phone_channel(ch)

            success = manager.start()
            if success:
                logger.info("[奇士美 PRO] 电话业务员已通过API启动")
                return jsonify({
                    "success": True,
                    "message": "电话业务员已启动"
                })
            else:
                detail = getattr(manager, "_last_start_error", None)
                if not (detail and str(detail).strip()):
                    try:
                        st = manager.get_status()
                        if isinstance(st, dict):
                            detail = st.get("phone_agent_last_start_error") or detail
                    except Exception:
                        pass
                if not (detail and str(detail).strip()):
                    detail = (
                        "电话业务员启动失败（未记录具体原因；请查看运行 run.py 的控制台里「奇士美 PRO」相关日志）"
                    )
                return jsonify({
                    "success": False,
                    "message": str(detail).strip(),
                }), 200
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 启动电话业务员失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 200

    @bp.route("/phone-agent/stop", methods=["POST"])
    def stop_phone_agent():
        """停止电话业务员"""
        try:
            manager = _load_phone_agent_manager()
            if not manager:
                return jsonify({
                    "success": False,
                    "message": "电话业务员管理器加载失败"
                }), 200

            manager.stop()
            logger.info("[奇士美 PRO] 电话业务员已通过API停止")
            return jsonify({
                "success": True,
                "message": "电话业务员已停止"
            })
        except Exception as e:
            import traceback
            logger.error(f"[奇士美 PRO] 停止电话业务员失败: {e}")
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "message": str(e)
            }), 200

    return bp


def _load_phone_agent_manager():
    """动态加载电话业务员管理器"""
    try:
        from app.infrastructure.mods.mod_manager import import_mod_backend_py
        import os

        mod_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        module = import_mod_backend_py(mod_path, "sz-qsm-pro", "services")
        return module.get_phone_agent_manager()
    except Exception as e:
        import traceback
        logger.error(f"Failed to load phone agent manager: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return None


def register_blueprints(app, mod_id: str):
    """注册蓝图到 Flask 应用"""
    global _example_bp
    _example_bp = create_blueprint(mod_id)
    app.register_blueprint(_example_bp)
    logger.info(f"深圳奇士美定制 PRO 蓝图已注册：{mod_id}")


def _comms_mod_info(*args, **kwargs):
    """其他 Mod 可 call('sz-qsm-pro', 'mod_info') 获取本扩展元信息（演示 Mod 间通信）。"""
    from app.infrastructure.mods.comms import get_caller_mod_id

    return {
        "id": "sz-qsm-pro",
        "name": "奇士美 PRO",
        "caller_mod_id": get_caller_mod_id(),
    }


def mod_init():
    """Mod 初始化"""
    logger.info("深圳奇士美定制 PRO Mod 后端已初始化")
    try:
        from app.infrastructure.mods.comms import get_mod_comms

        get_mod_comms().register("sz-qsm-pro", "mod_info", _comms_mod_info, replace=True)
    except Exception as e:
        logger.warning("sz-qsm-pro comms register skipped: %s", e)

# 4243342
