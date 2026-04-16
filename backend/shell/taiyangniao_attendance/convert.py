"""钉钉导出 xlsx → 月度统计表 xlsx（实现说明见原 Mod 文档）。"""

from __future__ import annotations

import os
import re
import uuid
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from .mapping import DINGTALK_COLUMN_ALIASES, STATISTICS_OUTPUT_COLUMNS
from .paths import ensure_parent_dir
from .rules import process_attendance_dataframe, AttendanceRule


def _to_datetime_mixed(series: pd.Series) -> pd.Series:
    """钉钉列里常有字符串/时间戳混排；pandas 2.0+ 用 format='mixed'，旧版回退并抑制推断告警。"""
    s = series
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            return pd.to_datetime(s, errors="coerce", format="mixed")
        except TypeError:
            return pd.to_datetime(s, errors="coerce")


def _norm_header(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def _pick_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    cols = list(df.columns)
    norm_map = {_norm_header(c): str(c) for c in cols}
    for a in aliases:
        key = _norm_header(a)
        if key in norm_map:
            return norm_map[key]
    for a in aliases:
        ak = _norm_header(a)
        for c in cols:
            cn = _norm_header(c)
            if ak and ak in cn:
                return str(c)
    return None


def _extract_month_from_file(path: Path, sheet: str | int | None = 0) -> str | None:
    """从钉钉导出文件的标题行提取统计月份，如 '2026-03'。"""
    try:
        raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
        if raw_df.empty:
            return None
        title_val = raw_df.iloc[0, 0]
        if pd.isna(title_val):
            return None
        import re
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+至\s+(\d{4})-(\d{2})-(\d{2})", str(title_val))
        if m:
            return f"{m.group(1)}-{m.group(2)}"
    except Exception:
        pass
    return None


def read_dingtalk_dataframe(
    path: Path,
    *,
    sheet: str | int | None = 0,
    header_row: int | None = None,
) -> pd.DataFrame:
    if header_row is None:
        header_row = _auto_detect_header_row(path, sheet)
    return pd.read_excel(path, sheet_name=sheet, header=header_row, engine="openpyxl")


def _auto_detect_header_row(path: Path, sheet: str | int | None = 0) -> int:
    """自动检测钉钉导出文件的表头行。

    钉钉导出的文件通常有2-4行表头（标题、生成时间、列名、日期行）。
    通过查找包含已知列名（如"姓名"、"工号"）的行来确定表头行。
    """
    try:
        raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    except Exception:
        return 0

    if raw_df.empty:
        return 0

    known_columns = {"姓名", "工号", "部门", "打卡时间", "考勤日期"}
    max_scan_rows = min(10, len(raw_df))

    for row_idx in range(max_scan_rows):
        row_values = set(str(v).strip() for v in raw_df.iloc[row_idx].tolist() if pd.notna(v))
        matched = row_values & known_columns
        if len(matched) >= 2:
            return row_idx

    return 0


def _is_date_subheader_row(row: pd.Series) -> bool:
    """检测是否为钉钉日期子表头行（如 '日','2','3','4'...）。"""
    non_null = row.dropna()
    if len(non_null) == 0:
        return False
    str_vals = set(str(v).strip() for v in non_null)
    date_indicators = {"日", "一", "二", "三", "四", "五", "六", "天"}
    weekday_count = sum(1 for v in str_vals if v in date_indicators)
    if weekday_count >= 2:
        return True
    numeric_days = [v for v in str_vals if v.isdigit() and 1 <= int(v) <= 31]
    return len(numeric_days) >= 10


def _parse_date_columns(df: pd.DataFrame, header_row_idx: int) -> dict[int, str]:
    """解析日期子表头行，返回列索引到日期字符串的映射。"""
    date_map = {}
    if header_row_idx >= len(df):
        return date_map

    row = df.iloc[header_row_idx]
    for col_idx in range(len(row)):
        val = row.iloc[col_idx]
        if pd.isna(val):
            continue
        val_str = str(val).strip()
        if val_str.isdigit() and 1 <= int(val_str) <= 31:
            date_map[col_idx] = val_str
        elif val_str in {"日", "一", "二", "三", "四", "五", "六", "天"}:
            date_map[col_idx] = val_str
    return date_map


def _parse_check_times(val: Any) -> tuple[Any, Any]:
    """解析钉钉的打卡时间字符串，返回 (上班打卡, 下班打卡)。"""
    if pd.isna(val):
        return pd.NaT, pd.NaT
    val_str = str(val).strip()
    parts = val_str.split('\n')
    check_in = pd.NaT
    check_out = pd.NaT
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        p_clean = p.replace(' ', '')
        try:
            if ':' in p_clean:
                h, m = p_clean.split(':')[:2]
                if h.isdigit() and m.isdigit():
                    hours = int(h)
                    minutes = int(m)
                    if 0 <= hours <= 23 and 0 <= minutes <= 59:
                        import datetime
                        dt = datetime.datetime(1900, 1, 1, hours, minutes)
                        if i == 0:
                            check_in = dt
                        else:
                            check_out = dt
        except Exception:
            pass
    return check_in, check_out


def _build_wide_to_long(df: pd.DataFrame, meta_cols: dict[str, str | None]) -> pd.DataFrame:
    """将钉钉宽表格式转换为长表格式（每行一条打卡记录）。"""
    rows = []
    for _, emp_row in df.iterrows():
        emp_name = str(emp_row[meta_cols["name"]]).strip() if meta_cols.get("name") else ""
        emp_no = str(emp_row[meta_cols["emp_no"]]).strip() if meta_cols.get("emp_no") else ""
        dept = str(emp_row[meta_cols["dept"]]).strip() if meta_cols.get("dept") else ""

        for col_idx, date_info in meta_cols["date_columns"].items():
            day_str, date_month = date_info
            date_val = f"{date_month}-{int(day_str):02d}" if date_month else day_str
            check_in_val = emp_row.iloc[col_idx] if col_idx < len(emp_row) else None
            check_in, check_out = _parse_check_times(check_in_val)

            rows.append({
                "姓名": emp_name,
                "工号": emp_no,
                "部门": dept,
                "日期": date_val,
                "上班打卡": check_in,
                "下班打卡": check_out,
            })
    return pd.DataFrame(rows)


def build_normalized_frame(df: pd.DataFrame, *, month: str | None = None) -> pd.DataFrame:
    # 检测日期标题行（可能在第 0 行或第 1 行）
    date_header_row_idx = None
    if len(df) > 0 and _is_date_subheader_row(df.iloc[0]):
        date_header_row_idx = 0
    elif len(df) > 1 and _is_date_subheader_row(df.iloc[1]):
        date_header_row_idx = 1

    if date_header_row_idx is not None:
        # 跳过日期标题行
        df_data = df.drop(df.index[date_header_row_idx]).reset_index(drop=True)
    else:
        df_data = df

    picks: dict[str, str | None] = {}
    for logical, aliases in DINGTALK_COLUMN_ALIASES.items():
        picks[logical] = _pick_column(df_data, aliases)

    date_columns = {}
    if date_header_row_idx is not None:
        for col_idx in range(len(df.columns)):
            val = df.iloc[date_header_row_idx, col_idx]
            if pd.notna(val):
                val_str = str(val).strip()
                if val_str.isdigit() and 1 <= int(val_str) <= 31:
                    date_columns[col_idx] = (val_str, month)

    meta_cols = {
        "name": picks.get("name"),
        "emp_no": picks.get("emp_no"),
        "dept": picks.get("dept"),
        "date_columns": date_columns,
    }

    return _build_wide_to_long(df_data, meta_cols)


def _join_unique_results(s: pd.Series) -> str:
    parts = [str(x).strip() for x in s.tolist() if str(x).strip() and str(x).lower() != "nan"]
    return "、".join(dict.fromkeys(parts))


def aggregate_monthly_stats(norm: pd.DataFrame, *, month: str | None = None) -> pd.DataFrame:
    if norm.empty:
        return pd.DataFrame(columns=STATISTICS_OUTPUT_COLUMNS)

    gcols = ["工号", "姓名", "部门", "日期"]

    agg_specs = [
        ("上班打卡", "上班打卡", "min"),
        ("下班打卡", "下班打卡", "max"),
    ]
    if "工作时长" in norm.columns:
        agg_specs.append(("工作时长", "工作时长", "first"))
    if "考勤结果" in norm.columns:
        agg_specs.append(("考勤结果", "考勤结果", _join_unique_results))

    agg_dict = {out_name: (in_name, agg_fn) for out_name, in_name, agg_fn in agg_specs}
    agg = norm.groupby(gcols, dropna=False, as_index=False).agg(**agg_dict)

    agg = process_attendance_dataframe(agg, base_date=month)

    for c in STATISTICS_OUTPUT_COLUMNS:
        if c not in agg.columns:
            agg[c] = pd.NA

    return agg[STATISTICS_OUTPUT_COLUMNS]


def _write_workbook_to_path(
    stats: pd.DataFrame,
    target: Path,
    *,
    template_path: Path | None,
    dingtalk_detail: pd.DataFrame,
) -> None:
    """写入统计结果到模板。
    
    - 无模板时：生成「月度统计」和「钉钉解析」两个工作表
    - 有模板时：在模板的"明细"工作表中填充数据，保留所有格式、合并单元格和公式
    """
    import os
    import shutil
    
    # 检查模板文件是否存在（处理中文路径编码问题）
    use_template = False
    if template_path is not None:
        parent_dir = str(template_path.parent)
        file_name = template_path.name
        
        # 方法：通过目录列表找到实际的文件名
        try:
            dir_contents = os.listdir(parent_dir)
            # 查找匹配的文件（通过去除空格的方式比较）
            normalized_file_name = file_name.replace(' ', '')
            for f in dir_contents:
                if f.replace(' ', '') == normalized_file_name:
                    # 找到匹配的文件，先复制模板到输出路径
                    old_cwd = os.getcwd()
                    try:
                        os.chdir(parent_dir)
                        # 复制模板文件到输出路径
                        target_str = str(target)
                        target_parent = os.path.dirname(target_str)
                        if not os.path.exists(target_parent):
                            os.makedirs(target_parent)
                        shutil.copy2(f, target_str)
                        use_template = True
                    finally:
                        os.chdir(old_cwd)
                    break
        except Exception:
            # 如果目录列表失败，尝试直接使用 Path（通过目录列表验证）
            import os
            parent_dir = template_path.parent
            file_name = template_path.name
            try:
                dir_contents = os.listdir(str(parent_dir))
                normalized_file_name = file_name.replace(' ', '')
                for f in dir_contents:
                    if f.replace(' ', '') == normalized_file_name:
                        # 找到匹配的文件，使用 chdir 方式复制
                        old_cwd = os.getcwd()
                        try:
                            os.chdir(str(parent_dir))
                            target_str = str(target)
                            target_parent = os.path.dirname(target_str)
                            if not os.path.exists(target_parent):
                                os.makedirs(target_parent)
                            shutil.copy2(f, target_str)
                            use_template = True
                        finally:
                            os.chdir(old_cwd)
                        break
            except Exception:
                pass
    
    if use_template:
        from openpyxl import load_workbook
        
        # 加载已复制的模板（使用输出路径，避免编码问题）
        wb = load_workbook(str(target))
        
        # 使用模板的"明细"工作表
        if "明细" in wb.sheetnames:
            ws = wb["明细"]
        else:
            ws = wb.active
        
        # 清空数据区域（从第 4 行开始到最后）
        # 获取合并单元格范围，避免清空合并单元格
        merged_ranges = ws.merged_cells.ranges
        
        for row_idx in range(4, ws.max_row + 1):
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                # 检查是否在合并单元格范围内
                is_merged = False
                for merged_range in merged_ranges:
                    if (merged_range.min_row <= row_idx <= merged_range.max_row and
                        merged_range.min_col <= col_idx <= merged_range.max_col):
                        is_merged = True
                        break
                
                # 只清空非合并单元格和非公式单元格
                if not is_merged:
                    if not cell.value or (isinstance(cell.value, str) and not cell.value.startswith('=')):
                        cell.value = None
        
        # 从钉钉原始数据中提取员工打卡数据
        # dingtalk_detail 包含规范化的长表格式数据
        # 需要将其转换为模板需要的格式
        
        # 按员工分组
        if '姓名' in dingtalk_detail.columns:
            employees = dingtalk_detail['姓名'].dropna().unique()
        else:
            employees = []
        
        current_row = 4
        for emp_name in employees:
            emp_data = dingtalk_detail[dingtalk_detail['姓名'] == emp_name]
            
            if emp_data.empty:
                continue
            
            # 获取员工信息
            emp_dept = emp_data['部门'].iloc[0] if '部门' in emp_data.columns else ''
            
            # 每个员工占 6 行（上午、下午、晚上各 2 行）
            for time_period_idx, time_period in enumerate(['上午', '下午', '晚上']):
                base_row = current_row + time_period_idx * 2
                
                # 第一行填写部门、姓名、时段
                if time_period_idx == 0:
                    ws.cell(row=base_row, column=1, value=emp_dept)  # A 列：部门
                    ws.cell(row=base_row, column=2, value='计时')     # B 列：性质
                    ws.cell(row=base_row, column=3, value=emp_name)  # C 列：姓名
                
                ws.cell(row=base_row, column=4, value=time_period)   # D 列：时段
                
                # 填充 31 天的打卡数据
                # 模板中每天的列位置：G 列开始，每 3 列一组（标记、工时、标记）
                for day in range(1, 32):
                    date_str = f'2026-03-{day:02d}'
                    day_data = emp_data[emp_data['日期'] == date_str]
                    
                    col_base = 7 + (day - 1) * 3  # G 列是第 7 列
                    
                    if col_base + 2 <= ws.max_column:
                        if not day_data.empty:
                            check_in = day_data['上班打卡'].iloc[0] if '上班打卡' in day_data.columns else None
                            check_out = day_data['下班打卡'].iloc[0] if '下班打卡' in day_data.columns else None
                            work_hours = day_data['工作时长'].iloc[0] if '工作时长' in day_data.columns else 0
                            
                            # 根据打卡情况填充标记
                            if pd.notna(check_in) or pd.notna(check_out):
                                # 有打卡记录
                                ws.cell(row=base_row, column=col_base, value='√')
                                ws.cell(row=base_row, column=col_base + 1, value=work_hours if pd.notna(work_hours) else 0)
                                ws.cell(row=base_row, column=col_base + 2, value='√')
                            else:
                                # 无打卡记录
                                ws.cell(row=base_row, column=col_base, value='☆')
                                ws.cell(row=base_row, column=col_base + 2, value='☆')
                        else:
                            # 无数据
                            ws.cell(row=base_row, column=col_base, value='☆')
                            ws.cell(row=base_row, column=col_base + 2, value='☆')
            
            current_row += 6
        
        # 保存文件（覆盖已复制的模板）
        wb.save(str(target))
        wb.close()
    else:
        # 无模板时，生成两个工作表
        with pd.ExcelWriter(target, engine="openpyxl", mode="w") as writer:
            stats.to_excel(writer, sheet_name="月度统计", index=False)
            dingtalk_detail.to_excel(writer, sheet_name="钉钉解析", index=False)


def write_statistics_workbook(
    stats: pd.DataFrame,
    output_path: Path,
    *,
    template_path: Path | None = None,
    dingtalk_detail: pd.DataFrame | None = None,
) -> None:
    """先写到同目录临时文件再 ``os.replace``，避免目标已存在时部分环境直接打开失败。"""
    ensure_parent_dir(output_path)
    detail = dingtalk_detail if dingtalk_detail is not None else stats
    parent = output_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / f"{output_path.stem}_writing_{uuid.uuid4().hex[:12]}{output_path.suffix}"
    try:
        _write_workbook_to_path(stats, tmp, template_path=template_path, dingtalk_detail=detail)
        os.replace(tmp, output_path)
    except PermissionError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise PermissionError(
            "无法写入输出文件：若该文件正被 Excel（或其它程序）打开，请先关闭后再试；"
            "或在前端修改「输出相对路径」为新的文件名。"
        ) from e
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def convert_dingtalk_file(
    source: Path,
    output: Path,
    *,
    month: str | None = None,
    sheet: str | int | None = 0,
    header_row: int | None = None,
    template_path: Path | None = None,
) -> dict[str, Any]:
    raw = read_dingtalk_dataframe(source, sheet=sheet, header_row=header_row)
    if month is None:
        month = _extract_month_from_file(source, sheet)
    norm = build_normalized_frame(raw, month=month)
    stats = aggregate_monthly_stats(norm, month=month)

    write_statistics_workbook(
        stats,
        output,
        template_path=template_path,
        dingtalk_detail=norm,
    )

    return {
        "rows_in": len(raw),
        "rows_stats": len(stats),
        "output": str(output.resolve()),
        "month": month or "",
    }


def coerce_sheet_arg(raw: Any) -> str | int:
    if raw is None or raw == "":
        return 0
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    s = str(raw).strip()
    if s.isdigit():
        return int(s)
    return s
