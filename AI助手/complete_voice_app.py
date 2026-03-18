#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的语音输入前端应用 - 5000端口，使用现有完整API
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import logging
from datetime import datetime

# 导入完整的发货单API
from shipment_api import shipment_bp

# 配置上传和输出目录
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

# 创建目录（如果不存在）
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 日志配置
logging.basicConfig(
    filename="logs/complete_voice.log",
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

# 注册完整的发货单API蓝图
app.register_blueprint(shipment_bp)

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

# 语音优化API - 使用现有的智能解析功能
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
        
        # 直接调用现有的智能解析API
        try:
            from ai_augmented_parser import AIAugmentedShipmentParser
            parser = AIAugmentedShipmentParser()
            
            # 使用编号模式进行解析
            result = parser.parse(voice_text, number_mode=True)
            
            if result.is_valid():
                return jsonify({
                    "success": True,
                    "optimized_text": voice_text,
                    "ai_analysis": result.to_dict(),
                    "message": "语音识别成功"
                })
            else:
                return jsonify({
                    "success": True,
                    "optimized_text": voice_text,
                    "ai_analysis": None,
                    "message": "语音识别成功（AI解析未能完全识别）"
                })
                
        except Exception as ai_error:
            logger.warning(f"AI优化失败: {ai_error}")
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

# 生成发货单API - 前端调用的统一接口
@app.route('/api/generate', methods=['POST'])
def generate_shipment():
    """生成发货单"""
    try:
        data = request.get_json()
        order_text = data.get('order_text', '')
        template_name = data.get('template_name', 'default')
        custom_mode = data.get('custom_mode', False)
        number_mode = data.get('number_mode', False)
        auto_print = data.get('auto_print', False)
        excel_sync = data.get('excel_sync', False)
        
        if not order_text:
            return jsonify({
                "success": False,
                "message": "订单文本不能为空"
            }), 400
        
        # 使用现有的发货单API生成器
        try:
            from shipment_document import DocumentAPIGenerator
            generator = DocumentAPIGenerator()
            
            # 调用parse_and_generate方法，传递编号模式参数
            result = generator.parse_and_generate(
                order_text, 
                custom_mode=custom_mode, 
                number_mode=number_mode
            )
            
            if result.get("success"):
                return jsonify(result)
            else:
                return jsonify({
                    "success": False,
                    "message": result.get("message", "生成失败")
                }), 500
                
        except Exception as gen_error:
            logger.error(f"生成发货单失败: {gen_error}")
            return jsonify({
                "success": False,
                "message": f"生成发货单失败: {str(gen_error)}"
            }), 500
        
    except Exception as e:
        logger.error(f"生成发货单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"生成发货单失败: {str(e)}"
        }), 500

# 打印机相关API
@app.route('/api/printers', methods=['GET'])
def get_printers():
    """获取打印机列表"""
    return jsonify({
        "printers": [],
        "success": True,
        "message": "暂无可用打印机"
    })

@app.route('/api/print_status', methods=['GET'])
def get_print_status():
    """获取打印机状态"""
    return jsonify({
        "status": "ready",
        "success": True,
        "message": "打印机就绪"
    })

# 下载API
@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """下载文件"""
    try:
        import os
        from flask import send_from_directory
        
        # 安全检查
        filename = os.path.basename(filename)
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "message": "文件不存在"
            }), 404
        
        return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({
            "success": False,
            "message": f"下载失败: {str(e)}"
        }), 500

if __name__ == "__main__":
    print("=== 完整语音输入前端启动 ===")
    print("服务地址: http://0.0.0.0:5000")
    print("语音输入前端: http://0.0.0.0:5000/")
    print("完整发货单API: http://0.0.0.0:5000/api/shipment/*")
    print("语音优化API: http://0.0.0.0:5000/api/optimize_voice")
    print("=========================")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)