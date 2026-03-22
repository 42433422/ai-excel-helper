# -*- coding: utf-8 -*-
"""
闭环工具：打开指定联系人对话框并用剪贴板发送消息。
用法: python send_wechat_message.py "联系人昵称或备注" "要发送的消息"
示例: python send_wechat_message.py "文件传输助手" "你好"
依赖: 微信 PC 已打开，与本机同机。需 pywin32、pyautogui，可选 easyocr、opencv。
"""
import sys
import time

def main():
    if len(sys.argv) < 3:
        print("用法: python send_wechat_message.py \"联系人昵称或备注\" \"要发送的消息\"")
        print("示例: python send_wechat_message.py \"文件传输助手\" \"你好\"")
        sys.exit(1)
    contact_name = sys.argv[1].strip()
    message = sys.argv[2].strip()
    if not contact_name or not message:
        print("联系人和消息不能为空")
        sys.exit(1)
    try:
        from wechat_cv_send import open_chat_by_cv, send_to_current_chat_by_cv
    except ImportError as e:
        print("未找到 wechat_cv_send，请确保在 wechat_cv 目录下运行:", e)
        sys.exit(1)
    open_result = open_chat_by_cv(contact_name, use_ocr=True)
    if open_result.get("status") != "success":
        print("打开对话框失败:", open_result.get("message", "未知"))
        sys.exit(1)
    time.sleep(0.8)
    send_result = send_to_current_chat_by_cv(message, delay=0.8, use_ocr=True)
    if send_result.get("status") == "success":
        print("已发送:", message[:80] + ("…" if len(message) > 80 else ""))
    else:
        print("发送失败:", send_result.get("message", "未知"))
        sys.exit(1)

if __name__ == "__main__":
    main()
