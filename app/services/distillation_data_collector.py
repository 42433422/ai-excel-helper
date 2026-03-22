# -*- coding: utf-8 -*-
"""
蒸馏数据采集服务

从 DeepSeek API 批量生成意图识别训练数据，用于微调 BERT 模型。

数据来源：
1. 规则引擎覆盖的真实用户 query（人工标注）
2. 基于 DeepSeek 批量生成的高置信度伪标签数据

使用方法：
    python -m app.services.distillation_data_collector
"""

import json
import logging
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DISTILL_DIR = os.path.join(BASE_DIR, "distillation")
DB_PATH = os.path.join(DISTILL_DIR, "distillation.db")
LOG_DIR = os.path.join(DISTILL_DIR, "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


INTENT_LABELS = [
    "shipment_generate",
    "customers",
    "products",
    "shipments",
    "wechat_send",
    "print_label",
    "upload_file",
    "materials",
    "shipment_template",
    "excel_decompose",
    "show_images",
    "show_videos",
    "greet",
    "goodbye",
    "help",
    "negation",
    "customer_export",
    "customer_edit",
    "customer_supplement",
]

SAMPLE_QUERIES = {
    "shipment_generate": [
        "生成发货单给七彩乐园",
        "开发货单，3桶规格20的PE白底漆",
        "帮侯雪梅开一张发货单",
        "做出货单，5桶20kg规格的",
        "打单给向总",
        "发货单七彩乐园2桶28规格",
        "我要给恒达公司开单",
        "生成一张发货单，客户是利民厂",
        "帮客户做发货单，数量3桶",
    ],
    "customers": [
        "查看客户列表",
        "购买单位有哪些",
        "显示所有客户",
        "我想看客户信息",
        "客户名单在哪",
        "都有哪些购买单位",
    ],
    "products": [
        "查看产品列表",
        "产品库有哪些",
        "显示产品规格",
        "产品型号有什么",
        "PE白底漆的规格",
        "查一下产品信息",
    ],
    "shipments": [
        "查看发货记录",
        "最近的发货单",
        "订单列表",
        "出货记录查询",
        "我的订单有哪些",
    ],
    "wechat_send": [
        "发微信给客户",
        "发送微信消息",
        "发消息通知向总",
    ],
    "print_label": [
        "打印标签",
        "导出商标",
        "标签打印",
        "产品标签怎么打印",
        "导出产品标签",
    ],
    "upload_file": [
        "上传文件",
        "导入Excel",
        "解析发货单文件",
        "上传数据文件",
    ],
    "materials": [
        "查看原材料库存",
        "材料库查询",
        "还有多少原料",
    ],
    "shipment_template": [
        "发货单模板",
        "查看模板设置",
        "模板是什么",
    ],
    "excel_decompose": [
        "分解Excel",
        "提取词条",
        "表头提取",
    ],
    "show_images": [
        "查看图片",
        "产品图片",
        "显示图片",
    ],
    "show_videos": [
        "查看视频",
        "产品视频",
    ],
    "greet": [
        "你好",
        "您好",
        "早上好",
        "hello",
        "hi",
    ],
    "goodbye": [
        "再见",
        "拜拜",
        "退出",
        "关闭",
    ],
    "help": [
        "帮助",
        "怎么用",
        "功能介绍",
        "教我使用",
    ],
    "negation": [
        "不要开单",
        "别发消息",
        "取消订单",
        "不要打印",
    ],
    "customer_export": [
        "导出客户列表",
        "导出Excel",
        "下载客户数据",
    ],
    "customer_edit": [
        "修改客户信息",
        "编辑客户",
        "更新客户资料",
    ],
    "customer_supplement": [
        "补充客户信息",
        "添加联系人",
        "完善客户资料",
    ],
}


def init_distillation_db():
    """初始化蒸馏数据库"""
    os.makedirs(DISTILL_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distillation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            intent TEXT NOT NULL,
            slots TEXT,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_for_training INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_intent ON distillation_log(intent)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_used ON distillation_log(used_for_training)
    """)

    conn.commit()
    conn.close()
    logger.info(f"蒸馏数据库初始化完成: {DB_PATH}")


def get_deepseek_api_key() -> str:
    """获取 DeepSeek API Key"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key

    config_path = os.path.join(BASE_DIR, "resources", "config", "deepseek_config.py")
    if os.path.exists(config_path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("deepseek_config", config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                return getattr(config_module, "DEEPSEEK_API_KEY", "") or ""
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")

    return ""


async def call_deepseek_intent(api_key: str, message: str) -> Optional[Dict[str, Any]]:
    """调用 DeepSeek API 进行意图识别"""
    import httpx

    if not api_key:
        logger.error("DeepSeek API Key 未配置")
        return None

    intent_list = "\n".join([f"- {k}: {v}" for k, v in {
        "shipment_generate": "生成发货单、开单、打单",
        "customers": "查看客户列表",
        "products": "查看产品列表",
        "shipments": "查看发货记录",
        "wechat_send": "发微信",
        "print_label": "打印标签",
        "upload_file": "上传文件",
        "materials": "原材料库存",
        "shipment_template": "发货单模板",
        "excel_decompose": "分解Excel",
        "show_images": "查看图片",
        "show_videos": "查看视频",
        "greet": "问候",
        "goodbye": "告别",
        "help": "请求帮助",
        "negation": "否定指令",
        "customer_export": "导出客户",
        "customer_edit": "修改客户",
        "customer_supplement": "补充客户",
    }.items()])

    slot_list = "\n".join([
        "unit_name: 购买单位",
        "quantity_tins: 桶数",
        "tin_spec: 规格",
    ])

    system_prompt = f"""你是一个业务助手意图分类器。根据用户消息，识别意图和提取关键信息。

可选意图：
{intent_list}

槽位定义：
{slot_list}

回复格式（严格JSON）：
{{"intent": "意图ID", "slots": {{"槽位名": "槽位值"}}}}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                }
            )
            result = response.json()
            if result.get("choices"):
                content = result["choices"][0]["message"]["content"]
                data = json.loads(content)
                return {
                    "intent": data.get("intent", "unk"),
                    "slots": data.get("slots", {}),
                    "confidence": 1.0
                }
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")

    return None


def save_distillation_sample(query: str, intent: str, slots: Dict, confidence: float = 1.0, source: str = "manual"):
    """保存蒸馏样本到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO distillation_log (query, intent, slots, confidence, source)
        VALUES (?, ?, ?, ?, ?)
    """, (query, intent, json.dumps(slots, ensure_ascii=False), confidence, source))

    conn.commit()
    conn.close()


def generate_samples_from_queries(queries: Dict[str, List[str]]) -> int:
    """基于预定义 query 生成蒸馏样本（使用规则匹配，模拟 DeepSeek 结果）"""
    count = 0

    for intent, query_list in queries.items():
        for query in query_list:
            slots = {}

            if "给" in query:
                idx = query.index("给")
                after_give = query[idx+1:].strip().split()[0]
                if after_give and len(after_give) > 1:
                    slots["unit_name"] = after_give

            import re
            qty_match = re.search(r'(\d+)\s*桶', query)
            if qty_match:
                slots["quantity_tins"] = int(qty_match.group(1))

            spec_match = re.search(r'规格\s*(\d+)', query)
            if spec_match:
                slots["tin_spec"] = float(spec_match.group(1))

            save_distillation_sample(query, intent, slots, confidence=0.95, source="template")
            count += 1

    logger.info(f"生成了 {count} 个蒸馏样本")
    return count


async def collect_samples_via_deepseek(api_key: str, target_count: int = 500) -> int:
    """通过 DeepSeek API 收集真实样本"""
    import asyncio

    count = 0
    existing_count = get_sample_count()
    logger.info(f"当前样本数: {existing_count}, 目标: {target_count}")

    if existing_count >= target_count:
        logger.info("样本数量已满足要求")
        return 0

    all_queries = []
    for queries in SAMPLE_QUERIES.values():
        all_queries.extend(queries)

    needed = target_count - existing_count
    batch_size = 10

    for i in range(0, min(needed, 100), batch_size):
        batch = all_queries[i:i+batch_size]
        tasks = [call_deepseek_intent(api_key, q) for q in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for query, result in zip(batch, results):
            if isinstance(result, dict) and result.get("intent"):
                intent = result["intent"]
                if intent in INTENT_LABELS:
                    save_distillation_sample(
                        query, intent,
                        result.get("slots", {}),
                        result.get("confidence", 0.9),
                        source="deepseek"
                    )
                    count += 1
                else:
                    logger.warning(f"未知意图: {intent}, query: {query}")
            else:
                logger.warning(f"API 返回无效结果: {result}")

        logger.info(f"已收集 {count} 个新样本")
        await asyncio.sleep(0.5)

    return count


def get_sample_count(intent: Optional[str] = None) -> int:
    """获取样本数量"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if intent:
        cursor.execute("SELECT COUNT(*) FROM distillation_log WHERE intent = ?", (intent,))
    else:
        cursor.execute("SELECT COUNT(*) FROM distillation_log")

    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_sample_stats() -> Dict[str, int]:
    """获取各类别样本统计"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT intent, COUNT(*) FROM distillation_log GROUP BY intent")
    rows = cursor.fetchall()
    conn.close()

    return {intent: count for intent, count in rows}


def export_training_data(output_path: Optional[str] = None, format: str = "jsonl") -> str:
    """导出训练数据"""
    if output_path is None:
        output_path = os.path.join(DISTILL_DIR, "training_data.jsonl")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT query, intent, slots FROM distillation_log
        WHERE used_for_training = 0
        ORDER BY RANDOM()
        LIMIT 1000
    """)

    rows = cursor.fetchall()
    conn.close()

    if format == "jsonl":
        with open(output_path, "w", encoding="utf-8") as f:
            for query, intent, slots in rows:
                data = {
                    "text": query,
                    "label": intent,
                    "slots": json.loads(slots) if slots else {}
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
    elif format == "bert":
        with open(output_path.replace(".jsonl", "_bert.tsv"), "w", encoding="utf-8") as f:
            f.write("text\tlabel\n")
            for query, intent, slots in rows:
                f.write(f"{query}\t{intent}\n")

    logger.info(f"导出训练数据到: {output_path}, 共 {len(rows)} 条")
    return output_path


def mark_samples_as_used(ids: List[int]):
    """标记样本已用于训练"""
    if not ids:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    placeholders = ",".join("?" * len(ids))
    cursor.execute(f"UPDATE distillation_log SET used_for_training = 1 WHERE id IN ({placeholders})", ids)

    conn.commit()
    conn.close()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="蒸馏数据采集工具")
    parser.add_argument("--init", action="store_true", help="初始化数据库")
    parser.add_argument("--generate", action="store_true", help="从模板生成样本")
    parser.add_argument("--collect", action="store_true", help="通过 DeepSeek 收集样本")
    parser.add_argument("--target", type=int, default=500, help="目标样本数量")
    parser.add_argument("--export", action="store_true", help="导出训练数据")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")

    args = parser.parse_args()

    if args.init:
        init_distillation_db()
        return

    init_distillation_db()

    if args.generate:
        generate_samples_from_queries(SAMPLE_QUERIES)

    if args.collect:
        api_key = get_deepseek_api_key()
        if not api_key:
            logger.error("请设置 DEEPSEEK_API_KEY 环境变量")
            return
        await collect_samples_via_deepseek(api_key, args.target)

    if args.stats:
        stats = get_sample_stats()
        print("\n=== 样本统计 ===")
        for intent, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {intent}: {count}")
        print(f"\n总计: {sum(stats.values())} 条")

    if args.export:
        export_training_data()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
