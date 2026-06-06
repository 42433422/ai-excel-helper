# -*- coding: utf-8 -*-
"""所有 Mod 物理视图不得使用 ``../`` 相对 import。"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODS_ROOT = REPO / "mods"

BAD = re.compile(r"""from\s+['"]\.\./""")


def test_all_mod_physical_views_use_alias_imports():
    offenders: list[str] = []
    for views_dir in sorted(MODS_ROOT.glob("*/frontend/views")):
        if not views_dir.is_dir():
            continue
        mod_id = views_dir.parent.parent.name
        for vue in sorted(views_dir.glob("*.vue")):
            text = vue.read_text(encoding="utf-8")
            if BAD.search(text):
                offenders.append(f"{mod_id}/{vue.name}")
    assert offenders == [], f"relative parent imports: {offenders}"
