"""调试上传 API"""

import requests
import os
import sys

# 测试文件路径
test_file = r"e:\FHD\424\钉钉导出来的考勤数据.xlsx"
template_file = r"e:\FHD\424\考勤 -2026-3 月份考勤统计表.xlsx"

# API 端点
url = "http://localhost:8000/api/mod/taiyangniao-pro/attendance/convert-upload"

# 准备表单数据
files = {
    "file": (
        "钉钉导出来的考勤数据.xlsx",
        open(test_file, "rb"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
}

data = {
    "output_relpath": "424/测试上传输出.xlsx",
    "template_relpath": "424/考勤 -2026-3 月份考勤统计表.xlsx",
    "month": "2026-03",
    "sheet": "打卡时间",
    "header_row": "0",
}

print(f"发送请求到：{url}")
print(f"文件：{test_file}")
print(f"模板：{template_file}")

try:
    response = requests.post(url, files=files, data=data, timeout=30)
    print(f"\n状态码：{response.status_code}")
    print(f"响应头：{dict(response.headers)}")
    print(f"响应内容：{response.text[:500]}")
    try:
        print(f"响应 JSON: {response.json()}")
    except:
        pass
except requests.exceptions.Timeout:
    print("\n请求超时")
except requests.exceptions.ConnectionError as e:
    print(f"\n连接错误：{e}")
except Exception as e:
    print(f"\n请求失败：{e}")
    import traceback

    traceback.print_exc()
