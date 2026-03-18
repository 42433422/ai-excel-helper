"""
工具管理路由

提供工具列表、分类管理等 API。
"""

from flask import Blueprint, jsonify, request
from flasgger import swag_from
import logging

logger = logging.getLogger(__name__)
tools_bp = Blueprint('tools', __name__)


def _parse_order_text(order_text: str) -> dict:
    """
    解析订单文本，提取单位名和产品信息
    
    支持的格式：
    - "发货单七彩乐园 1 桶 9803 规格 12"
    - "送货单公司名称 2 箱产品 A 规格 100"
    - 等
    
    Returns:
        {
            "success": True/False,
            "unit_name": "单位名称",
            "products": [
                {
                    "name": "产品名称",
                    "quantity_tins": 桶数，
                    "tin_spec": 每桶规格，
                    "model_number": "型号"
                }
            ],
            "message": "错误消息（如果有）"
        }
    """
    try:
        import re
        
        # 去掉开头的"发货单"、"送货单"、"出货单"（使用字符串方法更可靠）
        text = order_text.strip()
        for prefix in ['发货单', '送货单', '出货单']:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        
        if not text:
            return {
                "success": False,
                "message": "订单文本格式不正确，缺少内容"
            }
        
        # 简单解析：按"桶"、"规格"分割
        patterns = [
            # 模式 1: "七彩乐园 1 桶 9803 规格 12"
            r'^([^\d]+?)(\d+)\s*桶\s*(\d+)\s*规格\s*(\d+(?:\.\d+)?)',
            # 模式 2: "七彩乐园 1 桶 9803"
            r'^([^\d]+?)(\d+)\s*桶\s*(\d+)',
            # 模式 3: "七彩乐园 2 箱产品 A"
            r'^([^\d]+?)(\d+)\s*(箱 | 件)\s*(.+)',
            # 模式 4: "公司 A 3 公斤材料 B"
            r'^([^\d]+?)(\d+(?:\.\d+)?)\s*(公斤|kg)\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    unit_name = groups[0].strip()
                    
                    # 判断是否是数字开头（型号）还是单位
                    if groups[2] in ['箱', '件', '公斤', 'kg']:
                        # 模式 3 或 4
                        try:
                            quantity = float(groups[1])
                        except:
                            quantity = 1
                        
                        product_name = groups[3].strip() if len(groups) > 3 else "产品"
                        
                        result = {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": product_name,
                                "tin_spec": 10.0,  # 默认规格
                            }]
                        }
                        
                        if '公斤' in groups[2] or 'kg' in groups[2]:
                            result["products"][0]["quantity_kg"] = quantity
                        else:
                            result["products"][0]["quantity_tins"] = int(quantity) if groups[2] in ['箱', '件'] else quantity
                        
                        return result
                    else:
                        # 模式 1 或 2: "七彩乐园 1 桶 9803 规格 12"
                        try:
                            quantity = int(groups[1])
                            model_number = groups[2]
                            spec = float(groups[3]) if len(groups) > 3 else 10.0
                        except:
                            return {
                                "success": False,
                                "message": "解析数字失败"
                            }
                        
                        # name 留空，让后续数据库匹配来填充正确的产品名称
                        return {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": "",  # 留空，等待数据库匹配
                                "model_number": model_number,
                                "quantity_tins": quantity,
                                "tin_spec": spec,
                            }]
                        }
        
        # 如果所有模式都不匹配，尝试简单分割
        parts = text.split()
        if len(parts) >= 2:
            unit_name = parts[0].strip()
            return {
                "success": True,
                "unit_name": unit_name,
                "products": [{
                    "name": " ".join(parts[1:]),
                    "quantity_tins": 1,
                    "tin_spec": 10.0,
                }]
            }
        
        return {
            "success": False,
            "message": f"无法解析订单文本：{order_text}，请使用格式：发货单 + 单位名 + 数量 + 桶 + 型号 + 规格"
        }
        
    except Exception as e:
        logger.error(f"解析订单文本失败：{e}")
        return {
            "success": False,
            "message": f"解析失败：{str(e)}"
        }


