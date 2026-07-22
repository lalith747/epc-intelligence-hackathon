import sqlite3
from typing import List, Dict, Any
from backend.database.init_db import DB_PATH


class StructuredService:
    def __init__(self) -> None:
        self.db_path = DB_PATH

    def list_structured_records(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, title, document_type, vendor, revision, issue_date, approval_status, equipment_ids, drawing_numbers, spec_references, status, created_at FROM documents WHERE document_type IN ('CSV', 'SCHEDULE', 'DATA') ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
