#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版Flask应用，只包含发货单功能
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import logging
from datetime import datetime

# 配置上传和输出目录
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
TEMPLATE_FOLDER = "templates"

# 创建目录（如果不存在）
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs(os.path.join(TEMPLATE_FOLDER, "base"), exist_ok=True)
os.makedirs(os.path.join(TEMPLATE_FOLDER, "user"), exist_ok=True)

# 日志配置
logging.basicConfig(
    filename="logs/app.log",
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
app.config["TEMPLATE_FOLDER"] = TEMPLATE_FOLDER

# 导入发货单API蓝图
from shipment_api import shipment_bp
app.register_blueprint(shipment_bp)

# 调试：打印注册的蓝图
logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")
logger.info(f"Shipment blueprint URL prefix: {app.blueprints.get('shipment', {}).url_prefix if 'shipment' in app.blueprints else 'Not found'}")

# 测试端点
@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Test endpoint working"})

@app.route("/test_shipment", methods=["GET"])  
def test_shipment():
    return jsonify({"message": "Test shipment endpoint working"})

# 主页路由 - 智能发货单生成器
@app.route("/")
def index():
    """主页 - 智能发货单生成器"""
    return render_template("create_shipment_enhanced.html")

# 创建发货单页面 - 智能文字解析
@app.route("/create")
def create_shipment_page():
    """智能文字解析生成发货单"""
    return render_template("create_shipment_enhanced.html")

# 工作流页面（备用）
@app.route("/workflow")
def workflow_page():
    """传统工作流页面"""
    return render_template("shipment_workflow.html")

# 测试页面
@app.route("/test")
def test_page():
    """测试页面"""
    return "测试页面"

if __name__ == "__main__":
    print("=== 简化版Flask应用启动 ===")
    print("服务地址: http://0.0.0.0:5000")
    print("新建发货单: http://0.0.0.0:5000/create")
    print("工作流页面: http://0.0.0.0:5000/shipment-workflow")
    print("API地址: http://0.0.0.0:5000/api/shipment")
    print("=========================")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
