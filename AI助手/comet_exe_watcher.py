#!/usr/bin/env python3
"""
科密CM500 EXE程序监控服务
监控科密扫描程序生成的图像文件，自动进行OCR识别
"""

import os
import time
import logging
import requests
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 配置
COMET_EXE_PATH = r"C:\Program Files\Comet Scanner_V2.0(1.1)\comet.exe"
WATCH_FOLDER = r"D:\Images"  # 监控文件夹（科密扫描输出目录）
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']

# 确保监控文件夹存在
os.makedirs(WATCH_FOLDER, exist_ok=True)

class CometImageHandler(FileSystemEventHandler):
    """科密图像文件处理器"""
    
    def __init__(self):
        self.processed_files = set()
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        
        # 检查文件扩展名
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return
        
        # 避免重复处理
        if filepath in self.processed_files:
            return
        
        logger.info(f"📁 检测到新文件: {filename}")
        
        # 等待文件写入完成
        time.sleep(1)
        
        # 立即关闭科密程序（用户要求监控到图片就关闭）
        self.close_comet_exe()
        
        # 处理文件
        self.process_image(filepath)
    
    def process_image(self, filepath):
        """处理图像文件"""
        try:
            logger.info(f"🔄 正在处理: {filepath}")
            
            # 发送到主服务进行OCR识别
            with open(filepath, 'rb') as f:
                files = {'image': f}
                response = requests.post(
                    'http://127.0.0.1:5000/api/ocr/process-image',
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"✅ OCR识别成功: {result.get('result', {})}")
                    # 可以在这里添加更多处理逻辑，比如自动填充表单
                else:
                    logger.warning(f"⚠️ OCR识别失败: {result.get('message')}")
            else:
                logger.error(f"❌ 请求失败: {response.status_code}")
            
            # 标记为已处理
            self.processed_files.add(filepath)
            
        except Exception as e:
            logger.error(f"❌ 处理图像失败: {e}")
    
    def close_comet_exe(self):
        """关闭科密扫描程序"""
        try:
            import subprocess
            # 查找并关闭科密程序进程
            result = subprocess.run(
                ['taskkill', '/F', '/IM', 'comet.exe'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("✅ 已关闭科密扫描程序")
            else:
                logger.debug("科密程序未运行或已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭科密程序失败: {e}")

@app.route('/')
def index():
    """服务首页"""
    return jsonify({
        "service": "科密CM500 EXE监控服务",
        "version": "1.0.0",
        "status": "running",
        "watch_folder": WATCH_FOLDER,
        "comet_exe": COMET_EXE_PATH,
        "comet_exists": os.path.exists(COMET_EXE_PATH)
    })

@app.route('/api/start-comet', methods=['POST'])
def start_comet_exe():
    """启动科密扫描程序"""
    try:
        if not os.path.exists(COMET_EXE_PATH):
            return jsonify({
                "success": False,
                "error": "科密程序不存在"
            })
        
        # 清理之前的图片
        clear_previous_images()
        
        # 启动科密程序
        import subprocess
        subprocess.Popen([COMET_EXE_PATH], shell=True)
        
        logger.info("🚀 已启动科密扫描程序")
        
        return jsonify({
            "success": True,
            "message": "科密程序已启动"
        })
        
    except Exception as e:
        logger.error(f"❌ 启动科密程序失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/watch-folder')
def get_watch_folder():
    """获取监控文件夹信息"""
    try:
        files = []
        for f in os.listdir(WATCH_FOLDER):
            filepath = os.path.join(WATCH_FOLDER, f)
            if os.path.isfile(filepath):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append({
                        "name": f,
                        "path": filepath,
                        "size": os.path.getsize(filepath),
                        "modified": datetime.fromtimestamp(
                            os.path.getmtime(filepath)
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return jsonify({
            "success": True,
            "folder": WATCH_FOLDER,
            "files": files
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/image')
def get_image():
    """获取图像文件"""
    try:
        filepath = request.args.get('path')
        
        if not filepath:
            return jsonify({"success": False, "error": "未指定文件路径"}), 400
        
        # 安全检查：确保文件在监控文件夹内
        if not filepath.startswith(WATCH_FOLDER):
            return jsonify({"success": False, "error": "非法路径"}), 403
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "文件不存在"}), 404
        
        # 返回图像文件
        return send_file(filepath, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"❌ 读取图像失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def clear_previous_images():
    """清理监控文件夹中的旧图片"""
    try:
        if not os.path.exists(WATCH_FOLDER):
            return
        
        deleted_count = 0
        for filename in os.listdir(WATCH_FOLDER):
            filepath = os.path.join(WATCH_FOLDER, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ 无法删除文件 {filename}: {e}")
        
        if deleted_count > 0:
            logger.info(f"🗑️ 已清理 {deleted_count} 张旧图片")
        else:
            logger.info("📁 文件夹已清空或没有旧图片")
            
    except Exception as e:
        logger.error(f"❌ 清理图片失败: {e}")

def start_watcher():
    """启动文件监控"""
    event_handler = CometImageHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()
    
    logger.info(f"👁️ 开始监控文件夹: {WATCH_FOLDER}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == '__main__':
    import threading
    
    # 在后台启动文件监控
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    
    # 启动Flask服务
    logger.info("🚀 启动科密EXE监控服务，端口: 5003")
    app.run(host='127.0.0.1', port=5003, debug=False)
