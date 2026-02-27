#!/usr/bin/env python3
"""微信AI自动回复 - OCR版（改进版）"""

import warnings
warnings.filterwarnings('ignore')

import sys
import time
import pyautogui
from pathlib import Path

# 禁用PyAutoGUI安全机制（允许在后台运行）
pyautogui.FAILSAFE = False

sys.path.insert(0, str(Path(__file__).parent))

from wechat_window import WeChatWindowDetector
from wechat_reader_final_v2 import FinalReader
from wechat_automator import WeChatAutomator
from ai_conversation_engine import ConversationEngine

class WeChatOCRBot:
    """微信AI机器人 - OCR版"""
    
    def __init__(self):
        print("=" * 70)
        print("🤖 微信AI自动回复（OCR版）")
        print("=" * 70)
        
        # 初始化组件
        self.detector = WeChatWindowDetector()
        self.reader = FinalReader()
        self.automator = WeChatAutomator()
        self.ai = ConversationEngine()
        
        # 状态
        self.last_message_hash = None
        self.check_interval = 3  # 秒
        
        print("✅ 组件初始化完成")
        print("=" * 70)
    
    def extract_user_messages(self, messages):
        """从所有消息中提取用户发的消息（is_self=False）"""
        user_messages = []
        for msg in messages:
            if not msg.is_self:
                content = msg.content.strip()
                if content and len(content) > 1:
                    user_messages.append({
                        'content': content,
                        'timestamp': msg.timestamp
                    })
        return user_messages
    
    def detect_new_message(self, messages):
        """检测是否有新的用户消息"""
        user_msgs = self.extract_user_messages(messages)
        
        if not user_msgs:
            return None
        
        # 获取最后一条用户消息
        last_msg = user_msgs[-1]
        msg_hash = hash(last_msg['content'])
        
        # 检查是否是新消息
        if msg_hash != self.last_message_hash:
            self.last_message_hash = msg_hash
            return last_msg['content']
        
        return None
    
    def smart_reply(self, message_content, window, messages):
        """智能回复 - 调用AI处理订单并创建发货单"""
        if not message_content or len(message_content.strip()) < 2:
            return None
        
        cleaned_msg = message_content.strip()
        
        print(f"\n📨 消息: {cleaned_msg}")
        
        try:
            # 调用AI处理消息
            print("🔄 调用AI处理消息...")
            response = self.ai.get_response(
                user_id='wechat_user',
                message=cleaned_msg,
                context={'source': 'ocr_bot', 'messages_count': len(messages)}
            )
            
            print(f"📋 AI响应: {response}")
            
            if not response.get('success'):
                print(f"❌ AI错误: {response.get('error')}")
                return None
            
            reply_text = response.get('text', '')
            action = response.get('action')
            data = response.get('data', {})
            
            print(f"📝 回复文本: {reply_text}")
            print(f"🔧 动作: {action}")
            print(f"📊 数据: {data}")
            
            # 如果是订单处理，获取回复
            if action == 'process_order':
                # 订单已解析，等待用户确认
                print(f"💬 AI: 订单已解析")
                # 打印订单详情
                if data.get('order'):
                    order = data.get('order')
                    print(f"📦 订单详情: 公司={order.get('company_name')}, 联系人={order.get('contact_person')}, 产品数={len(order.get('products', []))}")
                return reply_text
            
            return reply_text
            
        except Exception as e:
            print(f"❌ 处理异常: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def run(self):
        """运行机器人"""
        print("\n🚀 机器人启动")
        print("特点：OCR识别消息，AI理解并回复")
        print("按 Ctrl+C 停止")
        print("-" * 70)
        
        consecutive_errors = 0
        
        try:
            while True:
                try:
                    # 1. 检测微信窗口
                    window = self.detector.find_wechat_window()
                    if not window:
                        time.sleep(self.check_interval)
                        continue
                    
                    # 2. OCR识别消息
                    messages = self.reader.read(window)
                    
                    if messages:
                        # 3. 检测新消息
                        new_msg = self.detect_new_message(messages)
                        
                        if new_msg:
                            # 4. 生成回复（传入window和messages）
                            reply = self.smart_reply(new_msg, window, messages)
                            
                            if reply:
                                print(f"💬 AI回复: {reply[:80]}...")
                                
                                # 5. 发送回复
                                result = self.automator.send_message(window, reply)
                                
                                if result.success:
                                    print("✅ 回复已发送！\n")
                                else:
                                    print(f"❌ 发送失败: {result.message}\n")
                            else:
                                print("⚠️ 无有效回复\n")
                        else:
                            # 没有新消息，短时间休眠
                            time.sleep(1)
                    else:
                        # 没有识别到消息
                        time.sleep(1)
                    
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"⚠️ 错误: {e}")
                    
                    if consecutive_errors > 5:
                        print("连续错误，重置状态...")
                        self.last_message_hash = None
                        consecutive_errors = 0
                    
                    time.sleep(2)
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n⏹️ 机器人已停止")
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def main():
    """主函数"""
    bot = WeChatOCRBot()
    bot.run()


if __name__ == '__main__':
    main()
