# -*- coding: utf-8 -*-
"""
微信联系人路由（兼容旧版前端路径）

提供 /api/wechat_contacts 路径的兼容接口
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

# 导入 wechat 蓝图的服务
from app.services.wechat_contact_service import WechatContactService

wechat_contacts_bp = Blueprint("wechat_contacts", __name__, url_prefix="/api/wechat_contacts")


def get_wechat_contact_service():
    return WechatContactService()


@wechat_contacts_bp.route("", methods=["GET"])
@swag_from({
    "summary": "获取微信联系人列表（兼容旧路径）",
    "description": "获取微信联系人列表，支持按类型筛选",
    "parameters": [
        {
            "name": "type",
            "in": "query",
            "type": "string",
            "description": "联系人类型（contact/group/all），默认 all"
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认 100"
        }
    ],
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "total": {"type": "integer"}
                }
            }
        }
    }
})
def wechat_contacts_list_compat():
    """获取微信联系人列表（兼容旧路径）"""
    try:
        contact_type = request.args.get("type", "all")
        limit = request.args.get("limit", 100, type=int)

        service = get_wechat_contact_service()
        contacts = service.get_contacts(
            contact_type=contact_type,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": contacts,
            "total": len(contacts)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/ensure_contact_cache", methods=["POST", "GET"])
@swag_from({
    "summary": "确保联系人缓存",
    "description": "确保微信联系人缓存已初始化",
    "responses": {
        "200": {
            "description": "操作成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def ensure_contact_cache():
    """确保联系人缓存已初始化"""
    try:
        # 这个接口只是为了兼容前端，实际逻辑已经在 get_contacts 中处理
        return jsonify({
            "success": True,
            "message": "联系人缓存已就绪"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"检查缓存失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/search", methods=["GET"])
@swag_from({
    "summary": "搜索联系人",
    "description": "根据关键词搜索微信联系人",
    "parameters": [
        {
            "name": "q",
            "in": "query",
            "type": "string",
            "description": "搜索关键词",
            "required": True
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认 20"
        }
    ],
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "results": {"type": "array"}
                }
            }
        }
    }
})
def wechat_contacts_search():
    """搜索联系人（在所有联系人中搜索，用于添加星标）"""
    try:
        query = request.args.get("q", "")
        limit = request.args.get("limit", 20, type=int)

        service = get_wechat_contact_service()
        # 搜索时在所有联系人中搜索，不限制类型
        contacts = service.get_contacts(
            keyword=query,
            contact_type=None,  # 不限制类型，搜索所有联系人
            limit=limit
        )

        # 转换为前端期望的格式
        results = []
        for c in contacts:
            results.append({
                "display_name": c.get("contact_name"),
                "nick_name": c.get("contact_name"),
                "username": c.get("wechat_id"),
                "remark": c.get("remark"),
                "already_starred": c.get("is_starred") == 1
            })

        return jsonify({
            "success": True,
            "results": results
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"搜索失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/unstar_all", methods=["POST"])
@swag_from({
    "summary": "取消所有星标（兼容旧路径）",
    "description": "取消所有联系人的星标状态",
    "responses": {
        "200": {
            "description": "操作成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def wechat_contacts_unstar_all():
    """取消所有联系人星标（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        result = service.unstar_all()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"操作失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["GET"])
def wechat_contact_get_compat(contact_id):
    """获取单个联系人（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        contact = service.get_contact_by_id(contact_id)

        if contact:
            return jsonify({
                "success": True,
                "data": contact
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "联系人不存在"
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["PUT"])
def wechat_contact_update_compat(contact_id):
    """更新联系人（兼容旧路径）"""
    try:
        data = request.get_json() or {}
        contact_name = data.get("contact_name", "").strip()
        remark = data.get("remark", "").strip()
        wechat_id = data.get("wechat_id", "").strip()
        contact_type = data.get("contact_type")
        is_starred = data.get("is_starred")

        service = get_wechat_contact_service()
        result = service.update_contact(
            contact_id=contact_id,
            contact_name=contact_name if contact_name else None,
            remark=remark if remark else None,
            wechat_id=wechat_id if wechat_id else None,
            contact_type=contact_type,
            is_starred=is_starred
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["DELETE"])
def wechat_contact_delete_compat(contact_id):
    """删除联系人（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        result = service.delete_contact(contact_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>/context", methods=["GET"])
def wechat_contact_context_compat(contact_id):
    """获取联系人聊天上下文（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        messages = service.get_contact_context(contact_id)

        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>/refresh_messages", methods=["POST"])
@swag_from({
    "summary": "刷新联系人聊天记录",
    "description": "从微信数据库拉取最新消息并保存到聊天上下文",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人 ID",
            "required": True
        }
    ],
    "requestBody": {
        "description": "可选的请求体参数",
        "required": False,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "拉取消息数量限制，默认 50",
                            "default": 50
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "刷新成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "count": {"type": "integer"}
                }
            }
        },
        "400": {
            "description": "刷新失败，联系人不存在或参数错误"
        },
        "500": {
            "description": "服务器内部错误"
        }
    }
})
def wechat_contact_refresh_messages_compat(contact_id):
    """刷新联系人聊天记录（兼容旧路径）"""
    try:
        data = request.get_json() or {}
        limit = data.get("limit", 50, type=int)
        
        service = get_wechat_contact_service()
        result = service.refresh_messages(contact_id=contact_id, limit=limit)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"刷新失败：{str(e)}"
        }), 500
