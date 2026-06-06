# -*- coding: utf-8 -*-
"""Mod / 发行版相关测试的宽松断言集合（实现演进时避免逐文件改 phase / execution_path）。"""

from __future__ import annotations

MOD_FACADE_EXECUTION_PATHS = frozenset({"mod_facade", "mod_bus_runtime"})
NEURO_BUS_PHASES = frozenset({"M", "M+", "N", "S"})
ERP_REPOSITORY_ADAPTERS = frozenset({"mod_delegated", "mod_factory"})
ERP_PHASE_TOKENS = frozenset({"L", "L+", "L++", "K+", "O+"})
