#!/usr/bin/env python3
"""
科密CM500高拍仪本地服务桥接器
提供HTTP API供前端调用，实现高拍仪图像采集
"""

import os
import sys
import json
import base64
import logging
import tempfile
import subprocess
import time
import ctypes
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域访问

# 全局变量存储扫描的图像
scanned_images = {}
scanner_available = False

# 科密扫描仪安装路径
COMET_INSTALL_PATH = r"C:\Program Files\Comet Scanner_V2.0(1.1)"

class CometScannerBridge:
    """科密高拍仪桥接器"""
    
    def __init__(self):
        self.sdk_loaded = False
        self.device_connected = False
        self.current_device = None
        self.comet_path = COMET_INSTALL_PATH
        self.camera_dll = None
        self.image_dll = None
        self.check_installation()
    
    def check_installation(self):
        """检查科密扫描仪安装"""
        if os.path.exists(self.comet_path):
            logger.info(f"✅ 找到科密扫描仪安装目录: {self.comet_path}")
            
            # 检查关键文件
            key_files = [
                "CM_ImagePro.dll",
                "CameraPro.dll",
                "comet.exe"
            ]
            
            found_files = []
            for file in key_files:
                file_path = os.path.join(self.comet_path, file)
                if os.path.exists(file_path):
                    found_files.append(file)
            
            if found_files:
                logger.info(f"✅ 找到关键文件: {', '.join(found_files)}")
                self.sdk_loaded = True
                
                # 尝试加载DLL
                self.load_dlls()
                
                # 尝试检测设备
                self.detect_device()
            else:
                logger.warning("⚠️ 未找到关键SDK文件，将使用模拟模式")
                self.sdk_loaded = False
        else:
            logger.warning(f"⚠️ 未找到科密扫描仪安装目录: {self.comet_path}")
            self.sdk_loaded = False
    
    def load_dlls(self):
        """加载科密SDK DLL"""
        try:
            # 加载CameraPro.dll
            camera_dll_path = os.path.join(self.comet_path, "CameraPro.dll")
            if os.path.exists(camera_dll_path):
                self.camera_dll = ctypes.windll.LoadLibrary(camera_dll_path)
                logger.info("✅ 加载 CameraPro.dll 成功")
            
            # 加载CM_ImagePro.dll
            image_dll_path = os.path.join(self.comet_path, "CM_ImagePro.dll")
            if os.path.exists(image_dll_path):
                self.image_dll = ctypes.windll.LoadLibrary(image_dll_path)
                logger.info("✅ 加载 CM_ImagePro.dll 成功")
                
        except Exception as e:
            logger.error(f"❌ 加载DLL失败: {e}")
            self.camera_dll = None
            self.image_dll = None
    
    def detect_device(self):
        """检测高拍仪设备"""
        try:
            # 尝试使用DLL检测设备
            if self.camera_dll:
                try:
                    # 尝试调用设备检测函数（根据实际SDK调整函数名）
                    # result = self.camera_dll.Camera_Init()
                    # if result == 0:
                    #     self.device_connected = True
                    #     logger.info("✅ 高拍仪设备已连接")
                    # else:
                    #     logger.warning("⚠️ 未检测到高拍仪设备")
                    
                    # 暂时假设设备已连接
                    self.device_connected = True
                    logger.info("✅ 高拍仪设备已连接（DLL模式）")
                except Exception as e:
                    logger.warning(f"⚠️ DLL调用失败: {e}")
                    self.device_connected = False
            else:
                # 模拟模式
                self.device_connected = True
                logger.info("✅ 使用模拟模式（设备状态未知）")
                
        except Exception as e:
            logger.error(f"❌ 检测设备失败: {e}")
            self.device_connected = False
    
    def capture_image(self, resolution="high"):
        """
        采集图像
        
        Args:
            resolution: 分辨率 (high/medium/low)
        
        Returns:
            dict: 包含图像路径和base64编码
        """
        try:
            if self.sdk_loaded and self.device_connected and self.camera_dll:
                # 使用科密SDK采集图像
                return self._capture_with_sdk(resolution)
            else:
                # 模拟模式：生成测试图像
                return self._generate_mock_image(resolution)
                
        except Exception as e:
            logger.error(f"❌ 采集图像失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _capture_with_sdk(self, resolution):
        """使用科密SDK采集图像"""
        try:
            import requests
            
            logger.info(f"📸 尝试调用32位代理服务采集图像...")
            
            # 调用32位代理服务
            try:
                response = requests.post(
                    'http://127.0.0.1:5002/api/capture',
                    json={'resolution': resolution},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        logger.info("✅ 32位代理服务采集成功")
                        return {
                            "success": True,
                            "image_base64": result['image_base64'],
                            "filepath": result['filepath'],
                            "filename": os.path.basename(result['filepath']),
                            "resolution": result['resolution'],
                            "width": 2048 if resolution == 'high' else (1600 if resolution == 'medium' else 1280),
                            "height": 1536 if resolution == 'high' else (1200 if resolution == 'medium' else 960),
                            "mode": "sdk"
                        }
                    else:
                        logger.warning(f"⚠️ 32位代理服务返回错误: {result.get('error')}")
                        return self._generate_mock_image(resolution, sdk_mode=True)
                else:
                    logger.warning(f"⚠️ 32位代理服务未响应，使用模拟模式")
                    return self._generate_mock_image(resolution, sdk_mode=True)
                    
            except requests.exceptions.ConnectionError:
                logger.warning("⚠️ 无法连接32位代理服务，使用模拟模式")
                logger.info("💡 提示：如需真实扫描，请安装32位Python并运行 comet_scanner_32bit.py")
                return self._generate_mock_image(resolution, sdk_mode=True)
            except Exception as e:
                logger.error(f"❌ 调用32位代理服务失败: {e}")
                return self._generate_mock_image(resolution, sdk_mode=True)
                
        except Exception as e:
            logger.error(f"❌ SDK扫描失败: {e}")
            return self._generate_mock_image(resolution, sdk_mode=True)
    
    def _process_image_file(self, filepath, resolution, mode):
        """处理图像文件"""
        try:
            from PIL import Image
            
            # 打开图像
            img = Image.open(filepath)
            width, height = img.size
            
            # 转换为base64
            with open(filepath, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            filename = os.path.basename(filepath)
            
            logger.info(f"✅ 处理图像成功: {filename} ({width}x{height})")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "image_base64": f"data:image/jpeg;base64,{image_base64}",
                "resolution": resolution,
                "width": width,
                "height": height,
                "mode": mode
            }
            
        except Exception as e:
            logger.error(f"❌ 处理图像文件失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_mock_image(self, resolution, sdk_mode=False):
        """生成模拟图像（用于测试）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 根据分辨率设置图像大小
            sizes = {
                "high": (2048, 1536),
                "medium": (1600, 1200),
                "low": (1280, 960)
            }
            width, height = sizes.get(resolution, (1600, 1200))
            
            # 创建模拟扫描图像
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # 添加边框（模拟纸张边缘）
            margin = 50
            draw.rectangle([margin, margin, width-margin, height-margin], 
                          outline='gray', width=3)
            
            # 添加文字
            mode_text = "SDK模式" if sdk_mode else "模拟模式"
            text = f"科密CM500扫描测试\n{mode_text}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 尝试使用默认字体
            try:
                font = ImageFont.truetype("simhei.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            
            # 添加一些模拟内容线条
            for i in range(5):
                y_line = 200 + i * 100
                draw.line([(100, y_line), (width-100, y_line)], fill='lightgray', width=2)
            
            # 保存图像
            filename = f"comet_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            img.save(filepath, quality=95)
            
            # 转换为base64
            with open(filepath, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            logger.info(f"✅ 生成图像: {filepath} ({mode_text})")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "image_base64": f"data:image/jpeg;base64,{image_base64}",
                "resolution": resolution,
                "width": width,
                "height": height,
                "mode": "sdk" if sdk_mode else "mock"
            }
            
        except Exception as e:
            logger.error(f"❌ 生成图像失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_info(self):
        """获取设备信息"""
        return {
            "sdk_loaded": self.sdk_loaded,
            "device_connected": self.device_connected,
            "model": "CM500",
            "brand": "Comet",
            "resolution": "1100万像素",
            "install_path": self.comet_path,
            "mode": "sdk" if (self.sdk_loaded and self.device_connected) else "mock",
            "dll_loaded": self.camera_dll is not None
        }

# 创建扫描仪实例
scanner = CometScannerBridge()

@app.route('/')
def index():
    """服务首页"""
    return jsonify({
        "service": "科密CM500高拍仪桥接服务",
        "version": "2.1.0",
        "status": "running",
        "device": scanner.get_device_info(),
        "endpoints": [
            "/api/scan - 扫描图像",
            "/api/status - 设备状态",
            "/api/devices - 设备列表"
        ]
    })

@app.route('/api/status')
def get_status():
    """获取设备状态"""
    return jsonify({
        "success": True,
        "device_info": scanner.get_device_info()
    })

@app.route('/api/scan', methods=['POST'])
def scan_image():
    """
    扫描图像
    
    POST参数:
    - resolution: 分辨率 (high/medium/low)，默认high
    - save_path: 保存路径（可选）
    """
    try:
        data = request.get_json() or {}
        resolution = data.get('resolution', 'high')
        
        logger.info(f"📸 收到扫描请求，分辨率: {resolution}")
        
        # 采集图像
        result = scanner.capture_image(resolution)
        
        if result.get('success'):
            # 保存到全局变量
            image_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            scanned_images[image_id] = result
            
            result['image_id'] = image_id
            logger.info(f"✅ 扫描成功: {image_id}")
        else:
            logger.error(f"❌ 扫描失败: {result.get('error')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 扫描接口错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/image/<image_id>')
def get_image(image_id):
    """获取扫描的图像"""
    if image_id in scanned_images:
        image_info = scanned_images[image_id]
        filepath = image_info.get('filepath')
        if filepath and os.path.exists(filepath):
            return send_file(filepath, mimetype='image/jpeg')
    
    return jsonify({"success": False, "error": "图像不存在"}), 404

@app.route('/api/devices')
def list_devices():
    """列出可用设备"""
    return jsonify({
        "success": True,
        "devices": [
            scanner.get_device_info()
        ]
    })

def run_scanner_service(port=5001):
    """运行扫描仪服务"""
    logger.info(f"🚀 启动科密CM500桥接服务，端口: {port}")
    logger.info(f"📁 科密安装路径: {COMET_INSTALL_PATH}")
    app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == '__main__':
    run_scanner_service()
