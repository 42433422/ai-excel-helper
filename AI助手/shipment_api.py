# 发货单工作流API
from flask import Blueprint, request, jsonify, send_file
import logging
import os
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

shipment_bp = Blueprint('shipment', __name__, url_prefix='/api/shipment')

# 导入OCR学习数据库
from ocr_learning_db import get_ocr_learning_db

# 存储活跃的订单会话
_active_orders = {}


def get_shipment_controller():
    """获取发货单控制器"""
    from ai_augmented_parser import AIAugmentedShipmentParser
    from shipment_parser import ShipmentRecordManager
    from shipment_document import ShipmentDocumentGenerator, DocumentAPIGenerator
    return {
        "parser": AIAugmentedShipmentParser(),
        "record_manager": ShipmentRecordManager(),
        "document_generator": ShipmentDocumentGenerator(),
        "api_generator": DocumentAPIGenerator()
    }


@shipment_bp.route('/parse', methods=['POST'])
def parse_order():
    """解析订单文本"""
    try:
        data = request.get_json()
        order_text = data.get('order_text', '').strip()
        number_mode = data.get('number_mode', False)
        
        if not order_text:
            return jsonify({
                "success": False,
                "message": "订单文本不能为空"
            }), 400
        
        controller = get_shipment_controller()
        result = controller["parser"].parse(order_text, number_mode=number_mode)
        
        return jsonify({
            "success": True,
            "message": "解析成功",
            "data": result.to_dict(),
            "is_valid": result.is_valid()
        })
        
    except Exception as e:
        logger.error(f"解析订单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"解析失败: {str(e)}"
        }), 500


@shipment_bp.route('/create', methods=['POST'])
def create_shipment():
    """创建发货单并生成文档"""
    try:
        data = request.get_json()
        order_text = data.get('order_text', '').strip()
        
        # 获取OCR相关信息（如果是从OCR识别结果生成的）
        ocr_raw_text = data.get('ocr_raw_text', '')  # OCR原始识别文本
        save_to_learning = data.get('save_to_learning', False)  # 是否保存到学习库
        product_info = data.get('product_info')  # 商品信息
        
        if not order_text:
            return jsonify({
                "success": False,
                "message": "订单文本不能为空"
            }), 400
        
        controller = get_shipment_controller()
        result = controller["api_generator"].parse_and_generate(order_text)
        
        # 如果请求中包含了OCR原始文本，并且要求保存到学习库
        if save_to_learning and ocr_raw_text:
            try:
                db = get_ocr_learning_db()
                db.add_entry(
                    ocr_raw_text=ocr_raw_text,
                    final_text=order_text,
                    product_info=product_info,
                    ocr_source=data.get('ocr_source', 'unknown'),
                    status='confirmed',
                    notes='从发货单生成流程保存'
                )
                logger.info(f"已保存OCR学习词条: {ocr_raw_text[:50]}... -> {order_text[:50]}...")
            except Exception as e:
                logger.error(f"保存OCR学习词条失败: {e}")
                # 不影响主流程，继续返回结果
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"创建发货单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"创建发货单失败: {str(e)}"
        }), 500


@shipment_bp.route('/calculate_tins', methods=['POST'])
def calculate_tins():
    """计算桶数"""
    try:
        data = request.get_json()
        kg = float(data.get('kg', 0))
        tin_spec = float(data.get('tin_spec', 0))
        
        controller = get_shipment_controller()
        tins, used_spec = controller["parser"].calculate_tins_from_kg(kg, tin_spec)
        
        return jsonify({
            "success": True,
            "data": {
                "kg": kg,
                "tins": tins,
                "tin_spec": used_spec
            }
        })
        
    except Exception as e:
        logger.error(f"计算桶数失败: {e}")
        return jsonify({
            "success": False,
            "message": f"计算失败: {str(e)}"
        }), 500


@shipment_bp.route('/records', methods=['GET'])
def get_records():
    """获取发货记录列表"""
    try:
        status = request.args.get('status', 'pending')
        
        controller = get_shipment_controller()
        records = controller["record_manager"].get_pending_records()
        
        return jsonify({
            "success": True,
            "data": records,
            "count": len(records)
        })
        
    except Exception as e:
        logger.error(f"获取记录失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取记录失败: {str(e)}"
        }), 500


@shipment_bp.route('/records/<int:record_id>', methods=['GET'])
def get_record(record_id):
    """获取单个发货记录"""
    try:
        controller = get_shipment_controller()
        record = controller["record_manager"].get_record(record_id)
        
        if record:
            return jsonify({
                "success": True,
                "data": record
            })
        else:
            return jsonify({
                "success": False,
                "message": "记录不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"获取记录失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取记录失败: {str(e)}"
        }), 500


