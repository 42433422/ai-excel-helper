# -*- coding: utf-8 -*-
"""
意图识别配置 v2

支持热更新：修改此文件后调用 reload_intent_config() 即可生效，无需重启服务
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "intent_config.yaml"

_intent_config: Optional[Dict[str, Any]] = None
_config_mtime: float = 0


def _load_config() -> Dict[str, Any]:
    """加载配置文件"""
    global _intent_config, _config_mtime

    if not CONFIG_FILE.exists():
        logger.warning(f"意图配置文件不存在: {CONFIG_FILE}，使用默认配置")
        return _get_default_config()

    current_mtime = CONFIG_FILE.stat().st_mtime
    if _intent_config is None or current_mtime > _config_mtime:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                _intent_config = yaml.safe_load(f)
            _config_mtime = current_mtime
            logger.info(f"意图配置已加载: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"加载意图配置失败: {e}")
            _intent_config = _get_default_config()

    return _intent_config or _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """获取默认配置"""
    return {
        "negation": {
            "prefixes": [
                "不要", "别", "不用", "不需要", "不必", "取消", "别给我", "别帮我",
                "不用了", "不要了", "算了", "不生成", "不开发", "不导入", "不上传",
                "不想", "不用帮我", "别弄", "不用弄", "不用做", "不要做",
            ],
            "phrases": [
                "不要生成", "别生成", "不用生成", "不要开发货单", "别开发货单", "不要开单", "别开单",
                "不要上传", "别上传", "不用上传", "不要导入", "别导入",
                "不要打印", "别打印", "不用打印", "取消打印", "不打印", "不要打标签",
            ]
        },
        "greeting": {
            "patterns": [
                "你好", "您好", "嗨", "嗨喽", "hello", "hi", "早上好", "下午好", "晚上好",
                "在吗", "在么", "有人吗", "在不在", "在不在呀",
            ]
        },
        "goodbye": {
            "patterns": [
                "再见", "拜拜", "bye", "先这样", "没事了", "谢谢再见", "好的谢谢", "先忙",
            ]
        },
        "help": {
            "patterns": [
                "你能做什么", "你会什么", "有什么功能", "怎么用", "帮助", "帮帮我",
                "功能介绍", "说明一下", "有什么可以帮", "能干啥", "支持什么", "怎么操作",
            ]
        },
        "tool_intents": [
            {
                "id": "shipment_generate",
                "keywords": [
                    "生成发货单", "发货单生成", "做发货单", "开发货单", "生成送货单",
                    "开单", "打单", "开送货单", "做出货单", "生成出货单",
                ],
                "priority": 12,
                "tool_key": "shipment_generate",
                "block_if_negated": True,
                "patterns": [
                    r"^发货单(.+?)\s*(\d+)\s*桶",
                    r"^送货单(.+?)\s*(\d+)\s*箱",
                    r"^出货单(.+?)\s*(\d+)\s*件",
                ]
            },
            {
                "id": "wechat_send",
                "keywords": [
                    "发给他", "发送", "发微信", "发消息", "转发给他", "发一下", "发给",
                    "转给他", "发给对方", "发过去", "发消息给", "发送消息给", "发送给",
                ],
                "priority": 10,
                "tool_key": "wechat_send",
                "block_if_negated": True,
            },
            {
                "id": "shipment_template",
                "keywords": [
                    "发货单模板", "模板", "抬头", "购货单位", "联系人", "订单编号",
                    "当前模板", "现在用的模板", "哪个模板", "词条", "可编辑词条",
                ],
                "priority": 9,
                "tool_key": "shipment_template",
                "block_if_negated": False,
            },
            {
                "id": "excel_decompose",
                "keywords": [
                    "分解 excel", "解析 excel", "分解模板", "提取词条", "excel 模板", "表头",
                    "解析模板", "表头提取", "词条提取", "分解表",
                ],
                "priority": 9,
                "tool_key": "excel_decompose",
                "block_if_negated": False,
            },
            {
                "id": "excel_analyzer",
                "keywords": [
                    "分析 excel", "分析模板", "模板分析", "excel 结构", "Excel 分析",
                    "模板结构", "可编辑区域", "表头分析", "分析表结构", "查看模板",
                ],
                "priority": 8,
                "tool_key": "excel_analyzer",
                "block_if_negated": False,
            },
            {
                "id": "shipments",
                "keywords": ["出货", "订单", "发货", "出货单", "发货记录", "订单列表"],
                "priority": 8,
                "tool_key": "shipments",
                "block_if_negated": False,
            },
            {
                "id": "products",
                "keywords": ["产品", "商品", "型号", "产品列表", "产品库", "规格"],
                "priority": 7,
                "tool_key": "products",
                "block_if_negated": False,
            },
            {
                "id": "customers",
                "keywords": [
                    "客户", "顾客", "单位", "用户列表", "用户名单", "购买单位", "单位列表",
                    "客户列表", "用户清单", "客户名单",
                ],
                "priority": 6,
                "tool_key": "customers",
                "block_if_negated": False,
            },
            {
                "id": "show_images",
                "keywords": ["图片", "照片", "图片列表", "查看图片", "看图片", "打开图片"],
                "priority": 6,
                "tool_key": "show_images",
                "block_if_negated": False,
            },
            {
                "id": "show_videos",
                "keywords": ["视频", "录像", "视频列表", "查看视频", "看视频", "打开视频"],
                "priority": 6,
                "tool_key": "show_videos",
                "block_if_negated": False,
            },
            {
                "id": "print_label",
                "keywords": [
                    "打印", "标签", "打印标签", "商标导出", "标签导出", "下载标签", "打标签",
                    "商标打印", "商标",
                ],
                "priority": 5,
                "tool_key": "print_label",
                "block_if_negated": True,
            },
            {
                "id": "upload_file",
                "keywords": ["上传", "导入", "解析", "上传文件", "导入文件", "上传 excel"],
                "priority": 5,
                "tool_key": "upload_file",
                "block_if_negated": True,
            },
            {
                "id": "materials",
                "keywords": ["原材料", "材料", "库存", "原材料库存", "库存查询", "材料库"],
                "priority": 4,
                "tool_key": "materials",
                "block_if_negated": False,
            },
        ],
        "hint_intents": [
            {
                "id": "template_query",
                "keywords": ["发货单模板", "当前模板", "现在用的模板", "现在模板", "哪个模板", "用的哪个模板"],
                "priority": 8,
            },
            {
                "id": "customer_export",
                "keywords": ["导出 excel", "导出 xlsx", "导出表格", "导出用户列表", "导出客户列表", "导出购买单位", "导出单位"],
                "priority": 7,
            },
            {
                "id": "customer_list",
                "keywords": ["查看用户列表", "用户列表", "用户名单", "查看用户", "客户列表", "查看客户列表", "购买单位列表"],
                "priority": 7,
            },
            {
                "id": "customer_edit",
                "keywords": ["改成", "修改", "更新", "设为", "设置为", "改一下", "改下"],
                "priority": 5,
            },
            {
                "id": "customer_supplement",
                "keywords": ["联系人", "电话", "手机", "地址", "补充"],
                "priority": 6,
            },
        ],
        "confirmation_keywords": [
            "是", "好的", "确认", "没问题", "可以", "行", "执行", "开始", "来", "好", "同意", "就这么做", "对", "是的",
        ],
        "negation_keywords": [
            "否", "不要", "不用", "算了", "取消", "不用了", "不要了", "不对", "不是", "别", "停止", "终止",
        ],
    }


def get_intent_config() -> Dict[str, Any]:
    """获取意图配置（带缓存）"""
    return _load_config()


def reload_intent_config() -> Dict[str, Any]:
    """强制重新加载配置（热更新）"""
    global _intent_config, _config_mtime
    _intent_config = None
    _config_mtime = 0
    return _load_config()


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_config(config: Dict[str, Any]) -> bool:
    """保存配置到文件"""
    try:
        ensure_config_dir()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        reload_intent_config()
        return True
    except Exception as e:
        logger.error(f"保存意图配置失败: {e}")
        return False
