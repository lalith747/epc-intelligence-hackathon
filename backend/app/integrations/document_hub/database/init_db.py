import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hub.sqlite3"


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_name TEXT NOT NULL,
            document_type TEXT,
            vendor TEXT,
            project TEXT,
            revision TEXT,
            issue_date TEXT,
            approval_status TEXT,
            equipment_ids TEXT,
            drawing_numbers TEXT,
            spec_references TEXT,
            status TEXT DEFAULT 'processed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            content TEXT,
            section TEXT,
            page_number INTEGER,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            prompt TEXT,
            response TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            document TEXT,
            user TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS compliance_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            overall_score REAL,
            status TEXT,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    # Lightweight migration for DBs created before conversation_id existed.
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(chat_history)").fetchall()}
    if "conversation_id" not in existing_cols:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN conversation_id TEXT")
        conn.commit()
    conn.close()

    from backend.database.seed import seed_sample_documents

    seed_sample_documents()