@tools_bp.route('/api/database/backup', methods=['POST'])
@swag_from({
    'summary': '备份数据库',
    'description': '备份 SQLite 数据库到备份目录',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'file_path': {'type': 'string', 'description': '备份文件路径'},
                    'filename': {'type': 'string', 'description': '备份文件名'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def backup_database():
    """备份数据库"""
    try:
        from app.services.database_service import get_database_service
        db_service = get_database_service()
        result = db_service.backup_database()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"备份数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/restore', methods=['POST'])
@swag_from({
    'summary': '恢复数据库',
    'description': '从备份文件恢复数据库',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['backup_file'],
                'properties': {
                    'backup_file': {'type': 'string', 'description': '备份文件路径或文件名'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def restore_database():
    """恢复数据库"""
    try:
        from app.services.database_service import get_database_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        backup_file = data.get('backup_file')
        if not backup_file:
            return jsonify({"success": False, "message": "缺少参数：backup_file"}), 400
        
        db_service = get_database_service()
        result = db_service.restore_database(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"恢复数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backups', methods=['GET'])
@swag_from({
    'summary': '列出备份文件',
    'description': '列出所有数据库备份文件',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'backups': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'filename': {'type': 'string'},
                                'file_path': {'type': 'string'},
                                'size': {'type': 'integer'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    },
                    'count': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def list_database_backups():
    """列出备份文件"""
    try:
        from app.services.database_service import get_database_service
        db_service = get_database_service()
        result = db_service.list_backups()
        return jsonify(result)
    except Exception as e:
        logger.error(f"列出备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backup/<path:backup_file>', methods=['DELETE'])
@swag_from({
    'summary': '删除备份文件',
    'description': '删除指定的数据库备份文件',
    'parameters': [
        {
            'name': 'backup_file',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '备份文件名'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def delete_database_backup(backup_file):
    """删除备份文件"""
    try:
        from app.services.database_service import get_database_service
        db_service = get_database_service()
        result = db_service.delete_backup(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"删除备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['GET'])
@swag_from({
    'summary': '获取开机自启配置',
    'description': '获取当前应用的开机自启状态',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                            'app_path': {'type': 'string'},
                            'startup_path': {'type': 'string'},
                            'platform': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_startup_config():
    """获取开机自启配置"""
    try:
        from app.services.system_service import get_system_service
        system_service = get_system_service()
        result = system_service.get_startup_config()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取开机自启配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['POST'])
@swag_from({
    'summary': '启用开机自启',
    'description': '启用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'command': {'type': 'string', 'description': '启动命令'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def enable_startup():
    """启用开机自启"""
    try:
        from app.services.system_service import get_system_service
        system_service = get_system_service()
        result = system_service.enable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"启用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['DELETE'])
@swag_from({
    'summary': '禁用开机自启',
    'description': '禁用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def disable_startup():
    """禁用开机自启"""
    try:
        from app.services.system_service import get_system_service
        system_service = get_system_service()
        result = system_service.disable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"禁用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/info', methods=['GET'])
@swag_from({
    'summary': '获取系统信息',
    'description': '获取系统信息，包括操作系统、Python 版本等',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'platform': {'type': 'string'},
                            'platform_version': {'type': 'string'},
                            'python_version': {'type': 'string'},
                            'app_path': {'type': 'string'},
                            'working_directory': {'type': 'string'},
                            'executable': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_system_info():
    """获取系统信息"""
    try:
        from app.services.system_service import get_system_service
        system_service = get_system_service()
        result = system_service.get_system_info()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取系统信息失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['GET'])
@swag_from({
    'summary': '获取打印机配置',
    'description': '获取可用的打印机列表和默认打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printers': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'default_printer': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_printer_config():
    """获取打印机配置"""
    try:
        from app.services.system_service import get_system_service
        system_service = get_system_service()
        result = system_service.get_printer_config()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取打印机配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['POST'])
@swag_from({
    'summary': '设置默认打印机',
    'description': '设置系统默认打印机',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['printer_name'],
                'properties': {
                    'printer_name': {'type': 'string', 'description': '打印机名称'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def set_default_printer():
    """设置默认打印机"""
    try:
        from app.services.system_service import get_system_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        printer_name = data.get('printer_name')
        if not printer_name:
            return jsonify({"success": False, "message": "缺少参数：printer_name"}), 400
        
        system_service = get_system_service()
        result = system_service.set_default_printer(printer_name)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"设置默认打印机失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/db-tools', methods=['GET'])
def get_db_tools_compat():
    """兼容旧版前端的 /api/db-tools 接口"""
    return get_tools_list()


@tools_bp.route('/api/tools', methods=['GET'])
@swag_from({
    'summary': '获取工具列表',
    'description': '获取可用工具列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'tools': {'type': 'array'}
                }
            }
        }
    }
})
def get_tools_list():
    """获取可用工具列表"""
    try:
        tools = [
            {"id": "products", "name": "产品管理", "description": "查看、搜索产品与型号，管理产品库", "category": "products",
             "actions": [{"name": "查看产品", "description": "查看所有产品列表"}, {"name": "添加产品", "description": "添加新产品"}, {"name": "搜索产品", "description": "按型号或名称搜索"}]},
            {"id": "customers", "name": "客户/购买单位", "description": "查看、编辑客户列表，或上传 Excel 更新购买单位", "category": "customers",
             "actions": [{"name": "查看客户", "description": "查看客户/购买单位列表"}, {"name": "添加客户", "description": "添加新客户"}, {"name": "搜索客户", "description": "搜索客户"}]},
            {"id": "orders", "name": "出货单", "description": "查看出货订单、创建订单、导出 Excel", "category": "orders",
             "actions": [{"name": "查看订单", "description": "查看出货订单列表"}, {"name": "创建订单", "description": "创建新订单"}, {"name": "导出订单", "description": "导出订单到 Excel"}]},
            {"id": "shipment_generate", "name": "生成发货单", "description": "按订单文本或「打印+订单」生成发货单，支持编号模式与商标导出", "category": "orders",
             "actions": [{"name": "生成发货单", "description": "输入订单内容直接生成发货单"}]},
            {"id": "print", "name": "标签打印", "description": "打印产品标签或导出商标到本地下载", "category": "print",
             "actions": [{"name": "打印标签", "description": "打印商标导出目录下标签"}, {"name": "批量打印", "description": "批量打印多个标签"}, {"name": "查看标签", "description": "查看可用标签列表"}]},
            {"id": "materials", "name": "原材料仓库", "description": "查看原材料库存与预警", "category": "materials",
             "actions": [{"name": "查看库存", "description": "查看原材料库存"}, {"name": "预警设置", "description": "设置库存预警阈值"}]},
            {"id": "database", "name": "数据库管理", "description": "数据库备份与恢复", "category": "database",
             "actions": [{"name": "备份", "description": "备份数据库"}, {"name": "恢复", "description": "从备份恢复"}]},
            {"id": "system", "name": "系统设置", "description": "开机自启、打印配置等", "category": "system",
             "actions": [{"name": "开机启动", "description": "设置开机自启动"}, {"name": "打印设置", "description": "配置打印机"}]},
            {"id": "shipment_template", "name": "发货单模板", "description": "保存/展示模板、可编辑词条与字段映射、介绍抬头与金额计算", "category": "orders",
             "actions": [{"name": "保存模板", "description": "将指定 xlsx 保存为发货单模板.xlsx"}, {"name": "展示模板", "description": "展示可编辑词条与字段映射"}, {"name": "介绍功能", "description": "介绍抬头、业务字段与价格计算逻辑"}]},
            {"id": "excel_decompose", "name": "Excel 模板分解", "description": "自动分解 Excel 结构，提取表头、可编辑词条与金额字段", "category": "excel",
             "actions": [{"name": "分解模板", "description": "输出表头、词条、样例行与金额字段"}]},
            {"id": "ocr", "name": "图片 OCR", "description": "识别图片中的文字", "category": "ocr",
             "actions": [{"name": "文字识别", "description": "上传图片识别文字"}, {"name": "结构化提取", "description": "从图片中提取结构化数据"}]},
            {"id": "wechat", "name": "微信任务", "description": "扫描微信消息，识别订单和发货单", "category": "wechat",
             "actions": [{"name": "扫描消息", "description": "扫描微信消息"}, {"name": "查看任务", "description": "查看待处理任务"}]},
        ]
        return jsonify({"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tool-categories', methods=['GET'])
@swag_from({
    'summary': '获取工具分类',
    'description': '获取工具分类列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'categories': {'type': 'array'}
                }
            }
        }
    }
})
def get_tool_categories():
    """获取工具分类列表"""
    try:
        categories = [
            {"id": 1, "category_name": "产品管理", "category_key": "products", "description": "产品与型号管理", "icon": "📦", "sort_order": 1, "is_active": True},
            {"id": 2, "category_name": "客户/购买单位", "category_key": "customers", "description": "客户信息管理", "icon": "👥", "sort_order": 2, "is_active": True},
            {"id": 3, "category_name": "出货单", "category_key": "orders", "description": "订单与发货单管理", "icon": "📋", "sort_order": 3, "is_active": True},
            {"id": 4, "category_name": "标签打印", "category_key": "print", "description": "标签打印管理", "icon": "🖨️", "sort_order": 4, "is_active": True},
            {"id": 5, "category_name": "原材料仓库", "category_key": "materials", "description": "原材料库存管理", "icon": "🏭", "sort_order": 5, "is_active": True},
            {"id": 6, "category_name": "Excel 处理", "category_key": "excel", "description": "Excel 模板与数据处理", "icon": "📊", "sort_order": 6, "is_active": True},
            {"id": 7, "category_name": "图片 OCR", "category_key": "ocr", "description": "图片文字识别", "icon": "🔍", "sort_order": 7, "is_active": True},
            {"id": 8, "category_name": "数据库管理", "category_key": "database", "description": "数据库备份与恢复", "icon": "💾", "sort_order": 8, "is_active": True},
            {"id": 9, "category_name": "系统设置", "category_key": "system", "description": "系统配置与管理", "icon": "⚙️", "sort_order": 9, "is_active": True},
            {"id": 10, "category_name": "微信任务", "category_key": "wechat", "description": "微信消息处理", "icon": "💬", "sort_order": 10, "is_active": True},
        ]
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        logger.error(f"获取工具分类失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tools/execute', methods=['POST'])
@swag_from({
    'summary': '执行工具',
    'description': '执行工具操作，支持 database 和 system 工具的实际操作\n\n支持的工具和操作：\n- database: backup, restore, list, delete\n- system: get_startup_config, enable_startup, disable_startup, get_system_info, get_printer_config, set_default_printer\n- 其他工具主要返回重定向 URL',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'tool_id': {'type': 'string', 'description': '工具 ID', 'enum': ['products', 'customers', 'orders', 'database', 'system', 'print', 'materials', 'ocr', 'wechat', 'excel_decompose', 'shipment_template', 'shipment_generate']},
                    'action': {'type': 'string', 'description': '操作类型', 'enum': ['view', 'backup', 'restore', 'list', 'delete', 'get_startup_config', 'enable_startup', 'disable_startup', 'get_system_info', 'get_printer_config', 'set_default_printer']},
                    'params': {
                        'type': 'object',
                        'description': '操作参数',
                        'properties': {
                            'backup_file': {'type': 'string', 'description': '备份文件路径（用于 restore 和 delete 操作）'},
                            'printer_name': {'type': 'string', 'description': '打印机名称（用于 set_default_printer 操作）'},
                            'order_text': {'type': 'string', 'description': '订单文本（用于 shipment_generate 操作）'}
                        }
                    }
                },
                'required': ['tool_id', 'action']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'result': {'type': 'object'},
                    'message': {'type': 'string'},
                    'redirect': {'type': 'string', 'description': '重定向 URL（仅部分工具）'},
                    'data': {'type': 'object', 'description': '返回数据（system 工具）'},
                    'backups': {'type': 'array', 'description': '备份列表（database list 操作）'},
                    'count': {'type': 'integer', 'description': '数量（database list 操作）'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def execute_tool():
    """执行工具操作"""
    try:
        from flask import request
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "未收到数据"}), 400
        
        tool_id = data.get('tool_id')
        action = data.get('action', 'view')
        params = data.get('params', {})
        
        if tool_id == 'products':
            from app.routes.products import products_bp
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=products"})
            return jsonify({"success": True, "message": "产品管理"})
        
        elif tool_id == 'customers':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=customers"})
            return jsonify({"success": True, "message": "客户管理"})
        
        elif tool_id == 'orders':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment-orders"})
            return jsonify({"success": True, "message": "出货单"})
        
        elif tool_id == 'shipment_generate':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment"})
            
            # 真正调用发货单生成 API
            try:
                # 从 params 中获取订单文本或产品信息
                order_text = params.get('order_text', '')
                
                logger.info(f"收到发货单生成请求：order_text={order_text}")
                
                if order_text:
                    # 使用 XCAGI 自己的发货单服务层
                    from app.services.shipment_service import ShipmentService
                    from app.db.session import get_db
                    from app.db.models import Product
                    from sqlalchemy.orm import Session
                    
                    # 解析订单文本（简单解析：提取单位名、产品、数量、规格）
                    # 格式示例："发货单七彩乐园 1 桶 9803 规格 12"
                    parsed_result = _parse_order_text(order_text)
                    
                    if not parsed_result.get('success'):
                        return jsonify(parsed_result), 400
                    
                    unit_name = parsed_result['unit_name']
                    products = parsed_result['products']
                    
                    # 调用服务层生成发货单
                    service = ShipmentService()
                    result = service.generate_shipment_document(
                        unit_name=unit_name,
                        products=products,
                        template_name=None,
                    )
                    
                    logger.info(f"发货单生成结果：{result}")
                    return jsonify(result)
                
                return jsonify({
                    "success": False,
                    "message": "缺少必要的参数：order_text"
                }), 400
                
            except Exception as e:
                logger.error(f"生成发货单失败：{e}", exc_info=True)
                return jsonify({
                    "success": False,
                    "message": f"生成失败：{str(e)}"
                }), 500
        
        elif tool_id == 'print':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=print"})
            return jsonify({"success": True, "message": "标签打印"})
        
        elif tool_id == 'materials':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=materials"})
            return jsonify({"success": True, "message": "原材料仓库"})
        
        elif tool_id == 'ocr':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=ocr"})
            return jsonify({"success": True, "message": "图片 OCR"})
        
        elif tool_id == 'wechat':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=wechat-contacts"})
            return jsonify({"success": True, "message": "微信任务"})
        
        elif tool_id == 'excel_decompose':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=excel"})
            return jsonify({"success": True, "message": "Excel 模板分解"})
        
        elif tool_id == 'shipment_template':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=template-preview"})
            return jsonify({"success": True, "message": "发货单模板"})
        
        elif tool_id == 'database':
            from app.services.database_service import get_database_service
            
            db_service = get_database_service()
            
            if action == 'backup':
                result = db_service.backup_database()
                return jsonify(result)
            
            elif action == 'restore':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.restore_database(backup_file)
                return jsonify(result)
            
            elif action == 'list':
                result = db_service.list_backups()
                return jsonify(result)
            
            elif action == 'delete':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.delete_backup(backup_file)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的数据库操作：{action}"
                }), 400
        
        elif tool_id == 'system':
            from app.services.system_service import get_system_service
            
            system_service = get_system_service()
            
            if action == 'get_startup_config':
                result = system_service.get_startup_config()
                return jsonify({"success": True, "data": result})
            
            elif action == 'enable_startup':
                result = system_service.enable_startup()
                return jsonify(result)
            
            elif action == 'disable_startup':
                result = system_service.disable_startup()
                return jsonify(result)
            
            elif action == 'get_system_info':
                result = system_service.get_system_info()
                return jsonify({"success": True, "data": result})
            
            elif action == 'get_printer_config':
                result = system_service.get_printer_config()
                return jsonify(result)
            
            elif action == 'set_default_printer':
                printer_name = params.get('printer_name')
                if not printer_name:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：printer_name"
                    }), 400
                result = system_service.set_default_printer(printer_name)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的系统操作：{action}"
                }), 400
        
        return jsonify({"success": False, "message": f"未知工具: {tool_id}"}), 400
        
    except Exception as e:
        logger.error(f"执行工具失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
