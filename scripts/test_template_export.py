"""
[已停用] 原脚本依赖已移除的 ``backend.*`` 模板栈。

请改用主应用中的 Excel/Word 文档模板能力（``app/fastapi_routes/excel_templates.py``、
``app/services/document_templates``）或通过 API 验证导出；若需旧行为，请从仓库归档中恢复对应模块。
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "test_template_export.py 已停用：backend 包已合并至 app/，" "本脚本未迁移。退出码 2。",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
