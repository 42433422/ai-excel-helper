#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音输入前端应用 - 5000端口
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import logging
from datetime import datetime

# 配置上传和输出目录
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

# 创建目录（如果不存在）
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 日志配置
logging.basicConfig(
    filename="logs/voice_frontend.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 启用CORS
CORS(app)

# 配置应用
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# 主页路由 - 语音输入前端
@app.route("/")
def index():
    """语音输入前端主页"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"无法读取语音输入页面: {e}")
        return '''
        <div style="text-align: center; padding: 50px;">
            <h1>语音输入页面加载失败</h1>
            <p>错误: ''' + str(e) + '''</p>
        </div>
        '''

# 语音优化API
@app.route('/api/optimize_voice', methods=['POST'])
def optimize_voice():
    """语音识别优化API"""
    try:
        data = request.get_json()
        voice_text = data.get('voice_text', '').strip()
        
        if not voice_text:
            return jsonify({
                "success": False,
                "message": "语音文本不能为空"
            }), 400
        
        # 使用AI解析器优化语音识别结果
        try:
            from ai_augmented_parser import AIAugmentedShipmentParser
            parser = AIAugmentedShipmentParser()
            
            # 尝试解析语音文本
            result = parser.parse(voice_text, number_mode=True)
            
            if result.is_valid():
                # 如果解析成功，返回优化的文本
                optimized_text = voice_text
                # 如果有产品信息，可以在返回中添加解析结果
                return jsonify({
                    "success": True,
                    "optimized_text": optimized_text,
                    "ai_analysis": result.to_dict(),
                    "message": "语音识别成功"
                })
            else:
                # 解析失败，返回原始文本
                return jsonify({
                    "success": True,
                    "optimized_text": voice_text,
                    "ai_analysis": None,
                    "message": "语音识别成功（AI解析未能完全识别）"
                })
                
        except Exception as ai_error:
            logger.warning(f"AI优化失败: {ai_error}")
            # AI优化失败，返回原始文本
            return jsonify({
                "success": True,
                "optimized_text": voice_text,
                "ai_analysis": None,
                "message": "语音识别成功"
            })
        
    except Exception as e:
        logger.error(f"语音优化失败: {e}")
        return jsonify({
            "success": False,
            "message": f"语音优化失败: {str(e)}"
        }), 500

# 测试端点
@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "语音输入前端测试正常"})

# 打印机API
@app.route('/api/printers', methods=['GET'])
def get_printers():
    """获取打印机列表"""
    return jsonify({
        "printers": [],
        "message": "暂无可用打印机"
    })

# 生成发货单API
@app.route('/api/generate', methods=['POST'])
def generate_shipment():
    """生成发货单"""
    try:
        data = request.get_json()
        
        # 这里应该调用发货单生成逻辑
        # 但现在只是返回成功消息
        return jsonify({
            "success": True,
            "message": "发货单生成功能正在开发中",
            "document": {
                "filename": "test_shipment.xlsx"
            }
        })
        
    except Exception as e:
        logger.error(f"生成发货单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"生成发货单失败: {str(e)}",
            "document": {
                "filename": ""
            }
        }), 500

# 下载API
@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """下载文件"""
    return jsonify({
        "success": False,
        "message": "下载功能暂未实现"
    })

if __name__ == "__main__":
    print("=== 语音输入前端启动 ===")
    print("服务地址: http://0.0.0.0:5000")
    print("语音输入前端: http://0.0.0.0:5000/")
    print("语音优化API: http://0.0.0.0:5000/api/optimize_voice")
    print("=========================")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)