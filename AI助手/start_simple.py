#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Flask应用启动脚本
"""

import sys
import os

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    try:
        print("🚀 启动简化的Flask应用...")
        
        # 导入Flask应用
        from app_api import app
        
        print("✅ Flask应用加载成功")
        print("🌐 启动服务器...")
        
        # 启动Flask应用
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=False,  # 关闭调试模式以避免重启问题
            use_reloader=False,  # 禁用自动重载器
            threaded=True
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 启动错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ 服务器启动成功！")
    else:
        print("❌ 服务器启动失败")
        sys.exit(1)