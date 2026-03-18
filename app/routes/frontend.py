"""
前端页面路由

提供前端页面的路由，包括首页、控制台等。
"""

import os
from flask import Blueprint, send_from_directory, render_template, jsonify

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
def index():
    """首页 → 使用 HTML 版本的 AI 助手控制台"""
    return render_template('ai_assistant_console.html')


@frontend_bp.route('/assets/<path:path>')
def serve_vue_assets(path):
    """提供 Vue 构建的 assets 静态资源"""
    vue_dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'vue-dist')
    return send_from_directory(vue_dist_dir, 'assets/' + path)


@frontend_bp.route('/vite.svg')
def serve_vite_svg():
    """提供 Vite favicon"""
    vue_dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'vue-dist')
    return send_from_directory(vue_dist_dir, 'vite.svg', mimetype='image/svg+xml')


@frontend_bp.route('/static/<path:path>')
def serve_static(path):
    """提供 Vue 应用的静态 CSS 文件"""
    vue_dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'vue-dist')
    return send_from_directory(os.path.join(vue_dist_dir, 'static'), path)


@frontend_bp.route('/products-test')
def products_test():
    """产品管理测试页面（HTML 版本）"""
    return render_template('products_test.html')


@frontend_bp.route('/console')
def console():
    """控制台页面"""
    return render_template('ai_assistant_console.html')


@frontend_bp.route('/favicon.ico')
def favicon():
    """提供 favicon，避免 404 错误"""
    # 返回一个简单的 1x1 透明 GIF，避免浏览器报 404
    from flask import Response
    import base64
    
    # 1x1 透明 GIF 的 base64 编码
    transparent_gif = base64.b64decode(
        'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    )
    return Response(transparent_gif, mimetype='image/gif')


@frontend_bp.route('/outputs/<path:filename>')
def serve_outputs(filename):
    """提供发货单输出文件的下载"""
    try:
        # 获取 AI 助手目录（注意：目录名是"AI助手"不是"AI 助手"）
        # 从 XCAGI/app/routes 向上两级到 XCAGI，再向上一级到 FHD
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # 尝试两个可能的目录名
        possible_dirs = [
            os.path.join(base_dir, 'AI助手'),  # 无空格版本
            os.path.join(base_dir, 'AI 助手'),  # 有空格版本
        ]
        
        outputs_dir = None
        for dir_path in possible_dirs:
            if os.path.exists(os.path.join(dir_path, 'outputs')):
                outputs_dir = os.path.join(dir_path, 'outputs')
                break
        
        if not outputs_dir:
            return jsonify({
                "success": False,
                "message": "输出目录不存在"
            }), 404
        
        # 检查文件是否存在
        file_path = os.path.join(outputs_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": f"文件不存在：{filename}"
            }), 404
        
        # 发送文件
        return send_from_directory(outputs_dir, filename, as_attachment=True)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"下载失败：{str(e)}"
        }), 500
