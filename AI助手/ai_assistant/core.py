# AI会计助手 - 核心自动化模块
import os
import time
import threading
import logging
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型"""
    WECHAT_MESSAGE = "wechat_message"  # 微信消息
    EXCEL_DATA = "excel_data"  # Excel数据
    DOCUMENT = "document"  # 文档处理
    ORDER_PROCESS = "order_process"  # 订单处理
    CUSTOM = "custom"  # 自定义任务


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"  # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: TaskType
    content: str
    source: str  # 来源：screen, wechat, excel, manual
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 优先级 1-10
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class TaskManager:
    """任务管理器"""

    def __init__(self, max_workers: int = 3):
        self.pending_tasks: List[Task] = []
        self.processing_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def add_task(self, task: Task) -> str:
        """添加任务"""
        with self._lock:
            # 根据优先级插入到合适位置
            inserted = False
            for i, existing_task in enumerate(self.pending_tasks):
                if task.priority > existing_task.priority:
                    self.pending_tasks.insert(i, task)
                    inserted = True
                    break

            if not inserted:
                self.pending_tasks.append(task)

            logger.info(f"任务已添加: {task.task_id}, 类型: {task.task_type.value}")
            return task.task_id

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理任务"""
        with self._lock:
            if self.pending_tasks:
                task = self.pending_tasks.pop(0)
                task.status = TaskStatus.PROCESSING
                task.started_at = time.time()
                self.processing_tasks[task.task_id] = task
                return task
            return None

    def complete_task(self, task_id: str, result: Dict):
        """完成任务"""
        with self._lock:
            if task_id in self.processing_tasks:
                task = self.processing_tasks.pop(task_id)
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
                self.completed_tasks.append(task)

                # 触发回调
                if task.task_id in self.task_callbacks:
                    self.task_callbacks[task.task_id](task)
                    del self.task_callbacks[task.task_id]

                logger.info(f"任务完成: {task_id}")

    def fail_task(self, task_id: str, error: str):
        """任务失败"""
        with self._lock:
            if task_id in self.processing_tasks:
                task = self.processing_tasks.pop(task_id)
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error = error
                self.completed_tasks.append(task)
                logger.error(f"任务失败: {task_id}, 错误: {error}")

    def register_callback(self, task_id: str, callback: Callable):
        """注册任务完成回调"""
        self.task_callbacks[task_id] = callback

    def get_status(self) -> Dict:
        """获取管理器状态"""
        with self._lock:
            return {
                "pending_count": len(self.pending_tasks),
                "processing_count": len(self.processing_tasks),
                "completed_count": len(self.completed_tasks),
                "total_tasks": len(self.completed_tasks) + len(self.processing_tasks) + len(self.pending_tasks)
            }

    def shutdown(self):
        """关闭任务管理器"""
        self.executor.shutdown(wait=False)
        logger.info("任务管理器已关闭")


