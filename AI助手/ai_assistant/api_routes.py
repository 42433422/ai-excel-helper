# AI助手Flask API
from flask import Blueprint, request, jsonify, Response
import logging
import json
import time
import sys
import os
from functools import wraps

# 添加上级目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import cached_endpoint, status_cache

logger = logging.getLogger(__name__)

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/api/ai')

_ai_controller = None


def get_controller():
    """获取AI控制器"""
    global _ai_controller
    if _ai_controller is None:
        from .core import init_ai_assistant
        _ai_controller = init_ai_assistant()
    return _ai_controller


def require_initialized(f):
    """检查AI助手是否已初始化"""
    @wraps(f)
    def decorated(*args, **kwargs):
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI助手未初始化"
            }), 500
        return f(*args, **kwargs)
    return decorated


@ai_assistant_bp.route('/status', methods=['GET'])
@cached_endpoint(ttl=10, key_prefix="status")
def get_status():
    """获取AI助手状态"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": True,
                "initialized": False,
                "message": "AI助手尚未初始化"
            })

        status = controller.get_system_status()
        return jsonify({
            "success": True,
            "initialized": True,
            "data": status
        })

    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        })


@ai_assistant_bp.route('/init', methods=['POST'])
def initialize():
    """初始化AI助手"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "无法创建AI控制器"
            }), 500

        return jsonify({
            "success": True,
            "message": "AI助手初始化成功",
            "modules": controller.get_system_status().get("modules", {})
        })

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return jsonify({
            "success": False,
            "message": f"初始化失败: {str(e)}"
        }), 500


@ai_assistant_bp.route('/capture', methods=['POST'])
def capture_screen():
    """捕获屏幕"""
    try:
        controller = get_controller()
        if controller is None or controller.screen_captor is None:
            return jsonify({
                "success": False,
                "message": "屏幕捕获模块不可用"
            }), 500

        # 可选：指定捕获区域
        area = request.json.get('area') if request.is_json else None

        if area and len(area) == 4:
            screenshot = controller.screen_captor.capture(tuple(area))
        else:
            screenshot = controller.screen_captor.capture()

        if screenshot is None:
            return jsonify({
                "success": False,
                "message": "屏幕捕获失败"
            })

        # 保存截图
        screenshot_path = controller.screen_captor.capture_and_save()

        return jsonify({
            "success": True,
            "message": "屏幕捕获成功",
            "screenshot_path": screenshot_path
        })

    except Exception as e:
        logger.error(f"屏幕捕获失败: {e}")
        return jsonify({
            "success": False,
            "message": f"屏幕捕获失败: {str(e)}"
        })


@ai_assistant_bp.route('/ocr', methods=['POST'])
def recognize_text():
    """OCR文字识别"""
    try:
        controller = get_controller()
        if controller is None or controller.ocr_processor is None:
            return jsonify({
                "success": False,
                "message": "OCR模块不可用"
            }), 500

        # 捕获屏幕
        screenshot = controller.screen_captor.capture()
        if screenshot is None:
            return jsonify({
                "success": False,
                "message": "屏幕捕获失败"
            })

        # OCR识别
        text = controller.ocr_processor.recognize(screenshot)

        # 提取结构化数据
        structured_data = controller.ocr_processor.extract_structured_data(text)

        # 验证可读性
        verification = controller.ocr_processor.verify_readability(text)

        return jsonify({
            "success": True,
            "message": "OCR识别成功",
            "data": {
                "raw_text": text,
                "structured_data": structured_data,
                "verification": verification
            }
        })

    except Exception as e:
        logger.error(f"OCR识别失败: {e}")
        return jsonify({
            "success": False,
            "message": f"OCR识别失败: {str(e)}"
        })


@ai_assistant_bp.route('/analyze', methods=['POST'])
def analyze_content():
    """AI分析内容"""
    try:
        controller = get_controller()
        if controller is None or controller.ai_analyzer is None:
            return jsonify({
                "success": False,
                "message": "AI分析模块不可用"
            }), 500

        data = request.json if request.is_json else {}
        content = data.get('content', '')
        context = data.get('context', 'general')

        if not content:
            # 如果没有提供内容，自动捕获屏幕
            screenshot = controller.screen_captor.capture()
            if screenshot is not None:
                content = controller.ocr_processor.recognize(screenshot)

        if not content:
            return jsonify({
                "success": False,
                "message": "没有可供分析的内容"
            })

        result = controller.ai_analyzer.analyze(content, context)

        # 生成回复
        response_text = controller.ai_analyzer.generate_response(result)

        return jsonify({
            "success": True,
            "message": "分析完成",
            "data": {
                "analysis": result,
                "suggested_response": response_text
            }
        })

    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        return jsonify({
            "success": False,
            "message": f"分析失败: {str(e)}"
        })


@ai_assistant_bp.route('/execute', methods=['POST'])
def execute_actions():
    """执行自动化操作"""
    try:
        controller = get_controller()
        if controller is None or controller.automation_executor is None:
            return jsonify({
                "success": False,
                "message": "自动化执行模块不可用"
            }), 500

        data = request.json if request.is_json else {}
        actions = data.get('actions', [])

        if not actions:
            return jsonify({
                "success": False,
                "message": "没有提供操作指令"
            })

        result = controller.automation_executor.execute(actions)

        return jsonify({
            "success": True,
            "message": "操作执行完成",
            "data": result
        })

    except Exception as e:
        logger.error(f"操作执行失败: {e}")
        return jsonify({
            "success": False,
            "message": f"执行失败: {str(e)}"
        })


