"""
System API Routes - FastAPI Implementation

Provides endpoints for:
- GET /api/system/industries - List all available industries
- GET /api/system/industry - Get current industry profile
- POST /api/system/industry - Set current industry
- GET /api/system/industry/{industry_id} - Get specific industry profile

行业数据优先级（2026-04 调整）：
    已加载 Mod 的 manifest.industry 声明 > resources/config/industry_config.yaml

Mod 在 manifest.json 顶层声明 ``"industry": {"id": "...", "name": "...", ...}``
即把该行业注入可用集合；YAML 仅作为无 Mod 环境的开发/回退配置。详见
resources/config/industry_config.py::_mod_industries_dict 与
app/infrastructure/mods/manifest.py::ModMetadata.industry。
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


class IndustryResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str = ""
    config: dict[str, Any] = {}


class IndustriesListData(BaseModel):
    industries: list
    current: str


class IndustryData(BaseModel):
    industry: dict[str, Any]


class SetIndustryRequest(BaseModel):
    industry_id: str


def _build_industry_response(industry_id: str, profile: Any) -> dict[str, Any]:
    """Build industry response dict from profile object"""
    return {
        "id": industry_id,
        "name": profile.name,
        "code": industry_id,
        "description": profile.name,
        "config": {
            "units": profile.units,
            "quantity_fields": profile.quantity_fields,
            "product_fields": profile.product_fields,
            "order_types": profile.order_types,
            "print_config": profile.print_config,
        },
    }


@router.get("/industries")
async def get_industries():
    """Get list of all available industries"""
    try:
        from resources.config.industry_config import (
            get_available_industries,
            get_current_industry,
            get_industry_profile,
        )

        industries = get_available_industries()
        current = get_current_industry()

        result_industries = []
        for ind in industries:
            profile = get_industry_profile(ind["id"])
            result_industries.append(_build_industry_response(ind["id"], profile))

        return {
            "success": True,
            "data": {
                "industries": result_industries,
                "current": current,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get industries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry")
async def get_current_industry_endpoint():
    """Get current industry profile"""
    try:
        from resources.config.industry_config import (
            get_current_industry,
            get_industry_profile,
        )

        current_id = get_current_industry()
        profile = get_industry_profile(current_id)

        return {"success": True, "data": _build_industry_response(current_id, profile)}
    except Exception as e:
        logger.exception("Failed to get current industry: %s", e)
        # 避免 Mod manifest / YAML 异常时侧栏整页 500：回退到内置「涂料」档案
        try:
            from resources.config.industry_config import get_industry_profile

            fid = "涂料"
            profile = get_industry_profile(fid)
            return {"success": True, "data": _build_industry_response(fid, profile)}
        except Exception:
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/industry")
async def set_industry_endpoint(request: SetIndustryRequest):
    """Set current industry"""
    try:
        from resources.config.industry_config import (
            get_industry_profile,
            set_current_industry,
        )

        success = set_current_industry(request.industry_id)
        if not success:
            raise HTTPException(status_code=400, detail=f"Unknown industry: {request.industry_id}")

        profile = get_industry_profile(request.industry_id)

        return {"success": True, "data": _build_industry_response(request.industry_id, profile)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set industry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/host-profile")
async def get_host_profile():
    """宿主 SKU profile（bridge 列表、打包白名单、工作流交付形态等）。"""
    try:
        from app.mod_sdk.host_profile import build_host_profile_api_payload

        return {"success": True, "data": build_host_profile_api_payload()}
    except Exception as e:
        logger.error("Failed to get host profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/industry-presets")
async def get_industry_presets():
    """跨行业 UI 预设（config/industry_presets.json），供前端与 MODstore 制作端共用。"""
    try:
        from app.mod_sdk.host_profile import load_industry_presets_document

        doc = load_industry_presets_document()
        return {
            "success": True,
            "data": {
                "schema_version": doc.get("schema_version", 1),
                "preset_ids": doc.get("preset_ids") or list((doc.get("presets") or {}).keys()),
                "presets": doc.get("presets") or {},
            },
        }
    except Exception as e:
        logger.error("Failed to get industry presets: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/workflow-employee-catalog")
async def get_workflow_employee_catalog():
    """工作流员工目录（配置 + 扫描 mods 目录）。"""
    try:
        from app.mod_sdk.host_profile import (
            load_host_profile,
            load_workflow_employee_catalog,
            scan_workflow_employee_catalog_from_mods,
        )

        catalog = scan_workflow_employee_catalog_from_mods()
        prof = load_host_profile()
        return {
            "success": True,
            "data": {
                "catalog": catalog,
                "workflow_delivery": prof.get("workflow_delivery"),
                "workflow_monolith_mod_id": prof.get("workflow_monolith_mod_id"),
                "workflow_split_mod_ids": prof.get("workflow_split_mod_ids"),
                "static_catalog": load_workflow_employee_catalog(),
            },
        }
    except Exception as e:
        logger.error("Failed to get workflow employee catalog: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/employee-registry-rules")
async def get_employee_registry_rules():
    """副窗工作流员工注册规则（替代前端硬编码过滤）。"""
    try:
        from app.mod_sdk.host_profile import get_employee_registry_rules

        return {"success": True, "data": get_employee_registry_rules()}
    except Exception as e:
        logger.error("Failed to get employee registry rules: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/industry/{industry_id}")
async def get_industry_detail(industry_id: str):
    """Get specific industry profile"""
    try:
        from resources.config.industry_config import (
            get_available_industries,
            get_industry_profile,
        )

        available = get_available_industries()
        industry_ids = [ind["id"] for ind in available]

        if industry_id not in industry_ids:
            raise HTTPException(status_code=404, detail=f"Industry not found: {industry_id}")

        profile = get_industry_profile(industry_id)

        return {"success": True, "data": _build_industry_response(industry_id, profile)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get industry {industry_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
