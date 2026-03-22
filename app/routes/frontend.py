"""
前端页面路由

提供前端页面的路由，包括首页、控制台等。
"""

import os

from flask import Blueprint, jsonify, render_template, send_from_directory

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/test-buttons')
def test_buttons():
    """按钮布局测试页面"""
    return render_template('test-buttons.html')


@frontend_bp.route('/health')
def health():
    """健康检查端点，用于 Docker/K8s 健康检查"""
    return jsonify({
        "status": "healthy",
        "service": "xcagi-backend"
    })


@frontend_bp.route('/')
def index():
    """首页 → 优先使用 Vue 版本的 AI 助手控制台，缺失时回退到 HTML 版本"""
    from app.utils.path_utils import get_base_dir

    base_dir = get_base_dir()
    vue_index = os.path.join(base_dir, 'templates', 'vue-dist', 'index.html')

    # 优先返回 Vue 构建产物
    if os.path.exists(vue_index):
        return send_from_directory(
            os.path.join(base_dir, 'templates', 'vue-dist'),
            'index.html',
            mimetype='text/html'
        )

    # 回退到旧的 HTML 模板，避免在部署窗口期白屏
    return render_template('ai_assistant_console.html')


@frontend_bp.route('/assets/<path:path>')
def serve_vue_assets(path):
    """提供 Vue 构建的 assets 静态资源"""
    from app.utils.path_utils import get_base_dir

    vue_dist_dir = os.path.join(get_base_dir(), 'templates', 'vue-dist')
    assets_dir = os.path.join(vue_dist_dir, 'assets')

    # 先尝试在 assets 子目录下查找
    asset_path = os.path.join(assets_dir, path)
    if os.path.exists(asset_path) and not os.path.isdir(asset_path):
        return send_from_directory(assets_dir, path)

    # 兼容部分构建产物直接位于 vue_dist 根目录
    direct_path = os.path.join(vue_dist_dir, path)
    if os.path.exists(direct_path) and not os.path.isdir(direct_path):
        return send_from_directory(vue_dist_dir, path)

    return jsonify({
        "success": False,
        "message": f"资源不存在：{path}"
    }), 404


@frontend_bp.route('/vite.svg')
def serve_vite_svg():
    """提供 Vite favicon"""
    from app.utils.path_utils import get_base_dir

    vue_dist_dir = os.path.join(get_base_dir(), 'templates', 'vue-dist')
    svg_path = os.path.join(vue_dist_dir, 'vite.svg')

    if os.path.exists(svg_path):
        return send_from_directory(
            vue_dist_dir,
            'vite.svg',
            mimetype='image/svg+xml'
        )

    return jsonify({
        "success": False,
        "message": "vite.svg 不存在"
    }), 404


@frontend_bp.route('/static/<path:path>')
def serve_static(path):
    """提供 Vue 应用的静态 CSS/JS 等静态文件"""
    from app.utils.path_utils import get_base_dir

    vue_dist_dir = os.path.join(get_base_dir(), 'templates', 'vue-dist')
    static_dir = os.path.join(vue_dist_dir, 'static')

    static_path = os.path.join(static_dir, path)
    if os.path.exists(static_path) and not os.path.isdir(static_path):
        return send_from_directory(static_dir, path)

    return jsonify({
        "success": False,
        "message": f"静态资源不存在：{path}"
    }), 404


@frontend_bp.route('/products-test')
def products_test():
    """产品管理测试页面（HTML 版本）"""
    return render_template('products_test.html')


@frontend_bp.route('/console')
def console():
    """控制台页面 → 与首页保持一致，优先使用 Vue，缺失时回退到 HTML 版本"""
    return index()


@frontend_bp.route('/favicon.ico')
def favicon():
    """提供 favicon，避免 404 错误"""
    # 返回一个简单的 1x1 透明 GIF，避免浏览器报 404
    import base64

    from flask import Response

    # 1x1 透明 GIF 的 base64 编码
    transparent_gif = base64.b64decode(
        'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    )
    return Response(transparent_gif, mimetype='image/gif')


@frontend_bp.route('/outputs/<path:filename>')
def serve_outputs(filename):
    """提供发货单输出文件的下载"""
    try:
        from app.utils.path_utils import get_app_data_dir, get_base_dir, get_resource_path

        # 1) 优先从发货单真实输出目录下载（shipment_outputs）
        shipment_outputs_dir = os.path.join(get_app_data_dir(), "shipment_outputs")
        if os.path.isdir(shipment_outputs_dir):
            outputs_dir = shipment_outputs_dir
        else:
            # 2) 回退到资源目录（历史兼容）
            outputs_dir = get_resource_path("ai_assistant", "outputs")
            if not os.path.isdir(outputs_dir):
                # 兼容期：XCAGI 内旧目录
                outputs_dir = os.path.join(get_base_dir(), "AI助手", "outputs")

        if not os.path.isdir(outputs_dir):
            return jsonify({
                "success": False,
                "message": f"输出目录不存在: {outputs_dir}"
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


@frontend_bp.route('/<path:fallback>')
def vue_history_fallback(fallback):
    """
    Vue Router History Mode 兼容：
    所有未匹配的路由都返回 index.html，让 Vue Router 处理前端路由。
    仅排除已知的静态资源路径和 API 路径。
    """
    excluded_prefixes = (
        'api/',
        'assets/',
        'static/',
        'outputs/',
        'uploads/',
        'fonts/',
        'images/',
        'js/',
        'css/',
        'favicon',
    )
    if any(fallback.startswith(p) for p in excluded_prefixes):
        return jsonify({
            "success": False,
            "message": f"资源不存在：/{fallback}"
        }), 404

    from app.utils.path_utils import get_base_dir

    vue_dist_dir = os.path.join(get_base_dir(), 'templates', 'vue-dist')
    vue_index = os.path.join(vue_dist_dir, 'index.html')

    if os.path.exists(vue_index):
        return send_from_directory(vue_dist_dir, 'index.html', mimetype='text/html')

    return jsonify({
        "success": False,
        "message": f"页面不存在：/{fallback}"
    }), 404
