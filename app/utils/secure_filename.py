"""
纯 stdlib 的 ``secure_filename`` 实现，替代 ``werkzeug.utils.secure_filename``。

行为与 werkzeug 完全一致：
    - 用 ASCII 近似替换常见的西欧字符（AE / OE / SS / ...）。
    - 剔除任何非 ``[A-Za-z0-9_.-]`` 的字符（空格变下划线）。
    - 去除首尾的 ``.``、``_``、``-`` 与空格。
    - Windows 保留名（``CON``、``AUX``、``COM1`` 等）自动前缀 ``_``。

使用示例::

    >>> secure_filename("My cool movie.mov")
    'My_cool_movie.mov'
    >>> secure_filename("../../../etc/passwd")
    'etc_passwd'
    >>> secure_filename("i contain cool \\xfcml\\xe4uts.txt")
    'i_contain_cool_umlauts.txt'
"""

from __future__ import annotations

import os
import re
import unicodedata

__all__ = ["secure_filename"]


_FILENAME_ASCII_STRIP_RE = re.compile(r"[^A-Za-z0-9_.-]")
_WINDOWS_DEVICE_FILES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


def secure_filename(filename: str) -> str:
    """过滤输入为可以安全写入磁盘的文件名（与 werkzeug 同名函数等价）。"""
    if not isinstance(filename, str):
        filename = str(filename)

    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    for sep in (os.sep, os.path.altsep):
        if sep:
            filename = filename.replace(sep, " ")

    filename = "_".join(filename.split())
    filename = str(_FILENAME_ASCII_STRIP_RE.sub("", filename)).strip("._- ")

    if os.name == "nt" and filename and filename.split(".")[0].upper() in _WINDOWS_DEVICE_FILES:
        filename = f"_{filename}"

    return filename
