# -*- coding: utf-8 -*-
"""
微信任务路由蓝图

提供微信任务查询、确认、联系人管理等 HTTP 接口。
"""

import os
from functools import lru_cache

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.application import get_wechat_contact_app_service, get_wechat_task_app_service

wechat_bp = Blueprint("wechat", __name__, url_prefix="/api/wechat")


@lru_cache(maxsize=1)
def get_wechat_task_service():
    return get_wechat_task_app_service()


def get_wechat_contact_service():
    return get_wechat_contact_app_service()


@wechat_bp.route("/tasks", methods=["GET"])
@swag_from({
    "summary": "获取微信任务列表",
    "description": "获取微信任务列表，支持按状态、联系人筛选，可设置返回数量限制",
    "parameters": [
        {
            "name": "status",
            "in": "query",
            "type": "string",
            "description": "任务状态筛选（pending/confirmed/ignored），默认 pending"
        },
        {
            "name": "contact_id",
            "in": "query",
            "type": "integer",
            "description": "联系人ID筛选"
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认20"
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
        },
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_tasks():
    """获取微信任务列表"""
    try:
        status = request.args.get("status", "pending")
        contact_id = request.args.get("contact_id", type=int)
        limit = request.args.get("limit", 20, type=int)

        service = get_wechat_task_service()
        tasks = service.get_tasks(contact_id=contact_id, status=status, limit=limit)

        return jsonify({
            "success": True,
            "data": tasks,
            "total": len(tasks)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_bp.route("/task/<int:task_id>/confirm", methods=["POST"])
@swag_from({
    "summary": "确认微信任务",
    "description": "确认指定的微信任务，表示该任务已被处理",
    "parameters": [
        {
            "name": "task_id",
            "in": "path",
            "type": "integer",
            "description": "任务ID",
            "required": True
        }
    ],
    "responses": {
        "200": {"description": "确认成功"},
        "400": {"description": "确认失败，任务不存在或状态异常"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_task_confirm(task_id):
    """确认微信任务"""
    try:
        service = get_wechat_task_service()
        result = service.confirm_task(task_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"确认失败：{str(e)}"
        }), 500


@wechat_bp.route("/task/<int:task_id>/ignore", methods=["POST"])
@swag_from({
    "summary": "忽略微信任务",
    "description": "忽略指定的微信任务，该任务将不再显示",
    "parameters": [
        {
            "name": "task_id",
            "in": "path",
            "type": "integer",
            "description": "任务ID",
            "required": True
        }
    ],
    "responses": {
        "200": {"description": "忽略成功"},
        "400": {"description": "忽略失败，任务不存在或状态异常"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_task_ignore(task_id):
    """忽略微信任务"""
    try:
        service = get_wechat_task_service()
        result = service.ignore_task(task_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"忽略失败：{str(e)}"
        }), 500


@wechat_bp.route("/contacts", methods=["GET"])
@swag_from({
    "summary": "获取微信联系人列表",
    "description": "获取微信联系人列表，支持按关键词、类型、星标状态筛选",
    "parameters": [
        {
            "name": "keyword",
            "in": "query",
            "type": "string",
            "description": "搜索关键词（姓名、微信号）"
        },
        {
            "name": "type",
            "in": "query",
            "type": "string",
            "description": "联系人类型筛选（contact/group/customer/all），默认 all"
        },
        {
            "name": "starred",
            "in": "query",
            "type": "boolean",
            "description": "仅返回星标联系人，默认 false"
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认100"
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
        },
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contacts_list():
    """获取微信联系人列表"""
    try:
        keyword = request.args.get("keyword")
        contact_type = request.args.get("type", "all")
        starred = request.args.get("starred", "false").lower() == "true"
        limit = request.args.get("limit", 100, type=int)

        service = get_wechat_contact_service()
        contacts = service.get_contacts(
            keyword=keyword,
            contact_type=contact_type if contact_type != "all" else None,
            starred_only=starred,
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


@wechat_bp.route("/contacts", methods=["POST"])
@swag_from({
    "summary": "添加微信联系人",
    "description": "添加新的微信联系人信息",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["contact_name"],
                "properties": {
                    "contact_name": {"type": "string", "description": "联系人名称"},
                    "remark": {"type": "string", "description": "备注"},
                    "wechat_id": {"type": "string", "description": "微信号"},
                    "contact_type": {"type": "string", "description": "联系人类型，默认 contact"},
                    "is_starred": {"type": "boolean", "description": "是否星标，默认 true"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "添加成功"},
        "400": {"description": "添加失败，参数错误或联系人名称为空"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contacts_add():
    """添加微信联系人"""
    try:
        data = request.get_json() or {}
        contact_name = data.get("contact_name", "").strip()
        remark = data.get("remark", "").strip()
        wechat_id = data.get("wechat_id", "").strip()
        contact_type = data.get("contact_type", "contact")
        is_starred = data.get("is_starred", True)

        if not contact_name:
            return jsonify({
                "success": False,
                "message": "联系人名称不能为空"
            }), 400

        service = get_wechat_contact_service()
        result = service.add_contact(
            contact_name=contact_name,
            remark=remark,
            wechat_id=wechat_id,
            contact_type=contact_type,
            is_starred=is_starred
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"添加失败：{str(e)}"
        }), 500


@wechat_bp.route("/contacts/<int:contact_id>", methods=["GET"])
@swag_from({
    "summary": "获取单个联系人",
    "description": "根据联系人ID获取详细信息",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人ID",
            "required": True
        }
    ],
    "responses": {
        "200": {"description": "查询成功"},
        "404": {"description": "联系人不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contact_get(contact_id):
    """获取单个联系人"""
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


@wechat_bp.route("/contacts/<int:contact_id>", methods=["PUT"])
@swag_from({
    "summary": "更新联系人",
    "description": "更新指定联系人的信息",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人ID",
            "required": True
        },
        {
            "name": "body",
            "in": "body",
            "schema": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "联系人名称"},
                    "remark": {"type": "string", "description": "备注"},
                    "wechat_id": {"type": "string", "description": "微信号"},
                    "contact_type": {"type": "string", "description": "联系人类型"},
                    "is_starred": {"type": "boolean", "description": "是否星标"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "更新成功"},
        "400": {"description": "更新失败"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contact_update(contact_id):
    """更新联系人"""
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


@wechat_bp.route("/contacts/<int:contact_id>", methods=["DELETE"])
@swag_from({
    "summary": "删除联系人",
    "description": "删除指定的微信联系人",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人ID",
            "required": True
        }
    ],
    "responses": {
        "200": {"description": "删除成功"},
        "400": {"description": "删除失败"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contact_delete(contact_id):
    """删除联系人"""
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


@wechat_bp.route("/contacts/<int:contact_id>/star", methods=["POST"])
@swag_from({
    "summary": "设置联系人星标",
    "description": "设置或取消联系人的星标状态",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人ID",
            "required": True
        },
        {
            "name": "body",
            "in": "body",
            "schema": {
                "type": "object",
                "properties": {
                    "starred": {"type": "boolean", "description": "是否星标，默认 true"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "操作成功"},
        "400": {"description": "操作失败"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contact_star(contact_id):
    """设置联系人星标"""
    try:
        data = request.get_json() or {}
        starred = data.get("starred", True)

        service = get_wechat_contact_service()
        # 兼容：旧服务提供 star_contact；新应用服务使用 update_contact
        star_fn = getattr(service, "star_contact", None)
        if callable(star_fn):
            result = star_fn(contact_id, starred)
        else:
            result = service.update_contact(contact_id=contact_id, is_starred=starred)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"操作失败：{str(e)}"
        }), 500


@wechat_bp.route("/contacts/unstar-all", methods=["POST"])
@swag_from({
    "summary": "取消所有联系人星标",
    "description": "清除所有联系人的星标状态",
    "responses": {
        "200": {"description": "操作成功"},
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contacts_unstar_all():
    """取消所有联系人星标"""
    try:
        service = get_wechat_contact_service()
        result = service.unstar_all()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"操作失败：{str(e)}"
        }), 500


@wechat_bp.route("/contacts/<int:contact_id>/context", methods=["GET"])
@swag_from({
    "summary": "获取联系人聊天上下文",
    "description": "获取与指定联系人的聊天历史消息记录",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人ID",
            "required": True
        }
    ],
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "messages": {"type": "array"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_contact_context(contact_id):
    """获取联系人聊天上下文"""
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


@wechat_bp.route("/scan", methods=["POST"])
@swag_from({
    "summary": "触发微信消息扫描",
    "description": "手动触发微信消息扫描任务，可指定联系人和扫描数量",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "schema": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer", "description": "指定联系人ID（可选）"},
                    "limit": {"type": "integer", "description": "扫描消息数量限制，默认20"}
                }
            }
        }
    ],
    "responses": {
        "202": {
            "description": "扫描任务已触发",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "task_id": {"type": "string"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def wechat_scan():
    """触发微信消息扫描"""
    try:
        data = request.get_json() or {}
        contact_id = data.get("contact_id")
        limit = data.get("limit", 20)

        from app.tasks.wechat_tasks import scan_wechat_messages
        task = scan_wechat_messages.delay(contact_id=contact_id, limit=limit)

        return jsonify({
            "success": True,
            "message": "扫描任务已触发",
            "task_id": task.id,
            "count": 0
        }), 202

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"扫描失败：{str(e)}"
        }), 500


@wechat_bp.route("/status", methods=["GET"])
@swag_from({
    "summary": "获取微信登录状态",
    "description": "检查微信是否已登录",
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "logined": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def wechat_status():
    """获取微信登录状态"""
    try:
        import sys

        from app.utils.path_utils import get_resource_path

        wechat_cv_path = get_resource_path("wechat_cv")
        if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
            sys.path.insert(0, wechat_cv_path)
        from wechat_cv_send import _find_wechat_handle
        hwnd = _find_wechat_handle()
        is_logined = hwnd is not None
        
        return jsonify({
            "success": True,
            "logined": is_logined,
            "message": "微信已登录" if is_logined else "微信未登录"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "logined": False,
            "message": f"检测失败：{str(e)}"
        }), 200


@wechat_bp.route("/test", methods=["GET"])
@swag_from({
    "summary": "测试微信服务",
    "description": "测试接口，用于检查微信服务是否正常运行",
    "responses": {
        "200": {
            "description": "服务正常",
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
def wechat_test():
    """测试接口"""
    return jsonify({
        "success": True,
        "message": "微信服务运行正常"
    }), 200
