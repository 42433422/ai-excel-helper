# -*- coding: utf-8 -*-
"""会话与偏好 API"""
import logging

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.application import get_user_preference_app_service
from app.utils.json_safe import json_safe
from app.services.conversation_service import (
    get_conversation_service as get_conversation_app_service,
)


def get_conversation_service():
    return get_conversation_app_service()


def get_user_preference_service():
    return get_user_preference_app_service()

logger = logging.getLogger(__name__)
conversations_bp = Blueprint('conversations', __name__)


def _normalize_user_id_for_session(value):
    """会话表 user_id 是整数外键，兼容历史 default/空字符串。"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return None


def _session_to_dict(session: object) -> dict:
    """兼容 tuple / dict / ORM 对象的会话结构。"""
    if isinstance(session, dict):
        return {
            "session_id": session.get("session_id"),
            "user_id": session.get("user_id"),
            "title": session.get("title") or "新会话",
            "summary": session.get("summary") or "",
            "message_count": session.get("message_count", 0),
            "last_message_at": session.get("last_message_at"),
            "created_at": session.get("created_at"),
        }
    if isinstance(session, tuple):
        return {
            "session_id": session[1] if len(session) > 1 else None,
            "user_id": session[2] if len(session) > 2 else None,
            "title": (session[3] if len(session) > 3 else None) or "新会话",
            "summary": (session[4] if len(session) > 4 else None) or "",
            "message_count": session[5] if len(session) > 5 else 0,
            "last_message_at": session[6] if len(session) > 6 else None,
            "created_at": session[7] if len(session) > 7 else None,
        }
    return {
        "session_id": getattr(session, "session_id", None),
        "user_id": getattr(session, "user_id", None),
        "title": getattr(session, "title", None) or "新会话",
        "summary": getattr(session, "summary", "") or "",
        "message_count": getattr(session, "message_count", 0),
        "last_message_at": getattr(session, "last_message_at", None),
        "created_at": getattr(session, "created_at", None),
    }


def _message_to_dict(message: object) -> dict:
    """兼容 tuple / dict / ORM 对象的消息结构。"""
    if isinstance(message, dict):
        return {
            "id": message.get("id"),
            "session_id": message.get("session_id"),
            "user_id": message.get("user_id"),
            "role": message.get("role"),
            "content": message.get("content"),
            "intent": message.get("intent") or "",
            "metadata": message.get("metadata") or message.get("conversation_metadata") or "",
            "created_at": message.get("created_at"),
        }
    if isinstance(message, tuple):
        return {
            "id": message[0] if len(message) > 0 else None,
            "session_id": message[1] if len(message) > 1 else None,
            "user_id": message[2] if len(message) > 2 else None,
            "role": message[3] if len(message) > 3 else None,
            "content": message[4] if len(message) > 4 else None,
            "intent": (message[5] if len(message) > 5 else "") or "",
            "metadata": (message[6] if len(message) > 6 else "") or "",
            "created_at": message[7] if len(message) > 7 else None,
        }
    return {
        "id": getattr(message, "id", None),
        "session_id": getattr(message, "session_id", None),
        "user_id": getattr(message, "user_id", None),
        "role": getattr(message, "role", None),
        "content": getattr(message, "content", None),
        "intent": getattr(message, "intent", "") or "",
        "metadata": getattr(message, "conversation_metadata", "") or "",
        "created_at": getattr(message, "created_at", None),
    }


@conversations_bp.route('/api/conversations/sessions', methods=['GET'])
@swag_from({
    'summary': '获取会话列表',
    'description': '获取会话列表',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '用户 ID'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '返回数量限制'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'sessions': {'type': 'array'}
                }
            }
        }
    }
})
def get_conversation_sessions():
    """获取会话列表"""
    try:
        service = get_conversation_service()
        user_id = request.args.get('user_id', 'default')
        limit = int(request.args.get('limit', 20))
        sessions = service.get_sessions(user_id, limit)
        result = []
        for s in sessions:
            result.append(_session_to_dict(s))
        return jsonify(json_safe({"success": True, "sessions": result}))
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@conversations_bp.route('/api/conversations/<session_id>', methods=['GET'])
@swag_from({
    'summary': '获取会话详情',
    'description': '获取会话详情，包括会话信息和消息列表',
    'parameters': [
        {
            'name': 'session_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '会话 ID'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '返回数量限制'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'session': {
                        'type': 'object',
                        'properties': {
                            'session_id': {'type': 'string'},
                            'user_id': {'type': 'string'},
                            'title': {'type': 'string'},
                            'summary': {'type': 'string'},
                            'message_count': {'type': 'integer'},
                            'last_message_at': {'type': 'string'},
                            'created_at': {'type': 'string'}
                        }
                    },
                    'messages': {'type': 'array'}
                }
            }
        }
    }
})
def get_conversation_messages(session_id):
    """获取会话详情"""
    try:
        service = get_conversation_service()
        limit = int(request.args.get('limit', 50))

        # 先读 messages：测试要求当 get_session_messages 抛异常时返回 500
        messages = service.get_session_messages(session_id, limit)

        sessions = service.get_sessions(user_id=None, limit=1000)
        session_info = None
        for s in sessions:
            current = _session_to_dict(s)
            if current.get("session_id") == session_id:
                session_info = current
                break

        result = []
        for m in messages:
            result.append(_message_to_dict(m))
        return jsonify(
            json_safe({"success": True, "session": session_info, "messages": result})
        )
    except Exception as e:
        logger.error(f"获取会话详情失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@conversations_bp.route('/api/conversations/<session_id>/title', methods=['PUT'])
@swag_from({
    'summary': '更新会话标题',
    'description': '更新会话标题',
    'parameters': [
        {
            'name': 'session_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '会话 ID'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string', 'description': '新标题'}
                },
                'required': ['title']
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
        }
    }
})
def update_conversation_title(session_id):
    """更新会话标题"""
    try:
        service = get_conversation_service()
        data = request.get_json()
        title = data.get('title', '')
        success = service.update_session_title(session_id, title)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"更新会话标题失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@conversations_bp.route('/api/conversations/<session_id>', methods=['DELETE'])
@swag_from({
    'summary': '删除会话',
    'description': '删除会话',
    'parameters': [
        {
            'name': 'session_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '会话 ID'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'}
                }
            }
        }
    }
})
def delete_conversation(session_id):
    """删除会话"""
    try:
        service = get_conversation_service()
        success = service.delete_session(session_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@conversations_bp.route('/api/conversations/message', methods=['POST'])
@swag_from({
    'summary': '保存对话消息',
    'description': '保存对话消息到数据库，支持用户消息和 AI 助手消息',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['session_id', 'role', 'content'],
                'properties': {
                    'session_id': {'type': 'string', 'description': '会话 ID'},
                    'user_id': {'type': 'string', 'description': '用户 ID', 'default': 'default'},
                    'role': {'type': 'string', 'description': '角色', 'enum': ['user', 'assistant', 'system']},
                    'content': {'type': 'string', 'description': '消息内容'},
                    'intent': {'type': 'string', 'description': '消息意图（可选）'},
                    'metadata': {'type': 'string', 'description': '元数据（可选，JSON 字符串）'}
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
                    'message_id': {'type': 'integer', 'description': '消息 ID'}
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
def save_conversation_message():
    """
    保存对话消息
    
    Request Body:
        - session_id: 会话 ID（必填）
        - user_id: 用户 ID（可选，默认'default'）
        - role: 角色（必填），可选值：user, assistant, system
        - content: 消息内容（必填）
        - intent: 消息意图（可选）
        - metadata: 元数据（可选，JSON 字符串）
        
    Response:
        - success: 是否成功
        - message_id: 消息 ID
    """
    try:
        service = get_conversation_service()
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请求数据不能为空"
            }), 400
        
        session_id = data.get('session_id')
        user_id = _normalize_user_id_for_session(data.get('user_id', 'default'))
        role = data.get('role')
        content = data.get('content')
        intent = data.get('intent', '')
        metadata = data.get('metadata', '')
        
        if not session_id:
            return jsonify({
                "success": False,
                "message": "会话 ID 不能为空"
            }), 400
        
        if not role:
            return jsonify({
                "success": False,
                "message": "角色不能为空"
            }), 400
        
        # 兼容前端历史字段：ai/bot -> assistant
        if role in ['ai', 'bot']:
            role = 'assistant'

        if role not in ['user', 'assistant', 'system']:
            return jsonify({
                "success": False,
                "message": f"无效的角色：{role}，可选值：user, assistant, system"
            }), 400
        
        if not content:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空"
            }), 400
        
        message_id = service.save_message(
            session_id, user_id, role, content, intent, metadata
        )
        
        return jsonify({
            "success": True,
            "message_id": message_id
        })
        
    except Exception as e:
        logger.error(f"保存对话消息失败：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"保存失败：{str(e)}"
        }), 500


@conversations_bp.route('/api/ai/conversation/new', methods=['POST'])
@swag_from({
    'summary': '创建新会话',
    'description': '创建新的 AI 对话会话',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': False,
            'schema': {
                'type': 'object',
                'properties': {
                    'user_id': {'type': 'string', 'description': '用户 ID'},
                    'title': {'type': 'string', 'description': '会话标题'}
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
                    'session_id': {'type': 'string'}
                }
            }
        }
    }
})
def create_new_conversation():
    """创建新会话"""
    try:
        service = get_conversation_service()
        data = request.get_json() or {}
        user_id = _normalize_user_id_for_session(data.get('user_id', 'default'))
        title = data.get('title')
        session_id = service.create_session(user_id, title)
        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        logger.error(f"创建新会话失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@conversations_bp.route('/api/ai/message/save', methods=['POST'])
@swag_from({
    'summary': '保存 AI 对话消息',
    'description': '保存 AI 对话消息（/api/conversations/message 的别名）',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': '会话 ID'},
                    'role': {'type': 'string', 'description': '角色'},
                    'content': {'type': 'string', 'description': '内容'}
                },
                'required': ['session_id', 'role', 'content']
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
                    'message_id': {'type': 'string'}
                }
            }
        }
    }
})
def save_ai_message():
    """保存 AI 对话消息（/api/conversations/message 的别名）"""
    return save_conversation_message()


@conversations_bp.route('/api/preferences', methods=['GET'])
@swag_from({
    'summary': '获取用户偏好',
    'description': '获取用户的所有偏好设置',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '用户 ID',
            'default': 'default'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'preferences': {
                        'type': 'object',
                        'description': '偏好设置字典，key 为偏好键，value 为偏好值',
                        'additionalProperties': {'type': 'string'}
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
def get_user_preferences():
    """
    获取用户偏好设置
    
    Query Parameters:
        - user_id: 用户 ID（可选，默认'default'）
        
    Response:
        - success: 是否成功
        - preferences: 偏好设置字典 {key: value}
    """
    try:
        service = get_user_preference_service()
        user_id = request.args.get('user_id', 'default')
        prefs = service.get_all_preferences(user_id)
        return jsonify({
            "success": True,
            "preferences": prefs
        })
    except Exception as e:
        logger.error(f"获取用户偏好失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取失败：{str(e)}"
        }), 500


@conversations_bp.route('/api/preferences', methods=['POST'])
@swag_from({
    'summary': '设置用户偏好',
    'description': '设置或更新用户的偏好设置',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['key', 'value'],
                'properties': {
                    'user_id': {'type': 'string', 'description': '用户 ID', 'default': 'default'},
                    'key': {'type': 'string', 'description': '偏好键'},
                    'value': {'type': 'string', 'description': '偏好值'}
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
def set_user_preference():
    """
    设置用户偏好
    
    Request Body:
        - user_id: 用户 ID（可选，默认'default'）
        - key: 偏好键（必填）
        - value: 偏好值（必填）
        
    Response:
        - success: 是否成功
    """
    try:
        service = get_user_preference_service()
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请求数据不能为空"
            }), 400
        
        user_id = data.get('user_id', 'default')
        preference_key = data.get('key')
        preference_value = data.get('value')
        
        if not preference_key:
            return jsonify({
                "success": False,
                "message": "偏好键不能为空"
            }), 400
        
        if preference_value is None:
            return jsonify({
                "success": False,
                "message": "偏好值不能为空"
            }), 400
        
        success = service.set_preference(user_id, preference_key, str(preference_value))
        
        return jsonify({
            "success": success,
            "message": "偏好设置已保存" if success else "偏好设置保存失败"
        })
        
    except Exception as e:
        logger.error(f"设置用户偏好失败：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"设置失败：{str(e)}"
        }), 500


@conversations_bp.route('/api/preferences/<key>', methods=['DELETE'])
@swag_from({
    'summary': '删除用户偏好',
    'description': '删除用户的指定偏好设置',
    'parameters': [
        {
            'name': 'key',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '偏好键'
        },
        {
            'name': 'user_id',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '用户 ID',
            'default': 'default'
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
def delete_user_preference(key):
    """
    删除用户偏好
    
    Path Parameters:
        - key: 偏好键（必填）
        
    Query Parameters:
        - user_id: 用户 ID（可选，默认'default'）
        
    Response:
        - success: 是否成功
    """
    try:
        service = get_user_preference_service()
        user_id = request.args.get('user_id', 'default')
        success = service.delete_preference(user_id, key)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"偏好设置 '{key}' 已删除"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"偏好设置 '{key}' 不存在或删除失败"
            })
            
    except Exception as e:
        logger.error(f"删除用户偏好失败：{e}")
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500
