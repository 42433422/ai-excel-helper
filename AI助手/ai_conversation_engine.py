#!/usr/bin/env python3
"""
AI对话引擎 - 智能发货单助手 (优化版)
支持自然语言对话、意图识别、上下文管理
集成DeepSeek AI实现智能对话和函数调用
优化了订单信息缺失的智能询问机制
"""

import json
import logging
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# 导入错误收集模块
try:
    from error_collection import collect_error
    ERROR_COLLECTION_AVAILABLE = True
except ImportError:
    ERROR_COLLECTION_AVAILABLE = False
    logger.debug("错误收集模块未安装")


class DeepSeekAI:
    """DeepSeek AI 集成 - 支持函数调用"""
    
    def __init__(self, api_key: str = None, model: str = "deepseek-chat"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.api_base = "https://api.deepseek.com/v1"
        
        # 加载AI工具
        self._load_tools()
        
    def _load_api_key(self) -> str:
        """从配置文件加载API密钥"""
        # 尝试多个可能的位置
        possible_paths = [
            Path(__file__).parent / "config" / "deepseek_config.py",
            Path("config/deepseek_config.py"),
            Path("../config/deepseek_config.py"),
            Path(__file__).parent.parent / "config" / "deepseek_config.py",
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("config", config_path)
                    config = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config)
                    api_key = getattr(config, 'DEEPSEEK_API_KEY', '')
                    if api_key:
                        return api_key
                except Exception as e:
                    logger.debug(f"加载配置文件失败 {config_path}: {e}")
        
        return ""
    
    def _load_tools(self):
        """加载AI工具列表"""
        self.tools = []
        
        # 订单查询工具
        self.tools.append({
            "type": "function",
            "function": {
                "name": "query_orders",
                "description": "查询订单信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "查询关键词"
                        }
                    }
                }
            }
        })
        
        # 产品查询工具
        self.tools.append({
            "type": "function",
            "function": {
                "name": "query_products",
                "description": "查询产品信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "产品关键词"
                        }
                    }
                }
            }
        })
        
        # 创建发货单工具
        self.tools.append({
            "type": "function",
            "function": {
                "name": "create_shipment",
                "description": "创建发货单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company": {
                            "type": "string",
                            "description": "公司名称"
                        },
                        "products": {
                            "type": "array",
                            "description": "产品列表"
                        }
                    }
                }
            }
        })
    
    def generate_response(self, user_message: str, context: str = "") -> Optional[str]:
        """生成AI响应"""
        if not self.api_key:
            return None
        
        try:
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": self._build_system_prompt()
                },
                {
                    "role": "user", 
                    "content": f"{user_message}\n\n上下文: {context}"
                }
            ]
            
            # 准备请求数据
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # 发送请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"API请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"生成AI响应失败: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """你是一个专业、智能的发货单助手，服务于成都国圣工业有限公司（五星花品牌）。

你的核心能力：
1. **智能订单处理** - 能理解自然语言订单，如"给我发5桶PE白底漆"，自动提取产品和数量
2. **自定义产品支持** - 当用户说"自定义产品"时，引导用户按格式输入产品信息
3. **表格智能编辑** - 能精准修改表格中的数据：
   - "把单价改成45元" - 修改单价字段
   - "修改第3行的数量为5桶" - 修改指定行的数量
   - "把所有PE白底漆的单价改为50元" - 批量修改特定产品
   - "把公司名称改成成都国圣" - 修改公司信息
4. **上下文理解** - 能记住对话历史，理解用户意图的变化
5. **智能回复生成** - 根据对话情境生成自然、友好的回复
6. **数据查询** - 能回答用户关于产品、订单、价格等问题
7. **日常交流** - 友好地与客户对话，解答疑问

对话规则：
- 使用简洁、专业、友好的中文回复
- 保持对话流畅，避免生硬的指令
- 当不确定用户意图时，礼貌询问
- 引导用户提供必要信息，如公司名称、产品详情等
- 确认订单前，清晰列出所有产品和数量
- 支持多种输入格式，灵活处理用户的不同表达方式
- **表格编辑时**，使用精准的语言确认修改内容

