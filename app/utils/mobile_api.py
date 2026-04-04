# -*- coding: utf-8 -*-
"""
移动端 API 响应格式优化工具

提供统一的响应格式和分页支持
"""

from typing import Any, Dict, List, Optional
from math import ceil


def format_mobile_response(
    data: Any,
    message: str = "success",
    success: bool = True,
    code: int = 200
) -> Dict[str, Any]:
    """
    格式化移动端统一响应格式
    
    Args:
        data: 响应数据
        message: 消息
        success: 是否成功
        code: 状态码
        
    Returns:
        dict: 统一格式的响应数据
    """
    return {
        "code": code,
        "message": message,
        "success": success,
        "data": data
    }


def format_error_response(
    error: str,
    message: str = "error",
    code: int = 400
) -> Dict[str, Any]:
    """
    格式化错误响应
    
    Args:
        error: 错误代码
        message: 错误消息
        code: 状态码
        
    Returns:
        dict: 统一格式的错误响应
    """
    return {
        "code": code,
        "message": message,
        "success": False,
        "data": {
            "error": error
        }
    }


def paginate_list(
    items: List[Any],
    total: int,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    格式化分页信息
    
    Args:
        items: 数据列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        
    Returns:
        dict: 包含数据和分页信息的响应
    """
    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": ceil(total / per_page) if per_page > 0 else 0,
            "has_next": page < ceil(total / per_page),
            "has_prev": page > 1
        }
    }


def optimize_product_data(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    优化产品数据，减少不必要字段
    
    Args:
        product: 原始产品数据
        
    Returns:
        dict: 优化后的产品数据
    """
    if not product:
        return {}
    
    optimized = {
        "id": product.get("id"),
        "name": product.get("name") or product.get("product_name"),
        "model_number": product.get("model_number"),
        "specification": product.get("specification"),
        "price": product.get("price"),
        "unit": product.get("unit"),
        "brand": product.get("brand"),
        "category": product.get("category"),
    }
    
    # 只保留非空字段
    return {k: v for k, v in optimized.items() if v is not None}


def optimize_customer_data(customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    优化客户数据，减少不必要字段
    
    Args:
        customer: 原始客户数据
        
    Returns:
        dict: 优化后的客户数据
    """
    if not customer:
        return {}
    
    optimized = {
        "id": customer.get("id"),
        "customer_name": customer.get("customer_name"),
        "contact_person": customer.get("contact_person"),
        "contact_phone": customer.get("contact_phone"),
        "contact_address": customer.get("contact_address"),
    }
    
    return {k: v for k, v in optimized.items() if v is not None}


def optimize_shipment_data(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """
    优化发货单数据，减少不必要字段
    
    Args:
        shipment: 原始发货单数据
        
    Returns:
        dict: 优化后的发货单数据
    """
    if not shipment:
        return {}
    
    optimized = {
        "id": shipment.get("id"),
        "order_number": shipment.get("order_number"),
        "unit_name": shipment.get("unit_name"),
        "products": shipment.get("products", []),
        "total_amount": shipment.get("total_amount"),
        "status": shipment.get("status"),
        "created_at": shipment.get("created_at"),
        "printed_at": shipment.get("printed_at"),
    }
    
    return {k: v for k, v in optimized.items() if v is not None}


def parse_pagination_params(
    request_args: Dict[str, Any],
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 100
) -> tuple:
    """
    解析分页参数
    
    Args:
        request_args: 请求参数
        default_page: 默认页码
        default_per_page: 默认每页数量
        max_per_page: 最大每页数量
        
    Returns:
        tuple: (page, per_page)
    """
    try:
        page = int(request_args.get("page", default_page))
        page = max(1, page)
    except (ValueError, TypeError):
        page = default_page
    
    try:
        per_page = int(request_args.get("per_page", default_per_page))
        per_page = min(max(1, per_page), max_per_page)
    except (ValueError, TypeError):
        per_page = default_per_page
    
    return page, per_page


def parse_search_params(
    request_args: Dict[str, Any],
    allowed_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    解析搜索参数
    
    Args:
        request_args: 请求参数
        allowed_fields: 允许的搜索字段
        
    Returns:
        dict: 搜索参数
    """
    search_params = {}
    
    keyword = request_args.get("keyword", "").strip()
    if keyword:
        search_params["keyword"] = keyword
    
    if allowed_fields:
        for field in allowed_fields:
            value = request_args.get(field)
            if value is not None:
                search_params[field] = value
    
    return search_params


def format_mobile_product_list(
    products: List[Dict[str, Any]],
    total: int,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    格式化产品列表为移动端格式
    
    Args:
        products: 产品列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        
    Returns:
        dict: 移动端格式的产品列表
    """
    optimized_products = [optimize_product_data(p) for p in products]
    
    return format_mobile_response(
        data=paginate_list(optimized_products, total, page, per_page)
    )


def format_mobile_customer_list(
    customers: List[Dict[str, Any]],
    total: int,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    格式化客户列表为移动端格式
    
    Args:
        customers: 客户列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        
    Returns:
        dict: 移动端格式的客户列表
    """
    optimized_customers = [optimize_customer_data(c) for c in customers]
    
    return format_mobile_response(
        data=paginate_list(optimized_customers, total, page, per_page)
    )


def format_mobile_shipment_list(
    shipments: List[Dict[str, Any]],
    total: int,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    格式化发货单列表为移动端格式
    
    Args:
        shipments: 发货单列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        
    Returns:
        dict: 移动端格式的发货单列表
    """
    optimized_shipments = [optimize_shipment_data(s) for s in shipments]
    
    return format_mobile_response(
        data=paginate_list(optimized_shipments, total, page, per_page)
    )
