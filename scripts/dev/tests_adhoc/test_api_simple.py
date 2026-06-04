"""测试 API 调用"""

import requests
import json
import os

url = "http://127.0.0.1:8000/api/mod/taiyangniao-pro/attendance/convert-upload"
source_file = r"e:\FHD\424\钉钉导出来的考勤数据.xlsx"
template_file = r"e:\FHD\424\考勤-2026-3月份考勤统计表.xlsx"

print(f"源文件存在: {os.path.exists(source_file)}")
print(f"模板文件存在: {os.path.exists(template_file)}")

# 测试1：不带模板
print("\n=== 测试1：不带模板 ===")
with open(source_file, "rb") as f:
    files = {
        "file": (
            "钉钉导出来的考勤数据.xlsx",
            f,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    data = {
        "output_relpath": "424/测试_无模板.xlsx",
        "month": "2026-03",
        "template_relpath": "",  # 空模板
        "sheet": "0",
        "header_row": "2",
    }
    try:
        response = requests.post(url, files=files, data=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"请求失败: {e}")

# 测试2：带模板（正确路径）
print("\n=== 测试2：带模板 ===")
with open(source_file, "rb") as f:
    files = {
        "file": (
            "钉钉导出来的考勤数据.xlsx",
            f,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    data = {
        "output_relpath": "424/测试_有模板.xlsx",
        "month": "2026-03",
        "template_relpath": "424/考勤-2026-3月份考勤统计表.xlsx",  # 注意：没有空格
        "sheet": "0",
        "header_row": "2",
    }
    try:
        response = requests.post(url, files=files, data=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"请求失败: {e}")

print("\n测试完成")
