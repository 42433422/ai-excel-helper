# -*- coding: utf-8 -*-
"""
微信小程序专用 API 路由模块

提供小程序所需的所有业务接口，包括：
- 产品查询
- 客户管理
- 发货单管理
- AI 对话
- 标签打印
"""

import logging
import os
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import and_, or_

from app.db.models import Customer, Product, ShipmentRecord
from app.db.session import get_db
from app.routes.wechat_miniprogram import (
    jsonify_response,
    miniprogram_auth_required,
    verify_jwt_token,
)
from app.utils.mobile_api import (
    format_mobile_response,
    format_error_response,
    paginate_list,
    parse_pagination_params,
    parse_search_params,
    optimize_product_data,
    optimize_customer_data,
    optimize_shipment_data,
)

logger = logging.getLogger(__name__)

miniprogram_api_bp = Blueprint("miniprogram_api", __name__, url_prefix="/api")


def get_auth_header() -> str:
    """获取 Authorization header"""
    return request.headers.get("Authorization", "")


def extract_token() -> str:
    """从 header 中提取 token"""
    auth_header = get_auth_header()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.args.get("token", "")


@miniprogram_api_bp.route("/products", methods=["GET"])
def get_products():
    """
    获取产品列表（移动端优化版）
    
    Query Parameters:
        - keyword: 搜索关键词
        - model_number: 型号
        - page: 页码，默认 1
        - per_page: 每页数量，默认 20
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "items": [...],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 5,
                    "has_next": true,
                    "has_prev": false
                }
            }
        }
    """
    try:
        page, per_page = parse_pagination_params(request.args)
        search_params = parse_search_params(request.args, ["keyword", "model_number"])
        
        with get_db() as db:
            query = db.query(Product).filter(Product.is_active == 1)
            
            if search_params.get("keyword"):
                keyword = f"%{search_params['keyword']}%"
                query = query.filter(
                    or_(
                        Product.name.like(keyword),
                        Product.product_name.like(keyword),
                        Product.model_number.like(keyword),
                    )
                )
            
            if search_params.get("model_number"):
                query = query.filter(
                    Product.model_number.like(f"%{search_params['model_number']}%")
                )
            
            total = query.count()
            products = query.offset((page - 1) * per_page).limit(per_page).all()
            
            product_list = [
                {
                    "id": p.id,
                    "name": p.name or p.product_name,
                    "model_number": p.model_number,
                    "specification": p.specification,
                    "price": float(p.price) if p.price else None,
                    "unit": p.unit,
                    "brand": p.brand,
                    "category": p.category,
                }
                for p in products
            ]
            
            return jsonify_response(200, "获取成功", {
                "items": product_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": page * per_page < total,
                    "has_prev": page > 1,
                }
            })
            
    except Exception as e:
        logger.error(f"获取产品列表失败：{e}", exc_info=True)
        return jsonify_response(500, f"查询失败：{str(e)}")


@miniprogram_api_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """
    获取产品详情
    
    Path Parameters:
        - product_id: 产品 ID
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "id": 1,
                "name": "产品名称",
                "model_number": "型号",
                ...
            }
        }
    """
    try:
        with get_db() as db:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.is_active == 1
            ).first()
            
            if not product:
                return jsonify_response(404, "产品不存在")
            
            product_data = {
                "id": product.id,
                "name": product.name or product.product_name,
                "model_number": product.model_number,
                "specification": product.specification,
                "price": float(product.price) if product.price else None,
                "unit": product.unit,
                "brand": product.brand,
                "category": product.category,
                "description": product.description,
                "quantity": product.quantity,
            }
            
            return jsonify_response(200, "获取成功", product_data)
            
    except Exception as e:
        logger.error(f"获取产品详情失败：{e}")
        return jsonify_response(500, f"查询失败：{str(e)}")


@miniprogram_api_bp.route("/customers", methods=["GET"])
@miniprogram_auth_required
def get_customers():
    """
    获取客户列表（移动端优化版）
    
    Query Parameters:
        - keyword: 搜索关键词
        - page: 页码，默认 1
        - per_page: 每页数量，默认 20
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "items": [...],
                "pagination": {...}
            }
        }
    """
    try:
        page, per_page = parse_pagination_params(request.args)
        keyword = request.args.get("keyword", "").strip()
        
        with get_db() as db:
            query = db.query(Customer)
            
            if keyword:
                query = query.filter(
                    or_(
                        Customer.customer_name.like(f"%{keyword}%"),
                        Customer.contact_person.like(f"%{keyword}%"),
                        Customer.contact_phone.like(f"%{keyword}%"),
                    )
                )
            
            total = query.count()
            customers = query.offset((page - 1) * per_page).limit(per_page).all()
            
            customer_list = [
                {
                    "id": c.id,
                    "customer_name": c.customer_name,
                    "contact_person": c.contact_person,
                    "contact_phone": c.contact_phone,
                    "contact_address": c.contact_address,
                }
                for c in customers
            ]
            
            return jsonify_response(200, "获取成功", {
                "items": customer_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": page * per_page < total,
                    "has_prev": page > 1,
                }
            })
            
    except Exception as e:
        logger.error(f"获取客户列表失败：{e}", exc_info=True)
        return jsonify_response(500, f"查询失败：{str(e)}")


