#!/usr/bin/env python3
"""
XCAGI 统一入口迁移 - 冒烟测试脚本

测试内容：
1. XCAGI 后端服务是否可启动（端口 5000）
2. 关键 API 端点是否正常工作
3. 弃用的 8000 端口是否不再响应

使用方法：
    cd E:\FHD\XCAGI
    python run.py  # 在另一个终端启动服务

    cd E:\FHD
    python smoke_test.py
"""

import json
import sys
import time
import urllib.request
from urllib.error import URLError, HTTPError

# 测试配置
XCAGI_BASE = "http://127.0.0.1:5000"
LEGACY_BASE = "http://127.0.0.1:8000"

# 测试端点列表 (注意: 所有端点都带 /api 前缀)
TEST_ENDPOINTS = [
    # 健康检查
    ("/api/health", "GET", None, "健康检查"),
    # 模板库（前端「模板库」页 /api/excel/templates）
    ("/api/excel/templates", "GET", None, "Excel模板列表"),
    # LLM 模式
    ("/api/mode", "GET", None, "LLM模式查询"),
    # 数据库模式
    ("/api/db/mode", "GET", None, "数据库模式查询"),
    # Ollama 模型列表
    ("/api/ollama/models", "GET", None, "Ollama模型列表"),
    # 系统配置
    ("/api/system/config", "GET", None, "系统配置"),
]

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}[PASS] {msg}{RESET}")


def print_error(msg):
    print(f"{RED}[FAIL] {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}[WARN] {msg}{RESET}")


def print_info(msg):
    print(f"[INFO] {msg}")


def test_endpoint(base_url, endpoint, method, data, description):
    """测试单个端点"""
    url = f"{base_url}{endpoint}"
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")

        if data and method in ["POST", "PUT"]:
            req.data = json.dumps(data).encode("utf-8")

        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            try:
                json.loads(body)
                return True, resp.status, body[:200]
            except json.JSONDecodeError:
                return True, resp.status, body[:200]
    except HTTPError as e:
        return False, e.code, str(e.reason)
    except URLError as e:
        return False, 0, str(e.reason)
    except Exception as e:
        return False, 0, str(e)


def check_service_available(base_url, description):
    """检查服务是否可用（XCAGI 统一入口为 /api/health）"""
    print_info(f"检查 {description} ({base_url})...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print_success(f"{description} 服务正常运行")
                return True
    except Exception:
        pass
    return False


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("XCAGI 统一入口迁移 - 冒烟测试")
    print("=" * 60)
    print()

    # 1. 检查 XCAGI 服务
    print("【步骤 1】检查 XCAGI 服务 (5000 端口)...")
    if not check_service_available(XCAGI_BASE, "XCAGI 服务"):
        print_error("XCAGI 服务未启动或未响应")
        print_info("请先启动 XCAGI 服务：")
        print_info("  cd E:\\FHD\\XCAGI")
        print_info("  python run.py")
        return False
    print()

    # 2. 测试 XCAGI 端点
    print("【步骤 2】测试 XCAGI 关键端点 (5000 端口)...")
    passed = 0
    failed = 0

    for endpoint, method, data, description in TEST_ENDPOINTS:
        ok, status, body = test_endpoint(XCAGI_BASE, endpoint, method, data, description)
        if ok:
            print_success(f"{description}: {endpoint} (HTTP {status})")
            passed += 1
        else:
            print_error(f"{description}: {endpoint} (HTTP {status}, {body})")
            failed += 1
        time.sleep(0.1)  # 避免请求过快

    print()
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print()

    # 3. 检查旧服务是否已停止
    print("【步骤 3】确认旧服务 (8000 端口) 已停止...")
    try:
        req = urllib.request.Request(f"{LEGACY_BASE}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                # 检查响应中是否有弃用标记
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("deprecated"):
                    print_warning("旧服务仍在运行，但已标记为弃用")
                    print_info("建议停止旧服务，仅使用 XCAGI 服务")
                else:
                    print_error("旧服务仍在运行且未标记弃用")
                    print_info(
                        "请停止旧服务: 找到占用 8000 且使用 backend.http_app 的进程并停止（主栈为 XCAGI/run.py:5000）"
                    )
    except:
        print_success("旧服务 (8000 端口) 未运行或已停止 ✅")
    print()

    # 4. 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    if failed == 0:
        print_success("所有测试通过！XCAGI 统一入口工作正常。")
        print()
        print("下一步建议:")
        print("  1. 验证前端可以正常调用新端点")
        print("  2. 执行业务功能测试")
        print("  3. 确认无误后，可以删除旧代码")
        return True
    else:
        print_error(f"有 {failed} 个测试失败，请检查 XCAGI 服务状态")
        print()
        print("排查建议:")
        print("  1. 检查 XCAGI 服务日志")
        print("  2. 确认数据库连接正常")
        print("  3. 检查端口 5000 是否被占用")
        return False


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"测试过程出错: {e}")
        sys.exit(1)
