"""直接测试 convert_dingtalk_file 函数"""

import sys

sys.path.insert(0, r"e:\FHD\backend")

from pathlib import Path
from shell.taiyangniao_attendance.convert import convert_dingtalk_file

source = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")
output = Path(r"e:\FHD\424\测试_直接转换.xlsx")
template = Path(r"e:\FHD\424\考勤-2026-3月份考勤统计表.xlsx")

print(f"源文件: {source}, 存在: {source.exists()}")
print(f"输出文件: {output}")
print(f"模板文件: {template}, 存在: {template.exists()}")

try:
    result = convert_dingtalk_file(
        source=source,
        output=output,
        month="2026-03",
        sheet=0,
        header_row=2,
        template_path=template,
    )
    print(f"\n结果: {result}")
except Exception as e:
    import traceback

    print(f"\n错误: {e}")
    traceback.print_exc()