@miniprogram_api_bp.route("/customers/<int:customer_id>", methods=["GET"])
@miniprogram_auth_required
def get_customer(customer_id):
    """
    获取客户详情
    
    Path Parameters:
        - customer_id: 客户 ID
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "id": 1,
                "customer_name": "客户名称",
                "contact_person": "联系人",
                ...
            }
        }
    """
    try:
        with get_db() as db:
            customer = db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer:
                return jsonify_response(404, "客户不存在")
            
            customer_data = {
                "id": customer.id,
                "customer_name": customer.customer_name,
                "contact_person": customer.contact_person,
                "contact_phone": customer.contact_phone,
                "contact_address": customer.contact_address,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
                "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
            }
            
            return jsonify_response(200, "获取成功", customer_data)
            
    except Exception as e:
        logger.error(f"获取客户详情失败：{e}")
        return jsonify_response(500, f"查询失败：{str(e)}")


@miniprogram_api_bp.route("/shipment/create", methods=["POST"])
@miniprogram_auth_required
def create_shipment():
    """
    创建发货单
    
    Request Body:
        {
            "unit_name": "单位名称",
            "products": [
                {
                    "product_id": 1,
                    "quantity": 10,
                    "price": 100.00
                }
            ],
            "date": "2024-01-01"
        }
        
    Response:
        {
            "code": 200,
            "message": "创建成功",
            "success": true,
            "data": {
                "id": 1,
                "order_number": "24-0100001A",
                ...
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        unit_name = data.get("unit_name", "").strip()
        products = data.get("products", [])
        date_str = data.get("date")
        
        if not unit_name:
            return jsonify_response(400, "单位名称不能为空")
        
        if not products:
            return jsonify_response(400, "产品列表不能为空")
        
        from datetime import datetime
        
        with get_db() as db:
            shipment = ShipmentRecord(
                unit_name=unit_name,
                order_number=_generate_order_number(db),
                total_amount=sum(p.get("price", 0) * p.get("quantity", 0) for p in products),
                status="pending",
                created_at=datetime.now(),
            )
            
            db.add(shipment)
            db.commit()
            db.refresh(shipment)
            
            shipment_data = {
                "id": shipment.id,
                "order_number": shipment.order_number,
                "unit_name": shipment.unit_name,
                "total_amount": float(shipment.total_amount) if shipment.total_amount else None,
                "status": shipment.status,
                "created_at": shipment.created_at.isoformat(),
            }
            
            return jsonify_response(201, "创建成功", shipment_data)
            
    except Exception as e:
        logger.error(f"创建发货单失败：{e}", exc_info=True)
        return jsonify_response(500, f"创建失败：{str(e)}")


def _generate_order_number(db) -> str:
    """生成订单编号"""
    from datetime import datetime
    
    today = datetime.now()
    year_month = today.strftime("%y-%m")
    
    count = db.query(ShipmentRecord).filter(
        ShipmentRecord.created_at >= today.replace(day=1)
    ).count()
    
    sequence = count + 1
    return f"{year_month}-{sequence:05d}A"


@miniprogram_api_bp.route("/shipment/list", methods=["GET"])
@miniprogram_auth_required
def get_shipment_list():
    """
    获取发货单列表
    
    Query Parameters:
        - unit_name: 单位名称
        - start_date: 开始日期 (YYYY-MM-DD)
        - end_date: 结束日期 (YYYY-MM-DD)
        - page: 页码，默认 1
        - per_page: 每页数量，默认 20
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "items": [...],
                "pagination": {...}
            }
        }
    """
    try:
        page, per_page = parse_pagination_params(request.args)
        unit_name = request.args.get("unit_name", "").strip()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        with get_db() as db:
            query = db.query(ShipmentRecord)
            
            if unit_name:
                query = query.filter(
                    ShipmentRecord.unit_name.like(f"%{unit_name}%")
                )
            
            if start_date:
                from datetime import datetime
                start = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(ShipmentRecord.created_at >= start)
            
            if end_date:
                from datetime import datetime
                end = datetime.strptime(end_date, "%Y-%m-%d")
                query = query.filter(ShipmentRecord.created_at <= end)
            
            query = query.order_by(ShipmentRecord.created_at.desc())
            
            total = query.count()
            shipments = query.offset((page - 1) * per_page).limit(per_page).all()
            
            shipment_list = [
                {
                    "id": s.id,
                    "order_number": s.order_number,
                    "unit_name": s.unit_name,
                    "total_amount": float(s.total_amount) if s.total_amount else None,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "printed_at": s.printed_at.isoformat() if s.printed_at else None,
                }
                for s in shipments
            ]
            
            return jsonify_response(200, "获取成功", {
                "items": shipment_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": page * per_page < total,
                    "has_prev": page > 1,
                }
            })
            
    except Exception as e:
        logger.error(f"获取发货单列表失败：{e}", exc_info=True)
        return jsonify_response(500, f"查询失败：{str(e)}")


@miniprogram_api_bp.route("/ai/chat", methods=["POST"])
def ai_chat():
    """
    AI 对话接口（小程序版）
    
    Request Body:
        {
            "message": "用户消息",
            "context": {}  # 可选的上下文
        }
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "reply": "AI 回复内容",
                "action": "reply",
                "data": {}
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        context = data.get("context", {})
        
        if not message:
            return jsonify_response(400, "消息内容不能为空")
        
        from app.application import get_ai_chat_app_service
        
        ai_chat_service = get_ai_chat_app_service()
        
        token = extract_token()
        payload = verify_jwt_token(token)
        user_id = payload.get("user_id") if payload else f"wx_{request.remote_addr}"
        
        result = ai_chat_service.process_chat(
            user_id=str(user_id),
            message=message,
            context=context,
            source="miniprogram",
            file_context={}
        )
        
        if result.get("success"):
            return jsonify_response(200, "获取成功", {
                "reply": result.get("message", ""),
                "action": result.get("action", "reply"),
                "data": result.get("data", {}),
            })
        else:
            return jsonify_response(500, result.get("message", "AI 处理失败"))
            
    except Exception as e:
        logger.error(f"AI 对话失败：{e}", exc_info=True)
        return jsonify_response(500, f"对话失败：{str(e)}")


