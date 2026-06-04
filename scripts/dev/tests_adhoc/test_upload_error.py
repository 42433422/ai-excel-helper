"""测试上传 API - 详细错误"""

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

print(f"发送 POST 请求到：{url}")
print(f'模板路径：{data["template_relpath"]}')

try:
    response = requests.post(url, files=files, data=data, timeout=60)
    print(f"\n状态码：{response.status_code}")
    print(f"响应：{response.json()}")

    if response.status_code != 200:
        print(f"\n错误详情:")
        print(f"  请求 URL: {response.url}")
        print(f"  请求头：{dict(response.request.headers)}")
        print(f"  请求体：{response.request.body[:500] if response.request.body else None}")

except Exception as e:
    print(f"\n请求失败：{e}")
    import traceback

    traceback.print_exc()
