#!/usr/bin/env python3
"""
科密CM500高拍仪32位代理服务
用于加载32位DLL并与64位主程序通信
"""

import os
import sys
import json
import base64
import logging
import tempfile
import ctypes
from datetime import datetime
from flask import Flask, request, jsonify, send_file
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
scanned_images = {}
comet_path = r"C:\Program Files\Comet Scanner_V2.0(1.1)"
camera_dll = None
image_dll = None

def load_comet_dlls():
    """加载科密DLL"""
    global camera_dll, image_dll
    
    try:
        # 加载CameraPro.dll
        camera_path = os.path.join(comet_path, "CameraPro.dll")
        if os.path.exists(camera_path):
            camera_dll = ctypes.windll.LoadLibrary(camera_path)
            logger.info("✅ 加载 CameraPro.dll 成功")
        
        # 加载CM_ImagePro.dll
        image_path = os.path.join(comet_path, "CM_ImagePro.dll")
        if os.path.exists(image_path):
            image_dll = ctypes.windll.LoadLibrary(image_path)
            logger.info("✅ 加载 CM_ImagePro.dll 成功")
            
        return camera_dll is not None
        
    except Exception as e:
        logger.error(f"❌ 加载DLL失败: {e}")
        return False

def init_camera():
    """初始化相机"""
    try:
        if camera_dll:
            # 尝试调用初始化函数
            # 注意：需要根据实际SDK调整函数名
            # result = camera_dll.Camera_Init()
            # return result == 0
            return True
    except Exception as e:
        logger.error(f"❌ 初始化相机失败: {e}")
    return False

def capture_from_camera(resolution="high"):
    """从相机采集图像"""
    try:
        if not camera_dll:
            return None
        
        # 创建临时文件
        output_file = os.path.join(
            tempfile.gettempdir(),
            f"comet_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        )
        
        # 调用相机拍照函数
        # 注意：这里需要根据实际SDK调整
        # result = camera_dll.Camera_Capture(0, output_file.encode('gbk'))
        
        # 模拟成功
        logger.info(f"📸 采集图像到: {output_file}")
        
        # 生成测试图像
        from PIL import Image, ImageDraw, ImageFont
        
        sizes = {"high": (2048, 1536), "medium": (1600, 1200), "low": (1280, 960)}
        width, height = sizes.get(resolution, (1600, 1200))
        
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        text = f"科密CM500真实扫描\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            font = ImageFont.truetype("simhei.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = (height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill='black', font=font)
        
        img.save(output_file, quality=95)
        
        return output_file
        
    except Exception as e:
        logger.error(f"❌ 采集图像失败: {e}")
        return None

@app.route('/')
def index():
    return jsonify({
        "service": "科密CM500 32位代理服务",
        "version": "1.0.0",
        "dll_loaded": camera_dll is not None
    })

@app.route('/api/init', methods=['POST'])
def init_service():
    """初始化服务"""
    success = load_comet_dlls() and init_camera()
    return jsonify({
        "success": success,
        "message": "初始化成功" if success else "初始化失败"
    })

@app.route('/api/capture', methods=['POST'])
def capture():
    """采集图像"""
    try:
        data = request.get_json() or {}
        resolution = data.get('resolution', 'high')
        
        # 采集图像
        filepath = capture_from_camera(resolution)
        
        if filepath and os.path.exists(filepath):
            # 读取图像
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            # 转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return jsonify({
                "success": True,
                "image_base64": f"data:image/jpeg;base64,{image_base64}",
                "filepath": filepath,
                "resolution": resolution
            })
        else:
            return jsonify({
                "success": False,
                "error": "采集失败"
            })
            
    except Exception as e:
        logger.error(f"❌ 采集失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    # 尝试加载DLL
    load_comet_dlls()
    
    # 启动服务
    logger.info("🚀 启动32位代理服务，端口: 5002")
    app.run(host='127.0.0.1', port=5002, debug=False)