@miniprogram_api_bp.route("/print/label/<int:shipment_id>", methods=["GET"])
@miniprogram_auth_required
def get_label_template(shipment_id):
    """
    获取标签模板（发货单）
    
    Path Parameters:
        - shipment_id: 发货单 ID
        
    Response:
        返回标签图片文件或 JSON 错误
    """
    try:
        from app.utils.path_utils import get_resource_path
        
        with get_db() as db:
            shipment = db.query(ShipmentRecord).filter(
                ShipmentRecord.id == shipment_id
            ).first()
            
            if not shipment:
                return jsonify_response(404, "发货单不存在")
            
            labels_dir = get_resource_path("ai_assistant", "商标导出")
            
            if not os.path.exists(labels_dir):
                return jsonify_response(404, "标签目录不存在")
            
            label_files = [
                f for f in os.listdir(labels_dir)
                if f.startswith(shipment.order_number) and f.endswith(".png")
            ]
            
            if not label_files:
                return jsonify_response(404, "未找到标签文件")
            
            label_path = os.path.join(labels_dir, label_files[0])
            
            return send_file(
                label_path,
                mimetype="image/png",
                as_attachment=True,
                download_name=label_files[0]
            )
            
    except Exception as e:
        logger.error(f"获取标签失败：{e}", exc_info=True)
        return jsonify_response(500, f"获取失败：{str(e)}")


@miniprogram_api_bp.route("/print/labels/<int:shipment_id>/list", methods=["GET"])
@miniprogram_auth_required
def get_label_list(shipment_id):
    """
    获取发货单标签列表
    
    Path Parameters:
        - shipment_id: 发货单 ID
        
    Response:
        {
            "code": 200,
            "message": "success",
            "success": true,
            "data": {
                "order_number": "24-0100001A",
                "labels": [
                    {
                        "filename": "24-0100001A_第 1 项.png",
                        "label_number": "1",
                        "url": "/api/print/label/1"
                    }
                ]
            }
        }
    """
    try:
        from app.utils.path_utils import get_resource_path
        
        with get_db() as db:
            shipment = db.query(ShipmentRecord).filter(
                ShipmentRecord.id == shipment_id
            ).first()
            
            if not shipment:
                return jsonify_response(404, "发货单不存在")
            
            labels_dir = get_resource_path("ai_assistant", "商标导出")
            
            if not os.path.exists(labels_dir):
                return jsonify_response(200, "标签目录不存在", {"labels": []})
            
            label_files = [
                f for f in os.listdir(labels_dir)
                if f.startswith(shipment.order_number) and f.endswith(".png")
            ]
            
            labels = []
            for filename in sorted(label_files):
                import re
                match = re.match(r".+?_?第？?(\d+)?项？\.png", filename, re.IGNORECASE)
                label_number = match.group(1) if match else "1"
                
                labels.append({
                    "filename": filename,
                    "label_number": label_number,
                    "url": f"/api/print/label/{shipment_id}",
                })
            
            return jsonify_response(200, "获取成功", {
                "order_number": shipment.order_number,
                "labels": labels,
                "count": len(labels),
            })
            
    except Exception as e:
        logger.error(f"获取标签列表失败：{e}", exc_info=True)
        return jsonify_response(500, f"获取失败：{str(e)}")
