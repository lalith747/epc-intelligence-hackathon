import csv
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from backend.database.init_db import DB_PATH


class ConnectorService:
    def __init__(self) -> None:
        self.db_path = DB_PATH

    def ingest_csv(self, file_path: str, source_type: str = "procurement") -> List[Dict[str, Any]]:
        path = Path(file_path)
        rows: List[Dict[str, Any]] = []
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append(self._normalize_row(row, source_type))
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            frame = pd.read_excel(path)
            for record in frame.to_dict(orient="records"):
                rows.append(self._normalize_row({str(k): v for k, v in record.items()}, source_type))
        self._store_rows(rows, source_type)
        return rows

    def _normalize_row(self, row: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        normalized = {
            "source_type": source_type,
            "source_id": row.get("Document Type") or row.get("Activity ID") or row.get("ID") or "",
            "title": row.get("Document Type") or row.get("Activity Name") or row.get("Item") or "Imported Record",
            "content": json.dumps(row, ensure_ascii=False),
            "metadata": json.dumps({k: v for k, v in row.items()}),
            "vendor": row.get("Vendor") or row.get("Resource") or "",
            "revision": row.get("Revision") or row.get("Rev") or "",
            "issue_date": row.get("Issue Date") or row.get("Start Date") or row.get("Date") or "",
            "approval_status": row.get("Approval Status") or row.get("Status") or "",
            "equipment_ids": row.get("Equipment IDs") or row.get("Equipment") or "",
            "drawing_numbers": row.get("Drawing Numbers") or row.get("Drawing") or "",
            "spec_references": row.get("Specification References") or row.get("Reference") or "",
        }
        return normalized

    def _store_rows(self, rows: List[Dict[str, Any]], source_type: str) -> None:
        conn = sqlite3.connect(self.db_path)
        for row in rows:
            conn.execute(
                """
                INSERT INTO documents (title, file_name, document_type, vendor, project, revision, issue_date, approval_status, equipment_ids, drawing_numbers, spec_references, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed')
                """,
                (
                    row.get("title"),
                    f"{source_type}.import",
                    "CSV" if source_type in {"procurement", "schedule"} else "DATA",
                    row.get("vendor"),
                    "Data Center EPC Project",
                    row.get("revision"),
                    row.get("issue_date"),
                    row.get("approval_status"),
                    row.get("equipment_ids"),
                    row.get("drawing_numbers"),
                    row.get("spec_references"),
                ),
            )
            document_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO chunks (document_id, content, section, page_number, metadata) VALUES (?, ?, ?, ?, ?)",
                (document_id, row.get("content"), row.get("source_type"), 1, row.get("metadata")),
            )
        conn.commit()
        conn.close()
