# OCR API模块
from flask import Blueprint, request, jsonify
import logging
import os
import uuid
import requests

logger = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')

# 导入OCR学习数据库
from ocr_learning_db import get_ocr_learning_db

# OCR处理器单例
_ocr_processor = None

def get_ocr_processor():
    """获取OCR处理器单例"""
    global _ocr_processor
    if _ocr_processor is None:
        from ocr_processor import OCRProcessor
        _ocr_processor = OCRProcessor()
    return _ocr_processor

# 配置上传目录
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@ocr_bp.route('/process-image', methods=['POST'])
def process_image():
    """处理上传的图片并提取信息"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "message": "请上传图片文件"
            }), 400
        
        # 获取上传的文件
        file = request.files['image']
        
        # 检查文件是否为空
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "请选择一个文件"
            }), 400
        
        # 检查文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return jsonify({
                "success": False,
                "message": "请上传有效的图片文件"
            }), 400
        
        # 生成唯一的文件名
        unique_filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # 保存文件
        file.save(file_path)
        logger.info(f"保存上传的图片: {file_path}")
        
        try:
            # 获取OCR处理器并处理图片
            ocr_processor = get_ocr_processor()
            result = ocr_processor.process_image(file_path)
            logger.info(f"OCR处理成功: {result}")
            
            # 返回结果
            return jsonify({
                "success": True,
                "message": "图片处理成功",
                "result": result
            })
            
        finally:
            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"删除临时图片: {file_path}")
        
    except Exception as e:
        logger.error(f"处理图片失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"处理图片失败: {str(e)}"
        }), 500


@ocr_bp.route('/test', methods=['GET'])
def test_ocr():
    """测试OCR服务是否正常"""
    try:
        ocr_processor = get_ocr_processor()
        return jsonify({
            "success": True,
            "message": "OCR服务正常运行",
            "status": "ok"
        })
    except Exception as e:
        logger.error(f"测试OCR服务失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"测试失败: {str(e)}"
        }), 500


@ocr_bp.route('/balance', methods=['GET'])
def get_balance():
    """查询硅基流动账户余额"""
    try:
        result = {
            "success": True,
            "message": "查询成功",
            "data": {}
        }
        
        # 查询硅基流动余额
        try:
            ocr_processor = get_ocr_processor()
            api_key = ocr_processor.api_key
            
            url = "https://api.siliconflow.cn/v1/user/info"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result["data"] = {
                    "success": True,
                    "balance": data.get("data", {}).get("balance", 0),
                    "total_balance": data.get("data", {}).get("totalBalance", 0),
                    "charge_balance": data.get("data", {}).get("chargeBalance", 0),
                    "gift_balance": data.get("data", {}).get("giftBalance", 0),
                    "model": ocr_processor.model,
                    "platform": "硅基流动"
                }
            else:
                result["data"] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "platform": "硅基流动"
                }
        except Exception as e:
            logger.error(f"查询硅基流动余额失败: {str(e)}")
            result["data"] = {
                "success": False,
                "error": str(e),
                "platform": "硅基流动"
            }
        
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"查询余额失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"查询余额失败: {str(e)}",
            "data": None
        }), 500


# ==================== OCR识别学习库相关API ====================

@ocr_bp.route('/learning/save', methods=['POST'])
def save_learning_entry():
    """
    保存OCR识别学习词条
    用于存储图片识别的原始结果和最终用于发货单生成的结果
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
        product_info = data.get('product_info')
        image_reference = data.get('image_reference')
        ocr_source = data.get('ocr_source', 'unknown')
        status = data.get('status', 'pending')
        notes = data.get('notes', '')
        
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
                "message": "学习词条保存成功",
                "data": {
                    "entry_id": entry_id,
                    "ocr_raw_text": ocr_raw_text,
                    "final_text": final_text
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存学习词条失败"
            }), 500
            
    except Exception as e:
        logger.error(f"保存OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"保存失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/entries', methods=['GET'])
def get_learning_entries():
    """获取OCR识别学习词条列表"""
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        db = get_ocr_learning_db()
        entries = db.get_all_entries(status=status, limit=limit, offset=offset)
        
        return jsonify({
            "success": True,
            "message": "获取成功",
            "data": entries,
            "count": len(entries)
        })
        
    except Exception as e:
        logger.error(f"获取OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/entries/<int:entry_id>', methods=['GET'])
def get_learning_entry(entry_id):
    """获取单条OCR识别学习词条"""
    try:
        db = get_ocr_learning_db()
        entry = db.get_entry(entry_id)
        
        if entry:
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": entry
            })
        else:
            return jsonify({
                "success": False,
                "message": "词条不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"获取OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/entries/<int:entry_id>', methods=['PUT'])
def update_learning_entry(entry_id):
    """更新OCR识别学习词条"""
    try:
        data = request.get_json()
        
        db = get_ocr_learning_db()
        success = db.update_entry(
            entry_id=entry_id,
            final_text=data.get('final_text'),
            product_info=data.get('product_info'),
            status=data.get('status'),
            accuracy_score=data.get('accuracy_score'),
            notes=data.get('notes')
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "更新失败或词条不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"更新OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"更新失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/entries/<int:entry_id>', methods=['DELETE'])
def delete_learning_entry(entry_id):
    """删除OCR识别学习词条"""
    try:
        db = get_ocr_learning_db()
        success = db.delete_entry(entry_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "删除成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "删除失败或词条不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"删除OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"删除失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/search', methods=['GET'])
def search_learning_entries():
    """搜索OCR识别学习词条"""
    try:
        keyword = request.args.get('q', '').strip()
        search_in_raw = request.args.get('search_in_raw', 'true').lower() == 'true'
        search_in_final = request.args.get('search_in_final', 'true').lower() == 'true'
        
        if not keyword:
            return jsonify({
                "success": False,
                "message": "搜索关键词不能为空"
            }), 400
        
        db = get_ocr_learning_db()
        entries = db.search_entries(keyword, search_in_raw, search_in_final)
        
        return jsonify({
            "success": True,
            "message": "搜索成功",
            "data": entries,
            "count": len(entries)
        })
        
    except Exception as e:
        logger.error(f"搜索OCR学习词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"搜索失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/similar', methods=['POST'])
def find_similar_entries():
    """查找相似的OCR识别学习词条"""
    try:
        data = request.get_json()
        ocr_raw_text = data.get('ocr_raw_text', '').strip()
        similarity_threshold = data.get('similarity_threshold', 0.8)
        
        if not ocr_raw_text:
            return jsonify({
                "success": False,
                "message": "ocr_raw_text不能为空"
            }), 400
        
        db = get_ocr_learning_db()
        entries = db.find_similar_entries(ocr_raw_text, similarity_threshold)
        
        return jsonify({
            "success": True,
            "message": "查找成功",
            "data": entries,
            "count": len(entries)
        })
        
    except Exception as e:
        logger.error(f"查找相似词条失败: {e}")
        return jsonify({
            "success": False,
            "message": f"查找失败: {str(e)}"
        }), 500


@ocr_bp.route('/learning/statistics', methods=['GET'])
def get_learning_statistics():
    """获取OCR识别学习库统计信息"""
    try:
        db = get_ocr_learning_db()
        stats = db.get_statistics()
        
        return jsonify({
            "success": True,
            "message": "获取成功",
            "data": stats
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }), 500