@shipment_bp.route('/records/<int:record_id>/status', methods=['PUT'])
def update_record_status(record_id):
    """更新记录状态"""
    try:
        data = request.get_json()
        status = data.get('status', '')
        
        if not status:
            return jsonify({
                "success": False,
                "message": "状态不能为空"
            }), 400
        
        controller = get_shipment_controller()
        success = controller["record_manager"].update_status(record_id, status)
        
        if success:
            return jsonify({
                "success": True,
                "message": "状态更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "记录不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"更新状态失败: {e}")
        return jsonify({
            "success": False,
            "message": f"更新失败: {str(e)}"
        }), 500


@shipment_bp.route('/templates', methods=['GET'])
def get_templates():
    """获取可用模板列表"""
    try:
        controller = get_shipment_controller()
        templates = controller["document_generator"].get_template_list()
        
        return jsonify({
            "success": True,
            "data": templates,
            "count": len(templates)
        })
        
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取模板列表失败: {str(e)}"
        }), 500


# ==================== 对话式订单处理 ====================

@shipment_bp.route('/workflow/start', methods=['POST'])
def start_order_workflow():
    """开始订单工作流"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        order_text = data.get('order_text', '').strip()
        
        if not order_text:
            return jsonify({
                "success": False,
                "message": "请提供订单信息"
            }), 400
        
        # 解析订单
        controller = get_shipment_controller()
        parsed = controller["parser"].parse(order_text)
        
        if not parsed.is_valid():
            return jsonify({
                "success": False,
                "message": "无法识别的订单信息，请提供：购买单位、产品名称、数量",
                "parsed_data": parsed.to_dict()
            }), 400
        
        # 保存到活跃订单
        _active_orders[user_id] = {
            "order_text": order_text,
            "parsed": parsed.to_dict(),
            "status": "pending_confirmation",
            "created_at": str(datetime.now())
        }
        
        # 准备确认信息
        confirm_message = f"""请确认以下订单信息：

**购买单位**: {parsed.purchase_unit}
**产品名称**: {parsed.product_name}
**产品型号**: {parsed.model_number or '未匹配'}
**数量**: {parsed.quantity_kg}kg = {parsed.quantity_tins}桶（每桶{parsed.tin_spec}kg）
**单价**: {parsed.unit_price}
**金额**: {parsed.amount}

确认信息正确请回复"确认"，如有错误请指出。"""
        
        return jsonify({
            "success": True,
            "message": confirm_message,
            "parsed_data": parsed.to_dict(),
            "next_action": "confirm"
        })
        
    except Exception as e:
        logger.error(f"开始工作流失败: {e}")
        return jsonify({
            "success": False,
            "message": f"操作失败: {str(e)}"
        }), 500


@shipment_bp.route('/workflow/confirm', methods=['POST'])
def confirm_order():
    """确认订单并生成发货单"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        confirm = data.get('confirm', True)
        adjustments = data.get('adjustments', {})
        
        if user_id not in _active_orders:
            return jsonify({
                "success": False,
                "message": "没有待确认的订单"
            }), 400
        
        order_data = _active_orders[user_id]
        
        if not confirm:
            # 用户拒绝，重新开始
            del _active_orders[user_id]
            return jsonify({
                "success": True,
                "message": "订单已取消，请重新输入订单信息",
                "next_action": "new_order"
            })
        
        # 应用调整
        parsed_data = order_data["parsed"]
        if adjustments:
            for key, value in adjustments.items():
                if key in parsed_data:
                    parsed_data[key] = value
        
        # 生成发货单
        controller = get_shipment_controller()
        result = controller["api_generator"].parse_and_generate(
            order_data["order_text"]
        )
        
        if result["success"]:
            # 清除活跃订单
            del _active_orders[user_id]
            
            return jsonify({
                "success": True,
                "message": "发货单生成成功！",
                "document": result["document"],
                "download_url": f"/api/shipment/download/{result['document']['filename']}",
                "next_action": "download"
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get("message", "生成发货单失败")
            }), 500
        
    except Exception as e:
        logger.error(f"确认订单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"操作失败: {str(e)}"
        }), 500


