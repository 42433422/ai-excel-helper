#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单工作流引擎 - 智能对话式发货单助手
检测关键词 → 引导用户填写信息 → 自动生成发货单
"""

import json
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os


class OrderState(Enum):
    """订单收集状态"""
    IDLE = "IDLE"                    # 空闲状态
    COLLECTING = "COLLECTING"        # 收集信息中
    COMPLETED = "COMPLETED"          # 已完成
    CANCELLED = "CANCELLED"          # 已取消


class FieldType(Enum):
    """字段类型"""
    COMPANY_NAME = "company_name"       # 公司名称
    CONTACT_PERSON = "contact_person"   # 联系人
    CONTACT_PHONE = "contact_phone"    # 联系电话
    PRODUCTS = "products"              # 产品列表
    DELIVERY_DATE = "delivery_date"    # 发货日期
    REMARKS = "remarks"                # 备注


@dataclass
class ProductInfo:
    """产品信息"""
    name: str
    quantity: float  # 数量(KG)
    model: str = ""  # 型号
    spec: str = ""   # 规格
    unit_price: float = 0.0  # 单价
    amount: float = 0.0  # 金额

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "model": self.model,
            "spec": self.spec,
            "unit_price": self.unit_price,
            "amount": self.amount
        }


@dataclass
class OrderData:
    """订单数据"""
    company_name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    products: List[ProductInfo] = field(default_factory=list)
    delivery_date: str = ""
    remarks: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "company_name": self.company_name,
            "contact_person": self.contact_person,
            "contact_phone": self.contact_phone,
            "products": [p.to_dict() if hasattr(p, 'to_dict') else p for p in self.products],
            "delivery_date": self.delivery_date,
            "remarks": self.remarks
        }
    
    def is_complete(self, required_fields: List[str]) -> bool:
        """检查必填字段是否完整"""
        for field in required_fields:
            if field == FieldType.PRODUCTS.value:
                if len(self.products) == 0:
                    return False
            else:
                if not getattr(self, field, ""):
                    return False
        return True


class OrderWorkflow:
    """订单工作流引擎"""
    
    # 触发关键词
    TRIGGER_KEYWORDS = [
        "发货单", "开发票", "订单", "发货", "寄货",
        "快递单", "送货单", "出库单", "打印发货单"
    ]
    
    # 必填字段配置
    REQUIRED_FIELDS = [
        FieldType.COMPANY_NAME.value,
        FieldType.CONTACT_PERSON.value,
        FieldType.PRODUCTS.value
    ]
    
    # 可选字段
    OPTIONAL_FIELDS = [
        FieldType.CONTACT_PHONE.value,
        FieldType.DELIVERY_DATE.value,
        FieldType.REMARKS.value
    ]
    
    # 字段对应的问题
    FIELD_QUESTIONS = {
        FieldType.COMPANY_NAME.value: "请提供购买单位名称（公司名）？",
        FieldType.CONTACT_PERSON.value: "请问联系人是谁？",
        FieldType.CONTACT_PHONE.value: "请提供联系电话？",
        FieldType.PRODUCTS.value: "请提供需要购买的产品信息（格式：产品名 数量KG）？\n例如：A型产品 500KG，B型产品 300KG",
        FieldType.DELIVERY_DATE.value: "请提供期望发货日期？\n直接回复\"今天\"自动使用今天日期\n或回复具体日期，如：2024-01-20、1月20日",
        FieldType.REMARKS.value: "有什么需要备注的吗？"
    }
    
    def __init__(self, state_file: str = "order_workflow_state.json"):
        self.state_file = state_file
        self.active_orders: Dict[str, dict] = {}  # user_id -> order state
        self.load_state()
        
        # 数据库路径
        self.db_path = os.path.join(os.getcwd(), 'products.db')
        
        # 产品价格配置（优先从数据库加载，这里保留默认值作为备用）
        self.product_prices = {
            "A型产品": 50.0,
            "B型产品": 60.0,
            "C型产品": 70.0,
        }
    
    def load_state(self):
        """加载状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.active_orders = json.load(f)
                print(f"已加载 {len(self.active_orders)} 个活跃订单")
            except Exception as e:
                print(f"加载状态失败: {e}")
                self.active_orders = {}
    
    def save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存状态失败: {e}")
    
    def clear_all_orders(self):
        """清理所有活跃订单"""
        self.active_orders.clear()
        self.save_state()
        print("已清理所有活跃订单")
    
    def is_trigger_keyword(self, text: str) -> bool:
        """检查是否包含触发关键词"""
        # 按照关键词长度排序，优先匹配更长的关键词（如"打印发货单"）
        sorted_keywords = sorted(self.TRIGGER_KEYWORDS, key=len, reverse=True)
        
        text = text.strip()  # 移除首尾空格
        
        for keyword in sorted_keywords:
            if keyword in text:
                return True
        
        # 如果没有触发关键词，检查是否可能是订单消息（包含数量信息）
        return self._is_possible_order_message(text)
    
    def _is_possible_order_message(self, text: str) -> bool:
        """检测是否可能是订单消息"""
        # 数量模式：数字 + kg/千克/KG等
        quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|k g|千克|公斤|KG|K|g)'
        
        if re.search(quantity_pattern, text, re.IGNORECASE):
            # 包含数量信息，可能是订单
            return True
        
        return False
    
    def start_order(self, user_id: str, user_name: str = "") -> dict:
        """开始新的订单流程"""
        order_data = OrderData()
        
        self.active_orders[user_id] = {
            "state": OrderState.COLLECTING.value,
            "user_name": user_name,
            "start_time": datetime.now().isoformat(),
            "data": order_data.to_dict(),
            "current_step": FieldType.COMPANY_NAME.value,
            "message_count": 0
        }
        
        self.save_state()
        
        # 返回第一个问题，包含action字段
        next_question = self.get_next_question(user_id)
        if next_question:
            next_question["action"] = "CONTINUE"
        return next_question
    
    def get_next_question(self, user_id: str) -> Optional[dict]:
        """获取下一个问题"""
        if user_id not in self.active_orders:
            return None
        
        order = self.active_orders[user_id]
        if order["state"] != OrderState.COLLECTING.value:
            return None
        
        # 解析当前数据
        order_data = OrderData(**order["data"])
        
        # 首先检查所有必填字段是否已完成
        all_required_completed = True
        for field in self.REQUIRED_FIELDS:
            if field == FieldType.PRODUCTS.value:
                if len(order_data.products) == 0:
                    all_required_completed = False
                    break
            else:
                if not getattr(order_data, field, ""):
                    all_required_completed = False
                    break
        
        # 如果必填字段未完成，继续询问必填字段
        if not all_required_completed:
            for field in self.REQUIRED_FIELDS:
                if field == FieldType.PRODUCTS.value:
                    if len(order_data.products) == 0:
                        return {
                            "user_id": user_id,
                            "question": self.FIELD_QUESTIONS[field],
                            "step": field,
                            "completed": False,
                            "order_summary": order_data.to_dict(),
                            "action": "CONTINUE"
                        }
                else:
                    if not getattr(order_data, field, ""):
                        return {
                            "user_id": user_id,
                            "question": self.FIELD_QUESTIONS[field],
                            "step": field,
                            "completed": False,
                            "order_summary": order_data.to_dict(),
                            "action": "CONTINUE"
                        }
        
        # 所有必填字段已完成，检查当前步骤
        current_step = order.get("current_step", "")
        
        # 找到当前步骤在可选字段列表中的索引
        current_index = -1
        if current_step in self.OPTIONAL_FIELDS:
            current_index = self.OPTIONAL_FIELDS.index(current_step)
        
        # 从当前步骤的下一个可选字段开始检查
        for i in range(current_index + 1, len(self.OPTIONAL_FIELDS)):
            field = self.OPTIONAL_FIELDS[i]
            if not getattr(order_data, field, ""):
                return {
                    "user_id": user_id,
                    "question": f"{self.FIELD_QUESTIONS[field]}\n（可选，直接回复'跳过'或'不填'即可跳过）",
                    "step": field,
                    "completed": False,
                    "order_summary": order_data.to_dict(),
                    "action": "CONTINUE"
                }
        
        # 所有可选字段都已处理（要么已填写，要么已跳过）
        return {
            "user_id": user_id,
            "question": "所有信息已收集完毕，正在生成发货单...",
            "step": "GENERATING",
            "completed": True,
            "order_summary": order_data.to_dict(),
            "action": "COMPLETE"
        }
    
    def process_message(self, user_id: str, message: str) -> dict:
        """处理用户消息"""
        # 检查是否为问候或系统状态询问
        greeting_patterns = [
            r'小张.*在.*吗', r'小张.*在.*吗\?', r'小张.*在.*\?', r'小张.*在',
            r'在.*吗', r'在.*吗\?', r'在.*\?', r'在.*',
            r'有人.*吗', r'有人.*吗\?', r'有人.*\?', r'有人.*',
            r'系统.*正常', r'系统.*运行', r'系统.*工作', r'系统.*ok',
            r'你好', r'您好', r'哈喽', r'hi', r'hello',
            r'测试.*系统', r'检查.*系统', r'确认.*运行'
        ]
        
        message_lower = message.lower().strip()
        for pattern in greeting_patterns:
            if re.search(pattern, message_lower):
                return {
                    "action": "GREETING",
                    "message": "您好！我在，系统正常运行中。\n\n我可以帮您处理发货单相关业务，请发送您的订单信息。\n\n例如：\n• PE白底漆100kg，瑞星，今天\n• 公司名称，产品名称数量，日期"
                }
        
        # 检查是否是触发关键词或者是可能的订单消息
        is_trigger = self.is_trigger_keyword(message)
        is_possible_order = not is_trigger and self._is_possible_order_message(message)
        
        # 检查是否有订单（活跃或已完成）
        has_order = user_id in self.active_orders
        
        if is_trigger or is_possible_order:
            # 检查是否有活跃订单
            if has_order:
                # 已有订单，询问用户意图
                # 保存确认类型到订单状态
                self.active_orders[user_id]["confirm_type"] = "REGENERATE_ORDER"
                self.save_state()
                return {
                    "action": "CONFIRM",
                    "message": "您已有一个发货单记录。请问您想：\n1. 清理之前的记录并重新生成新发货单\n2. 查看当前发货单的处理进度",
                    "confirm_type": "REGENERATE_ORDER"
                }
            else:
                # 没有订单，询问是否为发货单
                self.active_orders[user_id] = {
                    "state": OrderState.COLLECTING.value,
                    "user_name": "",
                    "start_time": datetime.now().isoformat(),
                    "data": OrderData().to_dict(),
                    "current_step": "CONFIRM_ORDER_TYPE",
                    "message_count": 1,
                    "confirm_type": "ORDER_TYPE",  # 添加确认类型
                    "original_message": message  # 保存原始消息
                }
                self.save_state()
                
                # 根据消息类型调整确认文本
                if is_trigger:
                    confirm_text = "您发送了发货单相关内容。"
                else:
                    confirm_text = "您发送了包含数量信息的消息。"
                
                return {
                    "action": "CONFIRM",
                    "message": f"{confirm_text}\n\n这是否为发货单相关的内容？",
                    "confirm_type": "ORDER_TYPE"
                }
        
        # 不是触发关键词，检查是否有活跃订单
        if not has_order:
            return {"action": "NONE"}
        
        order = self.active_orders[user_id]
        
        # 解析用户回复
        return self._parse_answer(user_id, message)
    
    def _parse_answer(self, user_id: str, answer: str) -> dict:
        """解析用户回答"""
        print(f"=== 开始解析用户回答 ===")
        print(f"用户ID: {user_id}")
        print(f"用户回答: '{answer}'")
        
        if user_id not in self.active_orders:
            print(f"=== 解析失败: 订单不存在 ===")
            return {"action": "ERROR", "message": "订单不存在"}
        
        order = self.active_orders[user_id]
        order_data = OrderData(**order["data"])
        current_step = order["current_step"]
        print(f"当前步骤: {current_step}")
        
        # 检查是否是对重新生成订单确认的回复
        if "confirm_type" in order and order["confirm_type"] == "REGENERATE_ORDER":
            answer_lower = answer.strip().lower()
            
            # 处理用户选择
            if any(choice in answer_lower for choice in ["1", "一", "第一个", "第一项", "清理", "重新生成", "重新开始", "重新", "是", "重新创建"]):
                # 清理原有订单并开始新订单
                print(f"用户选择清理原有订单并重新生成")
                self.clear_order(user_id)
                return self.start_order(user_id)
            elif any(choice in answer_lower for choice in ["2", "二", "第二个", "第二项", "查看", "进度", "状态", "否", "查询"]):
                # 查看当前订单进度
                print(f"用户选择查看当前订单进度")
                # 清除确认类型
                if "confirm_type" in order:
                    del order["confirm_type"]
                    self.save_state()
                # 返回订单状态
                return {
                    "action": "INFO",
                    "message": f"当前订单进度：\n- 当前步骤：{current_step}\n- 状态：{order['state']}\n- 公司名称：{order_data.company_name}\n- 产品数量：{len(order_data.products)}种",
                    "order_data": order_data.to_dict()
                }
            else:
                # 未识别的选择，重新询问
                return {
                    "action": "CONFIRM",
                    "message": "请选择：\n1. 清理之前的记录并重新生成新发货单\n2. 查看当前发货单的处理进度",
                    "confirm_type": "REGENERATE_ORDER"
                }
        
        # 检查是否是对订单类型确认的回复
        if "confirm_type" in order and order["confirm_type"] == "ORDER_TYPE":
            answer_lower = answer.strip().lower()
            
            # 检查用户是否确认
            if answer_lower in ['是', 'yes', 'y', '确认', '1', '对的', '是的', '好', '好的', '确定']:
                # 用户确认这是发货单，尝试解析完整订单
                original_message = order.get("original_message", "")
                full_order_result = self._parse_full_order(user_id, original_message)
                
                if full_order_result:
                    # 成功解析完整订单，返回结果
                    # 清除临时状态
                    if "confirm_type" in order:
                        del order["confirm_type"]
                    if "original_message" in order:
                        del order["original_message"]
                    self.save_state()
                    return full_order_result
                else:
                    # 解析失败，返回错误并清理临时状态
                    if "confirm_type" in order:
                        del order["confirm_type"]
                    if "original_message" in order:
                        del order["original_message"]
                    self.save_state()
                    return {
                        "action": "ERROR",
                        "message": "抱歉，我无法解析您的消息。请重新输入更清晰的发货单信息：\n\n例如：发货单 瑞鑫家私 PE白底机100kg"
                    }
            elif answer_lower in ['否', 'no', 'n', '不', '不是', '不对', '取消']:
                # 用户否认，清理临时状态
                del order["confirm_type"]
                if "original_message" in order:
                    del order["original_message"]
                self.save_state()
                return {
                    "action": "INFO",
                    "message": "好的，已取消发货单流程。"
                }
            else:
                # 未识别的回答，重新询问
                return {
                    "action": "CONFIRM",
                    "message": "请确认这是否为发货单相关的内容？\n\n请回答：\n- 是 / 确认：开始处理发货单\n- 否 / 不：取消",
                    "confirm_type": "ORDER_TYPE"
                }
        
        # 检查是否是对产品确认的回复
        if "possible_products" in order:
            # 处理产品确认回复
            possible_products = order["possible_products"]
            answer_stripped = answer.strip()
            
            try:
                # 检查是否是数字选择
                choice = int(answer_stripped)
                if 1 <= choice <= len(possible_products):
                    # 用户选择了一个产品
                    selected_product = possible_products[choice - 1]
                    
                    # 更新产品信息
                    company_products = self.get_products_for_company(order_data.company_name)
                    
                    # 重新解析产品，使用选中的产品名称
                    # 从临时保存的产品中获取数量
                    for i, product in enumerate(order_data.products):
                        # 假设只有一个产品需要确认
                        if isinstance(product, dict):
                            quantity = product.get("quantity", 0)
                        else:
                            quantity = product.quantity
                        
                        # 使用选中的产品名称重新生成产品信息
                        new_product_text = f"{selected_product} {quantity}kg"
                        new_products = self._parse_products(new_product_text, company_products)
                        if new_products:
                            order_data.products[i] = new_products[0]
                            print(f"用户确认产品: {selected_product}")
                            break
            except ValueError:
                # 用户输入了产品名称
                company_products = self.get_products_for_company(order_data.company_name)
                # 重新解析用户输入的产品
                new_products = self._parse_products(answer, company_products)
                if new_products:
                    order_data.products = new_products
                    print(f"用户输入新产品: {new_products[0].name}")
                else:
                    return {
                        "action": "RETRY",
                        "message": "产品格式不正确，请使用：产品名 数量KG\n例如：A型产品 500KG，B型产品 300KG"
                    }
            
            # 更新订单数据
            order["data"] = order_data.to_dict()
            order["message_count"] += 1
            order["last_update"] = datetime.now().isoformat()
            
            # 清除确认信息
            if "possible_products" in order:
                del order["possible_products"]
            
            # 保存状态
            self.save_state()
            
            # 获取下一个问题，继续流程
            next_question = self.get_next_question(user_id)
            
            if next_question and next_question["completed"]:
                # 信息已完整，准备生成
                print(f"=== 工作流完成: 所有信息已收集完毕 ===")
                return {
                    "action": "COMPLETE",
                    "order_data": order_data.to_dict(),
                    "message": "所有信息已收集完毕！"
                }
            elif next_question:
                # 继续询问
                order["current_step"] = next_question["step"]
                self.save_state()
                
                print(f"=== 工作流继续: 下一步 -> {next_question['step']} ===")
                return {
                    "action": "CONTINUE",
                    "question": next_question["question"],
                    "step": next_question["step"],
                    "order_data": order_data.to_dict()
                }
            else:
                return {"action": "ERROR", "message": "未知错误"}
        
        # 检查是否是对公司名称确认的回复
        elif "confirmed_name" in order:
            # 处理公司名称确认
            answer_lower = answer.strip().lower()
            
            # 检查用户是否确认
            if answer_lower in ['是', 'yes', 'y', '确认', '1', '对的', '是的', '好', '好的', '确定']:
                # 用户确认使用匹配的公司名称
                confirmed_name = order["confirmed_name"]
                order_data.company_name = confirmed_name
                print(f"用户确认公司名称: {confirmed_name}")
                
                # 清除确认信息
                del order["confirmed_name"]
                
                # 更新订单数据
                order["data"] = order_data.to_dict()
                order["message_count"] += 1
                order["last_update"] = datetime.now().isoformat()
                
                # 如果有original_input，尝试继续解析
                if "original_input" in order:
                    original_msg = order["original_input"]
                    # 从原始消息中提取产品信息
                    parts = original_msg.split(" ", 1)
                    if len(parts) >= 2:
                        product_info = parts[1].strip()
                        quantity_pattern = r'(\d+(?:\.\d+)?)(?:kg|k g|千克|公斤)?'
                        quantity_match = re.search(quantity_pattern, product_info, re.IGNORECASE)
                        
                        if quantity_match:
                            quantity = float(quantity_match.group(1))
                            product_name = product_info[:quantity_match.start()].strip()
                            
                            # 解析产品
                            company_products = self.get_products_for_company(order_data.company_name)
                            products = self._parse_products(f"{product_name} {quantity}kg", company_products)
                            if products:
                                order_data.products = products
                                order["data"] = order_data.to_dict()
                    
                    del order["original_input"]
                
                self.save_state()
                
                # 返回完成状态
                print(f"=== 公司确认完成: {order_data.company_name} ===")
                return {
                    "action": "COMPLETE",
                    "order_data": order_data.to_dict(),
                    "message": f"公司已确认为：{order_data.company_name}\n产品：{', '.join([p.name if hasattr(p, 'name') else p['name'] for p in order_data.products])}\n\n信息收集完成，正在生成发货单..."
                }
            elif answer_lower in ['否', 'no', 'n', '不', '不是', '不对', '取消']:
                # 用户否认，提示重新输入
                del order["confirmed_name"]
                if "original_input" in order:
                    del order["original_input"]
                self.save_state()
                
                return {
                    "action": "RETRY",
                    "message": f"请重新输入正确的公司名称："
                }
            else:
                # 用户可能输入了新的公司名称，重新匹配
                company_match = match_company_name(answer.strip())
                if company_match:
                    order_data.company_name = company_match['matched_name']
                    order_data.contact_person = company_match.get('contact_person', '')
                    order_data.contact_phone = company_match.get('contact_phone', '')
                    order["confirmed_name"] = company_match['matched_name']
                    order["data"] = order_data.to_dict()
                    
                    if company_match['similarity'] < 1.0:
                        # 仍然不是精确匹配，再次询问
                        self.save_state()
                        return {
                            "action": "CONFIRM",
                            "message": f"是否是指 '{company_match['matched_name']}'？\n（联系人：{company_match.get('contact_person', '未设置')}）",
                            "confirm_type": "COMPANY_MATCH"
                        }
                    else:
                        # 精确匹配，确认并继续
                        del order["confirmed_name"]
                        order["data"] = order_data.to_dict()
                        self.save_state()
                        
                        return {
                            "action": "COMPLETE",
                            "order_data": order_data.to_dict(),
                            "message": f"公司已确认为：{order_data.company_name}\n\n信息收集完成，正在生成发货单..."
                        }
                else:
                    # 未找到匹配的公司
                    del order["confirmed_name"]
                    if "original_input" in order:
                        del order["original_input"]
                    self.save_state()
                    
                    return {
                        "action": "RETRY",
                        "message": f"未找到 '{answer.strip()}'，请重新输入公司名称："
                    }
        
        # 检查回答是否只是触发关键词
        if self.is_trigger_keyword(answer.strip()):
            # 如果用户明确想重新开始，允许启动新订单
            print(f"用户回答是触发关键词，继续当前流程")
            return {
                "action": "CONFIRM",
                "message": "您已经有一个活跃的订单流程。请问您想：\n1. 清理之前的记录并重新生成新发货单\n2. 查看当前发货单的处理进度",
                "confirm_type": "REGENERATE_ORDER"
            }
        
        # 检查是否跳过可选字段
        skip_keywords = ['跳过', '趾过', '跳過', '不填', 'none', '无', '不需要', '不用填', 'skip', '不 需要', '不 填']
        # 全部跳过关键词
        all_skip_keywords = ['全部跳过', '全部不填', '跳过全部', '不填全部', 'skip all', 'all skip']
        answer_lower = answer.strip().lower()
        is_skip = any(keyword.lower() in answer_lower for keyword in skip_keywords)
        is_all_skip = any(keyword.lower() in answer_lower for keyword in all_skip_keywords)
        
        if is_all_skip:
            # 全部跳过：直接标记所有可选字段为已处理，返回COMPLETE状态
            print(f"用户选择全部跳过剩余字段")
            # 更新订单数据
            order["data"] = order_data.to_dict()
            order["message_count"] += 1
            order["last_update"] = datetime.now().isoformat()
            self.save_state()
            
            # 直接返回完成状态
            print(f"=== 工作流完成: 所有信息已收集完毕 (全部跳过) ===")
            return {
                "action": "COMPLETE",
                "order_data": order_data.to_dict(),
                "message": "已跳过所有剩余字段，所有信息已收集完毕！"
            }
        elif is_skip:
            # 跳过当前可选字段，直接进入下一步
            print(f"用户跳过了当前可选字段: {current_step}")
            # 对于可选字段，跳过即视为已处理
            if current_step in self.OPTIONAL_FIELDS:
                # 将当前步骤标记为已处理（跳过）
                # 注意：这里不需要修改order_data，因为跳过意味着不填写该字段
                pass
        else:
            # 解析不同类型的回答
            if current_step == FieldType.COMPANY_NAME.value:
                # 检查是否为空或只是空格
                if not answer.strip():
                    return {
                        "action": "RETRY",
                        "message": "公司名称不能为空，请重新输入"
                    }
                
                # 验证公司名称（模糊匹配）
                from company_matcher import match_company_name
                company_match = match_company_name(answer.strip())
                
                if company_match:
                    # 找到匹配的公司
                    order_data.company_name = company_match['matched_name']
                    order_data.contact_person = company_match.get('contact_person', '')
                    order_data.contact_phone = company_match.get('contact_phone', '')
                    print(f"匹配到公司: {company_match['matched_name']}")
                    
                    # 如果相似度不是100%，提示用户确认
                    if company_match['similarity'] < 1.0:
                        return {
                            "action": "CONFIRM",
                            "message": f"是否是指 '{company_match['matched_name']}'？\n（联系人：{company_match.get('contact_person', '未设置')}）",
                            "confirmed_name": company_match['matched_name'],
                            "order_data": order_data.to_dict()
                        }
                    # 相似度100%，无需确认，继续下一步
                else:
                    # 未找到匹配的公司，提示用户选择
                    from company_matcher import get_all_companies
                    all_companies = get_all_companies()
                    
                    if all_companies:
                        # 提供建议列表
                        companies_list = '\n'.join([c['unit_name'] for c in all_companies[:10]])
                        return {
                            "action": "RETRY",
                            "message": f"未找到 '{answer.strip()}'，请选择或重新输入：\n{companies_list}\n\n或者发送'添加新单位'来添加新的购买单位",
                            "suggestions": [c['unit_name'] for c in all_companies[:10]]
                        }
                    else:
                        # 没有公司数据，直接保存用户输入
                        order_data.company_name = answer.strip()
            elif current_step == FieldType.PRODUCTS.value:
                # 获取该公司的产品信息
                company_name = order_data.company_name
                company_products = self.get_products_for_company(company_name)
                
                # 解析产品信息，传入公司产品数据
                products = self._parse_products(answer, company_products)
                
                if products:
                    # 检查是否需要产品确认
                    need_confirmation = False
                    possible_matches = []
                    target_product_name = ""
                    
                    # 检查每个产品是否需要确认
                    for i, product in enumerate(products):
                        # 获取原始输入的产品名称
                        for item in re.split(r'[,，\n]', answer):
                            item = item.strip()
                            if not item:
                                continue
                                
                            # 提取产品名称
                            quantity_pattern = r'(\d+(?:\.\d+)?)(?:kg|k g|千克|公斤)?'
                            quantity_match = re.search(quantity_pattern, item, re.IGNORECASE)
                            if quantity_match:
                                input_product_name = item[:quantity_match.start()].strip()
                                
                                # 计算与数据库产品的相似度
                                exact_match = False
                                product_matches = []
                                
                                for db_product in company_products:
                                    similarity = self._calculate_similarity(input_product_name.lower(), db_product.lower())
                                    product_matches.append((db_product, similarity))
                                
                                # 按相似度排序
                                product_matches.sort(key=lambda x: x[1], reverse=True)
                                
                                if product_matches:
                                    best_match, best_similarity = product_matches[0]
                                    
                                    # 如果相似度小于0.9，需要确认
                                    if best_similarity < 0.9:
                                        need_confirmation = True
                                        # 获取相似度大于0.5的所有匹配项
                                        possible_matches = [p[0] for p in product_matches if p[1] >= 0.5][:5]
                                        target_product_name = input_product_name
                                        break
                                
                                if need_confirmation:
                                    break
                        
                        if need_confirmation:
                            break
                    
                    if need_confirmation:
                        # 需要用户确认产品
                        order_data.products = products  # 先保存临时产品
                        matches_str = '\n'.join([f"{i+1}. {p}" for i, p in enumerate(possible_matches[:5])])
                        
                        # 将确认信息保存到订单状态
                        order["possible_products"] = possible_matches
                        order["data"] = order_data.to_dict()
                        self.save_state()
                        
                        return {
                            "action": "CONFIRM",
                            "message": f"未找到完全匹配的产品 '{target_product_name}'，是否是指：\n{matches_str}\n\n请回复对应的数字或直接输入正确的产品名称",
                            "possible_products": possible_matches,
                            "order_data": order_data.to_dict()
                        }
                    
                    # 完全匹配，直接保存
                    order_data.products = products
                    print(f"保存产品信息: {[p.name for p in products]}")
                else:
                    return {
                        "action": "RETRY",
                        "message": "产品格式不正确，请使用：产品名 数量KG\n例如：A型产品 500KG，B型产品 300KG"
                    }
            elif current_step == FieldType.CONTACT_PERSON.value:
                if not answer.strip():
                    return {
                        "action": "RETRY",
                        "message": "联系人不能为空，请重新输入"
                    }
                order_data.contact_person = answer.strip()
                print(f"保存联系人: {order_data.contact_person}")
            elif current_step == FieldType.CONTACT_PHONE.value:
                # 验证联系电话格式
                phone = answer.strip()
                # 只接受数字、空格、连字符、括号、加号等电话相关字符
                if not re.match(r'^[\d\s\-()\+]*$', phone):
                    return {
                        "action": "RETRY",
                        "message": "联系电话格式不正确，请只输入数字、空格、连字符、括号等电话相关字符\n例如：13800138000、(020) 12345678"
                    }
                order_data.contact_phone = phone
                print(f"保存联系电话: {order_data.contact_phone}")
            elif current_step == FieldType.DELIVERY_DATE.value:
                # 解析日期（支持多种格式）
                parsed_date = self._parse_date(answer.strip())
                if parsed_date:
                    order_data.delivery_date = parsed_date
                    print(f"保存发货日期: {order_data.delivery_date}")
                else:
                    return {
                        "action": "RETRY",
                        "message": "日期格式不正确，请回答：\n- 输入\"今天\"自动使用今天日期\n- 或使用格式：2024-01-20、2024年1月20日、1月20日"
                    }
            elif current_step == FieldType.REMARKS.value:
                order_data.remarks = answer.strip()
                print(f"保存备注: {order_data.remarks}")
        
        # 更新状态
        order["data"] = order_data.to_dict()
        order["message_count"] += 1
        order["last_update"] = datetime.now().isoformat()
        self.save_state()
        
        # 获取下一个问题
        next_question = self.get_next_question(user_id)
        
        if next_question and next_question["completed"]:
            # 信息已完整，准备生成
            print(f"=== 工作流完成: 所有信息已收集完毕 ===")
            return {
                "action": "COMPLETE",
                "order_data": order_data.to_dict(),
                "message": "所有信息已收集完毕！"
            }
        elif next_question:
            # 继续询问
            order["current_step"] = next_question["step"]
            self.save_state()
            
            print(f"=== 工作流继续: 下一步 -> {next_question['step']} ===")
            return {
                "action": "CONTINUE",
                "question": next_question["question"],
                "step": next_question["step"],
                "order_data": order_data.to_dict()
            }
        else:
            print(f"=== 工作流错误: 未知错误 ===")
            return {"action": "ERROR", "message": "未知错误"}
    
    def _validate_date(self, date_str: str) -> bool:
        """验证日期格式"""
        patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # 2024-01-20
            r'^\d{4}年\d{1,2}月\d{1,2}日$',  # 2024年1月20日
        ]
        for pattern in patterns:
            if re.match(pattern, date_str):
                return True
        return False
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期，支持多种格式，处理OCR常见错误"""
        from datetime import datetime, timedelta
        
        original_date = date_str
        print(f"=== 开始日期解析 ===")
        print(f"原始日期: '{date_str}'")
        
        # 清理日期字符串，处理OCR可能产生的空格和常见错误
        date_str = date_str.strip().lower()
        print(f"清理后: '{date_str}'")
        
        # 移除所有空格，处理OCR可能产生的空格问题
        date_str = date_str.replace(' ', '')
        print(f"移除空格后: '{date_str}'")
        
        # 处理常见的OCR误识别
        ocr_fixes = {
            '今夭': '今天',  # 天字误识别为夭
            '今大': '今天',  # 天字误识别为大
            '今夫': '今天',  # 天字误识别为夫
            '令天': '今天',  # 今字误识别为令
            '日天': '今天',  # 今字误识别为日
            '明夭': '明天',  # 天字误识别为夭
            '明大': '明天',  # 天字误识别为大
            '后夭': '后天',  # 天字误识别为夭
            '后大': '后天',  # 天字误识别为大
        }
        
        # 应用OCR修复
        if date_str in ocr_fixes:
            fixed_date = ocr_fixes[date_str]
            print(f"日期OCR修复: '{date_str}' -> '{fixed_date}'")
            date_str = fixed_date
        
        # 处理相对日期
        if date_str in ['今天', '今日', 'today']:
            result = datetime.now().strftime('%Y-%m-%d')
            print(f"相对日期处理: '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        elif date_str in ['明天', '明日', 'tomorrow']:
            result = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"相对日期处理: '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        elif date_str in ['后天', '后日']:
            result = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
            print(f"相对日期处理: '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        # 格式1: 2024-01-20
        match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
        if match:
            result = date_str
            print(f"格式1匹配: '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        # 格式2: 2024年1月20日 或 2024年01月20日
        match = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', date_str)
        if match:
            year, month, day = match.groups()
            result = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            print(f"格式2匹配: '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        # 格式3: 1月20日 或 01-20 (使用当前年份)
        match = re.match(r'^(\d{1,2})月(\d{1,2})日$', date_str)
        if match:
            month, day = match.groups()
            year = datetime.now().year
            result = f"{year}-{int(month):02d}-{int(day):02d}"
            print(f"格式3匹配(月日): '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        match = re.match(r'^(\d{1,2})-(\d{1,2})$', date_str)
        if match:
            month, day = match.groups()
            year = datetime.now().year
            result = f"{year}-{int(month):02d}-{int(day):02d}"
            print(f"格式3匹配(月-日): '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        # 格式4: 1月20 (无"日")
        match = re.match(r'^(\d{1,2})月(\d{1,2})$', date_str)
        if match:
            month, day = match.groups()
            year = datetime.now().year
            result = f"{year}-{int(month):02d}-{int(day):02d}"
            print(f"格式4匹配(月日无日): '{date_str}' -> '{result}'")
            print(f"=== 日期解析完成: '{original_date}' -> '{result}' ===")
            return result
        
        print(f"=== 日期解析失败: '{original_date}' ===")
        return None
    
    def _parse_full_order(self, user_id: str, message: str) -> Optional[dict]:
        """解析完整订单指令
        
        支持格式：
        - "打印发货单 瑞幸家私 PE 白底机100千克"
        - "发货单 瑞幸家私 PE 白底机100千克 跳过"
        - "打印 帮我打印一下PE白底漆稀释剂，100kg瑞星的"
        """
        try:
            cleaned_message = message.strip()
            
            # 按照关键词长度排序，优先匹配更长的关键词
            sorted_keywords = sorted(self.TRIGGER_KEYWORDS, key=len, reverse=True)
            
            trigger_keyword = None
            for keyword in sorted_keywords:
                # 使用更灵活的匹配方式
                if keyword in cleaned_message:
                    trigger_keyword = keyword
                    cleaned_message = cleaned_message.replace(keyword, "").strip()
                    break
            
            if not cleaned_message:
                return None
            
            # 移除常见的连接词和填充词
            prefixes_to_remove = [
                '一下', '帮我', '帮', '给我', '请', '需要', '要', '麻烦',
                '谢谢', '感谢', '辛苦', '拜托'
            ]
            
            # 循环移除多个填充词
            for prefix in prefixes_to_remove:
                cleaned_message = cleaned_message.replace(prefix, '').strip()
            
            # 清理多余的空格
            cleaned_message = re.sub(r'\s+', ' ', cleaned_message).strip()
            
            if not cleaned_message:
                return None
            
            # 如果清理后的消息仍然包含触发关键词（可能是自然语言），再次清理
            for keyword in sorted_keywords:
                if keyword in cleaned_message:
                    cleaned_message = cleaned_message.replace(keyword, "").strip()
                    break
            
            if not cleaned_message:
                return None
            
            # 提取公司名称和产品信息
            # 尝试找到公司名称（通常在数量信息之后）
            # 数量模式：数字 + kg/千克/KG等
            quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|k g|千克|公斤|KG|K|g)'
            
            quantity_match = re.search(quantity_pattern, cleaned_message, re.IGNORECASE)
            
            if not quantity_match:
                return None
            
            # 获取数量
            quantity = float(quantity_match.group(1))
            
            # 提取数量之前和之后的内容
            before_quantity = cleaned_message[:quantity_match.start()].strip()
            after_quantity = cleaned_message[quantity_match.end():].strip()
            
            print(f"DEBUG: before_quantity='{before_quantity}', after_quantity='{after_quantity}'")
            
            if not before_quantity:
                return None
            
            # 尝试从数量之后提取公司名称
            company_name = ""
            if after_quantity:
                # 清理公司名称（移除逗号、的等）
                company_name = after_quantity.strip().rstrip('的').rstrip(',').rstrip('，').rstrip('.')
            
            # 从数量之前的内容中提取产品名称
            product_name = ""
            
            # 常见的产品前缀和后缀
            product_prefixes = ['PE', 'PVC', 'UV', 'PU', 'NC', 'AC', '环氧', '丙烯酸', '醇酸', '氟碳', '白底', '面漆', '底漆', '稀释剂', '固化剂', '色精', '色浆', '助剂']
            product_suffixes = ['剂', '料', '浆', '粉', '油', '胶', '漆', '剂']
            
            # 查找产品名称
            if before_quantity:
                # 先尝试从后往前查找产品前缀
                product_start = len(before_quantity)
                for prefix in product_prefixes:
                    pos = before_quantity.rfind(prefix)
                    if pos != -1 and pos < product_start:
                        product_start = pos
                
                # 如果找到了产品前缀，产品名称是从前缀开始到逗号之前的内容
                if product_start < len(before_quantity):
                    product_name = before_quantity[product_start:].rstrip('，').rstrip(',').strip()
                
                # 如果没找到特定前缀，检查是否包含常见产品后缀
                if not product_name:
                    for suffix in product_suffixes:
                        pos = before_quantity.rfind(suffix)
                        if pos != -1:
                            # 从开头到包含后缀的位置
                            product_name = before_quantity[:pos+len(suffix)].rstrip('，').rstrip(',').strip()
                            break
                
                # 如果仍然没找到，整个before_quantity作为产品名称
                if not product_name:
                    product_name = before_quantity.rstrip('，').rstrip(',').strip()
            
            if not company_name and not product_name:
                return None
            
            if not product_name:
                product_name = company_name
                company_name = ""
            
            print(f"解析结果: 公司='{company_name}', 产品='{product_name}', 数量={quantity}kg")
            
            # 开始新订单
            # user_id已经在函数参数中定义，直接使用
            
            # 清理可能存在的旧订单
            if user_id in self.active_orders:
                self.clear_order(user_id)
            
            # 匹配公司名称
            from company_matcher import match_company_name
            company_match = match_company_name(company_name)
            
            # 直接创建订单数据
            order_data = OrderData()
            
            if company_match:
                order_data.company_name = company_match['matched_name']
                order_data.contact_person = company_match.get('contact_person', '')
                order_data.contact_phone = company_match.get('contact_phone', '')
                
                # 如果相似度不是100%，提示用户确认
                if company_match['similarity'] < 1.0:
                    # 添加产品
                    company_products = self.get_products_for_company(order_data.company_name)
                    products = self._parse_products(f"{product_name} {quantity}kg", company_products)
                    order_data.products = products
                    
                    # 设置发货日期为今天
                    from datetime import datetime
                    order_data.delivery_date = datetime.now().strftime("%Y-%m-%d")
                    
                    # 创建新订单，添加确认信息
                    self.active_orders[user_id] = {
                        "state": OrderState.COLLECTING.value,
                        "user_name": "",
                        "start_time": datetime.now().isoformat(),
                        "data": order_data.to_dict(),
                        "current_step": FieldType.COMPANY_NAME.value,
                        "message_count": 1,
                        "confirmed_name": company_match['matched_name'],  # 用于确认的公司名称
                        "original_input": message  # 保存原始输入
                    }
                    
                    self.save_state()
                    
                    # 返回确认状态，使用现有的一致逻辑
                    return {
                        "action": "CONFIRM",
                        "message": f"您输入的是 '{company_name}'，是否是指 '{company_match['matched_name']}'？\n（联系人：{company_match.get('contact_person', '未设置')}）",
                        "confirm_type": "COMPANY_MATCH"
                    }
            else:
                order_data.company_name = company_name
            
            # 设置发货日期为今天
            from datetime import datetime
            order_data.delivery_date = datetime.now().strftime("%Y-%m-%d")
            
            # 添加产品
            company_products = self.get_products_for_company(order_data.company_name)
            products = self._parse_products(f"{product_name} {quantity}kg", company_products)
            order_data.products = products
            
            # 创建新订单
            self.active_orders[user_id] = {
                "state": OrderState.COLLECTING.value,
                "user_name": "",
                "start_time": datetime.now().isoformat(),
                "data": order_data.to_dict(),
                "current_step": "GENERATING",
                "message_count": 1
            }
            
            self.save_state()
            
            # 直接返回完成状态，开始生成发货单
            return {
                "action": "COMPLETE",
                "order_data": order_data.to_dict(),
                "message": "信息收集完成，正在生成发货单..."
            }
        except Exception as e:
            print(f"解析完整订单失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _parse_products(self, text: str, company_products: dict = None) -> List[ProductInfo]:
        """解析产品信息"""
        products = []
        
        # 如果没有提供公司产品数据，使用默认的产品价格配置
        if company_products is None:
            company_products = self.product_prices
        
        # 支持的格式：
        # "A型产品 500KG" 
        # "A型产品 500KG，B型产品 300KG"
        # "A 500, B 300"
        # "KGA500, KGB300" (型号+数量)
        # "B型产品30KG" (无空格)
        # "B型产品30OKG" (OCR误识别)
        
        # 分割多个产品
        items = re.split(r'[,，\n]', text)
        
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            # 如果匹配到标准产品格式，提取产品名称并标准化
            # 模式1: 产品名 数量KG
            match = re.search(r'([^\d]+?)\s*(\d+(?:\.\d+)?)*kg', item, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                qty = float(match.group(2))
                
                # 标准化产品名称
                standardized_name = self._standardize_product_name(name)
                print(f"🔄 产品名称标准化: '{name}' -> '{standardized_name}'")
                
                # 查找单价，支持大小写不敏感
                unit_price = 50.0
                matched_name = standardized_name  # 使用标准化后的名称作为默认值
                
                # 遍历公司产品，寻找匹配项
                for product_name in company_products:
                    # 基本匹配：包含关系
                    if standardized_name.lower() in product_name.lower() or product_name.lower() in standardized_name.lower():
                        unit_price = company_products[product_name]
                        matched_name = product_name  # 使用数据库中的产品名称
                        break
                
                # 如果没有匹配到，尝试更灵活的匹配
                if matched_name == standardized_name:
                    # 移除单位、型号和后缀信息，只保留核心产品名称
                    import string
                    
                    # 清理产品名称：移除单位、型号、特殊字符
                    cleaned_name = re.sub(r'\s*\d+.*', '', standardized_name)  # 移除数量和单位
                    cleaned_name = re.sub(r'\s*(pe|pp|pvc|9806a|型号|规格)\s*', '', cleaned_name, flags=re.IGNORECASE)  # 移除常见前缀和型号
                    cleaned_name = re.sub(r'[{}]'.format(string.punctuation), '', cleaned_name)  # 移除标点符号
                    
                    # 移除常见后缀
                    suffixes = ['机', '剂', '水', '油', '漆', '稀释剂', '溶液', '胶']
                    for suffix in suffixes:
                        if cleaned_name.endswith(suffix):
                            cleaned_name = cleaned_name[:-len(suffix)]
                            break
                    
                    # 再次尝试匹配核心名称
                    for product_name in company_products:
                        # 清理数据库产品名称
                        cleaned_db_name = re.sub(r'[{}]'.format(string.punctuation), '', product_name)  # 移除标点符号
                        
                        # 检查核心名称匹配
                        if cleaned_name.lower() in cleaned_db_name.lower() or cleaned_db_name.lower() in cleaned_name.lower():
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                        
                        # 尝试更宽松的匹配：检查是否有共同的关键词
                        db_words = set(cleaned_db_name.lower().split())
                        input_words = set(cleaned_name.lower().split())
                        if db_words.intersection(input_words):
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                
                amount = qty * unit_price
                
                products.append(ProductInfo(
                    name=matched_name,  # 使用匹配到的名称
                    quantity=qty,
                    unit_price=unit_price,
                    amount=amount
                ))
                continue
            
            # 清理文本，统一单位格式
            cleaned_item = item.lower()  # 转换为小写，支持大小写不敏感匹配
            
            # 支持多种千克单位
            kg_variants = ['kg', 'k g', '千克', '公斤']
            for kg in kg_variants:
                cleaned_item = cleaned_item.replace(kg, 'kg')
            
            # 清理OCR误识别的情况: "30okg" -> "30kg"
            cleaned_item = re.sub(r'(\d+)o(kg)$', r'\1\2', cleaned_item, flags=re.IGNORECASE)
            
            # 模式4: 产品名 + 数字 + KG (无空格或有其他字符分隔)
            # 例如: "B型产品30KG", "B型产品 30KG"
            match = re.search(r'([^\d]*?)\s*(\d+(?:\.\d+)?+)\s*kg', cleaned_item, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                qty_str = match.group(2)
                if not qty_str:
                    # 尝试从原始文本中提取数量
                    qty_match = re.search(r'(\d+(?:\.\d+)?)', item)
                    if qty_match:
                        qty_str = qty_match.group(1)
                    else:
                        continue
                
                qty = float(qty_str)
                
                if name:
                    # 查找单价 - 优先使用公司特定产品价格，支持大小写不敏感
                    unit_price = 50.0
                    matched_name = name
                    
                    # 遍历公司产品，寻找匹配项
                    for product_name in company_products:
                        if name.lower() == product_name.lower():
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                        elif name.lower() in product_name.lower() or product_name.lower() in name.lower():
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                    
                    amount = qty * unit_price
                    
                    products.append(ProductInfo(
                        name=matched_name,
                        quantity=qty,
                        unit_price=unit_price,
                        amount=amount
                    ))
                continue
            
            # 模式3: 型号+数量 (如 KGA500, KGB300)
            match = re.search(r'^([A-Za-z]+)(\d+(?:\.\d+)?)$', item)
            if match:
                name = match.group(1).strip()
                qty = float(match.group(2))
                
                # 查找单价（使用型号作为名称），支持大小写不敏感
                unit_price = 50.0
                matched_name = name
                
                # 遍历公司产品，寻找匹配项
                for product_name in company_products:
                    if name.lower() == product_name.lower() or name.lower() in product_name.lower():
                        unit_price = company_products[product_name]
                        matched_name = product_name  # 使用数据库中的产品名称
                        break
                amount = qty * unit_price
                
                products.append(ProductInfo(
                    name=matched_name,
                    quantity=qty,
                    model=name,
                    unit_price=unit_price,
                    amount=amount
                ))
                continue
            
            # 尝试提取产品和数量
            # 模式1: 产品名 数量KG
            match = re.search(r'([^\d]+?)\s*(\d+(?:\.\d+)?)*kg', item, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                qty = float(match.group(2))
                
                # 查找单价，支持大小写不敏感
                unit_price = 50.0
                matched_name = name
                
                # 遍历公司产品，寻找匹配项
                for product_name in company_products:
                    # 基本匹配：包含关系
                    if name.lower() in product_name.lower() or product_name.lower() in name.lower():
                        unit_price = company_products[product_name]
                        matched_name = product_name  # 使用数据库中的产品名称
                        break
                
                # 如果没有匹配到，尝试更灵活的匹配
                if matched_name == name:
                    # 移除单位、型号和后缀信息，只保留核心产品名称
                    import string
                    
                    # 清理产品名称：移除单位、型号、特殊字符
                    cleaned_name = re.sub(r'\s*\d+.*', '', name)  # 移除数量和单位
                    cleaned_name = re.sub(r'\s*(pe|pp|pvc|9806a|型号|规格)\s*', '', cleaned_name, flags=re.IGNORECASE)  # 移除常见前缀和型号
                    cleaned_name = re.sub(r'[{}]'.format(string.punctuation), '', cleaned_name)  # 移除标点符号
                    
                    # 移除常见后缀
                    suffixes = ['机', '剂', '水', '油', '漆', '稀释剂', '溶液', '胶']
                    for suffix in suffixes:
                        if cleaned_name.endswith(suffix):
                            cleaned_name = cleaned_name[:-len(suffix)]
                            break
                    
                    # 再次尝试匹配核心名称
                    for product_name in company_products:
                        # 清理数据库产品名称
                        cleaned_db_name = re.sub(r'[{}]'.format(string.punctuation), '', product_name)  # 移除标点符号
                        
                        # 检查核心名称匹配
                        if cleaned_name.lower() in cleaned_db_name.lower() or cleaned_db_name.lower() in cleaned_name.lower():
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                        
                        # 尝试更宽松的匹配：检查是否有共同的关键词
                        db_words = set(cleaned_db_name.lower().split())
                        input_words = set(cleaned_name.lower().split())
                        if db_words.intersection(input_words):
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                    
                    # 如果还是没有匹配到，尝试使用产品型号或代码
                    if matched_name == name:
                        # 查找可能的型号匹配
                        for product_name in company_products:
                            # 检查产品名称中是否包含数字或代码
                            if re.search(r'\d+', product_name) or re.search(r'[A-Z]+', product_name):
                                unit_price = company_products[product_name]
                                matched_name = product_name  # 使用数据库中的产品名称
                                break
                
                amount = qty * unit_price
                
                products.append(ProductInfo(
                    name=matched_name,
                    quantity=qty,
                    unit_price=unit_price,
                    amount=amount
                ))
                continue
            
            # 模式2: 产品名 数量（无单位）
            match = re.search(r'([^\d]+?)\s+(\d+(?:\.\d+)?)\s*$', item)
            if match:
                name = match.group(1).strip()
                qty = float(match.group(2))
                
                # 查找单价，支持大小写不敏感
                unit_price = 50.0
                matched_name = name
                
                # 遍历公司产品，寻找匹配项
                for product_name in company_products:
                    # 基本匹配：包含关系
                    if name.lower() in product_name.lower() or product_name.lower() in name.lower():
                        unit_price = company_products[product_name]
                        matched_name = product_name  # 使用数据库中的产品名称
                        break
                
                # 如果没有匹配到，尝试更灵活的匹配
                if matched_name == name:
                    # 移除单位、型号和后缀信息，只保留核心产品名称
                    import string
                    
                    # 清理产品名称：移除单位、型号、特殊字符
                    cleaned_name = re.sub(r'\s*\d+.*', '', name)  # 移除数量和单位
                    cleaned_name = re.sub(r'\s*(pe|pp|pvc|9806a|型号|规格)\s*', '', cleaned_name, flags=re.IGNORECASE)  # 移除常见前缀和型号
                    cleaned_name = re.sub(r'[{}]'.format(string.punctuation), '', cleaned_name)  # 移除标点符号
                    
                    # 移除常见后缀
                    suffixes = ['机', '剂', '水', '油', '漆', '稀释剂', '溶液', '胶']
                    for suffix in suffixes:
                        if cleaned_name.endswith(suffix):
                            cleaned_name = cleaned_name[:-len(suffix)]
                            break
                    
                    # 再次尝试匹配核心名称
                    for product_name in company_products:
                        # 清理数据库产品名称
                        cleaned_db_name = re.sub(r'[{}]'.format(string.punctuation), '', product_name)  # 移除标点符号
                        
                        # 检查核心名称匹配
                        if cleaned_name.lower() in cleaned_db_name.lower() or cleaned_db_name.lower() in cleaned_name.lower():
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                        
                        # 尝试更宽松的匹配：检查是否有共同的关键词
                        db_words = set(cleaned_db_name.lower().split())
                        input_words = set(cleaned_name.lower().split())
                        if db_words.intersection(input_words):
                            unit_price = company_products[product_name]
                            matched_name = product_name  # 使用数据库中的产品名称
                            break
                    
                    # 如果还是没有匹配到，尝试使用产品型号或代码
                    if matched_name == name:
                        # 查找可能的型号匹配
                        for product_name in company_products:
                            # 检查产品名称中是否包含数字或代码
                            if re.search(r'\d+', product_name) or re.search(r'[A-Z]+', product_name):
                                unit_price = company_products[product_name]
                                matched_name = product_name  # 使用数据库中的产品名称
                                break
                
                amount = qty * unit_price
                
                products.append(ProductInfo(
                    name=matched_name,
                    quantity=qty,
                    unit_price=unit_price,
                    amount=amount
                ))
        
        return products
    
    def generate_shipment_order(self, user_id: str) -> Optional[str]:
        """生成发货单"""
        if user_id not in self.active_orders:
            return None
        
        order = self.active_orders[user_id]
        order_data = OrderData(**order["data"])
        
        if not order_data.is_complete(self.REQUIRED_FIELDS):
            return None
        
        try:
            from template_manager import TemplateManager
            
            tm = TemplateManager()
            
            # 准备数据
            today = datetime.now()
            date_str = today.strftime("%Y年%m月%d日")
            order_no = today.strftime("%Y%m%d") + "A"
            
            # 构建 custom_data - 直接映射到Excel单元格
            custom_data = {}
            
            # 更新A2单元格：购货单位信息 - 四个部分均等分，左右顶格
            # 计算四个字段的内容：购货单位、联系人、日期、订单编号
            company_field = f"购货单位：{order_data.company_name}"
            contact_field = f"联系人：{order_data.contact_person}"
            date_field = f"{date_str}"
            order_field = f"订单编号：{order_no}"
            
            # 计算最大宽度，四个字段均等分
            # 假设A2列宽度约为80字符，我们分成四个等份，每份约20字符
            field_width = 18
            
            # 左对齐并截断到指定宽度
            company_part = company_field.ljust(field_width)[:field_width]
            contact_part = contact_field.ljust(field_width)[:field_width]
            date_part = date_field.ljust(field_width)[:field_width]
            order_part = order_field.ljust(field_width)[:field_width]
            
            # 拼接四个部分，确保左右顶格
            a2_value = company_part + contact_part + date_part + order_part
            custom_data["A2"] = a2_value
            
            # 添加产品行 - 从第4行开始
            for i, product in enumerate(order_data.products, start=4):
                # 检查产品是否为字典（从JSON加载的情况）
                if isinstance(product, dict):
                    model = product.get("model", "") or "9806A"
                    name = product.get("name", "")
                    # 注意：模板中数量/件(E列)和规格/KG(F列)是分开的，这里我们简单处理
                    quantity_kg = product.get("quantity", 0)
                    unit_price = product.get("unit_price", 0)
                    amount = product.get("amount", 0)
                else:
                    # 产品为对象的情况
                    model = product.model or "9806A"
                    name = product.name
                    quantity_kg = product.quantity
                    unit_price = product.unit_price
                    amount = product.amount
                
                # 计算件数（这里简单处理，假设每件100KG）
                pieces = int(quantity_kg / 100) if quantity_kg >= 100 else 1
                
                # 填充产品信息到对应单元格
                custom_data[f"A{i}"] = model  # 产品型号
                custom_data[f"D{i}"] = name  # 产品名称
                custom_data[f"E{i}"] = pieces  # 数量/件
                custom_data[f"F{i}"] = 100  # 规格/KG（假设每件100KG）
                # G列是公式，不需要修改
                custom_data[f"H{i}"] = unit_price  # 单价/元
                # I列是公式，不需要修改
            
            # 生成自定义文件名：发货单_公司名称_日期.xlsx
            company_name = order_data.company_name.replace(" ", "")  # 移除空格
            date_filename = today.strftime("%Y%m%d")
            custom_filename = f"发货单_{company_name}_{date_filename}"
            
            # 生成文件
            file_path = tm.use_template(
                template_name="发货单",
                custom_data=custom_data,
                filename=custom_filename
            )
            
            if file_path:
                # 更新状态
                order["state"] = OrderState.COMPLETED.value
                order["completed_time"] = datetime.now().isoformat()
                order["file_path"] = file_path
                self.save_state()
            
            return file_path
            
        except Exception as e:
            print(f"生成发货单失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cancel_order(self, user_id: str) -> bool:
        """取消订单"""
        if user_id in self.active_orders:
            self.active_orders[user_id]["state"] = OrderState.CANCELLED.value
            self.active_orders[user_id]["cancelled_time"] = datetime.now().isoformat()
            self.save_state()
            return True
        return False
    
    def complete_order(self, user_id: str) -> bool:
        """完成订单"""
        if user_id in self.active_orders:
            self.active_orders[user_id]["state"] = OrderState.COMPLETED.value
            self.active_orders[user_id]["completed_time"] = datetime.now().isoformat()
            self.save_state()
            return True
        return False
    
    def clear_order(self, user_id: str) -> bool:
        """清理订单"""
        if user_id in self.active_orders:
            del self.active_orders[user_id]
            self.save_state()
            print(f"已清理用户 {user_id} 的订单")
            return True
        return False
    
    def generate_shipment_order_from_data(self, order_data: 'OrderData') -> Optional[str]:
        """从OrderData对象直接生成发货单（不依赖active_orders）"""
        if not order_data or not order_data.company_name:
            print("订单数据不完整，无法生成发货单")
            return None
        
        try:
            from template_manager import TemplateManager
            
            tm = TemplateManager()
            
            # 准备数据
            today = datetime.now()
            date_str = today.strftime("%Y年%m月%d日")
            order_no = today.strftime("%Y%m%d") + "A"
            
            # 构建 custom_data - 直接映射到Excel单元格
            custom_data = {}
            
            # 更新A2单元格：购货单位信息
            company_field = f"购货单位：{order_data.company_name}"
            contact_field = f"联系人：{order_data.contact_person}"
            date_field = f"{date_str}"
            order_field = f"订单编号：{order_no}"
            
            # 使用合适的字段宽度，确保所有信息都能显示
            field_width = 25  # 增加字段宽度
            company_part = company_field.ljust(field_width)
            contact_part = contact_field.ljust(field_width)
            date_part = date_field.ljust(field_width)
            order_part = order_field.ljust(field_width)
            
            a2_value = company_part + contact_part + date_part + order_part
            custom_data["A2"] = a2_value
            
            # 添加产品行 - 从第4行开始
            for i, product in enumerate(order_data.products, start=4):
                # 检查产品是否为字典
                if isinstance(product, dict):
                    model = product.get("model", "") or "9806A"
                    name = product.get("name", "")
                    quantity = product.get("quantity", 0)  # 数量/件
                    unit_price = product.get("unit_price", 0)  # 单价/元（每KG）
                    spec = product.get("spec", "")  # 规格（每桶KG数）
                    # 从规格中提取KG数
                    kg_match = re.search(r'\d+', spec)
                    kg_per_unit = float(kg_match.group()) if kg_match else 25  # 默认25KG/桶
                else:
                    # 产品为对象的情况
                    model = product.model or "9806A"
                    name = product.name
                    quantity = product.quantity  # 数量/件
                    unit_price = product.unit_price  # 单价/元（每KG）
                    spec = product.spec  # 规格（每桶KG数）
                    # 从规格中提取KG数
                    kg_match = re.search(r'\d+', spec)
                    kg_per_unit = float(kg_match.group()) if kg_match else 25  # 默认25KG/桶
                
                # 计算数量/KG：数量/件 × 规格/KG
                quantity_kg = quantity * kg_per_unit
                
                # 计算金额：数量/KG × 单价/元
                amount = quantity_kg * unit_price
                
                # 填充产品信息到对应单元格
                custom_data[f"A{i}"] = model  # 产品型号
                custom_data[f"D{i}"] = name  # 产品名称
                custom_data[f"E{i}"] = quantity  # 数量/件
                custom_data[f"F{i}"] = spec  # 规格/KG
                custom_data[f"G{i}"] = quantity_kg  # 数量/KG
                custom_data[f"H{i}"] = unit_price  # 单价/元（每KG）
                custom_data[f"I{i}"] = amount  # 金额/元
            
            # 生成自定义文件名
            company_name = order_data.company_name.replace(" ", "")
            date_filename = today.strftime("%Y%m%d")
            custom_filename = f"发货单_{company_name}_{date_filename}"
            
            # 生成文件
            file_path = tm.use_template(
                template_name="发货单",
                custom_data=custom_data,
                filename=custom_filename
            )
            
            if file_path:
                print(f"✅ 发货单已生成: {file_path}")
            
            return file_path
            
        except Exception as e:
            print(f"生成发货单失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_order_status(self, user_id: str) -> Optional[dict]:
        """获取订单状态"""
        if user_id not in self.active_orders:
            return None
        return self.active_orders[user_id]
    
    def get_products_for_company(self, company_name: str) -> dict:
        """根据公司名称从数据库获取产品信息"""
        import sqlite3
        
        products_dict = {}
        
        try:
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 首先获取公司ID
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", (company_name,))
            company = cursor.fetchone()
            
            if not company:
                conn.close()
                return products_dict
            
            company_id = company[0]
            
            # 查询该公司的所有活跃产品
            cursor.execute("""
                SELECT name, model_number, price 
                FROM product_names 
                WHERE purchase_unit_id = ? AND is_active = 1
            """, (company_id,))
            
            products = cursor.fetchall()
            
            # 构建产品字典
            for product in products:
                product_name = product[0]
                model_number = product[1]
                price = product[2]
                
                # 使用产品名称和型号作为键，支持多种匹配方式
                products_dict[product_name] = price
                if model_number:
                    products_dict[model_number] = price
                    products_dict[f"{product_name} {model_number}"] = price
            
            conn.close()
            
        except Exception as e:
            print(f"获取公司产品失败: {e}")
            import traceback
            traceback.print_exc()
        
        return products_dict
    
    def cleanup_old_orders(self, hours: int = 24):
        """清理旧订单（包括已取消和已完成的）"""
        cutoff = datetime.now().timestamp() - hours * 3600
        to_delete = []
        
        for user_id, order in self.active_orders.items():
            start_time = order.get("start_time", "")
            state = order.get("state", "")
            
            # 清理已取消或已完成的旧订单
            if state in [OrderState.CANCELLED.value, OrderState.COMPLETED.value]:
                if start_time:
                    try:
                        order_time = datetime.fromisoformat(start_time)
                        if order_time.timestamp() < cutoff:
                            to_delete.append(user_id)
                    except:
                        pass
        
        for user_id in to_delete:
            del self.active_orders[user_id]
        
        if to_delete:
            self.save_state()
            print(f"已清理 {len(to_delete)} 个旧订单")
        
        return len(to_delete)
    

    # ============ 快捷发货单功能 ============
    
    def process_quick_order(self, user_id: str, message: str) -> dict:
        """
        快捷发货单处理 - 最多2次确认，直接生成
        
        用户发送格式：
        - "蕊芯家私，郭总，PE白底漆100kg，明天送"
        - "瑞星，PE白底漆100kg"
        - "郭总，100kg稀释剂，蕊芯家私"
        
        返回：
        - 如果需要确认：返回确认问题
        - 如果无需确认：直接生成发货单
        """
        print(f"\n{'='*60}")
        print(f"🚀 快捷发货单处理: {message}")
        print(f"{'='*60}")
        
        try:
            # 1. 解析用户输入
            parsed = self._parse_quick_order(message)
            if not parsed:
                return {
                    "action": "RETRY",
                    "message": "无法解析订单信息，请按以下格式发送：\n公司名称，联系人，产品名称数量，发货日期\n\n例如：蕊芯家私，郭总，PE白底漆100kg，明天送"
                }
            
            company_name = parsed.get('company_name', '')
            contact_person = parsed.get('contact_person', '')
            product_name = parsed.get('product_name', '')
            quantity = parsed.get('quantity', 0)
            delivery_date = parsed.get('delivery_date', '')
            
            print(f"📋 解析结果:")
            print(f"  - 公司: {company_name}")
            print(f"  - 联系人: {contact_person}")
            print(f"  - 产品: {product_name} {quantity}kg")
            print(f"  - 日期: {delivery_date}")
            
            # 2. 匹配公司名称
            from company_matcher import match_company_name
            company_match = match_company_name(company_name) if company_name else None
            
            # 3. 准备订单数据
            order_data = OrderData()
            company_need_confirm = False
            product_need_confirm = False
            
            if company_match:
                order_data.company_name = company_match['matched_name']
                order_data.contact_person = company_match.get('contact_person', '') or contact_person
                order_data.contact_phone = company_match.get('contact_phone', '')
                if company_match['similarity'] < 1.0:
                    company_need_confirm = True
            else:
                order_data.company_name = company_name
                order_data.contact_person = contact_person
            
            # 4. 解析产品
            company_products = self.get_products_for_company(order_data.company_name)
            products = self._parse_products(f"{product_name} {quantity}kg", company_products)
            
            if products:
                order_data.products = products
            else:
                # 产品未匹配，添加默认产品 - 使用标准化的产品名称
                standardized_product_name = self._standardize_product_name(product_name)
                order_data.products = [ProductInfo(
                    name=standardized_product_name,
                    quantity=quantity,
                    unit_price=7.5,  # 默认单价
                    amount=quantity * 7.5
                )]
                product_need_confirm = True
            
            # 5. 设置发货日期
            if not delivery_date:
                delivery_date = datetime.now().strftime("%Y-%m-%d")
            order_data.delivery_date = delivery_date
            
            # 6. 确定是否需要确认 - 增强确认条件
            needs_company_confirm = company_need_confirm
            needs_product_confirm = product_need_confirm
            
            # 额外检查：产品名称是否需要标准化确认
            if product_name and not needs_product_confirm:
                # 检查产品名称是否被标准化了
                if len(product_name) < len(order_data.products[0].name) if order_data.products else False:
                    needs_product_confirm = True
                    print(f"🔍 产品名称被标准化: '{product_name}' -> '{order_data.products[0].name}'")
            
            print(f"🔍 确认检查:")
            print(f"  - 公司需要确认: {needs_company_confirm} (相似度: {company_match['similarity'] if company_match else 1.0})")
            print(f"  - 产品需要确认: {needs_product_confirm}")
            
            # 7. 构建确认消息 - 增强产品名称显示
            if needs_company_confirm or needs_product_confirm:
                confirm_msg = "请确认以下信息：\n\n"
                
                if needs_company_confirm:
                    confirm_msg += f"1️⃣ 公司名称：{company_name} → {company_match['matched_name']}\n"
                    confirm_msg += f"   （联系人：{company_match.get('contact_person', '未设置')}）\n\n"
                
                if needs_product_confirm:
                    # 显示原始产品和标准化后的产品
                    original_product = product_name
                    standardized_product = order_data.products[0].name if order_data.products else product_name
                    
                    if original_product != standardized_product:
                        confirm_msg += f"2️⃣ 产品名称：{original_product} → {standardized_product}\n"
                    else:
                        confirm_msg += f"2️⃣ 产品名称：{standardized_product}\n"
                    
                    confirm_msg += f"   数量：{quantity}kg\n"
                    confirm_msg += f"   单价：7.5元/kg\n\n"
                
                confirm_msg += "回复\"是\"确认全部信息，或回复修改内容"
                
                # 保存订单状态
                self.active_orders[user_id] = {
                    "state": OrderState.COLLECTING.value,
                    "user_name": "",
                    "start_time": datetime.now().isoformat(),
                    "data": order_data.to_dict(),
                    "current_step": "QUICK_CONFIRM",
                    "message_count": 1,
                    "company_match": company_match,
                    "product_need_confirm": product_need_confirm,
                    "original_input": message
                }
                self.save_state()
                
                return {
                    "action": "QUICK_CONFIRM",
                    "message": confirm_msg,
                    "data": order_data.to_dict()
                }
            
            # 8. 无需确认，直接生成发货单
            print(f"✅ 无需确认，直接生成发货单")
            return self._generate_shipment_direct(user_id, order_data)
            
        except Exception as e:
            print(f"❌ 快捷订单处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "action": "RETRY",
                "message": f"处理失败: {str(e)}\n请重新发送订单信息"
            }
    
    def _parse_quick_order(self, message: str) -> dict:
        """
        解析快捷订单消息
        
        支持格式：
        - "公司，联系人，产品 数量kg，日期"
        - "公司，产品 数量kg"
        - "联系人，公司，产品 数量kg，日期"
        - "产品 数量kg，公司  日期"  # 新增：产品数量公司日期格式
        """
        result = {}
        
        # 清理消息 - 预处理，移除无关的问候语和礼貌用语
        msg = message.strip()
        
        # 预处理：移除常见的问候语和礼貌用语
        original_msg = msg
        
        # 简单清理方法
        msg = re.sub(r'^(能不能|能不能够|能否|可以|能否)(帮我|给我)?', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(麻烦|劳驾|请)(帮我|给我)?', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'^(我想|我想要|我需要)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(能帮我|可以帮我|能否帮我|能不能帮我)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(有没有)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'^(给我)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'^(请)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(帮我|给我)?(打个|做个|生成|制作)(个)?', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(打一下|打印)(个)?', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(做个|生成|制作)(个)?', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'(个)?(发货单|送货单)', '', msg, flags=re.IGNORECASE).strip()
        msg = re.sub(r'[？?。]$', '', msg).strip()  # 移除结尾的标点
        msg = re.sub(r'^(好的|行|没问题|可以|能|能行)$', '', msg, flags=re.IGNORECASE).strip()  # 移除单独的回答
        
        # 如果消息太短，说明可能是问候语，返回空解析
        if len(msg) < 5:
            return {'delivery_date': '', 'quantity': 0, 'product_name': '', 'company_name': '', 'contact_person': ''}
        
        print(f"🔧 预处理后消息: {msg}")
        
        # 特殊处理：如果预处理后还是有问题，尝试更激进的清理
        if len(msg) > 20 and ('?' in msg or '？' in msg):
            # 对于过长的消息，尝试更激进的清理
            msg = re.sub(r'[？?].*$', '', msg).strip()  # 移除问号后所有内容
            msg = re.sub(r'(给我)?(打个|做个|生成|制作).*$', '', msg, flags=re.IGNORECASE).strip()  # 移除动词短语后的内容
            msg = re.sub(r'.*(发货单|送货单)', '', msg, flags=re.IGNORECASE).strip()  # 移除发货单相关后内容
            print(f"🔧 激进清理后消息: {msg}")
        
        # 解析日期
        date_patterns = [
            (r'今天', datetime.now().strftime("%Y-%m-%d")),
            (r'明天', (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")),
            (r'后天', (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")),
            (r'(\d{4}-\d{2}-\d{2})', None),  # YYYY-MM-DD格式
            (r'(\d{4}年\d{1,2}月\d{1,2}日)', None),  # YYYY年MM月DD日格式
        ]
        
        delivery_date = ""
        for pattern, date_str in date_patterns:
            match = re.search(pattern, msg)
            if match:
                if date_str:
                    delivery_date = date_str
                    msg = re.sub(pattern, '', msg).strip()
                else:
                    delivery_date = match.group(1)
                    msg = re.sub(pattern, '', msg).strip()
                break
        
        result['delivery_date'] = delivery_date
        
        # 解析数量（kg）
        quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|k g|千克|公斤)'
        quantity_match = re.search(quantity_pattern, msg, re.IGNORECASE)
        
        quantity = 0
        product_name = ""
        company_name = ""
        contact_person = ""
        
        if quantity_match:
            quantity = float(quantity_match.group(1))
            before_quantity = msg[:quantity_match.start()].strip()
            after_quantity = msg[quantity_match.end():].strip()
            
            # 清理标点符号
            before_quantity = before_quantity.rstrip('，,').rstrip('的').strip()
            after_quantity = after_quantity.lstrip('，,').strip()
            
            # 特殊处理：产品+数量+公司的格式
            # 检查是否包含"产品名称，数量kg，公司名称"的模式
            if before_quantity and after_quantity:
                # 将产品和公司分离
                # 模式：产品名称在前，公司名称在后
                parts = re.split(r'[，,]', before_quantity)
                if len(parts) >= 1:
                    product_name = parts[0].strip()
                
                # 剩余部分作为公司名称
                remaining = ' '.join(parts[1:]).strip()
                if remaining:
                    company_name = remaining
                elif after_quantity:
                    company_name = after_quantity
                
                result['quantity'] = quantity
                result['product_name'] = product_name
                result['company_name'] = company_name
                result['contact_person'] = contact_person
            else:
                # 标准处理：产品名称在数量之前
                product_name = before_quantity
                
                # 解析产品前面的内容（公司+联系人）
                parts_before = re.split(r'[，,]', before_quantity)
                if len(parts_before) >= 2:
                    company_name = parts_before[0].strip()
                    contact_person = parts_before[1].strip()
                    product_name = ' '.join(parts_before[2:]).strip() if len(parts_before) > 2 else parts_before[-1].strip()
                elif len(parts_before) == 1:
                    company_name = parts_before[0].strip()
                
                result['quantity'] = quantity
                result['product_name'] = product_name
                result['company_name'] = company_name
                result['contact_person'] = contact_person
        else:
            # 没有找到数量，尝试其他解析方式
            parts = re.split(r'[，,]', msg)
            if len(parts) >= 2:
                # 假设格式是：公司，联系人，产品
                company_name = parts[0].strip()
                if len(parts) >= 3:
                    contact_person = parts[1].strip()
                    product_name = parts[2].strip()
                else:
                    product_name = parts[-1].strip()
                
                result['company_name'] = company_name
                result['contact_person'] = contact_person
                result['product_name'] = product_name
        
        # 清理数据
        for key in ['company_name', 'contact_person', 'product_name']:
            if key in result and result[key]:
                result[key] = result[key].rstrip('的').rstrip('。').rstrip('.').strip()
        
        # 产品名称映射和标准化
        if result.get('product_name'):
            result['product_name'] = self._standardize_product_name(result['product_name'])
        
        print(f"📋 解析结果: {result}")
        return result
    
    def _standardize_product_name(self, product_name: str) -> str:
        """
        标准化产品名称，添加完整的产品全称
        """
        product_name = product_name.strip()
        
        # 产品名称映射规则
        product_mappings = {
            # PE白底漆系列
            "pe白底漆": "PE白底稀释剂",
            "PE白底漆": "PE白底稀释剂", 
            "pe白底稀释剂": "PE白底稀释剂",
            "PE白底稀释剂": "PE白底稀释剂",
            "白底漆": "PE白底稀释剂",
            "白底稀释剂": "PE白底稀释剂",
            
            # 稀释剂系列
            "稀释剂": "稀释剂",
            "稀释剂100": "稀释剂",
            "pe稀释剂": "PE白底稀释剂",
            
            # 其他常见产品
            "面漆": "面漆",
            "面漆100": "面漆",
        }
        
        # 检查是否匹配映射规则
        for key, full_name in product_mappings.items():
            if key in product_name.lower():
                print(f"🔄 产品名称映射: '{product_name}' -> '{full_name}'")
                return full_name
        
        # 如果没有匹配到映射，返回原始产品名称（但进行清理）
        cleaned_name = product_name.replace(" ", "").replace("  ", "")
        return cleaned_name
    
    def confirm_quick_order(self, user_id: str, answer: str) -> dict:
        """
        确认快捷订单 - 用户回复"是"后直接生成发货单
        """
        print(f"\n{'='*60}")
        print(f"✅ 确认快捷订单: {answer}")
        print(f"{'='*60}")
        
        # 检查是否有待确认的订单
        if user_id not in self.active_orders:
            return {
                "action": "NONE",
                "message": "没有待确认的订单"
            }
        
        order = self.active_orders[user_id]
        if order.get('current_step') != 'QUICK_CONFIRM':
            return {
                "action": "NONE",
                "message": "订单状态不正确"
            }
        
        # 检查用户回复
        if answer.strip().lower() in ['是', '是的', '对', '确认', 'yes', 'y', '1']:
            # 用户确认，生成发货单
            order_data = OrderData(**order['data'])
            return self._generate_shipment_direct(user_id, order_data)
        else:
            # 用户要修改，重新解析
            return self.process_quick_order(user_id, answer)
    
    def _generate_shipment_direct(self, user_id: str, order_data: OrderData) -> dict:
        """
        直接生成发货单并返回结果
        """
        print(f"\n🚀 直接生成发货单")
        print(f"  公司: {order_data.company_name}")
        print(f"  联系人: {order_data.contact_person}")
        print(f"  产品: {[p.name if hasattr(p, 'name') else p['name'] for p in order_data.products]}")
        print(f"  日期: {order_data.delivery_date}")
        
        # 先保存订单数据到active_orders
        self.active_orders[user_id] = {
            "state": OrderState.COLLECTING.value,
            "user_name": "",
            "start_time": datetime.now().isoformat(),
            "data": order_data.to_dict(),
            "current_step": "GENERATING",
            "message_count": 1
        }
        self.save_state()
        
        # 生成发货单
        file_path = self.generate_shipment_order(user_id)
        
        if file_path:
            # 清理订单状态
            if user_id in self.active_orders:
                del self.active_orders[user_id]
                self.save_state()
            
            # 构建产品列表文本
            products_text = ""
            for p in order_data.products:
                name = p.name if hasattr(p, 'name') else p.get('name', '')
                qty = p.quantity if hasattr(p, 'quantity') else p.get('quantity', 0)
                price = p.unit_price if hasattr(p, 'unit_price') else p.get('unit_price', 0)
                amount = p.amount if hasattr(p, 'amount') else p.get('amount', 0)
                products_text += f"  • {name} {qty}kg × {price}元 = {amount}元\n"
            
            total_amount = sum(
                p.amount if hasattr(p, 'amount') else p.get('amount', 0) 
                for p in order_data.products
            )
            
            return {
                "action": "COMPLETE",
                "message": f"✅ 发货单已生成！\n\n📦 发货单信息：\n公司：{order_data.company_name}\n联系人：{order_data.contact_person}\n日期：{order_data.delivery_date}\n\n📝 产品清单：\n{products_text}\n💰 总金额：{total_amount}元\n\n📄 文件：{file_path}",
                "order_data": order_data.to_dict(),
                "file_path": file_path
            }
        else:
            return {
                "action": "RETRY",
                "message": "生成发货单失败，请重试"
            }


# 测试
if __name__ == "__main__":
    workflow = OrderWorkflow()
    
    # 测试触发
    print("测试触发关键词检测:")
    print(f"'需要发货单' -> {workflow.is_trigger_keyword('需要发货单')}")
    print(f"'开发票' -> {workflow.is_trigger_keyword('开发票')}")
    print(f"'在吗' -> {workflow.is_trigger_keyword('在吗')}")
    
    # 测试开始订单
    print("\n测试开始订单:")
    result = workflow.start_order("test_user", "测试用户")
    print(f"第一个问题: {result['question']}")
    
    # 测试回答
    print("\n测试回答:")
    result = workflow.process_message("test_user", "ABC科技有限公司")
    print(f"动作: {result['action']}")
    if result['action'] == 'CONTINUE':
        print(f"下一步问题: {result['question']}")
        
        result = workflow.process_message("test_user", "张三")
        print(f"动作: {result['action']}")
        
        result = workflow.process_message("test_user", "A型产品 500KG")
        print(f"动作: {result['action']}")
        
        if result['action'] == 'COMPLETE':
            print("信息完整，可以生成发货单！")
            print(f"订单数据: {result['order_data']}")
    
    # 清理
    if "test_user" in workflow.active_orders:
        del workflow.active_orders["test_user"]
        workflow.save_state()
