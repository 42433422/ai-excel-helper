# -*- coding: utf-8 -*-
from app.services.intent_service import recognize_intents

test_cases = [
    '生成发货单',
    '产品列表',
    '客户列表',
    '你好',
    '不要发货单',
]

print('意图识别测试:')
for msg in test_cases:
    r = recognize_intents(msg)
    print(f'{msg}: tool_key={r.get("tool_key")}, primary_intent={r.get("primary_intent")}')