请根据用户的具体需求，提供精准、智能的服务。"""


class ConversationContext:
    """对话上下文管理"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages = []
        self.current_task = None
        
    def add_message(self, role: str, content: str):
        """添加消息到上下文"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # 保持最近20条消息
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]
    
    def set_task(self, task_type: str, data: Dict, description: str):
        """设置当前任务"""
        self.current_task = {
            'type': task_type,
            'data': data,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
    
    def clear_task(self):
        """清除当前任务"""
        self.current_task = None
    
    def get_summary(self) -> str:
        """获取对话摘要"""
        if not self.messages:
            return "无对话历史"
        
        recent_messages = self.messages[-5:]  # 最近5条消息
        summary_parts = []
        
        for msg in recent_messages:
            role = "用户" if msg['role'] == 'user' else "助手"
            content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            summary_parts.append(f"{role}: {content}")
        
        return " | ".join(summary_parts)


class ConversationEngine:
    """AI对话引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key', '')
        self.api_base = self.config.get('api_base', 'https://api.deepseek.com/v1')
        self.model = self.config.get('model', 'deepseek-chat')
        
        # 初始化DeepSeek AI
        self.deepseek = DeepSeekAI(api_key=self.api_key, model=self.model)
        
        # 初始化AI表格编辑器
        self.table_editor = None
        self._init_table_editor()
        
        # 对话上下文
        self.contexts = {}  # user_id -> ConversationContext
        
        # 意图模式
        self.intent_patterns = self._init_intent_patterns()
        
        # 知识库
        self.knowledge_base = self._init_knowledge_base()
    
    def _init_intent_patterns(self) -> Dict[str, List[str]]:
        """初始化意图模式"""
        return {
            # 顺序很重要：先检查否定/取消意图，再检查确认意图
            "cancel": [
                "取消", "算了", "不要了", "不用了",
                "撤销", "删除", "退掉", "不", "不是",
                "否", "不行", "不创建", "不生成", "不确认"
            ],
            # 表格编辑意图 - 优先级很高，放在确认意图之前
            "edit_table": [
                "把单价改成", "修改单价", "价格改为", "单价改成", "单价改为",
                "把数量改成", "修改数量", "数量改成", "数量改为",
                "把编号改成", "修改编号", "编号改成", "编号改为",
                "把公司改成", "修改公司", "公司改成", "公司改为",
                "把联系人改成", "修改联系人", "联系人改成", "联系人改为",
                "把备注改成", "修改备注", "备注改成", "备注改为",
                "把第", "修改第", "调整第", "更新第", "更正第",
                "改一下", "修改", "更新", "调整", "更正",
                "修改表格", "编辑表格", "表格编辑"
            ],
            "confirm": [
                "好的", "确认", "行", "可以", "是的", "是",
                "对的", "同意", "就这么办", "没问题"
            ],
            # 添加产品和查询产品意图，优先级高于订单意图
            "add_product": [
                "添加产品", "新增产品", "录入产品", "产品入库",
                "添加新产品", "新增一个产品", "录入新产品"
            ],
            "query_company_products": [
                "有哪些产品", "公司产品", "产品列表", "产品清单",
                "查询产品", "查看产品", "产品信息", "什么产品"
            ],
            # 自定义产品意图
            "custom_product": [
                "自定义产品", "自定义", "自定义产品", "使用自定义产品"
            ],
            # 订单相关意图
            "order": [
                "下单", "订购", "买", "要", "订单", "发货",
                "发货单", "送货单", "快递单", "出库单", "出货单",
                "给我发", "发我", "送过来", "送些", "要桶", "要公斤",
                "白底", "面漆", "稀释剂", "固化剂", "哑光", "亮光",
                "PE", "PU", "NC", "桶", "kg"
            ],
            # 查询意图
            "query": [
                "查询", "统计", "报表", "数据", "价格", "多少钱",
                "有多少", "多少", "费用", "金额"
            ],
            # 发送意图
            "shipment": [
                "发货", "送货", "寄送", "发送", "发快递", "送",
                "寄", "装运", "运输"
            ],
            # 帮助意图
            "help": [
                "帮帮我", "怎么用", "说明", "帮助",
                "教我", "使用", "功能", "介绍"
            ],
            # 错误收集意图
            "collect_error": [
                "加入错误数据库", "记录错误", "保存错误", "无法解决",
                "无法处理", "没有这个功能", "处理不了", "解决不了",
                "找不到", "没找到", "无法识别", "识别不了",
                "处理不了这个请求", "找不到这个功能", "无法完成",
                "不知道", "无法理解", "处理失败", "操作失败",
                "报错", "异常", "错误", "无法执行"
            ]
        }
    
    def _init_knowledge_base(self) -> Dict:
        """初始化知识库"""
        return {
            "greetings": [
                "你好！我是成都国圣工业有限公司（五星花品牌）的发货单助手。很高兴为您服务！",
                "您好！欢迎来到成都国圣工业有限公司（五星花品牌）！我是您的发货单助手，很高兴为您服务！",
                "嗨！您好！我是成都国圣工业有限公司（五星花品牌）的发货单助手。很高兴为您服务！"
            ],
            "product_categories": {
                "底漆": ["PE白底漆", "底漆", "底层漆"],
                "面漆": ["面漆", "表层漆", "表面漆"],
                "稀释剂": ["稀释剂", "溶剂", "稀释液"]
            },
            "order_patterns": {
                "quantity_pattern": r"(\d+)(?:个|只|桶|罐|箱|袋|kg|公斤|克)",
                "price_pattern": r"(\d+(?:\.\d+)?)(?:元|块|钱)"
            }
        }
    
    def _init_table_editor(self):
        """初始化AI表格编辑器"""
        try:
            from table_editor import AITableEditor
            self.table_editor = AITableEditor()
        except ImportError as e:
            logger.warning(f"无法导入表格编辑器: {e}")
            self.table_editor = None
    
    def _recognize_intent(self, message: str) -> str:
        """识别用户意图"""
        message_lower = message.lower()
        
        # 按优先级检查意图
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern.lower() in message_lower:
                    return intent
        
        return "chat"  # 默认意图
    
    def _get_context(self, user_id: str) -> ConversationContext:
        """获取对话上下文"""
        if user_id not in self.contexts:
            self.contexts[user_id] = ConversationContext(user_id)
        return self.contexts[user_id]
    
    def _analyze_missing_info(self, task_data: Dict) -> str:
        """分析缺失信息并生成询问文本"""
        try:
            missing_items = []
            
            # 检查订单数据
            order_data = task_data.get('order', {})
            if not isinstance(order_data, dict):
                return "订单信息解析异常，请重新发送订单消息。"
            
            # 检查公司信息
            company_name = order_data.get('company_name')
            if not company_name:
                missing_items.append("公司名称")
            
            # 检查产品信息
            products = order_data.get('products', [])
            if not products:
                missing_items.append("产品信息")
            else:
                # 检查每个产品是否完整
                incomplete_products = []
                for i, product in enumerate(products, 1):
                    product_name = product.get('name', '')
                    quantity = product.get('quantity')
                    unit_price = product.get('unit_price')
                    
                    # 如果产品名不完整或缺少关键信息
                    if not product_name or not quantity:
                        incomplete_products.append(f"第{i}个产品")
                    elif not unit_price:
                        incomplete_products.append(f"第{i}个产品的单价")
                
                if incomplete_products:
                    missing_items.extend(incomplete_products)
            
            # 检查联系人信息
            contact_person = order_data.get('contact_person')
            if not contact_person:
                missing_items.append("联系人信息")
            
            # 生成询问文本
            if missing_items:
                response = "📋 检测到以下信息需要补充：\n\n"
                
                for item in missing_items:
                    response += f"• {item}\n"
                
                response += "\n💡 请补充这些信息，或者告诉我：\n"
                response += "• 【跳过】- 使用默认信息创建发货单\n"
                response += "• 【取消】- 取消此订单\n\n"
                response += "或者您可以直接回答缺失的信息。"
                
                return response
            else:
                return ""
                
        except Exception as e:
            logger.error(f"分析缺失信息失败: {e}")
            return "订单信息解析出现异常，请重新发送订单消息。"
    
    def get_response(self, user_id: str, message: str, context: Dict = None) -> Dict:
        """
        获取对话响应
        
        Args:
            user_id: 用户ID
            message: 用户消息
            context: 额外上下文（当前聊天记录等）
            
        Returns:
            响应字典
        """
        try:
            # 1. 意图识别
            intent = self._recognize_intent(message)
            
            # 2. 获取/创建对话上下文
            ctx = self._get_context(user_id)
            
            # 3. 记录用户消息
            ctx.add_message('user', message)
            
            # 4. 处理当前任务（如果有）
            if ctx.current_task:
                response = self._handle_current_task(message, intent, ctx)
            else:
                # 5. 问候语检查（最高优先级）
                if any(word in message.lower() for word in ['你好', '嗨', '您好', '早上好', '下午好', '晚上好']):
                    response = {
                        'text': "老板你好，我是你的助理小张，目前的版本号是1.2.1。有什么可以为您效劳的吗？",
                        'action': 'greeting'
                    }
                
                # 6. 版本信息检查
                elif any(word in message.lower() for word in ['版本', 'version', '版本号', '当前版本']):
                    response = {
                        'text': "老板你好，我是你的助理小张，目前的版本号是1.2.1。",
                        'action': 'version_info'
                    }
                
                # 7. 开发者信息检查
                elif any(word in message.lower() for word in ['谁开发的', '开发者', '开发人员', '作者', '谁做的', '开发团队', '开发方']):
                    response = {
                        'text': "这个AI助手是由佳诺开发的。",
                        'action': 'developer_info'
                    }
                
                # 8. 发货单修改相关检查
                elif any(word in message.lower() for word in ['修改发货单', '调整发货单', '编辑发货单', '修改已生成', '调整已生成']):
                    response = {
                        'text': "当然可以！我可以帮您修改已生成的发货单。\n\n请告诉我：\n1. **具体要修改什么？**\n   - \"把单价改成45元\"\n   - \"修改第3行的数量为5桶\" \n   - \"把所有PE白底漆的单价改为50元\"\n\n2. **或者直接告诉我修改内容**\n   - \"把PE白底漆的单价从10元改成45元\"\n   - \"第2行的数量改成8桶\"\n\n我会精准定位并修改相应的数据！",
                        'action': 'shipment_edit_help'
                    }
                
                # 9. 错误收集请求
                elif any(word in message.lower() for word in ['收集错误', '加入错误', '保存错误', '记录错误']):
                    response = self._handle_error_collection(message, ctx)
                
                # 10. 订单意图直接使用本地处理（跳过AI）
                elif intent == "order":
                    response = self._handle_order(message, ctx)
                
                # 11. 其他意图尝试使用DeepSeek AI生成响应
                else:
                    use_ai = True
                    ai_response = None
                    
                    # 构建上下文信息
                    context_info = f"当前任务: {ctx.current_task.get('description', '无')}" if ctx.current_task else ""
                    
                    if use_ai and self.deepseek.api_key:
                        # 调用DeepSeek AI
                        ai_response = self.deepseek.generate_response(
                            user_message=message,
                            context=context_info
                        )
                    
                    # 12. 根据意图生成响应
                    if ai_response:
                        # 使用AI响应
                        response_text = ai_response
                        action = None
                        
                        # 检查是否需要触发特定操作
                        if intent == "query":
                            action = 'query_data'
                        elif intent == "help":
                            action = 'show_help'
                        
                        response = {
                            'text': response_text,
                            'action': action,
                            'data': {
                                'raw_message': message,
                                'needs_processing': intent in ['query', 'shipment']
                            }
                        }
                    else:
                        # 使用本地规则响应（备用）
                        if intent == "order":
                            response = self._handle_order(message, ctx)
                        elif intent == "edit_table":
                            response = self._handle_table_edit(message, ctx)
                        elif intent == "chat":
                            response = self._handle_chat(message, ctx)
                        elif intent == "query":
                            response = self._handle_query(message, ctx)
                        elif intent == "shipment":
                            response = self._handle_shipment(message, ctx)
                        elif intent == "help":
                            response = self._handle_help(message)
                        elif intent == "cancel":
                            response = self._handle_cancel(ctx)
                        elif intent == "confirm":
                            response = self._handle_confirm(ctx)
                        else:
                            response = self._handle_general(message, ctx)
            
            # 6. 记录助手响应
            if response and response.get('text'):
                ctx.add_message('assistant', response['text'])
            
            # 7. 添加响应标记
            response['intent'] = intent
            response['success'] = True
            response['timestamp'] = datetime.now().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"生成响应失败: {e}")
            return {
                'text': f"抱歉，处理您的消息时出现了问题：{str(e)}",
                'action': 'error',
                'data': {},
                'intent': 'error',
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def _handle_current_task(self, message: str, intent: str, ctx: ConversationContext) -> Dict:
        """处理当前任务"""
        task_type = ctx.current_task['type']
        task_data = ctx.current_task['data']
        
        # 如果有待确认的订单
        if task_type == 'create_shipment':
            if intent == "confirm":
                # 确认创建发货单
                response = self._handle_confirm(ctx)
            elif intent == "cancel":
                # 取消订单
                response = self._handle_cancel(ctx)
            else:
                # 其他消息也尝试处理任务
                if intent == "confirm":
                    response = self._handle_confirm(ctx)
                else:
                    # 检查订单信息是否完整
                    missing_info = self._analyze_missing_info(task_data)
                    
                    if missing_info:
                        # 有缺失信息，详细询问
                        response = {
                            'text': missing_info,
                            'action': 'collect_missing_info',
                            'data': task_data
                        }
                    else:
                        # 没有缺失信息，要求确认
                        response = {
                            'text': '请确认是否创建发货单，回复【是】或【否】',
                            'action': 'wait_confirmation',
                            'data': task_data
                        }
        else:
            # 其他任务类型
            if intent == "confirm":
                response = self._handle_confirm(ctx)
            elif intent == "cancel":
                response = self._handle_cancel(ctx)
            else:
                response = self._handle_general(message, ctx)
        
        return response
    
    def _handle_error_collection(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理错误收集请求"""
        if not ERROR_COLLECTION_AVAILABLE:
            return {
                'text': "抱歉，错误收集功能暂不可用。",
                'action': 'error_collection_unavailable',
                'data': {}
            }
        
        try:
            # 收集错误信息
            user_id = ctx.user_id if hasattr(ctx, 'user_id') else 'unknown'
            
            # 分析错误类型
            error_type = self._analyze_error_type(message)
            
            # 收集错误
            success = collect_error(
                user_message=message,
                ai_response="AI无法处理该请求，已收集到错误数据库",
                intent_detected="collect_error",
                confidence_score=0.0,
                error_type=error_type,
                error_details=f"用户请求无法处理: {message}",
                user_id=user_id,
                priority='medium',
                tags=[error_type, 'manual_collection']
            )
            
            if success:
                return {
                    'text': "✅ 已将您的请求加入错误数据库。\n\n我们会尽快分析并完善相关功能，谢谢您的反馈！",
                    'action': 'error_collected',
                    'data': {
                        'success': True,
                        'error_type': error_type
                    }
                }
            else:
                return {
                    'text': "❌ 收集错误信息时出现异常。",
                    'action': 'error_collection_failed',
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"错误收集失败: {e}")
            return {
                'text': f"❌ 错误收集功能异常: {str(e)}",
                'action': 'error_collection_error',
                'data': {'error': str(e)}
            }
    
    def _analyze_error_type(self, message: str) -> str:
        """分析错误类型"""
        message_lower = message.lower()
        
        # 意图分析
        if any(word in message_lower for word in ['下单', '订单', '订购', '买']):
            return 'order_processing'
        elif any(word in message_lower for word in ['查询', '统计', '报表']):
            return 'data_query'
        elif any(word in message_lower for word in ['表格', '编辑', '修改']):
            return 'table_edit'
        elif any(word in message_lower for word in ['产品', '单价', '价格']):
            return 'product_management'
        elif any(word in message_lower for word in ['发货', '物流', '运输']):
            return 'shipment_tracking'
        else:
            return 'general_unhandled'
    
    def _handle_chat(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理日常对话"""
        import random
        
        message_lower = message.lower()
        
        # 检查是否是询问版本信息
        if any(word in message_lower for word in ['版本', 'version', '版本号', '当前版本']):
            return {
                'text': "老板你好，我是你的助理小张，目前的版本号是1.2.1。",
                'action': None
            }
        
        # 检查是否是询问开发者信息
        if any(word in message_lower for word in ['谁开发的', '开发者', '开发人员', '作者', '谁做的', '开发团队', '开发方']):
            return {
                'text': "这个AI助手是由佳诺开发的。",
                'action': None
            }
        
        # 检查是否请求手动收集错误
        if any(word in message_lower for word in ['收集错误', '加入错误', '保存错误', '记录错误']):
            # 触发错误收集
            response = self._handle_error_collection(message, ctx)
            return response
        
        # 问候（首次交互）
        if any(word in message_lower for word in ['你好', '在吗', '嗨', '您好', '早上好', '下午好', '晚上好']):
            return {
                'text': "老板你好，我是你的助理小张，目前的版本号是1.2.1。有什么可以为您效劳的吗？",
                'action': None
            }
        
        # 询问近况
        if any(word in message_lower for word in ['怎么样', '忙不忙', '最近', '还好', '情况如何', '如何']):
            return {
                'text': "我这边一切都好，随时待命！\n\n目前系统运行正常，已处理多个发货单。\n需要我帮您查询什么数据吗？",
                'action': None
            }
        
        # 闲聊
        return {
            'text': "我在这里！有什么可以帮您的？",
            'action': None
        }
    
    def _handle_general(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理一般消息"""
        # 获取对话摘要
        summary = ctx.get_summary()
        
        return {
            'text': f"我理解您想表达的意思。\n\n目前我主要帮助您处理发货单、查询产品信息、修改表格等。\n\n如果需要帮助，请告诉我具体需求，比如：\n• \"瑞星家私P1白底10桶\"\n• \"查询PE白底漆的价格\"\n• \"把表格的单价改成45元\"",
            'action': 'general_help',
            'data': {
                'conversation_summary': summary
            }
        }
    
    def _handle_query(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理查询请求"""
        return {
            'text': "好的，我来帮您查询相关信息。\n\n请告诉我您想查询什么？比如：\n• 产品价格\n• 客户信息\n• 订单历史\n• 库存情况",
            'action': 'query_data',
            'data': {'message': message}
        }
    
    def _handle_shipment(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理发货相关请求"""
        return {
            'text': "我来帮您处理发货相关事务。\n\n请提供详细信息：\n• 发货地址\n• 产品清单\n• 联系电话\n• 备注要求",
            'action': 'shipment_processing',
            'data': {'message': message}
        }
    
    def _handle_help(self, message: str) -> Dict:
        """处理帮助请求"""
        help_text = """📚 **AI发货单助手使用指南**

**1. 订单处理**
• "瑞星家私P1白底10桶"
• "PE白底漆5桶，稀释剂2桶"

**2. 查询信息**
• "查询PE白底漆价格"
• "显示所有产品"
• "统计订单数据"

**3. 表格编辑**
• "把单价改成45元"
• "修改第3行的数量为5桶"
• "把所有PE白底漆的单价改为50元"

**4. 日常对话**
• "你好" - 获取问候
• "版本" - 查看版本信息
• "谁开发的" - 查看开发者信息

请直接输入您的需求，我会智能理解并帮助您！"""
        
        return {
            'text': help_text,
            'action': 'show_help',
            'data': {'help_category': 'general'}
        }
    
    def _handle_confirm(self, ctx: ConversationContext) -> Dict:
        """处理确认请求"""
        if not ctx.current_task:
            return {
                'text': "好的，已确认。还需要其他帮助吗？",
                'action': None
            }
        
        task_type = ctx.current_task['type']
        task_data = ctx.current_task['data']
        
        # 处理创建发货单确认
        if task_type == 'create_shipment':
            try:
                from ai_workflow_integration import AIWorkflowIntegration, ExtractedOrder
                from wechat_window import WeChatWindowDetector
                from wechat_automator import WeChatAutomator
                
                # 获取订单数据（可能是ExtractedOrder对象或字典）
                order_raw = task_data.get('order', {})
                
                if isinstance(order_raw, ExtractedOrder):
                    order = order_raw
                else:
                    order = ExtractedOrder(
                        company_name=order_raw.get('company_name') if hasattr(order_raw, 'get') else getattr(order_raw, 'company_name', None),
                        contact_person=order_raw.get('contact_person') if hasattr(order_raw, 'get') else getattr(order_raw, 'contact_person', None),
                        contact_phone=order_raw.get('contact_phone') if hasattr(order_raw, 'get') else getattr(order_raw, 'contact_phone', None),
                        products=order_raw.get('products') if hasattr(order_raw, 'get') else getattr(order_raw, 'products', []),
                        delivery_date=order_raw.get('delivery_date') if hasattr(order_raw, 'get') else getattr(order_raw, 'delivery_date', None),
                        remarks=order_raw.get('remarks') if hasattr(order_raw, 'get') else getattr(order_raw, 'remarks', None)
                    )
                
                # 创建发货单
                integration = AIWorkflowIntegration()
                create_result = integration.create_shipment_order(order)
                
                if create_result['success']:
                    file_path = create_result['file_path']
                    
                    # 自动发送文件到微信
                    send_result = None
                    try:
                        detector = WeChatWindowDetector()
                        window = detector.find_wechat_window()
                        
                        if window:
                            automator = WeChatAutomator()
                            send_result = automator.send_file(window, file_path)
                            
                            if send_result.success:
                                send_msg = f"\n\n📤 已自动发送到微信！"
                            else:
                                send_msg = f"\n\n⚠️ 文件已创建，但发送到微信失败: {send_result.message}"
                        else:
                            send_msg = f"\n\n⚠️ 文件已创建，但未检测到微信窗口"
                    except Exception as se:
                        logger.error(f"发送文件失败: {se}")
                        send_msg = f"\n\n⚠️ 文件已创建，但发送到微信失败: {str(se)}"
                    
                    ctx.clear_task()
                    return {
                        'text': create_result['reply'] + send_msg,
                        'action': 'shipment_created',
                        'data': {
                            'file_path': file_path,
                            'sent_to_wechat': send_result.success if send_result else False
                        }
                    }
                else:
                    return {
                        'text': f"❌ 创建发货单失败：{create_result['reply']}",
                        'action': 'error',
                        'data': {}
                    }
                        
            except Exception as e:
                logger.error(f"创建发货单失败: {e}")
                return {
                    'text': f"❌ 创建发货单失败：{str(e)}",
                    'action': 'error',
                    'data': {}
                }
            
            # 其他确认任务
            return {
                'text': "好的，已确认执行！",
                'action': 'confirm_task',
                'data': ctx.current_task
            }
        
        return {
            'text': "好的，已确认。还需要其他帮助吗？",
            'action': None
        }
    
    def _handle_cancel(self, ctx: ConversationContext) -> Dict:
        """处理取消请求"""
        if ctx.current_task:
            task_type = ctx.current_task['type']
            if task_type == 'create_shipment':
                ctx.clear_task()
                return {
                    'text': "好的，已取消发货单创建。还需要其他帮助吗？",
                    'action': 'order_cancelled',
                    'data': {}
                }
            else:
                ctx.clear_task()
                return {
                    'text': "好的，已取消。还需要其他帮助吗？",
                    'action': 'task_cancelled',
                    'data': {}
                }
        
        return {
            'text': "好的，已取消。还需要其他帮助吗？",
            'action': None
        }
    
    def _handle_table_edit(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理表格编辑请求"""
        if not self.table_editor:
            return {
                'text': "抱歉，表格编辑器暂不可用。",
                'action': 'table_edit_error',
                'data': {'error': 'table_editor_not_available'}
            }
        
        try:
            # 解析编辑意图
            edit_instruction = self.table_editor.parse_edit_intent(message)
            if not edit_instruction:
                return {
                    'text': f"抱歉，我无法理解您的编辑请求：\"{message}\"\n\n请使用以下格式：\n• \"把单价改成45元\"\n• \"修改第3行的数量为5桶\"\n• \"把所有PE白底漆的单价改为50元\"",
                    'action': 'table_edit_help',
                    'data': {'original_message': message}
                }
            
            # 获取当前表格文件
            current_file = self._get_current_table_file()
            if not current_file:
                return {
                    'text': "请先打开或创建一个表格文件，然后再进行编辑。\n\n您可以：\n• 使用\"创建发货单\"功能生成表格\n• 上传现有的Excel文件进行编辑",
                    'action': 'table_edit_no_file',
                    'data': {}
                }
            
            # 执行编辑
            edit_result = self.table_editor.execute_edit(edit_instruction, current_file)
            
            if edit_result['success']:
                # 编辑成功
                changes_summary = edit_result.get('details', '表格已更新')
                
                # 获取表格摘要信息
                table_summary = self.table_editor.get_table_summary(current_file)
                
                response_text = f"✅ 表格编辑成功！\n\n{changes_summary}\n\n📄 文件：{table_summary.get('file_name', '当前表格')}"
                
                return {
                    'text': response_text,
                    'action': 'edit_table',
                    'data': {
                        'success': True,
                        'changes': edit_result.get('changes', []),
                        'table_summary': table_summary,
                        'edit_instruction': edit_instruction
                    }
                }
            else:
                # 编辑失败
                return {
                    'text': f"❌ 表格编辑失败\n\n{edit_result['message']}\n\n请检查：\n• 字段名称是否正确\n• 行号是否存在\n• 文件是否被其他程序占用",
                    'action': 'table_edit_failed',
                    'data': {
                        'success': False,
                        'error': edit_result['message'],
                        'edit_instruction': edit_instruction
                    }
                }
                
        except Exception as e:
            logger.error(f"表格编辑异常: {e}")
            return {
                'text': f"❌ 表格编辑遇到问题: {str(e)}",
                'action': 'table_edit_error',
                'data': {'error': str(e)}
            }
    
    def _get_current_table_file(self) -> Optional[str]:
        """获取当前表格文件路径"""
        # 优先级：用户当前打开的文件 > 最新创建的文件 > 默认模板
        try:
            # 1. 检查是否有当前会话中打开的文件
            workspace_path = Path.cwd()
            
            # 查找最近的Excel文件
            excel_files = list(workspace_path.glob("*.xlsx")) + list(workspace_path.glob("*.xls"))
            if excel_files:
                # 返回最新的文件
                latest_file = max(excel_files, key=lambda f: f.stat().st_mtime)
                return str(latest_file)
            
            return None
            
        except Exception as e:
            logger.error(f"获取当前表格文件失败: {e}")
            return None
    
    def _handle_order(self, message: str, ctx: 'ConversationContext', context: Dict = None) -> Dict:
        """处理订单相关消息 - 直接生成发货单"""
        try:
            from shipment_document import DocumentAPIGenerator
            
            # 使用DocumentAPIGenerator解析并生成发货单
            generator = DocumentAPIGenerator()
            result = generator.parse_and_generate(message)
            
            if result['success']:
                file_path = result.get('document', {}).get('filepath', '')
                order_data = result.get('parsed_data', {})
                
                # 构建订单摘要
                products = order_data.get('products', [order_data])
                if isinstance(products, dict):
                    products = [products]
                
                summary = []
                for i, p in enumerate(products[:3], 1):
                    name = p.get('product_name', p.get('name', '未知产品'))
                    qty = p.get('quantity_kg', p.get('quantity', 0))
                    summary.append(f"{i}. {name} {qty}kg")
                
                summary_text = '\n'.join(summary)
                total_amount = order_data.get('amount', 0)
                
                reply_text = f"✅ 发货单已生成！\n\n📄 文件路径: {file_path}\n\n📦 订单摘要：\n{summary_text}\n\n💰 总金额：¥{total_amount}"
                
                # 尝试发送到微信
                try:
                    from wechat_window import WeChatWindowDetector
                    from wechat_automator import WeChatAutomator
                    
                    detector = WeChatWindowDetector()
                    window = detector.find_wechat_window()
                    
                    if window:
                        automator = WeChatAutomator()
                        send_result = automator.send_file(window, file_path)
                        
                        if send_result.success:
                            reply_text += "\n\n📤 文件已发送到微信！"
                except Exception as send_e:
                    reply_text += f"\n\n⚠️ 发送失败: {str(send_e)}"
                
                return {
                    'text': reply_text,
                    'action': 'shipment_created',
                    'data': {
                        'file_path': file_path,
                        'order_data': order_data,
                        'raw_message': message
                    }
                }
            else:
                return {
                    'text': result.get('message', '抱歉，我无法理解这个订单信息。'),
                    'action': 'order_parse_failed',
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"处理订单失败: {e}")
            return {
                'text': f"抱歉，处理订单时出现问题：{str(e)}",
                'action': 'order_error',
                'data': {}
            }
    
    def _handle_custom_product(self, message: str, ctx: 'ConversationContext') -> Dict:
        """处理自定义产品请求"""
        return {
            'text': "✅ 已进入自定义产品模式。\n\n请输入产品名称，我会为您匹配可能的产品编号：\n\n例如：\nPE白底漆\n\n如果需要添加多个产品，请用分号分隔：\nPE白底漆;稀释剂\n\n输入完成后，我会为您显示匹配的产品编号供选择。",
            'action': 'custom_product',
            'data': {'step': 'input_product_names'}
        }
    
    def get_context(self, user_id: str) -> ConversationContext:
        """获取对话上下文"""
        return self.contexts.get(user_id)