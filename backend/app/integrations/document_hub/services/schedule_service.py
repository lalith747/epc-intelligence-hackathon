import csv
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from backend.database.init_db import DB_PATH


class ScheduleService:
    def __init__(self) -> None:
        self.db_path = DB_PATH

    def ingest_schedule(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)
        records: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                record = {
                    "activity_id": row.get("Activity ID") or row.get("ID") or "",
                    "activity_name": row.get("Activity Name") or row.get("Name") or "",
                    "start_date": row.get("Start Date") or row.get("Start") or "",
                    "finish_date": row.get("Finish Date") or row.get("Finish") or "",
                    "percent_complete": row.get("Percent Complete") or row.get("Progress") or "",
                    "resource": row.get("Resource") or row.get("Assigned To") or "",
                }
                records.append(record)
                self._store_record(record)
        return records

    def _store_record(self, record: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO documents (title, file_name, document_type, vendor, project, revision, issue_date, approval_status, equipment_ids, drawing_numbers, spec_references, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed')
            """,
            (
                record.get("activity_name"),
                f"schedule_{record.get('activity_id', 'record')}.csv",
                "SCHEDULE",
                record.get("resource"),
                "Data Center EPC Project",
                "",
                record.get("start_date"),
                record.get("percent_complete"),
                "",
                "",
                "",
            ),
        )
        document_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO chunks (document_id, content, section, page_number, metadata) VALUES (?, ?, ?, ?, ?)",
            (document_id, json.dumps(record, ensure_ascii=False), "Schedule", 1, json.dumps(record)),
        )
        conn.commit()
        conn.close()
