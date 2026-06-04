"""上传 zip/xcemp 的沙盒审核：五维评分、静态功能检查、可选 HTTP 探测。"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from modman.artifact_constants import ARTIFACT_EMPLOYEE_PACK, ARTIFACT_MOD, normalize_artifact
from modman.manifest_util import validate_manifest_dict
from modstore_server.employee_config_v2 import validate_v2_config

MAX_ZIP_BYTES = 80 * 1024 * 1024
MAX_SINGLE_FILE_BYTES = 16 * 1024 * 1024
MAX_PY_SCAN_CHARS = 450_000

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{24,}", re.I), "疑似 API Key（sk-…）"),
    (re.compile(r"BEGIN\s+RSA\s+PRIVATE\s+KEY", re.I), "RSA PEM 私钥"),
    (re.compile(r"BEGIN\s+OPENSSH\s+PRIVATE\s+KEY", re.I), "OpenSSH 私钥"),
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}", re.I), "疑似 Google API Key"),
]

_TEXT_SUFFIX = frozenset(
    {".py", ".json", ".js", ".mjs", ".ts", ".tsx", ".vue", ".yaml", ".yml", ".md", ".txt", ".env", ".toml"}
)


def _clamp_score(n: int) -> int:
    return max(0, min(100, int(n)))


def _find_manifest_path(root: Path) -> Optional[Path]:
    cands = list(root.rglob("manifest.json"))
    if not cands:
        return None
    cands.sort(key=lambda p: (len(p.relative_to(root).parts), str(p)))
    return cands[0]


def _load_manifest_at(path: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return None, str(e)
    if not isinstance(data, dict):
        return None, "manifest 根须为对象"
    return data, ""


def _wf_phone_path(manifest: Dict[str, Any]) -> str:
    wes = manifest.get("workflow_employees")
    if isinstance(wes, list):
        for w in wes:
            if isinstance(w, dict):
                p = str(w.get("phone_agent_base_path") or "").strip()
                if p:
                    return p.strip("/")
    return ""


def _collect_py_text(root: Path) -> str:
    chunks: List[str] = []
    total = 0
    for p in sorted(root.rglob("*.py")):
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if sz > 256 * 1024:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if total + len(t) > MAX_PY_SCAN_CHARS:
            chunks.append(t[: max(0, MAX_PY_SCAN_CHARS - total)])
            break
        chunks.append(t)
        total += len(t)
    return "\n".join(chunks)


def _scan_secrets_in_tree(root: Path, max_files: int = 80) -> List[str]:
    hits: List[str] = []
    n = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.lower() == "manifest.json":
            continue
        suf = p.suffix.lower()
        if suf not in _TEXT_SUFFIX and p.name not in (".env",):
            continue
        try:
            if p.stat().st_size > 512 * 1024:
                continue
        except OSError:
            continue
        try:
            sample = p.read_text(encoding="utf-8", errors="ignore")[:120_000]
        except OSError:
            continue
        for rx, label in SECRET_PATTERNS:
            if rx.search(sample):
                hits.append(f"{p.relative_to(root).as_posix()}: {label}")
                break
        n += 1
        if n >= max_files:
            break
    return hits


def _zip_size_and_max_member(raw: bytes) -> Tuple[int, int, List[str]]:
    issues: List[str] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile as e:
        return 0, 0, [f"非法 zip: {e}"]
    with zf:
        infos = zf.infolist()
        total = sum(i.file_size for i in infos)
        max_one = max((i.file_size for i in infos), default=0)
        for i in infos:
            if i.file_size > MAX_SINGLE_FILE_BYTES:
                issues.append(f"成员过大 {i.filename!r} ({i.file_size} bytes)")
    return total, max_one, issues


def _dim_manifest_compliance(manifest: Dict[str, Any], expected_artifact: Optional[str]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    errs = validate_manifest_dict(manifest)
    if errs:
        reasons.extend(errs)
    art = normalize_artifact(manifest)
    if expected_artifact:
        exp = expected_artifact.strip().lower()
        if exp in (ARTIFACT_MOD, ARTIFACT_EMPLOYEE_PACK) and exp != art:
            reasons.append(f"声明 artifact 为 {art}，与登记意图 {exp} 不一致")
    score = 100 if not reasons else _clamp_score(100 - min(80, len(reasons) * 15))
    if not reasons:
        reasons.append("manifest 通过 validate_manifest_dict")
    return score, reasons


def _dim_declaration(manifest: Dict[str, Any]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    art = normalize_artifact(manifest)
    if art == ARTIFACT_EMPLOYEE_PACK:
        emp = manifest.get("employee")
        if not isinstance(emp, dict):
            reasons.append("employee_pack 缺少 employee 对象")
        else:
            if not str(emp.get("label") or "").strip():
                reasons.append("employee.label 为空")
    else:
        wes = manifest.get("workflow_employees")
        if not isinstance(wes, list) or not wes:
            reasons.append("mod 未声明 workflow_employees 数组或为空")
        else:
            for i, w in enumerate(wes):
                if not isinstance(w, dict):
                    reasons.append(f"workflow_employees[{i}] 非对象")
                    continue
                if not str(w.get("id") or "").strip():
                    reasons.append(f"workflow_employees[{i}].id 为空")
                if not str(w.get("label") or "").strip() and not str(w.get("panel_title") or "").strip():
                    reasons.append(f"workflow_employees[{i}] 缺少 label / panel_title")
            pp = _wf_phone_path(manifest)
            if pp and "/" in pp:
                reasons.append("phone_agent_base_path 建议为单层路径片段")
    score = 100 if not reasons else _clamp_score(100 - len(reasons) * 18)
    if not reasons:
        reasons.append("声明字段完整")
    return score, reasons


def _dim_api_static(root: Path, manifest: Dict[str, Any]) -> Tuple[int, List[str]]:
    base = _wf_phone_path(manifest)
    if not base:
        return 100, ["未声明 phone_agent_base_path，跳过路由静态扫描"]
    blob = _collect_py_text(root)
    if not blob.strip():
        return 40, ["未找到可扫描的 Python 文件以核对路由"]
    miss: List[str] = []
    for verb in ("status", "start", "stop"):
        pat = re.compile(re.escape(base) + r"[^\w]{0,12}" + re.escape(verb), re.I)
        if not pat.search(blob):
            loose = re.compile(re.escape(verb), re.I)
            if not loose.search(blob):
                miss.append(f"未在 .py 中匹配 {base!r} 与 {verb!r} 邻近片段")
            else:
                miss.append(f"找到 {verb} 但与路径前缀 {base!r} 邻近关系不明确")
    if not miss:
        return 100, [f"在 backend Python 中匹配到 {base!r} 与 status/start/stop 相关片段"]
    return _clamp_score(100 - 28 * len(miss)), miss


def _dim_security_size(raw: bytes, root: Path) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    total, max_one, zissues = _zip_size_and_max_member(raw)
    reasons.extend(zissues)
    if total > MAX_ZIP_BYTES:
        reasons.append(f"zip 解压后总体积过大（>{MAX_ZIP_BYTES}）")
    sec = _scan_secrets_in_tree(root)
    reasons.extend(sec[:12])
    if len(sec) > 12:
        reasons.append(f"… 另有 {len(sec) - 12} 处敏感模式命中")
    score = 100
    score -= min(40, len(zissues) * 20)
    score -= min(50, len(sec) * 12)
    score -= 30 if total > MAX_ZIP_BYTES else 0
    return _clamp_score(score), reasons if reasons else ["体积与敏感信息扫描未发现严重问题"]


def _dim_metadata(manifest: Dict[str, Any]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    name = str(manifest.get("name") or "").strip()
    desc = str(manifest.get("description") or "").strip()
    if len(name) < 2:
        reasons.append("name 过短或缺失")
    if len(desc) < 8:
        reasons.append("description 过短或缺失（建议至少一句完整说明）")
    ind = str(manifest.get("industry") or manifest.get("library_industry") or "").strip()
    if not ind:
        reasons.append("未填写 industry / library_industry（可选但建议填写）")
    score = 100 - len(reasons) * 22
    return _clamp_score(score), reasons if reasons else ["元数据可读性良好"]


def _functional_checks(
    manifest: Dict[str, Any], root: Path, manifest_err: str
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    out.append(
        {
            "name": "manifest.json 可读",
            "ok": not bool(manifest_err),
            "detail": manifest_err or "已解析为 JSON 对象",
        }
    )
    ve = validate_manifest_dict(manifest) if manifest else ["无 manifest"]
    out.append(
        {
            "name": "validate_manifest_dict",
            "ok": not ve,
            "detail": "; ".join(ve) if ve else "无校验错误",
        }
    )
    base = _wf_phone_path(manifest)
    if base:
        blob = _collect_py_text(root)
        for verb in ("status", "start", "stop"):
            ok = bool(
                re.search(re.escape(base) + r"[^\w]{0,12}" + re.escape(verb), blob, re.I)
            )
            out.append({"name": f"静态路由片段 {base}/{verb}", "ok": ok, "detail": "见 Python 聚合扫描"})
    else:
        out.append({"name": "phone_agent 路由静态检查", "ok": True, "detail": "未声明 phone_agent_base_path，跳过"})
    return out


def _parse_allow_hosts() -> List[str]:
    raw = (os.environ.get("MODSTORE_SANDBOX_PROBE_HOST_ALLOWLIST") or "127.0.0.1,localhost").strip()
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def _probe_base_url() -> str:
    return (os.environ.get("MODSTORE_SANDBOX_PROBE_BASE_URL") or "").strip().rstrip("/")


async def _http_probe_phone_status(
    *,
    mod_id: str,
    phone_base_path: str,
) -> Dict[str, Any]:
    base = _probe_base_url()
    if not base:
        return {"skipped": True, "name": "HTTP GET status", "detail": "未配置 MODSTORE_SANDBOX_PROBE_BASE_URL"}
    try:
        u = urlparse(base)
    except Exception as e:  # noqa: BLE001
        return {"skipped": True, "name": "HTTP GET status", "detail": f"基址无效: {e}"}
    host = (u.hostname or "").lower()
    if host not in _parse_allow_hosts():
        return {
            "skipped": True,
            "name": "HTTP GET status",
            "detail": f"hostname {host!r} 不在 MODSTORE_SANDBOX_PROBE_HOST_ALLOWLIST",
        }
    b = phone_base_path.strip().strip("/")
    if not b:
        return {"skipped": True, "name": "HTTP GET status", "detail": "无 phone_agent_base_path"}
    mid = str(mod_id or "").strip()
    if not mid:
        return {"skipped": True, "name": "HTTP GET status", "detail": "未提供 probe_mod_id，无法拼路由"}
    url = f"{base}/api/mod/{mid}/{b}/status"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            r = await client.get(url)
        ok = r.status_code == 200
        return {
            "skipped": False,
            "name": "HTTP GET status",
            "ok": ok,
            "detail": f"{url} -> HTTP {r.status_code}",
            "url": url,
        }
    except Exception as e:  # noqa: BLE001
        return {"skipped": False, "name": "HTTP GET status", "ok": False, "detail": f"{url} 请求失败: {e}", "url": url}


async def run_package_audit_async(
    zip_bytes: bytes,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    解压、评分、静态功能测试；可选 HTTP 探测（环境变量 + allowlist + probe_mod_id）。
    metadata 可选: artifact, probe_mod_id
    """
    meta = metadata if isinstance(metadata, dict) else {}
    expected_artifact = str(meta.get("artifact") or "").strip().lower() or None
    probe_mod_id = str(meta.get("probe_mod_id") or "").strip() or None
    metadata_v2 = meta.get("employee_config_v2") if isinstance(meta.get("employee_config_v2"), dict) else None

    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError(f"上传包超过上限 {MAX_ZIP_BYTES} bytes")

    tmp = tempfile.mkdtemp(prefix="modstore_audit_")
    root = Path(tmp)
    manifest: Dict[str, Any] = {}
    manifest_err = ""
    try:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                zf.extractall(root)
        except zipfile.BadZipFile as e:
            return {
                "ok": False,
                "error": str(e),
                "dimensions": {},
                "functional_tests": [],
                "summary": {"average": 0, "pass": False},
            }

        mp = _find_manifest_path(root)
        if not mp:
            return {
                "ok": True,
                "dimensions": {
                    "manifest_compliance": {"score": 0, "reasons": ["缺少 manifest.json"]},
                    "declaration_completeness": {"score": 0, "reasons": ["无法评估"]},
                    "api_testability_static": {"score": 0, "reasons": ["无法评估"]},
                    "security_and_size": {"score": 50, "reasons": ["已解压；无 manifest 可对照"]},
                    "metadata_quality": {"score": 0, "reasons": ["无 manifest"]},
                },
                "functional_tests": [
                    {"name": "manifest 存在", "ok": False, "detail": "未找到 manifest.json"},
                ],
                "summary": {"average": 10, "pass": False},
            }

        data, manifest_err = _load_manifest_at(mp)
        if not data:
            manifest = {}
        else:
            manifest = data

        s1, r1 = _dim_manifest_compliance(manifest, expected_artifact)
        s2, r2 = _dim_declaration(manifest)
        s3, r3 = _dim_api_static(root, manifest)
        s4, r4 = _dim_security_size(zip_bytes, root)
        s5, r5 = _dim_metadata(manifest)
        if metadata_v2:
            v2errs = validate_v2_config(metadata_v2, db=None, user_id=None, require_workflow_heart=True)
            if v2errs:
                r2 = list(r2) + [f"V2: {x}" for x in v2errs]
                s2 = _clamp_score(s2 - min(40, len(v2errs) * 12))
        dims = {
            "manifest_compliance": {"score": s1, "reasons": r1},
            "declaration_completeness": {"score": s2, "reasons": r2},
            "api_testability_static": {"score": s3, "reasons": r3},
            "security_and_size": {"score": s4, "reasons": r4},
            "metadata_quality": {"score": s5, "reasons": r5},
        }

        ftests = _functional_checks(manifest, root, manifest_err)

        phone = _wf_phone_path(manifest)
        eff_mod_id = probe_mod_id or (
            str(manifest.get("id") or "").strip()
            if normalize_artifact(manifest) == ARTIFACT_MOD
            else ""
        )
        http_res = await _http_probe_phone_status(mod_id=eff_mod_id, phone_base_path=phone)
        ftests.append(http_res)

        scores = [v["score"] for v in dims.values()]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        passed = avg >= 60 and dims["manifest_compliance"]["score"] >= 40 and not manifest_err

        return {
            "ok": True,
            "dimensions": dims,
            "functional_tests": ftests,
            "summary": {
                "average": avg,
                "pass": passed,
                "artifact": normalize_artifact(manifest),
            },
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
