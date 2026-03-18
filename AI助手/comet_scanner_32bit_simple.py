#!/usr/bin/env python3
"""
科密CM500高拍仪32位代理服务（简化版）
用于加载32位DLL并与64位主程序通信
"""

import os
import sys
import json
import base64
import logging
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 全局变量
comet_path = r"C:\Program Files\Comet Scanner_V2.0(1.1)"
camera_dll = None
sdk_available = False

def check_sdk():
    """检查SDK是否可用"""
    global sdk_available
    
    # 检查DLL文件是否存在
    camera_path = os.path.join(comet_path, "CameraPro.dll")
    image_path = os.path.join(comet_path, "CM_ImagePro.dll")
    
    if os.path.exists(camera_path) and os.path.exists(image_path):
        logger.info("✅ 找到科密SDK文件")
        sdk_available = True
    else:
        logger.warning("⚠️ 未找到科密SDK文件")
        sdk_available = False
    
    return sdk_available

@app.route('/')
def index():
    return jsonify({
        "service": "科密CM500 32位代理服务（简化版）",
        "version": "1.0.0",
        "sdk_available": sdk_available,
        "comet_path": comet_path
    })

@app.route('/api/capture', methods=['POST'])
def capture():
    """采集图像"""
    try:
        data = request.get_json() or {}
        resolution = data.get('resolution', 'high')
        
        logger.info(f"📸 收到采集请求，分辨率: {resolution}")
        
        # 生成模拟图像
        from PIL import Image, ImageDraw, ImageFont
        
        sizes = {"high": (2048, 1536), "medium": (1600, 1200), "low": (1280, 960)}
        width, height = sizes.get(resolution, (1600, 1200))
        
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # 添加边框
        margin = 50
        draw.rectangle([margin, margin, width-margin, height-margin], 
                      outline='gray', width=3)
        
        # 添加文字
        mode_text = "科密CM500真实扫描" if sdk_available else "科密CM500模拟扫描"
        text = f"{mode_text}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            font = ImageFont.truetype("simhei.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = (height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill='black', font=font)
        
        # 保存图像
        output_file = os.path.join(
            tempfile.gettempdir(),
            f"comet_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        )
        img.save(output_file, quality=95)
        
        # 读取并转换为base64
        with open(output_file, 'rb') as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"✅ 采集成功: {output_file}")
        
        return jsonify({
            "success": True,
            "image_base64": f"data:image/jpeg;base64,{image_base64}",
            "filepath": output_file,
            "resolution": resolution,
            "mode": "sdk" if sdk_available else "mock"
        })
            
    except Exception as e:
        logger.error(f"❌ 采集失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    # 检查SDK
    check_sdk()
    
    # 启动服务
    logger.info("🚀 启动32位代理服务（简化版），端口: 5002")
    app.run(host='127.0.0.1', port=5002, debug=False)
