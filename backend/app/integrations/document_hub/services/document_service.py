import json
import sqlite3
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from backend.database.init_db import DB_PATH
from backend.schemas.models import SearchRequest
from backend.services.audit_service import AuditService
from backend.services.extraction_service import extract_text
from backend.services.metadata_extractor import extract_metadata, infer_category_from_filename

STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

_EXT_TYPE_MAP = {
    ".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT", ".csv": "CSV",
    ".xlsx": "XLSX", ".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
}


class DocumentService:
    def __init__(self) -> None:
        self.db_path = DB_PATH
        self.audit_service = AuditService()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_documents(self) -> List[dict]:
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count
            FROM documents d ORDER BY d.created_at DESC
            """
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_document(self, document_id: int) -> Optional[dict]:
        conn = self._connect()
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            conn.close()
            return None
        doc = dict(row)
        doc["chunks"] = [
            dict(r) for r in conn.execute(
                "SELECT id, section, page_number, content FROM chunks WHERE document_id = ? ORDER BY id",
                (document_id,),
            ).fetchall()
        ]
        doc["versions"] = [
            dict(r) for r in conn.execute(
                "SELECT id, version, created_at FROM document_versions WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
        ]
        conn.close()
        return doc

    def get_file_path(self, document_id: int) -> Optional[Path]:
        conn = self._connect()
        row = conn.execute("SELECT file_name FROM documents WHERE id = ?", (document_id,)).fetchone()
        conn.close()
        if not row:
            return None
        candidate = STORAGE_DIR / row["file_name"]
        return candidate if candidate.exists() else None

    def upload_document(self, file: UploadFile, title: str) -> dict:
        file_name = file.filename or "document"
        destination = STORAGE_DIR / file_name
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        text_body, chunks = extract_text(destination)
        meta = extract_metadata(text_body, file_name)
        ext_type = _EXT_TYPE_MAP.get(destination.suffix.lower(), "PDF")
        category = meta["document_category"]
        document_type = category if category != "Unclassified" else ext_type

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (title, file_name, document_type, vendor, project, revision, issue_date, approval_status, equipment_ids, drawing_numbers, spec_references, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed')
            """,
            (
                title,
                file_name,
                document_type,
                meta.get("vendor") or "Unspecified",
                "Riyadh Data Centre EPC Program",
                meta.get("revision") or "Unspecified",
                meta.get("issue_date") or "",
                meta.get("approval_status") or "Pending",
                ", ".join(meta.get("equipment_ids") or []),
                ", ".join(meta.get("drawing_numbers") or []),
                ", ".join(meta.get("spec_references") or []),
            ),
        )
        document_id = cursor.lastrowid
        for index, chunk in enumerate(chunks, start=1):
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
                section_name = chunk.get("section") or f"Section {index}"
                page_number = chunk.get("page_number", 1)
                metadata = {"source": file_name, **{k: v for k, v in chunk.items() if k not in {"content", "section", "page_number"}}}
            else:
                content = chunk
                section_name = f"Section {index}"
                page_number = 1
                metadata = {"source": file_name}
            conn.execute(
                "INSERT INTO chunks (document_id, content, section, page_number, metadata) VALUES (?, ?, ?, ?, ?)",
                (document_id, content, section_name, page_number, json.dumps(metadata)),
            )
        conn.commit()
        conn.execute(
            "INSERT INTO document_versions (document_id, version) VALUES (?, ?)",
            (document_id, meta.get("revision") or "Unspecified"),
        )
        conn.commit()
        conn.close()
        self.audit_service.log("upload", title)
        return {
            "id": document_id, "title": title, "status": "processed", "file_name": file_name,
            "chunks": len(chunks), "document_type": document_type,
            "vendor": meta.get("vendor"), "revision": meta.get("revision"),
            "equipment_ids": meta.get("equipment_ids"), "is_scanned": text_body.strip() == "",
        }

    def delete_document(self, document_id: int) -> dict:
        conn = self._connect()
        row = conn.execute("SELECT title, file_name FROM documents WHERE id = ?", (document_id,)).fetchone()
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.execute("DELETE FROM document_versions WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        conn.commit()
        conn.close()
        self.audit_service.log("delete", row["title"] if row else str(document_id))
        return {"deleted": True, "id": document_id}

    def get_metadata(self) -> dict:
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) as count FROM documents").fetchone()["count"]
        types = conn.execute("SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type").fetchall()
        vendors = conn.execute(
            "SELECT DISTINCT vendor FROM documents WHERE vendor IS NOT NULL AND vendor != '' ORDER BY vendor"
        ).fetchall()
        revisions = conn.execute(
            "SELECT DISTINCT revision FROM documents WHERE revision IS NOT NULL AND revision != '' ORDER BY revision"
        ).fetchall()
        statuses = conn.execute(
            "SELECT DISTINCT approval_status FROM documents WHERE approval_status IS NOT NULL AND approval_status != ''"
        ).fetchall()
        conn.close()
        return {
            "total_documents": total,
            "types": [dict(row) for row in types],
            "vendors": [row["vendor"] for row in vendors],
            "revisions": [row["revision"] for row in revisions],
            "approval_statuses": [row["approval_status"] for row in statuses],
        }

    def get_dashboard(self) -> dict:
        conn = self._connect()
        documents = conn.execute("SELECT COUNT(*) as count FROM documents").fetchone()["count"]
        recent = conn.execute("SELECT id, title, document_type, created_at FROM documents ORDER BY created_at DESC LIMIT 6").fetchall()
        types = conn.execute(
            "SELECT document_type as name, COUNT(*) as count FROM documents GROUP BY document_type ORDER BY count DESC"
        ).fetchall()
        needing_review = conn.execute(
            "SELECT COUNT(*) as count FROM documents WHERE approval_status IN ('Pending', 'Under Review', 'Rejected')"
        ).fetchone()["count"]
        compliance_rows = conn.execute(
            "SELECT status, overall_score FROM compliance_reports"
        ).fetchall()
        compliance_status = {"pass": 0, "warning": 0, "fail": 0}
        for row in compliance_rows:
            score = (row["overall_score"] or "").lower()
            if score in compliance_status:
                compliance_status[score] += 1
        ai_queries = conn.execute("SELECT COUNT(*) as count FROM chat_history WHERE prompt IS NOT NULL").fetchone()["count"]

        storage_bytes = 0
        for f in STORAGE_DIR.glob("*"):
            if f.is_file():
                storage_bytes += f.stat().st_size
        storage_mb = round(storage_bytes / (1024 * 1024), 2)

        most_queried = conn.execute(
            """
            SELECT d.title, COUNT(*) as hits FROM chat_history ch
            JOIN documents d ON 1=1
            WHERE ch.response LIKE '%' || d.title || '%'
            GROUP BY d.title ORDER BY hits DESC LIMIT 5
            """
        ).fetchall()
        conn.close()

        return {
            "uploaded_documents": documents,
            "recent_uploads": [dict(row) for row in recent],
            "document_types": [dict(row) for row in types],
            "compliance_status": compliance_status,
            "documents_needing_review": needing_review,
            "most_queried_documents": [dict(row) for row in most_queried],
            "storage_usage": f"{storage_mb} MB",
            "ai_usage": f"{ai_queries} queries",
        }

    def search_documents(self, request: SearchRequest) -> dict:
        conn = self._connect()
        query = """
            SELECT DISTINCT d.*, c.content AS matched_content, c.page_number AS matched_page, c.section AS matched_section
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            WHERE 1=1
        """
        params: List[object] = []
        if request.document_type:
            query += " AND d.document_type = ?"
            params.append(request.document_type)
        if request.vendor:
            query += " AND d.vendor = ?"
            params.append(request.vendor)
        if request.revision:
            query += " AND d.revision = ?"
            params.append(request.revision)
        if request.date:
            query += " AND d.issue_date = ?"
            params.append(request.date)
        if request.equipment:
            query += " AND d.equipment_ids LIKE ?"
            params.append(f"%{request.equipment}%")
        if request.approval_status:
            query += " AND d.approval_status = ?"
            params.append(request.approval_status)
        if request.query:
            query += """ AND (
                d.title LIKE ? OR d.project LIKE ? OR d.document_type LIKE ?
                OR d.vendor LIKE ? OR d.spec_references LIKE ? OR c.content LIKE ?
            )"""
            params.extend([f"%{request.query}%" for _ in range(6)])
        query += " ORDER BY d.id"
        rows = conn.execute(query, params).fetchall()
        conn.close()

        results = []
        seen_ids = set()
        for row in rows:
            doc = dict(row)
            snippet = ""
            if doc.get("matched_content") and request.query:
                content = doc["matched_content"]
                idx = content.lower().find(request.query.lower())
                if idx >= 0:
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(request.query) + 60)
                    snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                else:
                    snippet = content[:150]
            if doc["id"] in seen_ids and not snippet:
                continue
            seen_ids.add(doc["id"])
            results.append({
                "id": doc["id"], "title": doc["title"], "document_type": doc["document_type"],
                "vendor": doc["vendor"], "revision": doc["revision"], "approval_status": doc["approval_status"],
                "spec_references": doc["spec_references"], "snippet": snippet or (doc.get("title") or ""),
                "page_number": doc.get("matched_page"), "section": doc.get("matched_section"),
                "confidence": 0.95 if snippet else 0.6,
            })
        return {"results": results, "count": len(results)}

    def _infer_document_type(self, file_name: str) -> str:
        category = infer_category_from_filename(file_name)
        if category != "Unclassified":
            return category
        return _EXT_TYPE_MAP.get(Path(file_name).suffix.lower(), "PDF")
