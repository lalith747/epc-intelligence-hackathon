import sqlite3
from datetime import datetime
from backend.database.init_db import DB_PATH


class AuditService:
    def __init__(self) -> None:
        self.db_path = DB_PATH

    def log(self, action: str, document: str, user: str = "demo-user") -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO audit_logs (action, document, user) VALUES (?, ?, ?)",
            (action, document, user),
        )
        conn.commit()
        conn.close()
