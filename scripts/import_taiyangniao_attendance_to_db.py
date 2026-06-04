from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shell.taiyangniao_attendance.parser import parse_attendance_workbook


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            month_label TEXT NOT NULL,
            rows_in INTEGER NOT NULL,
            rows_written INTEGER NOT NULL,
            imported_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            month_label TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            employee_name TEXT NOT NULL,
            attendance_group TEXT NOT NULL,
            department TEXT NOT NULL,
            employee_no TEXT NOT NULL,
            position TEXT NOT NULL,
            user_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            daily_times_json TEXT NOT NULL,
            raw_times_json TEXT NOT NULL,
            all_times_json TEXT NOT NULL,
            leave_hours REAL NOT NULL,
            absent_days REAL NOT NULL,
            late_count_hint REAL NOT NULL,
            early_count_hint REAL NOT NULL,
            missing_card_count REAL NOT NULL,
            notes_json TEXT NOT NULL,
            imported_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_attendance_source_row
        ON attendance_daily_records (source_file, source_row)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_attendance_employee_date
        ON attendance_daily_records (employee_name, work_date)
        """
    )


def _to_dt_str_list(values) -> list[str]:
    return [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in values]


def import_attendance(input_file: Path, db_file: Path, month: str | None = None) -> tuple[int, int]:
    parsed = parse_attendance_workbook(input_file, month=month)
    source_file = str(input_file.resolve())
    month_label = parsed.month or (month or "")
    imported_at = datetime.now().isoformat(timespec="seconds")

    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN")
        conn.execute("DELETE FROM attendance_daily_records WHERE source_file = ?", (source_file,))

        rows_written = 0
        for r in parsed.records:
            daily_times = _to_dt_str_list(r.daily_times)
            raw_times = _to_dt_str_list(r.raw_times)
            all_times = _to_dt_str_list(r.all_punch_times())
            conn.execute(
                """
                INSERT INTO attendance_daily_records (
                    source_file,
                    month_label,
                    source_row,
                    employee_name,
                    attendance_group,
                    department,
                    employee_no,
                    position,
                    user_id,
                    work_date,
                    shift_name,
                    daily_times_json,
                    raw_times_json,
                    all_times_json,
                    leave_hours,
                    absent_days,
                    late_count_hint,
                    early_count_hint,
                    missing_card_count,
                    notes_json,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_file,
                    month_label,
                    int(r.source_row),
                    r.employee_name,
                    r.attendance_group,
                    r.department,
                    r.employee_no,
                    r.position,
                    r.user_id,
                    r.work_date.isoformat(),
                    r.shift_name,
                    json.dumps(daily_times, ensure_ascii=False),
                    json.dumps(raw_times, ensure_ascii=False),
                    json.dumps(all_times, ensure_ascii=False),
                    float(r.leave_hours),
                    float(r.absent_days),
                    float(r.late_count_hint),
                    float(r.early_count_hint),
                    float(r.missing_card_count),
                    json.dumps(r.notes, ensure_ascii=False),
                    imported_at,
                ),
            )
            rows_written += 1

        conn.execute(
            """
            INSERT INTO attendance_import_batches (
                source_file, month_label, rows_in, rows_written, imported_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (source_file, month_label, int(parsed.rows_in), int(rows_written), imported_at),
        )
        conn.commit()
        return parsed.rows_in, rows_written
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import DingTalk attendance workbook into taiyangniao mod SQLite DB."
    )
    parser.add_argument(
        "--input",
        default="e:/FHD/424/钉钉导出来的考勤数据.xlsx",
        help="Input attendance workbook path",
    )
    parser.add_argument(
        "--db",
        default="e:/FHD/data/mod_dbs/taiyangniao_pro.db",
        help="Target sqlite database path",
    )
    parser.add_argument(
        "--month",
        default="",
        help="Optional month label, e.g. 2026-03; empty means auto-detect",
    )
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    db_file = Path(args.db).resolve()
    month = args.month.strip() or None

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    rows_in, rows_written = import_attendance(input_file, db_file, month=month)
    print(f"db={db_file}")
    print(f"input={input_file}")
    print(f"rows_in={rows_in}")
    print(f"rows_written={rows_written}")


if __name__ == "__main__":
    main()
