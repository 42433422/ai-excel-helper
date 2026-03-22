from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple, Type


@dataclass(frozen=True)
class LegacyGeneratorLoadResult:
    ShipmentDocumentGenerator: Type
    PurchaseUnitInfo: Type
    legacy_dir: str


def load_legacy_shipment_document_generator(*, caller_file: str) -> LegacyGeneratorLoadResult:
    """
    从旧版「AI助手/shipment_document.py」加载 ShipmentDocumentGenerator 与 PurchaseUnitInfo。

    这是基础设施适配逻辑：路径探测、sys.path 注入、importlib 动态导入都不应出现在应用/领域层。
    """
    current_dir = os.path.dirname(os.path.abspath(caller_file))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

    # 优先从 XCAGI/resources 引用旧 AI 助手代码（避免项目外依赖）
    try:
        from app.utils.path_utils import get_resource_path
        resources_ai_assistant_dir = get_resource_path("tools_legacy", "AI助手")
        resources_ai_assistant_alt = get_resource_path("ai_assistant")
    except Exception:
        resources_ai_assistant_dir = None
        resources_ai_assistant_alt = None

    possible_dirs = [
        # resources 优先
        *( [resources_ai_assistant_dir] if resources_ai_assistant_dir else [] ),
        *( [resources_ai_assistant_alt] if resources_ai_assistant_alt else [] ),
        os.path.join(project_root, "AI助手"),
        os.path.join(project_root, "AI助手", "AI助手"),
        os.path.join(project_root, "AI 助手"),
        os.path.join(project_root, "AI 助手", "AI助手"),
        os.path.join(project_root, "AI助手2"),
    ]

    legacy_dir: Optional[str] = None
    for dir_path in possible_dirs:
        if os.path.isdir(dir_path) and os.path.exists(os.path.join(dir_path, "shipment_document.py")):
            legacy_dir = dir_path
            break

    if not legacy_dir:
        raise ImportError(f"未找到包含 shipment_document.py 的 AI 助手目录。可能的目录：{possible_dirs}")

    # 方法 1：sys.path + 直接导入
    if legacy_dir not in sys.path:
        sys.path.insert(0, legacy_dir)

    try:
        from shipment_document import PurchaseUnitInfo, ShipmentDocumentGenerator  # type: ignore

        return LegacyGeneratorLoadResult(
            ShipmentDocumentGenerator=ShipmentDocumentGenerator,
            PurchaseUnitInfo=PurchaseUnitInfo,
            legacy_dir=legacy_dir,
        )
    except Exception:
        # 方法 2：importlib 动态导入
        spec_path = os.path.join(legacy_dir, "shipment_document.py")
        if not os.path.exists(spec_path):
            raise ImportError(f"文件不存在：{spec_path}")

        spec = importlib.util.spec_from_file_location("shipment_document", spec_path)
        if not spec or not spec.loader:
            raise ImportError(f"无法创建导入 spec：{spec_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        ShipmentDocumentGenerator = getattr(module, "ShipmentDocumentGenerator", None)
        PurchaseUnitInfo = getattr(module, "PurchaseUnitInfo", None)
        if not ShipmentDocumentGenerator or not PurchaseUnitInfo:
            raise ImportError("无法加载 ShipmentDocumentGenerator 或 PurchaseUnitInfo")

        return LegacyGeneratorLoadResult(
            ShipmentDocumentGenerator=ShipmentDocumentGenerator,
            PurchaseUnitInfo=PurchaseUnitInfo,
            legacy_dir=legacy_dir,
        )