@shipment_bp.route('/workflow/cancel', methods=['POST'])
def cancel_order():
    """取消订单"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        if user_id in _active_orders:
            del _active_orders[user_id]
        
        return jsonify({
            "success": True,
            "message": "订单已取消",
            "next_action": "new_order"
        })
        
    except Exception as e:
        logger.error(f"取消订单失败: {e}")
        return jsonify({
            "success": False,
            "message": f"操作失败: {str(e)}"
        }), 500


@shipment_bp.route('/workflow/status', methods=['GET'])
def get_workflow_status():
    """获取工作流状态"""
    try:
        return jsonify({
            "success": True,
            "active_orders": len(_active_orders),
            "orders": [
                {
                    "user_id": uid,
                    "status": data["status"],
                    "created_at": data["created_at"]
                }
                for uid, data in _active_orders.items()
            ]
        })
        
    except Exception as e:
        logger.error(f"获取工作流状态失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        }), 500


@shipment_bp.route('/download/<filename>', methods=['GET'])
def download_document(filename):
    """下载发货单文档"""
    try:
        # 安全检查
        filename = os.path.basename(filename)
        filepath = os.path.join("outputs", filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "message": "文件不存在"
            }), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({
            "success": False,
            "message": f"下载失败: {str(e)}"
        }), 500


@shipment_bp.route('/search-products', methods=['GET'])
def search_products():
    """实时搜索产品 - 用于输入时的预展示功能
    
    使用与生成发货单相同的逻辑：
    1. 首先识别购买单位
    2. 使用_match_product_from_db方法匹配产品（支持编号模式）
    3. 如果数据库匹配不到，使用AI解析
    4. 返回多个产品
    """
    try:
        order_text = request.args.get('q', '').strip()
        number_mode = request.args.get('number_mode', 'false').lower() == 'true'
        
        if not order_text:
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "purchase_unit": "",
                "message": "请输入订单信息"
            })
        
        from ai_augmented_parser import AIAugmentedShipmentParser
        
        ai_parser = AIAugmentedShipmentParser()
        
        # 1. 先提取购买单位
        traditional_unit = ai_parser._extract_purchase_unit(order_text)
        matched_unit = ai_parser._smart_match_unit(traditional_unit) if traditional_unit else None
        
        logger.info(f"预展示 - 识别到的购买单位: {matched_unit}, 原始: {traditional_unit}")
        
        if not matched_unit:
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "purchase_unit": "",
                "message": "请输入购买单位，例如：七彩乐园PE白底10桶"
            })
        
        # 2. 清理产品搜索文本，去除购买单位
        product_search_text = order_text
        if traditional_unit:
            product_search_text = order_text.replace(traditional_unit, '').strip()
        if not product_search_text:
            product_search_text = order_text
        
        # 3. 直接使用AI解析获取多个产品（与生成发货单相同的逻辑）
        matched_products = []
        
        logger.info(f"预展示 - 使用AI解析获取多个产品")
        parsed_order = ai_parser.parse(order_text, number_mode=number_mode)
        
        if parsed_order.products and len(parsed_order.products) > 0:
            for product in parsed_order.products:
                product_info = {
                    'name': product.get('name', ''),
                    'model_number': product.get('model_number', ''),
                    'price': product.get('unit_price', 0),
                    'quantity_kg': product.get('quantity_kg', 0),
                    'quantity_tins': product.get('quantity_tins', 0),
                    'tin_spec': product.get('tin_spec', 0),
                    'amount': product.get('amount', 0),
                    'purchase_unit': matched_unit
                }
                matched_products.append(product_info)
        
        logger.info(f"预展示 - 共找到 {len(matched_products)} 个产品")
        
        return jsonify({
            "success": True,
            "data": matched_products,
            "count": len(matched_products),
            "purchase_unit": matched_unit or "",
            "is_number_mode": number_mode
        })
        
    except Exception as e:
        logger.error(f"搜索产品失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"搜索失败: {str(e)}"
        }), 500


# 便捷函数：快速处理订单
def quick_create_shipment(order_text: str) -> dict:
    """快速创建发货单"""
    from shipment_parser import ShipmentParser, ShipmentRecordManager
    from shipment_document import ShipmentDocumentGenerator
    
    parser = ShipmentParser()
    parsed = parser.parse(order_text)
    
    if not parsed.is_valid():
        return {
            "success": False,
            "message": "无法解析订单信息",
            "parsed": parsed.to_dict()
        }
    
    doc_gen = ShipmentDocumentGenerator()
    doc = doc_gen.generate_document(
        order_text=order_text,
        parsed_data=parsed.to_dict()
    )
    
    record_mgr = ShipmentRecordManager()
    record_id = record_mgr.create_record(parsed)
    
    return {
        "success": True,
        "record_id": record_id,
        "document": doc.to_dict(),
        "parsed": parsed.to_dict()
    }


# ==================== OCR识别学习库相关API ====================

@shipment_bp.route('/save-ocr-learning', methods=['POST'])
def save_ocr_learning():
    """
    保存OCR识别学习词条
    用于存储图片识别的原始结果和最终用于发货单生成的结果以及对应的商品信息
    """
    try:
        data = request.get_json()
        
        # 验证必要参数
        ocr_raw_text = data.get('ocr_raw_text', '').strip()
        final_text = data.get('final_text', '').strip()
        
        if not ocr_raw_text or not final_text:
            return jsonify({
                "success": False,
                "message": "ocr_raw_text和final_text不能为空"
            }), 400
        
        # 获取可选参数
        product_info = data.get('product_info')  # 商品信息字典
        image_reference = data.get('image_reference')  # 图片引用
        ocr_source = data.get('ocr_source', 'unknown')  # OCR来源
        status = data.get('status', 'pending')  # 状态
        notes = data.get('notes', '')  # 备注
        
        # 保存到学习数据库
        db = get_ocr_learning_db()
        entry_id = db.add_entry(
            ocr_raw_text=ocr_raw_text,
            final_text=final_text,
            product_info=product_info,
            image_reference=image_reference,
            ocr_source=ocr_source,
            status=status,
            notes=notes
        )
        
        if entry_id:
            return jsonify({
                "success": True,
                "message": "OCR学习词条保存成功",
                "data": {
                    "entry_id": entry_id,
                    "ocr_raw_text": ocr_raw_text,
                    "final_text": final_text,
                    "product_info": product_info
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存OCR学习词条失败"
            }), 500
            
    except Exception as e:
        logger.error(f"保存OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"保存失败: {str(e)}"
        }), 500