"""测试完整转换流程"""

import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

from pathlib import Path
from taiyangniao_attendance.convert import convert_dingtalk_file

source_file = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")
output_file = Path(r"e:\FHD\424\考勤转换输出_测试.xlsx")
template_file = Path(r"e:\FHD\424\考勤 -2026-3 月份考勤统计表.xlsx")

print(f"源文件：{source_file}")
print(f"模板：{template_file}")
print(f"输出：{output_file}")

try:
    result = convert_dingtalk_file(
        source_file,
        output_file,
        month="2026-03",
        sheet="打卡时间",
        header_row=2,
        template_path=template_file,
    )
    print(f"\n✓ 转换成功！")
    print(f"结果：{result}")
except Exception as e:
    print(f"\n✗ 转换失败：{e}")
    import traceback

    traceback.print_exc()
