"""与前端 AdminDutyEmployeeGraph 编制矩阵对齐的岗位 ID（单一后端来源）。"""

from __future__ import annotations

from typing import Dict, List, Optional

# 与 FHD config/duty_roster.json areas 块、market yuangonDutyRoster.ts 保持一致
YUANGON_AREAS: Dict[str, Dict[str, object]] = {
    "site-and-marketing": {
        "label": "对外网站与 SEO",
        "ids": ["site-content-editor", "seo-sitemap-curator", "flask-entry-keeper", "marketing-site-builder"],
    },
    "server-and-ops": {
        "label": "服务器与运维",
        "ids": [
            "nginx-config-engineer",
            "push-update-context-officer",
            "deploy-release-officer",
            "security-secrets-guard",
            "log-monitor-incident",
            "retention-officer",
            "dbops-engineer",
            "legacy-archive-curator",
        ],
    },
    "modstore-backend": {
        "label": "MODstore 后端",
        "ids": [
            "modstore-backend-api",
            "employee-pack-curator",
            "payment-billing-reconciler",
            "java-payment-bridge-officer",
        ],
    },
    "modstore-frontend": {
        "label": "MODstore 前端",
        "ids": ["market-frontend-dev", "workbench-ux-stylist"],
    },
    "platform-core": {
        "label": "平台核心",
        "ids": [
            "fhd-core-maintainer",
            "vibe-coding-maintainer",
            "mods-and-eskill-curator",
            "change-request-auditor",
            "daily-orchestrator",
            "intake-dispatcher",
            "task-router-officer",
            "user-customer-service-officer",
            "enterprise-adoption-officer",
            "delivery-receipt-officer",
            "mobile-android-release-officer",
            "mobile-ios-release-officer",
        ],
    },
    "quality-and-docs": {
        "label": "质量与文档",
        "ids": [
            "test-qa-runner",
            "doc-knowledge-curator",
            "employee-interview-assistant",
            "employee-pack-quality-interviewer",
        ],
    },
    "craft-workshop": {
        "label": "制作车间",
        "ids": [
            "intent-analyst",
            "employee-planner",
            "artifact-generator",
            "quality-validator",
            "miniapp-builder",
            "script-binder",
            "workflow-automator",
            "pack-registrar",
            "sandbox-tester",
            "code-validator",
            "self-checker",
            "host-checker",
            "hex-quality-assessor",
        ],
    },
    "partner-ecosystem": {
        "label": "生态伙伴 O-B",
        "ids": [
            "ecosystem-partner-onboard-officer",
            "ecosystem-joint-catalog-officer",
            "ecosystem-delivery-reporter",
            "ecosystem-investor-portal-officer",
            "ecosystem-revenue-share-reconciler",
        ],
    },
}

