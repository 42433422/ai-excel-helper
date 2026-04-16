"""
太阳鸟 Mod 考勤转换 HTTP 接口（FastAPI）。

Mod 目录内 Flask 蓝图在仅启动 FastAPI 的宿主进程中不会挂载，故与前端约定的
``/api/mod/taiyangniao-pro/attendance/*`` 在此实现。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.shell.taiyangniao_attendance.convert import coerce_sheet_arg, convert_dingtalk_file
from backend.shell.taiyangniao_attendance.paths import resolve_workspace_excel, workspace_root
from backend.shell.taiyangniao_attendance.rules import AttendanceRule, ATTENDANCE_GROUP_SCHEDULES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mod/taiyangniao-pro", tags=["mod-taiyangniao-pro"])

# 未指定模板时，若该文件存在于 WORKSPACE_ROOT 下则用于「明细」表填充式导出
DEFAULT_ATTENDANCE_TEMPLATE_RELPATH = "424/考勤-2026-3月份考勤统计表.xlsx"


def _rel_under_workspace(p: Path | None) -> str | None:
    if p is None:
        return None
    root = workspace_root()
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return str(p.resolve())


def _resolve_attendance_template(template_relpath: str | None) -> Path | None:
    """显式路径优先；未填则用默认考勤统计表模板。``none`` / ``-`` / ``__none__`` 表示不要模板（两工作表）。"""
    raw = (template_relpath if template_relpath is not None else "").strip()
    if raw.lower() in ("-", "none", "__none__"):
        return None
    if raw:
        return resolve_workspace_excel(raw)
    try:
        return resolve_workspace_excel(DEFAULT_ATTENDANCE_TEMPLATE_RELPATH)
    except (OSError, ValueError, PermissionError, FileNotFoundError):
        logger.info(
            "attendance default template missing, two-sheet output: %s",
            DEFAULT_ATTENDANCE_TEMPLATE_RELPATH,
        )
        return None


def _default_attendance_rules_payload() -> dict:
    """与 ``rules.AttendanceRule`` / ``process_attendance_dataframe`` 默认行为一致的可读说明。"""
    rule = AttendanceRule()
    cfg = asdict(rule)
    sh = f"{rule.saturday_start_hour:02d}:{rule.saturday_start_minute:02d}"
    eh = f"{rule.saturday_end_hour:02d}:{rule.saturday_end_minute:02d}"
    lines = [
        "大小周：按自然周序号推算，默认以 2024-01-01 为基准日计算大周/小周。",
        f"未匹配到已知考勤组时：周六窗口为 {sh}-{eh}（上班不晚于起、下班不早于止，仅比较当日时刻）。",
        "已匹配惠州工厂-正班 / 公司-考勤 / 食堂员工：按该组规则中的周六起止时刻校验（与右侧钉钉班表一致，午间歇简化为单日窗）。",
        "大周周六：须满足当前规则下的周六窗口；否则「规则违规」列会写出具体时段要求。",
        "小周周六：允许休息；无完整上下班时「备注」为「小周周六可以休息」。",
        "统计表列：考勤组、周类型、是否周六、周六工作有效、规则违规、备注。",
    ]

    return {
        "config": cfg,
        "lines": lines,
        "saturday_window_label": f"{sh}-{eh}",
        "schedule_groups": list(ATTENDANCE_GROUP_SCHEDULES),
    }


@router.get("/attendance/rules")
async def attendance_rules() -> dict:
    """供 Mod 首页右侧「考勤规则」面板展示（与当前默认 ``AttendanceRule`` 一致）。"""
    return {"success": True, "data": _default_attendance_rules_payload()}


class AttendanceConvertBody(BaseModel):
    source_relpath: str = Field(..., description="相对 WORKSPACE_ROOT")
    output_relpath: str = Field(..., description="相对 WORKSPACE_ROOT")
    month: str | None = None
    sheet: str | int = 0
    header_row: int | None = Field(
        default=None,
        description="表头所在 0-based 行号；省略或 null 时按钉钉多行表头自动检测（推荐）",
    )
    template_relpath: str | None = Field(
        default=None,
        description=(
            "模板相对 WORKSPACE_ROOT；省略时使用默认 "
            f"{DEFAULT_ATTENDANCE_TEMPLATE_RELPATH}（若存在）。"
            "填 none 或 - 表示无模板，仅输出「月度统计」「钉钉解析」。"
        ),
    )


@router.post("/attendance/convert")
async def attendance_convert(body: AttendanceConvertBody) -> dict:
    src_rel = body.source_relpath.strip()
    out_rel = body.output_relpath.strip()
    if not src_rel or not out_rel:
        raise HTTPException(status_code=400, detail="source_relpath 与 output_relpath 必填")

    try:
        source = resolve_workspace_excel(src_rel)
        # 输出文件不需要检查是否存在，直接构建路径
        out_raw = Path(str(out_rel or "").strip())
        if ".." in out_raw.parts:
            raise PermissionError("output path must not contain '..'")
        output = workspace_root() / out_raw
        try:
            output.relative_to(workspace_root())
        except ValueError as e:
            raise PermissionError("output path must resolve inside WORKSPACE_ROOT") from e
    except (OSError, ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not source.is_file():
        raise HTTPException(status_code=404, detail=f"源文件不存在: {source}")

    try:
        template_path = _resolve_attendance_template(body.template_relpath)
    except (OSError, ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=f"模板路径无效：{e}") from e

    sheet = coerce_sheet_arg(body.sheet)
    try:
        meta = convert_dingtalk_file(
            source,
            output,
            month=body.month,
            sheet=sheet,
            header_row=body.header_row,
            template_path=template_path,
        )
    except PermissionError as e:
        logger.warning("attendance_convert permission denied: %s", e)
        raise HTTPException(
            status_code=409,
            detail=(e.args[0] if e.args and isinstance(e.args[0], str) else str(e)) or str(e),
        ) from e
    except Exception as e:
        logger.exception("attendance_convert failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "success": True,
        "message": "转换完成",
        "data": {**meta, "template_relpath_resolved": _rel_under_workspace(template_path)},
    }


def _parse_header_row_form(raw: str) -> int | None:
    """空串 / auto → 自动检测表头；否则为 0-based 表头行号。"""
    s = (raw or "").strip()
    if not s or s.lower() == "auto":
        return None
    try:
        return int(s)
    except ValueError:
        return None


@router.post("/attendance/convert-upload")
async def attendance_convert_upload(
    file: UploadFile = File(..., description="钉钉导出的 xlsx"),
    output_relpath: str = Form(""),
    month: str = Form(""),
    template_relpath: str = Form(
        "",
        description=(
            f"可选；留空则用默认 {DEFAULT_ATTENDANCE_TEMPLATE_RELPATH}。"
            "填 none 或 - 仅输出「月度统计」「钉钉解析」。"
        ),
    ),
    sheet: str = Form("0"),
    header_row: str = Form(
        "",
        description="表头 0-based 行号；留空则自动检测（钉钉「打卡时间」等多行表头）",
    ),
) -> dict:
    out_rel = (output_relpath or "").strip() or f"424/考勤转换输出_{uuid.uuid4().hex[:10]}.xlsx"

    hdr = _parse_header_row_form(header_row)

    upload_dir = workspace_root() / "424" / "_taiyangniao_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"upload_{uuid.uuid4().hex}.xlsx"

    try:
        data = await file.read()
        tmp_path.write_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存上传文件失败: {e}") from e

    try:
        # 输出文件不需要检查是否存在，直接构建路径
        out_raw = Path(str(out_rel or "").strip())
        if ".." in out_raw.parts:
            raise PermissionError("output path must not contain '..'")
        output = workspace_root() / out_raw
        try:
            output.relative_to(workspace_root())
        except ValueError as e:
            raise PermissionError("output path must resolve inside WORKSPACE_ROOT") from e
    except (OSError, ValueError, PermissionError) as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        template_path = _resolve_attendance_template(template_relpath)
    except (OSError, ValueError, PermissionError) as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"模板路径无效：{e}") from e

    sh = coerce_sheet_arg(sheet)
    month_clean = month.strip() or None

    try:
        meta = convert_dingtalk_file(
            tmp_path,
            output,
            month=month_clean,
            sheet=sh,
            header_row=hdr,
            template_path=template_path,
        )
        logger.info(f"convert_dingtalk_file 返回：{meta}")
        logger.info(f"rows_stats: {meta.get('rows_stats')}")
    except PermissionError as e:
        logger.warning("attendance_convert_upload permission denied: %s", e)
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail=(e.args[0] if e.args and isinstance(e.args[0], str) else str(e)) or str(e),
        ) from e
    except Exception as e:
        logger.exception("attendance_convert_upload failed")
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "success": True,
        "message": "上传并转换完成",
        "data": {
            **meta,
            "output_relpath": out_rel,
            "template_relpath_resolved": _rel_under_workspace(template_path),
        },
    }


@router.get("/attendance/download")
async def attendance_download(relpath: str) -> FileResponse:
    rel = (relpath or "").strip()
    if not rel:
        raise HTTPException(status_code=400, detail="relpath 必填")
    try:
        path = resolve_workspace_excel(rel)
    except (OSError, ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在或尚未生成")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
