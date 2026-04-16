"""WORKSPACE_ROOT 下安全解析 Excel 相对路径。"""

from __future__ import annotations

import os
from pathlib import Path


def workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()


def resolve_workspace_excel(relpath: str) -> Path:
    root = workspace_root()
    if not root.is_dir():
        raise FileNotFoundError(f"workspace root is not a directory: {root}")

    raw = Path(str(relpath or "").strip())
    if ".." in raw.parts:
        raise PermissionError("path must not contain '..'")

    candidate = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise PermissionError("path must resolve inside WORKSPACE_ROOT") from e

    suf = candidate.suffix.lower()
    if suf not in (".xlsx", ".xlsm", ".xls"):
        raise ValueError("only Excel files (.xlsx, .xlsm, .xls) are supported")

    # 检查文件是否存在（处理中文文件名编码问题）
    if not candidate.is_file():
        # 尝试通过目录列表来验证文件是否存在
        parent_dir = candidate.parent
        file_name = candidate.name
        try:
            dir_contents = os.listdir(str(parent_dir))
            # 通过去除空格的方式比较文件名
            normalized_file_name = file_name.replace(' ', '')
            for f in dir_contents:
                if f.replace(' ', '') == normalized_file_name:
                    # 找到匹配的文件，返回原始 candidate
                    # 注意：candidate.is_file() 可能返回 False，但文件实际存在
                    # 后续代码需要通过目录列表方式访问
                    return candidate
            # 没有找到匹配的文件
            raise FileNotFoundError(f"文件不存在：{relpath}")
        except Exception:
            raise FileNotFoundError(f"文件不存在：{relpath}")

    return candidate


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