class AIController:
    """AI控制器 - 主控制器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.task_manager = TaskManager(max_workers=2)
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.screen_captor = None
        self.ocr_processor = None
        self.ai_analyzer = None
        self.automation_executor = None

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置"""
        try:
            from config import AI_CONFIG, OMNIPARSER_CONFIG
            self.ai_config = AI_CONFIG
            self.screen_config = OMNIPARSER_CONFIG
            logger.info("配置加载成功")
        except ImportError as e:
            logger.warning(f"无法加载配置，使用默认配置: {e}")
            self.ai_config = {
                "model_name": "deepseek",
                "api_key": "",
                "base_url": "https://api.deepseek.com/v1",
                "temperature": 0.7,
                "max_tokens": 1000
            }
            self.screen_config = {
                "screen_capture_area": (0, 0, 1920, 1080),
                "confidence_threshold": 0.8
            }

    def initialize(self):
        """初始化所有模块"""
        logger.info("正在初始化AI助手模块...")

        try:
            from .screen_capture import ScreenCaptor
            self.screen_captor = ScreenCaptor(self.screen_config)
            logger.info("✓ 屏幕捕获模块初始化成功")
        except Exception as e:
            logger.error(f"✗ 屏幕捕获模块初始化失败: {e}")

        try:
            from .ocr_processor import OCRProcessor
            self.ocr_processor = OCRProcessor()
            logger.info("✓ OCR识别模块初始化成功")
        except Exception as e:
            logger.error(f"✗ OCR识别模块初始化失败: {e}")

        try:
            from .ai_analyzer import AIAnalyzer
            self.ai_analyzer = AIAnalyzer(self.ai_config)
            logger.info("✓ AI分析模块初始化成功")
        except Exception as e:
            logger.error(f"✗ AI分析模块初始化失败: {e}")

        try:
            from .automation_executor import AutomationExecutor
            self.automation_executor = AutomationExecutor()
            logger.info("✓ 自动化执行模块初始化成功")
        except Exception as e:
            logger.error(f"✗ 自动化执行模块初始化失败: {e}")

        logger.info("AI助手模块初始化完成")

    def start_monitoring(self, interval: float = 2.0):
        """开始监控"""
        if self.is_running:
            logger.warning("监控已在运行中")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"开始监控，间隔: {interval}秒")

    def _monitor_loop(self, interval: float):
        """监控主循环 - 专门监控微信聊天，对所有用户消息自动回复"""
        while self.is_running:
            try:
                # 1. 检测微信窗口
                try:
                    from wechat_window import WeChatWindowDetector
                    from wechat_automator import WeChatAutomator
                    from ai_assistant.screen_capture import ScreenCaptor
                    
                    detector = WeChatWindowDetector()
                    window_info = detector.find_wechat_window()
                    
                    if not window_info:
                        time.sleep(interval)
                        continue
                    
                    # 2. 截取微信聊天区域（输入框上方部分）
                    input_area = detector.get_input_area(window_info)
                    chat_area_top = window_info.top + 100  # 标题栏下方
                    chat_area_height = input_area[1] - chat_area_top - 10
                    
                    if chat_area_height <= 0:
                        time.sleep(interval)
                        continue
                    
                    captor = ScreenCaptor()
                    screenshot = captor.capture_region(
                        window_info.left + 200,  # 聊天内容区域左侧
                        chat_area_top,
                        window_info.width - 400,
                        chat_area_height
                    )
                    
                    if screenshot is None:
                        time.sleep(interval)
                        continue
                        
                except ImportError as e:
                    logger.error(f"导入模块失败: {e}")
                    time.sleep(interval)
                    continue
                
                # 3. OCR识别聊天内容
                text_content = self.ocr_processor.recognize(screenshot)
                if not text_content or len(text_content.strip()) < 2:
                    time.sleep(interval)
                    continue
                
                # 4. 检测是否有新消息（避免重复处理）
                # 只要检测到新的文本内容，就认为是新消息，需要AI回复
                current_hash = hash(text_content.strip())
                
                if hasattr(self, '_last_message_hash') and current_hash == self._last_message_hash:
                    # 消息没有变化，不重复处理
                    time.sleep(interval)
                    continue
                
                # 保存当前消息哈希
                self._last_message_hash = current_hash
                logger.info(f"检测到新消息: {text_content[:50]}...")
                
                # 5. 调用AI生成回复
                try:
                    from ai_conversation_engine import ConversationEngine
                    engine = ConversationEngine()
                    
                    response = engine.get_response(
                        user_id='wechat_user',
                        message=text_content.strip(),
                        context={'source': 'wechat_auto_reply'}
                    )
                    
                    if response.get('success'):
                        reply_text = response.get('text', '')
                        
                        if reply_text and self.auto_reply:
                            # 6. 自动发送回复
                            automator = WeChatAutomator()
                            result = automator.send_message(window_info, reply_text)
                            
                            if result.success:
                                logger.info(f"✅ AI自动回复成功: {reply_text[:50]}...")
                            else:
                                logger.warning(f"发送回复失败: {result.message}")
                        else:
                            logger.warning("AI回复为空或自动回复已关闭")
                    else:
                        logger.warning(f"AI生成回复失败: {response.get('error')}")
                        
                except Exception as e:
                    logger.error(f"AI处理出错: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(interval)

    def _should_process(self, text_content: str) -> bool:
        """判断是否需要处理该内容"""
        # 关键词检测
        keywords = ["订单", "发货", "客户", "产品", "价格", "数量", "金额", "微信", "消息"]
        return any(keyword in text_content for keyword in keywords)

    def process_task(self, task: Task) -> Dict:
        """处理单个任务"""
        logger.info(f"开始处理任务: {task.task_id}")

        try:
            # AI分析
            analysis_result = self.ai_analyzer.analyze(task.content, task.task_type.value)

            # 自动化执行
            if analysis_result.get("action_required"):
                execution_result = self.automation_executor.execute(
                    analysis_result["actions"]
                )
                analysis_result["execution_result"] = execution_result

            return analysis_result

        except Exception as e:
            logger.error(f"任务处理失败: {e}")
            raise

    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("监控已停止")

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "task_manager": self.task_manager.get_status(),
            "modules": {
                "screen_captor": self.screen_captor is not None,
                "ocr_processor": self.ocr_processor is not None,
                "ai_analyzer": self.ai_analyzer is not None,
                "automation_executor": self.automation_executor is not None
            }
        }

    def shutdown(self):
        """关闭系统"""
        self.stop_monitoring()
        self.task_manager.shutdown()
        logger.info("AI助手系统已关闭")


# 单例实例
_ai_controller: Optional[AIController] = None


def get_ai_controller() -> AIController:
    """获取AI控制器单例"""
    global _ai_controller
    if _ai_controller is None:
        _ai_controller = AIController()
    return _ai_controller


def init_ai_assistant() -> AIController:
    """初始化AI助手"""
    controller = get_ai_controller()
    controller.initialize()
    return controller
