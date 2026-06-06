"""发货单聚合使用的涂料行业值对象（来自 ``app/domain/value_objects.py`` 扁平模块）。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_LEGACY_NAME = "app.domain._shipment_legacy_value_objects"


def _load() -> object:
    if _LEGACY_NAME in sys.modules:
        return sys.modules[_LEGACY_NAME]
    path = Path(__file__).resolve().parent.parent / "value_objects.py"
    spec = importlib.util.spec_from_file_location(_LEGACY_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load legacy value objects from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_LEGACY_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


_legacy = _load()
Quantity = _legacy.Quantity
Money = _legacy.Money
ContactInfo = _legacy.ContactInfo
OrderNumber = _legacy.OrderNumber

__all__ = ["Quantity", "Money", "ContactInfo", "OrderNumber"]
