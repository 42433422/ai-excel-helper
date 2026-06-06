#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""专业模式诊断工具 - 检查为什么发送消息没有回复。从仓库根目录解析路径。"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    os.chdir(REPO_ROOT)

    print("=" * 60)
    print("专业模式诊断报告")
    print("=" * 60)

    api_key_env = os.environ.get("DEEPSEEK_API_KEY", "")
    print("\n1. 环境变量 DEEPSEEK_API_KEY:")
    if api_key_env:
        print(f"   ✅ 已配置 (长度: {len(api_key_env)} 字符)")
        print(f"   前缀: {api_key_env[:8]}...")
    else:
        print("   ❌ 未配置")

    config_path = REPO_ROOT / "resources" / "config" / "deepseek_config.py"
    print(f"\n2. 配置文件 {config_path}:")
    config_key = ""
    if config_path.is_file():
        content = config_path.read_text(encoding="utf-8")
        match = re.search(r'DEEPSEEK_API_KEY\s*=\s*["\']([^"\']*)["\']', content)
        if match:
            config_key = match.group(1)
            if config_key:
                print(f"   ✅ 已配置 (长度: {len(config_key)} 字符)")
                print(f"   前缀: {config_key[:8]}...")
            else:
                print("   ❌ 未配置（空字符串）")
        else:
            print("   ⚠️  无法解析配置")
    else:
        print("   ❌ 文件不存在")

    print("\n3. 实际使用的 API Key:")
    final_key = api_key_env or config_key
    if final_key:
        print(f"   ✅ 可用 (长度: {len(final_key)})")
    else:
        print("   ❌ 不可用 - 这就是专业模式无回复的原因！")

    print("\n4. 测试 DeepSeek API 连通性:")
    if final_key:
        try:
            req_data = json.dumps(
                {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "你好"}],
                    "max_tokens": 10,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {final_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                print("   ✅ API 调用成功！")
                reply = result["choices"][0]["message"]["content"]
                print(f"   AI 回复: {reply[:50]}...")
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ API 调用失败: {error_msg[:100]}")
            if "401" in error_msg or "Unauthorized" in error_msg:
                print("   原因: API Key 无效或过期")
            elif "timeout" in error_msg.lower():
                print("   原因: 网络超时，可能需要代理")
            elif "connection" in error_msg.lower():
                print("   原因: 无法连接到 DeepSeek 服务器")
    else:
        print("   ⏭️  跳过（无 API Key）")

    print("\n" + "=" * 60)
    print("诊断结论:")
    print("=" * 60)

    if final_key:
        print("✅ 配置正确，专业模式应该可以正常工作")
        print("")
        print("如果前端仍然没有回复，请检查：")
        print("  1. 浏览器控制台是否有错误信息")
        print("  2. 后端日志是否有异常（查看终端输出）")
        print("  3. 网络连接是否正常")
        print('  4. 是否勾选了"专业模式AI意图体验"复选框')
    else:
        print("❌ DEEPSEEK_API_KEY 未配置")
        print("")
        print("这就是专业模式下发送消息没有回复的根本原因！")
        print("")
        print("解决方案（任选其一）：")
        print("")
        print("  方案 A: 设置环境变量（临时）")
        print("    Windows CMD:")
        print("      set DEEPSEEK_API_KEY=sk-your-key-here")
        print("    Windows PowerShell:")
        print('      $env:DEEPSEEK_API_KEY="sk-your-key-here"')
        print("    Linux/Mac:")
        print("      export DEEPSEEK_API_KEY=sk-your-key-here")
        print("")
        print("  方案 B: 编辑配置文件（永久）")
        print(f"    编辑文件: {config_path}")
        print("    将 DEEPSEEK_API_KEY 设为有效值")
        print("")
        print("获取 API Key: https://platform.deepseek.com/")
        print("")
        print("配置完成后，重启后端服务即可。")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
    sys.exit(0)
