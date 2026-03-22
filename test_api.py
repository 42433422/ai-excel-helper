# -*- coding: utf-8 -*-
import requests
import json

resp = requests.get("http://localhost:5000/api/wechat_contacts/1/context")
data = resp.json()
print(f"Success: {data.get('success')}")
print(f"Count: {data.get('count')}")
messages = data.get('messages', [])
print(f"Messages: {len(messages)}")

if messages:
    # Check first message in detail
    msg = messages[0]
    text = msg.get('text', '')
    print(f"\nFirst message text (first 100 chars):")
    print(repr(text[:100]))
    print(f"\nText starts with: {text[:20]}")
    # Check if it's the XML or garbled
    if text.startswith('<'):
        print("Message starts with '<' - looks like XML")
    elif text.startswith('('):
        print("Message starts with '(' - looks like raw bytes")
    else:
        print(f"Message starts with: {repr(text[:20])}")