@ai_assistant_bp.route('/task', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        data = request.json if request.is_json else {}
        task_type = data.get('type', 'custom')
        content = data.get('content', '')
        source = data.get('source', 'manual')
        priority = data.get('priority', 5)

        from .core import Task, TaskType

        try:
            task_enum = TaskType(task_type)
        except ValueError:
            task_enum = TaskType.CUSTOM

        task = Task(
            task_id=f"task_{int(time.time())}_{hash(content) % 10000}",
            task_type=task_enum,
            content=content,
            source=source,
            priority=priority
        )

        task_id = controller.task_manager.add_task(task)

        return jsonify({
            "success": True,
            "message": "任务已创建",
            "data": {
                "task_id": task_id
            }
        })

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return jsonify({
            "success": False,
            "message": f"创建任务失败: {str(e)}"
        })


@ai_assistant_bp.route('/tasks', methods=['GET'])
@cached_endpoint(ttl=5, key_prefix="tasks")
def get_tasks():
    """获取任务列表"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        status = controller.task_manager.get_status()

        return jsonify({
            "success": True,
            "data": status
        })

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取任务列表失败: {str(e)}"
        })


@ai_assistant_bp.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """开始监控"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        interval = request.json.get('interval', 2.0) if request.is_json else 2.0
        controller.start_monitoring(interval)

        return jsonify({
            "success": True,
            "message": f"监控已开始，间隔: {interval}秒"
        })

    except Exception as e:
        logger.error(f"开始监控失败: {e}")
        return jsonify({
            "success": False,
            "message": f"开始监控失败: {str(e)}"
        })


@ai_assistant_bp.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """停止监控"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        controller.stop_monitoring()

        return jsonify({
            "success": True,
            "message": "监控已停止"
        })

    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        return jsonify({
            "success": False,
            "message": f"停止监控失败: {str(e)}"
        })


@ai_assistant_bp.route('/wechat/reply', methods=['POST'])
def wechat_auto_reply():
    """微信自动回复 - 集成AI对话引擎"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        data = request.json if request.is_json else {}
        message = data.get('message', '')
        user_id = data.get('user_id', 'wechat_user')

        if not message:
            # 捕获屏幕获取最新消息
            screenshot = controller.screen_captor.capture()
            if screenshot is not None:
                message = controller.ocr_processor.recognize(screenshot)

        if not message:
            return jsonify({
                "success": False,
                "message": "没有获取到消息内容"
            })

        # 使用AI对话引擎处理消息
        try:
            from ai_conversation_engine import ConversationEngine
            conversation_engine = ConversationEngine()
            
            # 获取对话响应
            ai_response = conversation_engine.get_response(
                user_id=user_id,
                message=message,
                context={'source': 'wechat'}
            )
            
            response_text = ai_response.get('text', '抱歉，我暂时无法处理您的请求。')
            action = ai_response.get('action')
            intent = ai_response.get('intent')
            
        except ImportError:
            # 如果AI对话引擎不可用，使用原有的分析器
            analysis = controller.ai_analyzer.analyze(message, "wechat")
            response_text = controller.ai_analyzer.generate_response(analysis)
            action = 'analyze'
            intent = 'general'
            analysis = {}

        return jsonify({
            "success": True,
            "message": "AI回复生成成功",
            "data": {
                "received": message,
                "response": response_text,
                "intent": intent,
                "action": action,
                "ai_powered": True
            }
        })

    except Exception as e:
        logger.error(f"微信自动回复失败: {e}")
        return jsonify({
            "success": False,
            "message": f"处理失败: {str(e)}"
        })


@ai_assistant_bp.route('/order/process', methods=['POST'])
def process_order():
    """处理订单"""
    try:
        controller = get_controller()
        if controller is None:
            return jsonify({
                "success": False,
                "message": "AI控制器不可用"
            }), 500

        data = request.json if request.is_json else {}
        order_content = data.get('order_content', '')

        if not order_content:
            # 捕获屏幕获取订单信息
            screenshot = controller.screen_captor.capture()
            if screenshot is not None:
                order_content = controller.ocr_processor.recognize(screenshot)

        if not order_content:
            return jsonify({
                "success": False,
                "message": "没有获取到订单内容"
            })

        # 提取订单信息
        order_info = controller.ai_analyzer.extract_order_info(order_content)

        if not order_info.get("is_order"):
            return jsonify({
                "success": False,
                "message": "未检测到订单信息"
            })

        # AI分析
        analysis = controller.ai_analyzer.analyze(order_content, "order")

        # 如果需要创建发货单
        if analysis.get("action_required"):
            for action in analysis.get("actions", []):
                if action.get("action_type") == "create_shipment":
                    controller.automation_executor.execute([action])

        return jsonify({
            "success": True,
            "message": "订单处理完成",
            "data": {
                "order_info": order_info,
                "analysis": analysis
            }
        })

    except Exception as e:
        logger.error(f"订单处理失败: {e}")
        return jsonify({
            "success": False,
            "message": f"处理失败: {str(e)}"
        })


@ai_assistant_bp.route('/config', methods=['GET'])
def get_config():
    """获取AI配置"""
    try:
        controller = get_controller()
        if controller is None or controller.ai_analyzer is None:
            return jsonify({
                "success": False,
                "message": "AI分析模块不可用"
            }), 500

        model_info = controller.ai_analyzer.get_model_info()

        return jsonify({
            "success": True,
            "data": model_info
        })

    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取配置失败: {str(e)}"
        })


@ai_assistant_bp.route('/shutdown', methods=['POST'])
def shutdown():
    """关闭AI助手"""
    try:
        controller = get_controller()
        if controller is not None:
            controller.shutdown()

        global _ai_controller
        _ai_controller = None

        return jsonify({
            "success": True,
            "message": "AI助手已关闭"
        })

    except Exception as e:
        logger.error(f"关闭失败: {e}")
        return jsonify({
            "success": False,
            "message": f"关闭失败: {str(e)}"
        })