# 六线部门（与 FHD config/duty_roster.json departments 块一致）
SIX_LINE_DEPARTMENTS: Dict[str, Dict[str, object]] = {
    "ops_acquisition": {
        "label": "O-A 获客部",
        "five_line_id": "ops_acquisition",
        "subzones": {
            "public-acquisition": {
                "label": "公域获客 O1",
                "ids": ["site-content-editor", "seo-sitemap-curator", "marketing-site-builder"],
            },
            "crm-pipeline": {
                "label": "CRM 与商机 O2-O3",
                "ids": ["user-customer-service-officer", "intake-dispatcher", "modstore-backend-api"],
            },
            "billing": {"label": "收费对账 O4/O10", "ids": ["payment-billing-reconciler"]},
            "delivery-feedback": {
                "label": "交付反馈签收 O5/O7-O8",
                "ids": [
                    "deploy-release-officer",
                    "change-request-auditor",
                    "test-qa-runner",
                    "enterprise-adoption-officer",
                    "delivery-receipt-officer",
                ],
            },
        },
    },
    "ops_partner": {
        "label": "O-B 伙伴部",
        "five_line_id": "ops_partner",
        "subzones": {
            "partner-onboard": {"label": "生态接入 B1", "ids": ["ecosystem-partner-onboard-officer"]},
            "joint-catalog": {"label": "联合 catalog B2", "ids": ["ecosystem-joint-catalog-officer"]},
            "delivery-bridge": {"label": "生态交付 B3", "ids": ["ecosystem-delivery-reporter"]},
            "investor-portal": {"label": "投资方视图 B4", "ids": ["ecosystem-investor-portal-officer"]},
            "revenue-share": {"label": "分润对账 B5", "ids": ["ecosystem-revenue-share-reconciler"]},
        },
    },
    "prod_web": {
        "label": "P-W 网站部",
        "five_line_id": "prod_web",
        "subzones": {
            "static-site": {
                "label": "营销静态 P1a",
                "ids": [
                    "site-content-editor",
                    "seo-sitemap-curator",
                    "marketing-site-builder",
                    "flask-entry-keeper",
                ],
            },
            "market-spa": {"label": "市场 SPA P1b", "ids": ["market-frontend-dev"]},
            "workbench": {
                "label": "工作台 P1c",
                "ids": ["workbench-ux-stylist", "daily-orchestrator", "task-router-officer", "vibe-coding-maintainer"],
            },
            "modstore-api": {
                "label": "MODstore 后端 P1d",
                "ids": ["modstore-backend-api", "employee-pack-curator", "java-payment-bridge-officer"],
            },
            "docs-seo": {"label": "文档 SEO P1e", "ids": ["doc-knowledge-curator", "seo-sitemap-curator"]},
            "nginx-deploy": {"label": "nginx 部署 P1f", "ids": ["nginx-config-engineer", "deploy-release-officer"]},
        },
    },
    "prod_mod": {
        "label": "P-M Mod 部",
        "five_line_id": "prod_mod",
        "subzones": {
            "craft-pipeline": {
                "label": "Craft 13 步 P2",
                "ids": [
                    "intent-analyst",
                    "employee-planner",
                    "artifact-generator",
                    "quality-validator",
                    "miniapp-builder",
                    "script-binder",
                    "workflow-automator",
                    "pack-registrar",
                    "sandbox-tester",
                    "code-validator",
                    "self-checker",
                    "host-checker",
                    "hex-quality-assessor",
                ],
            },
            "sandbox-catalog": {
                "label": "沙盒 catalog P3",
                "ids": [
                    "sandbox-tester",
                    "code-validator",
                    "self-checker",
                    "mods-and-eskill-curator",
                    "test-qa-runner",
                ],
            },
            "mod-ota": {"label": "Mod OTA P6", "ids": ["push-update-context-officer", "pack-registrar"]},
            "roster-quality": {
                "label": "编制质检",
                "ids": ["employee-interview-assistant", "employee-pack-quality-interviewer"],
            },
        },
    },
    "prod_software": {
        "label": "P-S 软件部",
        "five_line_id": "prod_software",
        "subzones": {
            "core-coding": {"label": "核心编码 P2", "ids": ["fhd-core-maintainer", "vibe-coding-maintainer"]},
            "testing": {
                "label": "自动测试 P3",
                "ids": ["test-qa-runner", "sandbox-tester", "code-validator", "self-checker"],
            },
            "build-release": {
                "label": "构建发布 P4-P5",
                "ids": [
                    "pack-registrar",
                    "deploy-release-officer",
                    "change-request-auditor",
                    "mobile-android-release-officer",
                    "mobile-ios-release-officer",
                ],
            },
            "ota-monitor": {
                "label": "OTA 监控 P6-P7",
                "ids": ["push-update-context-officer", "log-monitor-incident", "host-checker"],
            },
            "orchestration": {
                "label": "编排迭代 P9-P10",
                "ids": ["daily-orchestrator", "intake-dispatcher", "task-router-officer", "dbops-engineer"],
            },
        },
    },
    "shared_retention": {
        "label": "S-R 归档部",
        "five_line_id": "shared_retention",
        "subzones": {
            "ttl-janitor": {"label": "TTL 清理 R1", "ids": ["retention-officer"]},
            "commit-guards": {"label": "提交门禁 R2", "ids": ["security-secrets-guard"]},
            "legacy-archive": {"label": "legacy 归档 R3", "ids": ["retention-officer", "legacy-archive-curator"]},
            "alert-cve": {
                "label": "告警 CVE R4",
                "ids": ["log-monitor-incident", "daily-orchestrator", "security-secrets-guard"],
            },
        },
    },
}


def all_planned_employee_ids() -> frozenset[str]:
    ids: List[str] = []
    for block in YUANGON_AREAS.values():
        ids.extend(block["ids"])  # type: ignore[arg-type]
    return frozenset(ids)


def yuangon_area_for_pkg(pkg_id: str) -> Optional[str]:
    """编制矩阵中 ``pkg_id`` 所属区域目录名（``yuangon/<area>/…`` 第一段），未知返回 ``None``。"""
    pid = str(pkg_id or "").strip()
    if not pid:
        return None
    for area_key, block in YUANGON_AREAS.items():
        ids = block.get("ids") if isinstance(block.get("ids"), list) else []
        if pid in ids:
            return str(area_key)
    return None


def is_planned_duty_employee_pack(pkg_id: Optional[str], artifact: Optional[str]) -> bool:
    """编制矩阵内的 ``employee_pack``：运维/管理侧在岗岗位，不参与公开市场展示。"""
    if str(artifact or "").strip() != "employee_pack":
        return False
    pid = str(pkg_id or "").strip()
    return bool(pid) and pid in all_planned_employee_ids()
