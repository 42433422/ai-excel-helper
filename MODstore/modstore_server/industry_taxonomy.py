from __future__ import annotations

from typing import Any, Dict, List, Optional

INDUSTRY_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "GEN": {
        "name": "通用",
        "code": "GEN",
        "children": {
            "GEN01": "通用工具",
            "GEN02": "效率提升",
        },
    },
    "MFG": {
        "name": "制造业",
        "code": "MFG",
        "children": {
            "MFG01": "汽车制造",
            "MFG02": "电子制造",
            "MFG03": "机械加工",
            "MFG04": "化工制造",
            "MFG05": "食品饮料制造",
        },
    },
    "IT": {
        "name": "信息技术",
        "code": "IT",
        "children": {
            "IT01": "软件开发",
            "IT02": "云计算",
            "IT03": "大数据",
            "IT04": "人工智能",
            "IT05": "网络安全",
        },
    },
    "FIN": {
        "name": "金融保险",
        "code": "FIN",
        "children": {
            "FIN01": "银行",
            "FIN02": "证券",
            "FIN03": "保险",
            "FIN04": "基金",
        },
    },
    "EDU": {
        "name": "教育培训",
        "code": "EDU",
        "children": {
            "EDU01": "K12",
            "EDU02": "职业教育",
            "EDU03": "高等教育",
            "EDU04": "早教",
        },
    },
    "MED": {
        "name": "医疗健康",
        "code": "MED",
        "children": {
            "MED01": "医院",
            "MED02": "诊所",
            "MED03": "健康管理",
            "MED04": "医药",
        },
    },
    "RET": {
        "name": "零售电商",
        "code": "RET",
        "children": {
            "RET01": "跨境电商",
            "RET02": "新零售",
            "RET03": "供应链",
        },
    },
    "REA": {
        "name": "房地产建筑",
        "code": "REA",
        "children": {
            "REA01": "地产开发",
            "REA02": "建筑设计",
            "REA03": "物业管理",
        },
    },
    "LOG": {
        "name": "物流交通",
        "code": "LOG",
        "children": {
            "LOG01": "快递物流",
            "LOG02": "航空运输",
            "LOG03": "港口",
        },
    },
    "ENE": {
        "name": "能源环保",
        "code": "ENE",
        "children": {
            "ENE01": "电力",
            "ENE02": "新能源",
            "ENE03": "环保",
        },
    },
    "AGR": {
        "name": "农业",
        "code": "AGR",
        "children": {
            "AGR01": "种植",
            "AGR02": "养殖",
            "AGR03": "农产品加工",
        },
    },
    "MEDIA": {
        "name": "文化传媒",
        "code": "MEDIA",
        "children": {
            "MEDIA01": "影视",
            "MEDIA02": "游戏",
            "MEDIA03": "新媒体",
        },
    },
    "GOV": {
        "name": "政务公共",
        "code": "GOV",
        "children": {
            "GOV01": "政府服务",
            "GOV02": "公共服务",
        },
    },
    "PRO": {
        "name": "专业服务",
        "code": "PRO",
        "children": {
            "PRO01": "法律",
            "PRO02": "会计",
            "PRO03": "咨询",
        },
    },
}


def get_industry_tree() -> List[Dict[str, Any]]:
    tree: List[Dict[str, Any]] = []
    for primary_code, primary_data in INDUSTRY_TAXONOMY.items():
        children = [
            {"code": code, "name": name}
            for code, name in primary_data.get("children", {}).items()
        ]
        tree.append(
            {
                "code": primary_data["code"],
                "name": primary_data["name"],
                "children": children,
            }
        )
    return tree


def get_industry_name(code: str) -> Optional[str]:
    code = (code or "").strip()
    if not code:
        return None
    if code in INDUSTRY_TAXONOMY:
        return INDUSTRY_TAXONOMY[code]["name"]
    for primary_data in INDUSTRY_TAXONOMY.values():
        if code in (primary_data.get("children") or {}):
            return primary_data["children"][code]
    return None


def get_secondary_industries(primary_code: str) -> List[Dict[str, str]]:
    primary_code = (primary_code or "").strip()
    if not primary_code or primary_code not in INDUSTRY_TAXONOMY:
        return []
    children = INDUSTRY_TAXONOMY[primary_code].get("children", {})
    return [{"code": code, "name": name} for code, name in children.items()]


def validate_industry_code(code: str) -> bool:
    code = (code or "").strip()
    if not code:
        return False
    if code in INDUSTRY_TAXONOMY:
        return True
    for primary_data in INDUSTRY_TAXONOMY.values():
        if code in (primary_data.get("children") or {}):
            return True
    return False
