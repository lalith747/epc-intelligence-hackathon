import base64
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import smtplib
import sys
import uuid
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BOOT_BACKEND_DIR = Path(__file__).resolve().parents[2]
BOOT_VENDOR_DIR = BOOT_BACKEND_DIR / "vendor"
if BOOT_VENDOR_DIR.exists() and str(BOOT_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(BOOT_VENDOR_DIR))

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
DB_PATH = BACKEND_DIR / "ai_monitoring.db"
HUB_DIR = BACKEND_DIR / "data" / "intelligence_hub"
DOCUMENT_DIR = HUB_DIR / "documents"
SAMPLE_DIR = HUB_DIR / "samples"
REPORT_DIR = HUB_DIR / "reports"
VECTOR_DIR = BACKEND_DIR / "vector_store"
PROVIDED_STORAGE = BACKEND_DIR / "app" / "integrations" / "document_hub" / "storage"
PROVIDED_COMPLIANCE = BACKEND_DIR / "app" / "integrations" / "document_hub" / "database" / "Compliance_Rules.pdf"
ETHACK_SOURCE = ROOT_DIR.parent / "work" / "audit_ethack_source"

def load_local_env(override: bool = False) -> None:
    env_path = BACKEND_DIR / ".env"
    if load_dotenv is not None:
        load_dotenv(env_path, override=override)
        return
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


load_local_env()

DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)


class IntelligenceHub:
    def __init__(self) -> None:
        self.groq_client = None
        load_local_env()
        if Groq is not None and os.getenv("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        if genai is not None and (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        self.embedding_model = None
        self.embedding_model_failed = False
        self.embedding_model_error = ""
        self.gemini_last_error = ""

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS intelligence_documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    mime_type TEXT,
                    document_type TEXT,
                    vendor TEXT,
                    project TEXT,
                    revision TEXT,
                    issue_date TEXT,
                    approval_status TEXT,
                    extraction_method TEXT,
                    extracted_text TEXT,
                    metadata TEXT,
                    status TEXT DEFAULT 'processed',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS intelligence_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    section TEXT,
                    page_number INTEGER,
                    metadata TEXT,
                    FOREIGN KEY(document_id) REFERENCES intelligence_documents(id)
                );

                CREATE TABLE IF NOT EXISTS compliance_issues (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    category TEXT,
                    severity TEXT,
                    description TEXT,
                    evidence TEXT,
                    recommendation TEXT,
                    reference TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES intelligence_documents(id)
                );

                CREATE TABLE IF NOT EXISTS action_items (
                    id TEXT PRIMARY KEY,
                    source_document_id TEXT,
                    title TEXT,
                    owner TEXT,
                    due_date TEXT,
                    status TEXT DEFAULT 'open',
                    decision_summary TEXT,
                    similar_reference TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS report_history (
                    id TEXT PRIMARY KEY,
                    report_type TEXT,
                    period_start TEXT,
                    period_end TEXT,
                    file_path TEXT,
                    status TEXT,
                    summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS rag_chat_history (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    message TEXT,
                    citations TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS smart_notifications (
                    id TEXT PRIMARY KEY,
                    notification_type TEXT,
                    severity TEXT,
                    title TEXT,
                    message TEXT,
                    source TEXT,
                    related_entity_type TEXT,
                    related_entity_id TEXT,
                    channels TEXT,
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS equipment_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tag TEXT,
                    equipment_type TEXT,
                    source_document_id TEXT,
                    extracted_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS vendor_submittals (
                    id TEXT PRIMARY KEY,
                    vendor TEXT NOT NULL,
                    document_id TEXT,
                    equipment_id TEXT,
                    status TEXT DEFAULT 'under_review',
                    score_percent REAL DEFAULT 100,
                    extracted_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS engineering_requirements (
                    id TEXT PRIMARY KEY,
                    equipment_type TEXT,
                    field_name TEXT,
                    operator TEXT,
                    value TEXT,
                    severity TEXT,
                    reference TEXT,
                    params TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS engineering_standards (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    document_id TEXT,
                    category TEXT,
                    extracted_summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS rule_evaluations (
                    id TEXT PRIMARY KEY,
                    document_id TEXT,
                    requirement_id TEXT,
                    status TEXT,
                    requirement_value TEXT,
                    vendor_value TEXT,
                    severity TEXT,
                    explanation TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS integration_status (
                    name TEXT PRIMARY KEY,
                    configured INTEGER DEFAULT 0,
                    status TEXT,
                    detail TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notification_deliveries (
                    id TEXT PRIMARY KEY,
                    notification_id TEXT,
                    channel TEXT,
                    recipient TEXT,
                    status TEXT,
                    provider_response TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS weather_snapshots (
                    id TEXT PRIMARY KEY,
                    order_id TEXT,
                    location TEXT,
                    lat REAL,
                    lng REAL,
                    condition TEXT,
                    temperature_c REAL,
                    wind_speed REAL,
                    risk_score REAL,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS engineer_appointments (
                    id TEXT PRIMARY KEY,
                    engineer_name TEXT,
                    engineer_email TEXT,
                    discipline TEXT,
                    appointment_type TEXT,
                    related_entity_type TEXT,
                    related_entity_id TEXT,
                    scheduled_for TEXT,
                    status TEXT DEFAULT 'scheduled',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sustainability_metrics (
                    id TEXT PRIMARY KEY,
                    metric_date TEXT,
                    ai_requests INTEGER,
                    estimated_kwh REAL,
                    estimated_water_liters REAL,
                    avoided_rework_hours REAL,
                    guidance TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self.seed_requirements(conn)
            self.seed_engineer_appointments(conn)
            self.refresh_integration_status(conn)
        self.seed_samples()
        self.backfill_domain_records()
        self.rebuild_vector_store()
        self.refresh_notifications()

    def seed_requirements(self, conn: sqlite3.Connection) -> None:
        if conn.execute("SELECT COUNT(*) FROM engineering_requirements").fetchone()[0]:
            return
        rows = [
            ("UPS", "redundancy", "not_equals", "N", "critical", "UPS redundancy"),
            ("UPS", "capacity_kva", "greater_equal", "500", "major", "UPS capacity"),
            ("UPS", "certifications", "contains", "UL", "major", "Standards and certifications"),
            ("switchgear", "voltage_v", "greater_equal", "400", "major", "Electrical distribution"),
            ("cooling", "certifications", "contains", "IEC", "major", "Cooling equipment standards"),
            ("containment", "certifications", "contains", "CE", "minor", "Aisle containment certification"),
        ]
        for equipment_type, field_name, operator, value, severity, reference in rows:
            conn.execute(
                """
                INSERT INTO engineering_requirements
                (id, equipment_type, field_name, operator, value, severity, reference, params)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{}')
                """,
                (str(uuid.uuid4()), equipment_type, field_name, operator, value, severity, reference),
            )

    def seed_engineer_appointments(self, conn: sqlite3.Connection) -> None:
        if conn.execute("SELECT COUNT(*) FROM engineer_appointments").fetchone()[0]:
            return
        rows = [
            ("Priya Nair", "priya.nair@orion.example", "Electrical", "Compliance review", "compliance_issue", "", date.today().isoformat(), "Review UPS Hall 3 redundancy/certification flags."),
            ("Omar Khan", "omar.khan@orion.example", "Mechanical", "Site inspection", "schedule_task", "CP-102", (date.today() + timedelta(days=1)).isoformat(), "Validate chiller delivery and weather exposure risk."),
            ("Mei Tan", "mei.tan@orion.example", "Controls", "RFI workshop", "action_item", "", (date.today() + timedelta(days=2)).isoformat(), "Close open RFI/action-item ownership."),
        ]
        for name, email, discipline, appointment_type, entity_type, entity_id, scheduled_for, notes in rows:
            conn.execute(
                """
                INSERT INTO engineer_appointments
                (id, engineer_name, engineer_email, discipline, appointment_type, related_entity_type, related_entity_id, scheduled_for, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), name, email, discipline, appointment_type, entity_type, entity_id, scheduled_for, notes),
            )

    def refresh_integration_status(self, conn: sqlite3.Connection) -> None:
        integrations = {
            "groq": (bool(os.getenv("GROQ_API_KEY")), "Groq Llama 3.1 8B Instant for RAG/compliance generation"),
            "gemini": (bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")), "Gemini multimodal drawing/image analysis"),
            "openweather": (bool(os.getenv("OPENWEATHER_API_KEY")), "OpenWeather procurement route/weather risk"),
            "smtp_email": (bool(os.getenv("SMTP_HOST") and (os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME"))), "SMTP email notification delivery"),
            "twilio": (bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN") and os.getenv("TWILIO_FROM_NUMBER")), "Twilio SMS/WhatsApp notification delivery"),
            "gmail_reader": ((ETHACK_SOURCE / "gmail_reader" / "credentials.json").exists(), "Read-only Gmail import adapter from uploaded ethack code"),
        }
        for name, (configured, detail) in integrations.items():
            conn.execute(
                """
                INSERT INTO integration_status (name, configured, status, detail, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET configured=excluded.configured, status=excluded.status, detail=excluded.detail, updated_at=CURRENT_TIMESTAMP
                """,
                (name, 1 if configured else 0, "configured" if configured else "not_configured", detail),
            )

    def configure_integrations(self, payload: Dict[str, str]) -> Dict[str, Any]:
        allowed = {
            "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENWEATHER_API_KEY",
            "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_FROM_EMAIL",
            "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_WHATSAPP_FROM", "ALERT_RECIPIENT_PHONE",
            "ALERT_RECIPIENT_EMAIL",
        }
        clean = {key: str(value).strip() for key, value in payload.items() if key in allowed and str(value).strip()}
        if not clean:
            return {"updated": [], "status": self.integrations()}
        env_path = BACKEND_DIR / ".env"
        existing: Dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    existing[key.strip()] = value.strip()
        existing.update(clean)
        lines = ["# Unified AI Project Intelligence integration keys"]
        lines.extend(f"{key}={value}" for key, value in sorted(existing.items()))
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for key, value in clean.items():
            os.environ[key] = value
        if Groq is not None and os.getenv("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        if genai is not None and (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        with self.connect() as conn:
            self.refresh_integration_status(conn)
        return {"updated": sorted(clean.keys()), "status": self.integrations(), "env_path": str(env_path)}

    def seed_samples(self) -> None:
        mapping = {
            "sample_spec.pdf": "doc_001_Client_Specification.pdf",
            "sample_compliance.pdf": "Compliance_Rules.pdf",
            "sample_drawing.pdf": "doc_009_Shop_Drawing.pdf",
            "sample_scan.pdf": "doc_020_Test_Record.pdf",
            "sample_schedule.csv": "test_schedule.csv",
            "sample_procurement.csv": "test_proc.csv",
            "sample_rfis.xlsx": "doc_017_RFIs.xlsx",
            "sample_meeting_minutes.pdf": "doc_033_Meeting_Minutes.pdf",
        }
        for target, source in mapping.items():
            if source == "Compliance_Rules.pdf":
                src = PROVIDED_COMPLIANCE
            else:
                src = PROVIDED_STORAGE / source
            if src.exists():
                shutil.copy2(src, SAMPLE_DIR / target)
        png_sample = ETHACK_SOURCE / "hvac_diagram.png"
        if png_sample.exists():
            shutil.copy2(png_sample, SAMPLE_DIR / "sample_drawing.png")
        vendor_demo = ETHACK_SOURCE / "backend" / "vendor_datasheet_demo.pdf"
        if vendor_demo.exists():
            shutil.copy2(vendor_demo, SAMPLE_DIR / "sample_vendor_datasheet.pdf")
        email_csv = SAMPLE_DIR / "sample_emails.csv"
        if not email_csv.exists():
            email_csv.write_text(
                "from,to,subject,date,body\n"
                "lead@epc.example,pm@northstar.example,UPS submittal action,2026-07-18,"
                "\"Please confirm Hall 3 UPS N+1 redundancy and submit UL certificate by 2026-07-24.\"\n"
                "qa@northstar.example,vendor@example,Containment RFI,2026-07-19,"
                "\"RFI-114 asks whether aisle containment panels match the approved shop drawing. Same answer as RFI-082 applies.\"\n",
                encoding="utf-8",
            )
        workforce_csv = SAMPLE_DIR / "sample_workforce.csv"
        if not workforce_csv.exists():
            workforce_csv.write_text(
                "date,trade,planned,available\n"
                f"{date.today().isoformat()},Electrical,18,12\n"
                f"{date.today().isoformat()},Mechanical,14,13\n"
                f"{date.today().isoformat()},Controls,8,5\n",
                encoding="utf-8",
            )
        weather_csv = SAMPLE_DIR / "sample_weather.csv"
        if not weather_csv.exists():
            weather_csv.write_text(
                "date,condition,risk_score\n"
                f"{date.today().isoformat()},Heavy rain forecast,0.18\n"
                f"{(date.today() + timedelta(days=1)).isoformat()},Normal,0.04\n"
                f"{(date.today() + timedelta(days=2)).isoformat()},High humidity commissioning window,0.12\n",
                encoding="utf-8",
            )

        seed_sources = [sample for sample in sorted(SAMPLE_DIR.glob("*")) if sample.is_file()]
        seed_sources.extend(
            file
            for file in sorted(PROVIDED_STORAGE.glob("doc_*"))
            if file.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".json", ".xlsx", ".xls", ".docx", ".txt"}
        )

        for source in seed_sources:
            if not self.document_exists(source.name):
                self.ingest_path(source, is_sample=True)

    def backfill_domain_records(self) -> None:
        with self.connect() as conn:
            docs = [dict(row) for row in conn.execute("SELECT * FROM intelligence_documents").fetchall()]
            for doc in docs:
                existing_equipment = conn.execute("SELECT 1 FROM equipment_assets WHERE source_document_id=? LIMIT 1", (doc["id"],)).fetchone()
                existing_standard = conn.execute("SELECT 1 FROM engineering_standards WHERE document_id=? LIMIT 1", (doc["id"],)).fetchone()
                metadata = json.loads(doc.get("metadata") or "{}")
                if not existing_equipment and not existing_standard:
                    self.sync_domain_records(conn, doc["id"], doc["file_name"], doc["document_type"], metadata, doc.get("extracted_text") or "")
                if not conn.execute("SELECT 1 FROM rule_evaluations WHERE document_id=? LIMIT 1", (doc["id"],)).fetchone():
                    issues = self.run_deterministic_rules(conn, doc)
                    has_rule_issues = conn.execute(
                        "SELECT 1 FROM compliance_issues WHERE document_id=? AND category='Rule Engine' LIMIT 1",
                        (doc["id"],),
                    ).fetchone()
                    if issues and not has_rule_issues:
                        for issue in issues:
                            conn.execute(
                                """
                                INSERT INTO compliance_issues
                                (id, document_id, category, severity, description, evidence, recommendation, reference, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
                                """,
                                (
                                    str(uuid.uuid4()), doc["id"], issue["category"], issue["severity"], issue["description"],
                                    issue["evidence"], issue["recommendation"], issue["reference"],
                                ),
                            )

    def document_exists(self, file_name: str) -> bool:
        with self.connect() as conn:
            return bool(conn.execute("SELECT 1 FROM intelligence_documents WHERE file_name = ? LIMIT 1", (file_name,)).fetchone())

    def ingest_upload(self, upload: Any, title: Optional[str] = None) -> Dict[str, Any]:
        suffix = Path(upload.filename or "document").suffix.lower()
        destination = DOCUMENT_DIR / f"{uuid.uuid4()}{suffix}"
        with destination.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        return self.ingest_path(destination, title=title or upload.filename or destination.name)

    def preview_upload(self, upload: Any) -> Dict[str, Any]:
        suffix = Path(upload.filename or "document").suffix.lower()
        preview_dir = HUB_DIR / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        destination = preview_dir / f"{uuid.uuid4()}{suffix}"
        with destination.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        text, method, _ = self.extract_text(destination)
        metadata = self.extract_metadata(text, upload.filename or destination.name)
        payload: Dict[str, Any] = {
            "file_name": upload.filename or destination.name,
            "mime_type": self.mime_type(destination),
            "document_type": metadata.get("document_category") or self.document_type_from_name(destination.name),
            "extraction_method": method,
            "metadata": metadata,
            "text": text[:12000],
            "temporary_path": str(destination),
            "will_trigger": ["extract", "metadata", "compliance", "rag_reindex"],
        }
        if suffix in {".png", ".jpg", ".jpeg"}:
            payload["data_url"] = f"{self.mime_type(destination)};base64,{base64.b64encode(destination.read_bytes()).decode()}"
        return payload

    def ingest_path(self, path: Path, title: Optional[str] = None, is_sample: bool = False) -> Dict[str, Any]:
        stored = path
        if is_sample:
            stored = DOCUMENT_DIR / path.name
            shutil.copy2(path, stored)
        text, method, page_texts = self.extract_text(stored)
        metadata = self.extract_metadata(text, stored.name)
        doc_id = str(uuid.uuid4())
        chunks = self.chunk_text(text)
        document_type = metadata.get("document_category") or self.document_type_from_name(stored.name)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO intelligence_documents
                (id, title, file_name, stored_path, mime_type, document_type, vendor, project, revision,
                 issue_date, approval_status, extraction_method, extracted_text, metadata, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed')
                """,
                (
                    doc_id,
                    title or stored.stem.replace("_", " "),
                    stored.name,
                    str(stored),
                    self.mime_type(stored),
                    document_type,
                    metadata.get("vendor") or "Unspecified",
                    "Orion Data Centre Campus - Phase 1",
                    metadata.get("revision") or "A",
                    metadata.get("issue_date") or date.today().isoformat(),
                    metadata.get("approval_status") or "Pending",
                    method,
                    text,
                    json.dumps(metadata),
                ),
            )
            for index, chunk in enumerate(chunks, start=1):
                conn.execute(
                    "INSERT INTO intelligence_chunks (id, document_id, content, section, page_number, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), doc_id, chunk, f"Section {index}", 1, json.dumps({"source": stored.name})),
                )
            self.sync_domain_records(conn, doc_id, stored.name, document_type, metadata, text)
        if document_type.lower() in {"email", "emails", "rfi", "rfis", "meeting minutes"} or stored.suffix.lower() in {".csv", ".xlsx"}:
            self.process_communications(doc_id, text)
        issues = self.run_compliance(doc_id)
        self.rebuild_vector_store()
        self.refresh_notifications()
        return {"id": doc_id, "title": title or stored.name, "chunks": len(chunks), "compliance_issues": len(issues), "document_type": document_type}

    def extract_text(self, path: Path) -> Tuple[str, str, List[str]]:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            text = self.extract_csv(path)
            return text, "csv-structured", [text]
        if suffix == ".json":
            text = json.dumps(json.loads(path.read_text(encoding="utf-8", errors="ignore")), indent=2)
            return text, "json-structured", [text]
        if suffix in {".xlsx", ".xls"}:
            text = self.extract_excel(path)
            return text, "spreadsheet-structured", [text]
        if suffix == ".docx":
            text = self.extract_docx(path)
            return text, "docx-xml", [text]
        if suffix == ".pdf":
            text, pages = self.extract_pdf(path)
            method = "pdf-text"
            if len(text.strip()) < 40:
                text = self.ocr_pdf(path)
                pages = [text]
                method = "ocr-scanned-pdf"
            return text, method, pages
        if suffix in {".png", ".jpg", ".jpeg"}:
            ocr_text = self.ocr_image(path)
            visual_text = self.gemini_visual_summary(path)
            text = "\n".join(part for part in [ocr_text, visual_text] if part.strip())
            return text, "ocr+gemini-multimodal" if visual_text else "ocr-image", [text]
        return path.read_text(encoding="utf-8", errors="ignore"), "text", []

    def extract_csv(self, path: Path) -> str:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            return ""
        return "\n".join("; ".join(f"{k}: {v}" for k, v in row.items()) for row in rows)

    def extract_excel(self, path: Path) -> str:
        try:
            import pandas as pd  # type: ignore
            sheets = pd.read_excel(path, sheet_name=None)
            return "\n".join(f"Sheet {name}\n{frame.to_csv(index=False)}" for name, frame in sheets.items())
        except Exception:
            return ""

    def extract_docx(self, path: Path) -> str:
        import zipfile
        with zipfile.ZipFile(path) as archive:
            xml_content = archive.read("word/document.xml")
        root = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join("".join(t.text or "" for t in node.findall(".//w:t", ns)).strip() for node in root.findall(".//w:p", ns))

    def extract_pdf(self, path: Path) -> Tuple[str, List[str]]:
        if fitz is None:
            return "", []
        doc = fitz.open(path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages), pages

    def ocr_pdf(self, path: Path) -> str:
        if fitz is None or pytesseract is None:
            return ""
        doc = fitz.open(path)
        out: List[str] = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples) if Image is not None else None
            if img is not None:
                try:
                    out.append(pytesseract.image_to_string(img))
                except Exception:
                    out.append("")
        doc.close()
        return "\n".join(out)

    def ocr_image(self, path: Path) -> str:
        if Image is None or pytesseract is None:
            return f"Image file captured for visual analysis: {path.name}"
        try:
            return pytesseract.image_to_string(Image.open(path))
        except Exception:
            return f"Image file captured for visual analysis: {path.name}. Local Tesseract binary is not available."

    def gemini_visual_summary(self, path: Path) -> str:
        if genai is None or not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            return ""
        prompt = (
            "You are an expert engineer reviewing data-centre construction drawings, schematics, "
            "equipment nameplates, and technical visuals. Analyze the visual and return: "
            "1) diagram type, 2) all visible components/equipment tags, 3) flows/connections, "
            "4) named standards/technologies, 5) capacities/ratings/dimensions/setpoints, "
            "6) compliance risks, bottlenecks, single points of failure, redundancy concerns, "
            "7) exact transcribed labels/title block/revision notes. Do not summarize away details."
        )
        script = f"""
import os, sys
from pathlib import Path
sys.path.insert(0, {json.dumps(str(BOOT_VENDOR_DIR))})
import google.generativeai as genai
from PIL import Image
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")))
image = Image.open(Path({json.dumps(str(path))}))
response = model.generate_content([{json.dumps(prompt)}, image], request_options={{"timeout": 10}})
print(response.text or "")
"""
        env = os.environ.copy()
        vendor_path = str(BOOT_VENDOR_DIR)
        env["PYTHONPATH"] = vendor_path + os.pathsep + env.get("PYTHONPATH", "")
        env.setdefault("GRPC_VERBOSITY", "ERROR")
        env.setdefault("GLOG_minloglevel", "2")
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=str(BACKEND_DIR),
                env=env,
                text=True,
                capture_output=True,
                timeout=15,
            )
            if result.returncode != 0:
                self.gemini_last_error = (result.stderr or result.stdout or f"exit {result.returncode}")[:240]
                return ""
            self.gemini_last_error = ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.gemini_last_error = "Gemini multimodal request timed out after 15 seconds"
            return ""
        except Exception as exc:
            self.gemini_last_error = str(exc)[:240]
            return ""

    def extract_metadata(self, text: str, file_name: str) -> Dict[str, Any]:
        lower = file_name.lower()
        category = self.document_type_from_name(file_name)
        certifications = self.extract_certifications(text)
        vendor_match = (
            re.search(r'"vendor"\s*:\s*"([^"]+)"', text, re.I)
            or re.search(r"\bVendor[:\s]+([A-Za-z0-9 &.-]+)", text, re.I)
        )
        return {
            "document_category": category,
            "vendor": vendor_match.group(1).strip() if vendor_match else None,
            "revision": (re.search(r"\bRev(?:ision)?[:\s-]+([A-Z0-9.]+)", text, re.I) or [None, "A"])[1],
            "issue_date": (re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text) or [None, date.today().isoformat()])[1],
            "approval_status": "Rejected" if "rejected" in lower or "non-compliance" in text.lower() else "Pending",
            "capacity_kva": self.first_match(text, r"(\d{2,5})\s*kVA"),
            "voltage_v": self.first_match(text, r"(\d{3,4})\s*V"),
            "frequency_hz": self.first_match(text, r"(\d{2})\s*Hz"),
            "redundancy": self.first_match(text, r"\b(2N\+1|2N|N\+2|N\+1|N)\b"),
            "certifications": certifications,
        }

    def document_type_from_name(self, file_name: str) -> str:
        name = file_name.lower()
        suffix_label = {
            ".csv": "CSV",
            ".json": "JSON",
            ".xlsx": "Spreadsheet",
            ".xls": "Spreadsheet",
            ".png": "Drawing/Image",
            ".jpg": "Drawing/Image",
            ".jpeg": "Drawing/Image",
        }.get(Path(file_name).suffix.lower())
        if suffix_label:
            return suffix_label
        rules = [
            ("compliance", "Compliance Standard"), ("spec", "Specification"), ("submittal", "Vendor Submittal"),
            ("drawing", "Shop Drawing"), ("schedule", "Schedule"), ("proc", "Procurement"), ("email", "Email"),
            ("rfi", "RFIs"), ("meeting", "Meeting Minutes"), ("inspection", "Inspection Report"), ("ncr", "NCR"),
            ("change", "Change Order"), ("test", "Test Record"), ("scan", "Scanned Document"),
        ]
        for needle, label in rules:
            if needle in name:
                return label
        return Path(file_name).suffix.upper().strip(".") or "Document"

    def extract_certifications(self, text: str) -> List[str]:
        found = set()
        for match in re.finditer(r"\b(?:UL|CE|CSA|IEC\s?\d+|NEC|ISO\s?\d+)\b", text, flags=re.I):
            window = text[max(0, match.start() - 45):match.end() + 45].lower()
            if any(negation in window for negation in ["without", "missing", "no ", "not ", "absent", "lacks"]):
                continue
            found.add(match.group(0).upper())
        return sorted(found)

    def first_match(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.I)
        return match.group(1) if match else None

    def chunk_text(self, text: str, chunk_size: int = 220, overlap: int = 35) -> List[str]:
        words = re.sub(r"\s+", " ", text).strip().split()
        if not words:
            return []
        chunks, start = [], 0
        while start < len(words):
            end = min(len(words), start + chunk_size)
            chunks.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start = max(0, end - overlap)
        return chunks

    def run_compliance(self, document_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            doc = conn.execute("SELECT * FROM intelligence_documents WHERE id = ?", (document_id,)).fetchone()
            if not doc:
                return []
            standard = conn.execute(
                "SELECT extracted_text FROM intelligence_documents WHERE document_type = 'Compliance Standard' ORDER BY created_at LIMIT 1"
            ).fetchone()
            conn.execute("DELETE FROM compliance_issues WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM rule_evaluations WHERE document_id = ?", (document_id,))
            issues = self.compute_compliance(dict(doc), standard["extracted_text"] if standard else "")
            issues.extend(self.run_deterministic_rules(conn, dict(doc)))
            for issue in issues:
                conn.execute(
                    """
                    INSERT INTO compliance_issues
                    (id, document_id, category, severity, description, evidence, recommendation, reference, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        str(uuid.uuid4()), document_id, issue["category"], issue["severity"], issue["description"],
                        issue["evidence"], issue["recommendation"], issue["reference"],
                    ),
                )
        return issues

    def sync_domain_records(self, conn: sqlite3.Connection, document_id: str, file_name: str, document_type: str, metadata: Dict[str, Any], text: str) -> None:
        equipment_type = self.infer_equipment_type(text, file_name)
        if document_type in {"Compliance Standard", "Specification"}:
            conn.execute(
                "INSERT INTO engineering_standards (id, title, document_id, category, extracted_summary) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), Path(file_name).stem.replace("_", " "), document_id, document_type, text[:1200]),
            )
        if equipment_type:
            equipment_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO equipment_assets (id, name, tag, equipment_type, source_document_id, extracted_data) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    equipment_id,
                    metadata.get("equipment_name") or f"{equipment_type} package",
                    metadata.get("equipment_tag") or self.first_match(text, r"\b(?:TAG|Asset)[:\s-]+([A-Z0-9-]+)") or "",
                    equipment_type,
                    document_id,
                    json.dumps(metadata),
                ),
            )
            if document_type in {"Vendor Submittal", "Procurement", "Shop Drawing", "Scanned Document", "Test Record", "PDF", "Document"} or "vendor" in text.lower():
                conn.execute(
                    "INSERT INTO vendor_submittals (id, vendor, document_id, equipment_id, extracted_data) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), metadata.get("vendor") or "Unspecified", document_id, equipment_id, json.dumps(metadata)),
                )

    def infer_equipment_type(self, text: str, file_name: str) -> str:
        haystack = f"{file_name} {text}".lower()
        if "ups" in haystack:
            return "UPS"
        if "switchgear" in haystack or "busway" in haystack or "panel" in haystack:
            return "switchgear"
        if "chiller" in haystack or "cooling" in haystack or "hvac" in haystack:
            return "cooling"
        if "containment" in haystack:
            return "containment"
        return ""

    def run_deterministic_rules(self, conn: sqlite3.Connection, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        meta = json.loads(doc.get("metadata") or "{}")
        equipment_type = self.infer_equipment_type(doc.get("extracted_text") or "", doc.get("file_name") or "")
        if not equipment_type:
            return []
        requirements = conn.execute(
            "SELECT * FROM engineering_requirements WHERE lower(equipment_type)=lower(?)",
            (equipment_type,),
        ).fetchall()
        issues: List[Dict[str, Any]] = []
        score = 100.0
        for req in requirements:
            status, vendor_value, explanation = self.evaluate_rule(dict(req), meta)
            if status in {"fail", "warning"}:
                score -= {"critical": 40, "major": 20, "minor": 5}.get(req["severity"], 5)
                issues.append(
                    self.issue(
                        "Rule Engine",
                        "high" if req["severity"] == "major" else req["severity"],
                        f"{req['field_name']} failed deterministic {req['operator']} rule.",
                        explanation,
                        "Resolve vendor value or submit approved deviation.",
                        req["reference"],
                    )
                )
            conn.execute(
                """
                INSERT INTO rule_evaluations
                (id, document_id, requirement_id, status, requirement_value, vendor_value, severity, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), doc["id"], req["id"], status, req["value"], str(vendor_value) if vendor_value is not None else None, req["severity"], explanation),
            )
        conn.execute(
            "UPDATE vendor_submittals SET score_percent=?, status=? WHERE document_id=?",
            (max(0, round(score, 2)), "rejected" if score < 60 else "conditional" if score < 90 else "approved", doc["id"]),
        )
        return issues

    def evaluate_rule(self, rule: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[str, Any, str]:
        value = meta.get(rule["field_name"])
        if value in (None, "", []):
            return "not_available", value, f"{rule['field_name']} was not found in extracted metadata."
        operator = rule["operator"]
        expected = rule["value"]
        left_num = self.to_number(value)
        right_num = self.to_number(expected)
        passed = False
        if operator == "equals":
            passed = str(value).strip().lower() == str(expected).strip().lower()
        elif operator == "not_equals":
            passed = str(value).strip().lower() != str(expected).strip().lower()
        elif operator == "greater_equal":
            passed = left_num is not None and right_num is not None and left_num >= right_num
        elif operator == "less_equal":
            passed = left_num is not None and right_num is not None and left_num <= right_num
        elif operator == "contains":
            haystack = " ".join(value) if isinstance(value, list) else str(value)
            passed = str(expected).lower() in haystack.lower()
        elif operator == "not_contains":
            haystack = " ".join(value) if isinstance(value, list) else str(value)
            passed = str(expected).lower() not in haystack.lower()
        return ("pass" if passed else "fail", value, f"{rule['field_name']}={value}; required {operator} {expected}.")

    def to_number(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    def compute_compliance(self, doc: Dict[str, Any], standard_text: str) -> List[Dict[str, Any]]:
        text = doc.get("extracted_text") or ""
        meta = json.loads(doc.get("metadata") or "{}")
        issues: List[Dict[str, Any]] = []
        if not text.strip():
            issues.append(self.issue("Extraction", "critical", "No extractable text was found.", doc["file_name"], "Reprocess with OCR or request a native file.", "Document text"))
        if doc.get("document_type") not in {"Compliance Standard", "Schedule", "Procurement", "Email"}:
            if meta.get("redundancy") and meta["redundancy"].upper() == "N":
                issues.append(self.issue("Electrical", "critical", "Redundancy below data-centre expectation.", f"Detected {meta['redundancy']} redundancy.", "Request N+1 or approved client waiver.", "UPS redundancy"))
            if not meta.get("certifications") and any(token in text.lower() for token in ["ups", "panel", "switchgear", "cable"]):
                issues.append(self.issue("Certification", "high", "Missing certification evidence.", "No UL/CE/IEC/NEC/CSA reference detected.", "Ask vendor to submit certification pack.", "Standards and certifications"))
            if meta.get("capacity_kva") and int(meta["capacity_kva"]) < 500 and "ups" in text.lower():
                issues.append(self.issue("Capacity", "medium", "UPS capacity appears low for critical hall equipment.", f"Detected {meta['capacity_kva']} kVA.", "Validate load schedule and revise submittal if undersized.", "UPS capacity"))
        if "weather" in text.lower() and "delay" in text.lower():
            issues.append(self.issue("Schedule", "medium", "Weather delay mentioned in source document.", "Document references weather-related delay.", "Feed into schedule risk review.", "Delay risk"))
        issues.extend(self.llm_compliance_review(text, standard_text))
        return issues[:12]

    def issue(self, category: str, severity: str, description: str, evidence: str, recommendation: str, reference: str) -> Dict[str, Any]:
        return {"category": category, "severity": severity, "description": description, "evidence": evidence, "recommendation": recommendation, "reference": reference}

    def llm_compliance_review(self, text: str, standard_text: str) -> List[Dict[str, Any]]:
        if self.groq_client is None or not text.strip():
            return []
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a data-centre EPC compliance checker. Return JSON with an issues array only."},
                    {"role": "user", "content": f"STANDARD:\n{standard_text[:2500]}\n\nDOCUMENT:\n{text[:3500]}\nFlag missing certifications, wrong specs, mismatches, and contract risks."},
                ],
                temperature=0.1,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
            return [
                self.issue(
                    item.get("category", "AI Review"),
                    item.get("severity", "medium"),
                    item.get("description", "Potential compliance issue."),
                    item.get("evidence", ""),
                    item.get("recommendation", "Review manually."),
                    item.get("reference", "AI comparison"),
                )
                for item in data.get("issues", [])[:5]
            ]
        except Exception:
            return []

    def rebuild_vector_store(self) -> Dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.content, c.document_id, d.title, c.page_number
                FROM intelligence_chunks c JOIN intelligence_documents d ON d.id = c.document_id
                WHERE length(c.content) > 10
                ORDER BY d.created_at, c.rowid
                """
            ).fetchall()
        metadata = [dict(row) for row in rows]
        (VECTOR_DIR / "chunks.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        if not metadata:
            return {"chunks": 0, "backend": "empty"}
        vectors = self.embed([row["content"] for row in metadata])
        if faiss is not None and np is not None and vectors:
            arr = np.array(vectors, dtype="float32")
            index = faiss.IndexFlatIP(arr.shape[1])
            faiss.normalize_L2(arr)
            index.add(arr)
            faiss.write_index(index, str(VECTOR_DIR / "project.index"))
            return {"chunks": len(metadata), "backend": "faiss"}
        (VECTOR_DIR / "local_vectors.json").write_text(json.dumps(vectors), encoding="utf-8")
        return {"chunks": len(metadata), "backend": "local-hash"}

    def embed(self, texts: List[str]) -> List[List[float]]:
        if SentenceTransformer is not None and not self.embedding_model_failed:
            try:
                if self.embedding_model is None:
                    self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                vectors = self.embedding_model.encode(texts, normalize_embeddings=True)
                return vectors.tolist()
            except Exception as exc:
                self.embedding_model_failed = True
                self.embedding_model_error = str(exc)[:240]
        return [self.hash_embed(text) for text in texts]

    def hash_embed(self, text: str, dim: int = 384) -> List[float]:
        vec = [0.0] * dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[digest % dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session_id = session_id or str(uuid.uuid4())
        with self.connect() as conn:
            chunks = [dict(row) for row in conn.execute(
                "SELECT c.*, d.title, d.file_name FROM intelligence_chunks c JOIN intelligence_documents d ON d.id = c.document_id"
            ).fetchall()]
        ranked = self.rank_chunks(message, chunks)[:6]
        citations = [
            {"document_id": row["document_id"], "document_name": row["title"], "page_number": row["page_number"], "snippet": row["content"][:260]}
            for row in ranked
        ]
        if not ranked:
            answer = "I could not find evidence in the uploaded documents."
        elif self.groq_client is not None:
            context = "\n".join(f"[{i+1}] {row['title']}: {row['content']}" for i, row in enumerate(ranked))
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "Answer as a data-centre project intelligence assistant. Use only the cited context and cite sources like [1]."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {message}"},
                    ],
                    temperature=0.2,
                    max_tokens=700,
                )
                answer = response.choices[0].message.content or "I could not find evidence in the uploaded documents."
            except Exception:
                answer = self.extractive_answer(message, ranked)
        else:
            answer = self.extractive_answer(message, ranked)
        with self.connect() as conn:
            conn.execute("INSERT INTO rag_chat_history (id, session_id, role, message, citations) VALUES (?, ?, 'user', ?, '[]')", (str(uuid.uuid4()), session_id, message))
            conn.execute("INSERT INTO rag_chat_history (id, session_id, role, message, citations) VALUES (?, ?, 'assistant', ?, ?)", (str(uuid.uuid4()), session_id, answer, json.dumps(citations)))
        return {"session_id": session_id, "answer": answer, "citations": citations}

    def rank_chunks(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        qvec = self.embed([query])[0]
        scored = []
        for chunk in chunks:
            cvec = self.hash_embed(chunk["content"])
            score = sum(a * b for a, b in zip(qvec, cvec))
            scored.append((score, chunk))
        return [chunk for score, chunk in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0.02]

    def extractive_answer(self, question: str, rows: List[Dict[str, Any]]) -> str:
        snippets = " ".join(row["content"][:220] for row in rows[:3])
        return f"Based on the indexed project records: {snippets}"

    def process_communications(self, document_id: str, text: str) -> None:
        candidates = re.split(r"\n|\. ", text)
        with self.connect() as conn:
            for sentence in candidates:
                lower = sentence.lower()
                if any(word in lower for word in ["please", "action", "submit", "confirm", "due", "deadline", "rfi"]):
                    due = self.first_match(sentence, r"(20\d{2}-\d{2}-\d{2})") or (date.today() + timedelta(days=7)).isoformat()
                    owner = self.first_match(sentence, r"(?:owner|responsible|from|to)[:\s]+([A-Za-z .@-]+)") or "Project team"
                    similar = "Linked to similar prior RFI" if "same answer" in lower or "similar" in lower else ""
                    conn.execute(
                        "INSERT INTO action_items (id, source_document_id, title, owner, due_date, decision_summary, similar_reference) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), document_id, sentence[:140], owner[:80], due, self.summarize_sentence(sentence), similar),
                    )

    def dashboard(self) -> Dict[str, Any]:
        with self.connect() as conn:
            docs = conn.execute("SELECT COUNT(*) FROM intelligence_documents").fetchone()[0]
            issues = conn.execute("SELECT severity, COUNT(*) c FROM compliance_issues WHERE status='open' GROUP BY severity").fetchall()
            actions = conn.execute("SELECT COUNT(*) FROM action_items WHERE status='open'").fetchone()[0]
            recent = [dict(row) for row in conn.execute(
                "SELECT title, document_type, created_at FROM intelligence_documents ORDER BY created_at DESC LIMIT 8"
            ).fetchall()]
            issue_rows = [dict(row) for row in conn.execute(
                "SELECT category, COUNT(*) value FROM compliance_issues GROUP BY category"
            ).fetchall()]
        schedule = self.schedule_risk()
        procurement = self.procurement()
        issue_count = sum(row["c"] for row in issues)
        critical_count = sum(row["c"] for row in issues if row["severity"] in {"critical", "high"})
        health = max(0, 96 - critical_count * 8 - len([t for t in schedule["tasks"] if t["risk"] == "red"]) * 5)
        return {
            "kpis": {
                "health_score": health,
                "schedule_percent": schedule["completion_percent"],
                "compliance_issues": issue_count,
                "procurement_risks": len([p for p in procurement["orders"] if p["risk"] != "green"]),
                "docs_processed": docs,
                "hours_saved": docs * 3 + issue_count * 2 + actions,
            },
            "risk_over_time": [{"date": (date.today() - timedelta(days=6 - i)).isoformat(), "risk": max(12, 44 - i * 3 + critical_count)} for i in range(7)],
            "compliance_by_category": issue_rows or [{"category": "No issues", "value": 1}],
            "activity": recent,
            "critical_tasks": [t for t in schedule["tasks"] if t["risk"] != "green"][:5],
            "top_procurement_risks": [p for p in procurement["orders"] if p["risk"] != "green"][:5],
        }

    def refresh_notifications(self) -> List[Dict[str, Any]]:
        schedule_tasks = self.schedule_risk()["tasks"]
        procurement_orders = self.procurement()["orders"]
        with self.connect() as conn:
            conn.execute("DELETE FROM smart_notifications")
            for issue in conn.execute(
                """
                SELECT i.*, d.title AS document_title
                FROM compliance_issues i
                JOIN intelligence_documents d ON d.id = i.document_id
                WHERE i.status = 'open' AND i.severity IN ('critical', 'high')
                """
            ).fetchall():
                conn.execute(
                    """
                    INSERT INTO smart_notifications
                    (id, notification_type, severity, title, message, source, related_entity_type, related_entity_id, channels)
                    VALUES (?, 'compliance_failure', ?, ?, ?, 'Spec Compliance Agent', 'compliance_issue', ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        issue["severity"],
                        f"{issue['severity'].title()} compliance issue",
                        f"{issue['document_title']}: {issue['description']}",
                        issue["id"],
                        json.dumps(["dashboard", "email"]),
                    ),
                )
            for task in schedule_tasks:
                if task["risk"] == "red":
                    conn.execute(
                        """
                        INSERT INTO smart_notifications
                        (id, notification_type, severity, title, message, source, related_entity_type, related_entity_id, channels)
                        VALUES (?, 'schedule_delay', 'high', ?, ?, 'Schedule Risk Engine', 'schedule_task', ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            "Critical path schedule risk",
                            f"{task['name']} has {int(task['delay_probability'] * 100)}% delay probability. {task['mitigation']}",
                            task["id"],
                            json.dumps(["dashboard"]),
                        ),
                    )
            for order in procurement_orders:
                if order["risk"] == "red":
                    conn.execute(
                        """
                        INSERT INTO smart_notifications
                        (id, notification_type, severity, title, message, source, related_entity_type, related_entity_id, channels)
                        VALUES (?, 'procurement_issue', 'high', ?, ?, 'Procurement Agent', 'purchase_order', ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            "Procurement risk on critical material",
                            f"{order['material']} from {order['supplier']} is {order['status']} with ETA {order['eta']}.",
                            order["id"],
                            json.dumps(["dashboard", "email"]),
                        ),
                    )
            for action in conn.execute(
                "SELECT * FROM action_items WHERE status='open' AND due_date <= ?",
                (date.today().isoformat(),),
            ).fetchall():
                conn.execute(
                    """
                    INSERT INTO smart_notifications
                    (id, notification_type, severity, title, message, source, related_entity_type, related_entity_id, channels)
                    VALUES (?, 'pending_approval', 'medium', ?, ?, 'Communication Intelligence Agent', 'action_item', ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        "Overdue action or approval",
                        f"{action['title']} is due {action['due_date']} and remains open.",
                        action["id"],
                        json.dumps(["dashboard", "email"]),
                    ),
                )
            return [dict(row) for row in conn.execute("SELECT * FROM smart_notifications ORDER BY created_at DESC").fetchall()]

    def notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        self.refresh_notifications()
        query = "SELECT * FROM smart_notifications"
        if unread_only:
            query += " WHERE is_read = 0"
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["channels"] = json.loads(item.get("channels") or "[]")
            item["is_read"] = bool(item["is_read"])
            out.append(item)
        return out

    def dispatch_notifications(self) -> Dict[str, Any]:
        notifications = self.notifications(unread_only=True)
        results = []
        for item in notifications:
            channels = item.get("channels") or []
            if "email" in channels:
                results.append(self.send_email_notification(item))
            if "sms" in channels or item["severity"] in {"critical", "high"}:
                results.append(self.send_twilio_message(item, whatsapp=False))
            if "whatsapp" in channels:
                results.append(self.send_twilio_message(item, whatsapp=True))
        return {"attempted": len(results), "results": results}

    def send_email_notification(self, item: Dict[str, Any]) -> Dict[str, Any]:
        recipient = os.getenv("ALERT_RECIPIENT_EMAIL") or os.getenv("SMTP_TO") or "project.manager@example.com"
        status = "skipped"
        detail = "SMTP not configured"
        if os.getenv("SMTP_HOST") and (os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")):
            try:
                msg = EmailMessage()
                msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")
                msg["To"] = recipient
                msg["Subject"] = f"[Orion DC] {item['title']}"
                msg.set_content(item["message"])
                with smtplib.SMTP(os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "587")), timeout=10) as server:
                    if os.getenv("SMTP_USE_TLS", "true").lower() != "false":
                        server.starttls()
                    server.login(os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD", ""))
                    server.send_message(msg)
                status = "sent"
                detail = "SMTP message sent"
            except Exception as exc:
                status = "failed"
                detail = str(exc)[:240]
        return self.record_delivery(item["id"], "email", recipient, status, detail)

    def send_twilio_message(self, item: Dict[str, Any], whatsapp: bool = False) -> Dict[str, Any]:
        recipient = os.getenv("ALERT_RECIPIENT_PHONE") or ""
        channel = "whatsapp" if whatsapp else "sms"
        status = "skipped"
        detail = "Twilio not configured"
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_FROM" if whatsapp else "TWILIO_FROM_NUMBER")
        if sid and token and from_number and recipient:
            try:
                data = urlencode({
                    "From": from_number if not whatsapp else f"whatsapp:{from_number.replace('whatsapp:', '')}",
                    "To": recipient if not whatsapp else f"whatsapp:{recipient.replace('whatsapp:', '')}",
                    "Body": f"{item['title']}: {item['message']}"[:1500],
                }).encode("utf-8")
                request = Request(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                    data=data,
                    headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()},
                )
                with urlopen(request, timeout=10) as response:
                    detail = response.read().decode("utf-8")[:240]
                status = "sent"
            except Exception as exc:
                status = "failed"
                detail = str(exc)[:240]
        return self.record_delivery(item["id"], channel, recipient or "not_configured", status, detail)

    def record_delivery(self, notification_id: str, channel: str, recipient: str, status: str, detail: str) -> Dict[str, Any]:
        row = {"id": str(uuid.uuid4()), "notification_id": notification_id, "channel": channel, "recipient": recipient, "status": status, "provider_response": detail}
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO notification_deliveries (id, notification_id, channel, recipient, status, provider_response) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], notification_id, channel, recipient, status, detail),
            )
        return row

    def system_status(self) -> Dict[str, Any]:
        vector_chunks = []
        chunks_file = VECTOR_DIR / "chunks.json"
        if chunks_file.exists():
            vector_chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        with self.connect() as conn:
            counts = {
                "documents": conn.execute("SELECT COUNT(*) FROM intelligence_documents").fetchone()[0],
                "chunks": conn.execute("SELECT COUNT(*) FROM intelligence_chunks").fetchone()[0],
                "compliance_issues": conn.execute("SELECT COUNT(*) FROM compliance_issues").fetchone()[0],
                "action_items": conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0],
                "notifications": conn.execute("SELECT COUNT(*) FROM smart_notifications").fetchone()[0],
                "reports": conn.execute("SELECT COUNT(*) FROM report_history").fetchone()[0],
                "equipment_assets": conn.execute("SELECT COUNT(*) FROM equipment_assets").fetchone()[0],
                "vendor_submittals": conn.execute("SELECT COUNT(*) FROM vendor_submittals").fetchone()[0],
                "requirements": conn.execute("SELECT COUNT(*) FROM engineering_requirements").fetchone()[0],
                "standards": conn.execute("SELECT COUNT(*) FROM engineering_standards").fetchone()[0],
                "rule_evaluations": conn.execute("SELECT COUNT(*) FROM rule_evaluations").fetchone()[0],
                "appointments": conn.execute("SELECT COUNT(*) FROM engineer_appointments").fetchone()[0],
                "weather_snapshots": conn.execute("SELECT COUNT(*) FROM weather_snapshots").fetchone()[0],
                "notification_deliveries": conn.execute("SELECT COUNT(*) FROM notification_deliveries").fetchone()[0],
            }
        return {
            "database": str(DB_PATH),
            "vector_store": str(VECTOR_DIR),
            "vector_chunks": len(vector_chunks),
            "faiss_index_exists": (VECTOR_DIR / "project.index").exists(),
            "sample_documents_path": str(SAMPLE_DIR),
            "counts": counts,
            "llm": {
                "groq_generation": bool(self.groq_client),
                "gemini_multimodal": genai is not None and bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
                "gemini_error": self.gemini_last_error,
                "openweather": bool(os.getenv("OPENWEATHER_API_KEY")),
                "twilio": bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")),
                "smtp_email": bool(os.getenv("SMTP_HOST")),
                "sentence_transformers": SentenceTransformer is not None and not self.embedding_model_failed,
                "sentence_transformers_installed": SentenceTransformer is not None,
                "embedding_backend": "sentence-transformers" if self.embedding_model is not None and not self.embedding_model_failed else "local-hash",
                "embedding_error": self.embedding_model_error,
                "faiss": faiss is not None,
            },
        }

    def integrations(self) -> Dict[str, Any]:
        with self.connect() as conn:
            self.refresh_integration_status(conn)
            rows = [dict(row) for row in conn.execute("SELECT * FROM integration_status ORDER BY name").fetchall()]
        return {"integrations": rows, "env_path": str(BACKEND_DIR / ".env")}

    def appointments(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM engineer_appointments ORDER BY scheduled_for, engineer_name").fetchall()]

    def create_appointment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "engineer_name": payload.get("engineer_name") or "Project Engineer",
            "engineer_email": payload.get("engineer_email") or "engineer@example.com",
            "discipline": payload.get("discipline") or "General",
            "appointment_type": payload.get("appointment_type") or "Review",
            "related_entity_type": payload.get("related_entity_type") or "",
            "related_entity_id": payload.get("related_entity_id") or "",
            "scheduled_for": payload.get("scheduled_for") or (date.today() + timedelta(days=1)).isoformat(),
            "notes": payload.get("notes") or "",
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO engineer_appointments
                (id, engineer_name, engineer_email, discipline, appointment_type, related_entity_type, related_entity_id, scheduled_for, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(row.values()),
            )
        return row

    def sustainability(self) -> Dict[str, Any]:
        with self.connect() as conn:
            counts = {
                "chat": conn.execute("SELECT COUNT(*) FROM rag_chat_history WHERE role='user'").fetchone()[0],
                "reports": conn.execute("SELECT COUNT(*) FROM report_history").fetchone()[0],
                "documents": conn.execute("SELECT COUNT(*) FROM intelligence_documents").fetchone()[0],
            }
        ai_requests = counts["chat"] + counts["reports"] + counts["documents"]
        estimated_kwh = round(ai_requests * 0.012, 3)
        estimated_water_liters = round(estimated_kwh * 1.8, 2)
        avoided_rework_hours = round(counts["documents"] * 1.4 + counts["reports"] * 2.0, 1)
        guidance = [
            "Ask consolidated questions instead of repeated small prompts.",
            "Use document search and citations before sending broad LLM queries.",
            "Batch weekly report generation rather than repeatedly rendering reports.",
            "Prefer deterministic rule checks for compliance decisions; use LLMs for explanation and evidence synthesis.",
        ]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sustainability_metrics (id, metric_date, ai_requests, estimated_kwh, estimated_water_liters, avoided_rework_hours, guidance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), date.today().isoformat(), ai_requests, estimated_kwh, estimated_water_liters, avoided_rework_hours, json.dumps(guidance)),
            )
        return {
            "ai_requests": ai_requests,
            "estimated_kwh": estimated_kwh,
            "estimated_water_liters": estimated_water_liters,
            "avoided_rework_hours": avoided_rework_hours,
            "net_message": "Use AI deliberately: the platform saves rework, but unnecessary prompts consume electricity and water in data centres.",
            "guidance": guidance,
            "method": "Local awareness estimate: requests x 0.012 kWh, kWh x 1.8 L water. Configure site-specific factors if available.",
        }

    def import_gmail_messages(self, query: str = "from:vendor@example.com OR subject:RFI", max_results: int = 10) -> Dict[str, Any]:
        gmail_dir = ETHACK_SOURCE / "gmail_reader"
        imported = 0
        detail = "Gmail API libraries or OAuth credentials not available; imported sample_emails.csv instead."
        try:
            if str(gmail_dir) not in os.sys.path:
                os.sys.path.insert(0, str(gmail_dir))
            import gmail_reader as gmail_module  # type: ignore

            service = gmail_module.get_service()
            resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
            for ref in resp.get("messages", []):
                msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
                headers = msg["payload"]["headers"]
                sender = gmail_module._header(headers, "From")
                subject = gmail_module._header(headers, "Subject")
                msg_date = gmail_module._header(headers, "Date")
                body = gmail_module._extract_plain_text(msg["payload"])
                text = f"from: {sender}; subject: {subject}; date: {msg_date}; body: {body}"
                path = DOCUMENT_DIR / f"gmail_{ref['id']}.txt"
                path.write_text(text, encoding="utf-8")
                if not self.document_exists(path.name):
                    self.ingest_path(path, title=subject or path.name)
                    imported += 1
            detail = "Imported via ethack Gmail reader adapter."
        except Exception:
            sample = SAMPLE_DIR / "sample_emails.csv"
            if sample.exists() and not self.document_exists("gmail_sample_import.csv"):
                fallback = DOCUMENT_DIR / "gmail_sample_import.csv"
                shutil.copy2(sample, fallback)
                self.ingest_path(fallback, title="Gmail sample import")
                imported = 1
        return {"imported": imported, "detail": detail}

    def documents(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT d.*, (SELECT COUNT(*) FROM compliance_issues i WHERE i.document_id=d.id) issue_count
                FROM intelligence_documents d ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM intelligence_documents WHERE id=?", (document_id,)).fetchone()
            if not row:
                return None
            doc = dict(row)
            doc["chunks"] = [dict(r) for r in conn.execute("SELECT * FROM intelligence_chunks WHERE document_id=?", (document_id,)).fetchall()]
            doc["issues"] = [dict(r) for r in conn.execute("SELECT * FROM compliance_issues WHERE document_id=?", (document_id,)).fetchall()]
            doc["metadata"] = json.loads(doc.get("metadata") or "{}")
            doc["versions"] = [{"version": doc["revision"], "created_at": doc["created_at"], "status": doc["status"]}]
            return doc

    def compliance(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT i.*, d.title document_title FROM compliance_issues i JOIN intelligence_documents d ON d.id=i.document_id ORDER BY i.created_at DESC"
            ).fetchall()]

    def rule_evaluations(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(
                """
                SELECT r.*, d.title document_title, q.field_name, q.operator
                FROM rule_evaluations r
                LEFT JOIN intelligence_documents d ON d.id=r.document_id
                LEFT JOIN engineering_requirements q ON q.id=r.requirement_id
                ORDER BY r.created_at DESC
                """
            ).fetchall()]

    def equipment(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*, d.title document_title
                FROM equipment_assets e
                LEFT JOIN intelligence_documents d ON d.id=e.source_document_id
                ORDER BY e.created_at DESC
                """
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["extracted_data"] = json.loads(item.get("extracted_data") or "{}")
            out.append(item)
        return out

    def vendors(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT v.*, e.name equipment_name, d.title document_title
                FROM vendor_submittals v
                LEFT JOIN equipment_assets e ON e.id=v.equipment_id
                LEFT JOIN intelligence_documents d ON d.id=v.document_id
                ORDER BY v.created_at DESC
                """
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["extracted_data"] = json.loads(item.get("extracted_data") or "{}")
            out.append(item)
        return out

    def requirements(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM engineering_requirements ORDER BY equipment_type, field_name").fetchall()]

    def standards(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM engineering_standards ORDER BY created_at DESC").fetchall()]

    def schedule_risk(self) -> Dict[str, Any]:
        schedules = self.read_csv_dicts(SAMPLE_DIR / "sample_schedule.csv")
        if len(schedules) < 4:
            schedules = self.default_schedule_rows() + schedules
        workforce = self.read_csv_dicts(SAMPLE_DIR / "sample_workforce.csv")
        weather = self.read_csv_dicts(SAMPLE_DIR / "sample_weather.csv")
        procurement = self.procurement()["orders"]
        procurement_risk = {self.normalize(o["material"]): o for o in procurement}
        workforce_risk = max((1 - (float(row.get("available") or 0) / max(float(row.get("planned") or 1), 1)) for row in workforce), default=0)
        weather_risk = max((float(row.get("risk_score") or 0) for row in weather), default=0)
        tasks = []
        for idx, row in enumerate(schedules):
            name = row.get("task") or row.get("activity_name") or row.get("Activity") or row.get("name") or f"Task {idx+1}"
            percent = float(row.get("percent_complete") or row.get("progress") or (35 + idx * 8) % 100)
            dependency = row.get("dependencies") or row.get("predecessor") or ""
            days_to_finish = max(1, int(float(row.get("duration") or row.get("remaining_duration") or 10) * (100 - percent) / 100))
            linked_risk = max((0.25 if key in self.normalize(name) else 0 for key in procurement_risk), default=0)
            probability = min(0.95, 0.12 + (0.25 if percent < 50 else 0) + linked_risk + (0.15 if dependency else 0) + workforce_risk * 0.25 + weather_risk)
            risk = "red" if probability >= 0.62 else "yellow" if probability >= 0.35 else "green"
            tasks.append({
                "id": row.get("id") or row.get("activity_id") or f"T-{idx+1:03d}",
                "name": name,
                "start": row.get("start") or row.get("start_date") or (date.today() + timedelta(days=idx * 5)).isoformat(),
                "finish": row.get("finish") or row.get("finish_date") or (date.today() + timedelta(days=idx * 5 + days_to_finish)).isoformat(),
                "percent_complete": percent,
                "delay_probability": round(probability, 2),
                "risk": risk,
                "dependency": dependency,
                "workforce_risk": round(workforce_risk, 2),
                "weather_risk": round(weather_risk, 2),
                "mitigation": self.mitigation(risk, name),
            })
        if not tasks:
            tasks = self.default_tasks()
        completion = round(sum(t["percent_complete"] for t in tasks) / max(len(tasks), 1), 1)
        return {
            "completion_percent": completion,
            "tasks": tasks,
            "signals": {
                "workforce": workforce,
                "weather": weather,
                "procurement_risk_items": [order for order in procurement if order["risk"] != "green"],
            },
        }

    def procurement(self) -> Dict[str, Any]:
        rows = self.read_csv_dicts(SAMPLE_DIR / "sample_procurement.csv")
        if len(rows) < 4:
            rows = self.default_procurement_rows() + rows
        orders = []
        for idx, row in enumerate(rows):
            eta = row.get("eta") or row.get("expected_delivery_date") or (date.today() + timedelta(days=idx * 8 - 5)).isoformat()
            status = row.get("status") or ["Ordered", "In Transit", "Delivered", "Installed"][idx % 4]
            eta_date = self.parse_date(eta)
            days_late = (date.today() - eta_date).days if eta_date and status not in {"Delivered", "Installed"} else 0
            weather = self.weather_for_order(row.get("po_number") or row.get("po") or f"PO-{1000+idx}", 17.385 + idx * 0.02, 78.486 + idx * 0.02, row.get("supplier") or row.get("vendor") or "Unspecified")
            risk_score = (0.65 if days_late > 3 else 0.34 if status in {"Ordered", "In Transit"} and eta_date and eta_date <= date.today() + timedelta(days=5) else 0.12) + weather["risk_score"] * 0.25
            risk = "red" if risk_score >= 0.62 else "yellow" if risk_score >= 0.35 else "green"
            orders.append({
                "id": row.get("po_number") or row.get("po") or f"PO-{1000+idx}",
                "material": row.get("material") or row.get("description") or row.get("item") or f"Material {idx+1}",
                "supplier": row.get("supplier") or row.get("vendor") or "Unspecified",
                "status": status,
                "eta": eta,
                "risk": risk,
                "risk_score": round(risk_score, 2),
                "lat": 17.385 + idx * 0.02,
                "lng": 78.486 + idx * 0.02,
                "weather": weather,
                "score": max(55, 94 - max(days_late, 0) * 5 - idx * 2),
            })
        if not orders:
            orders = self.default_orders()
        suppliers: Dict[str, List[float]] = {}
        for order in orders:
            suppliers.setdefault(order["supplier"], []).append(order["score"])
        scorecards = [{"supplier": name, "score": round(sum(scores) / len(scores), 1), "orders": len(scores)} for name, scores in suppliers.items()]
        return {"orders": orders, "scorecards": scorecards, "weather_summary": self.weather_summary(orders)}

    def weather_for_order(self, order_id: str, lat: float, lng: float, location: str) -> Dict[str, Any]:
        today_prefix = date.today().isoformat()
        api_key = os.getenv("OPENWEATHER_API_KEY")
        with self.connect() as conn:
            cached = conn.execute(
                "SELECT * FROM weather_snapshots WHERE order_id=? AND created_at LIKE ? ORDER BY created_at DESC LIMIT 1",
                (order_id, f"{today_prefix}%"),
            ).fetchone()
            if cached and not (api_key and cached["source"] != "openweather"):
                return {
                    "condition": cached["condition"],
                    "temperature_c": cached["temperature_c"],
                    "wind_speed": cached["wind_speed"],
                    "risk_score": cached["risk_score"],
                    "source": cached["source"],
                }
        snapshot = {"condition": "Demo weather signal", "temperature_c": 32.0, "wind_speed": 4.2, "risk_score": 0.12, "source": "fallback"}
        if api_key:
            try:
                params = urlencode({"lat": lat, "lon": lng, "appid": api_key, "units": "metric"})
                request = Request(f"https://api.openweathermap.org/data/2.5/weather?{params}", headers={"User-Agent": "dc-project-intelligence/1.0"})
                with urlopen(request, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                condition = (data.get("weather") or [{}])[0].get("description") or "Unknown"
                temp = float(data.get("main", {}).get("temp") or 0)
                wind = float(data.get("wind", {}).get("speed") or 0)
                condition_l = condition.lower()
                risk_score = min(0.65, (0.25 if any(x in condition_l for x in ["storm", "rain", "thunder", "snow"]) else 0.08) + (0.15 if wind > 9 else 0) + (0.1 if temp > 38 else 0))
                snapshot = {"condition": condition, "temperature_c": temp, "wind_speed": wind, "risk_score": round(risk_score, 2), "source": "openweather"}
            except Exception as exc:
                snapshot["condition"] = f"OpenWeather unavailable: {str(exc)[:80]}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO weather_snapshots
                (id, order_id, location, lat, lng, condition, temperature_c, wind_speed, risk_score, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), order_id, location, lat, lng, snapshot["condition"], snapshot["temperature_c"], snapshot["wind_speed"], snapshot["risk_score"], snapshot["source"]),
            )
        return snapshot

    def weather_summary(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        risky = [order for order in orders if order.get("weather", {}).get("risk_score", 0) >= 0.2]
        return {
            "source": "openweather" if any(order.get("weather", {}).get("source") == "openweather" for order in orders) else "fallback",
            "weather_risk_orders": len(risky),
            "max_weather_risk": max((order.get("weather", {}).get("risk_score", 0) for order in orders), default=0),
            "insight": "Weather is affecting procurement risk." if risky else "No material weather risk detected for current shipments.",
        }

    def communications(self) -> Dict[str, Any]:
        with self.connect() as conn:
            return {"action_items": [dict(row) for row in conn.execute("SELECT * FROM action_items ORDER BY due_date LIMIT 40").fetchall()]}

    def generate_report(self, report_type: str = "weekly", days: int = 7) -> Dict[str, Any]:
        report_id = str(uuid.uuid4())
        period_end = date.today()
        period_start = period_end - timedelta(days=days)
        dashboard = self.dashboard()
        report_qmd = REPORT_DIR / f"{report_id}.qmd"
        pdf_path = REPORT_DIR / f"{report_id}.pdf"
        html_path = REPORT_DIR / f"{report_id}.html"
        risk_svg = REPORT_DIR / f"{report_id}_risk.svg"
        compliance_svg = REPORT_DIR / f"{report_id}_compliance.svg"
        risk_svg.write_text(self.risk_svg(dashboard["risk_over_time"]), encoding="utf-8")
        compliance_svg.write_text(self.compliance_svg(dashboard["compliance_by_category"]), encoding="utf-8")
        report_qmd.write_text(
            f"""---
title: "Data Centre Project Intelligence {report_type.title()} Report"
format:
  html:
    toc: true
  pdf: default
---

## Executive Metrics

Health Score: {dashboard['kpis']['health_score']}

Schedule Completion: {dashboard['kpis']['schedule_percent']}%

Compliance Issues: {dashboard['kpis']['compliance_issues']}

Procurement Risks: {dashboard['kpis']['procurement_risks']}

## Analytics

![Risk over time]({risk_svg.name})

![Compliance by category]({compliance_svg.name})

## Critical Schedule Risks

{self.markdown_table(dashboard['critical_tasks'], ['id', 'name', 'delay_probability', 'risk', 'mitigation'])}

## Procurement Risks

{self.markdown_table(dashboard['top_procurement_risks'], ['id', 'material', 'supplier', 'eta', 'risk'])}
""",
            encoding="utf-8",
        )
        status = "generated"
        output = html_path
        try:
            subprocess.run(["quarto", "render", str(report_qmd), "--to", "pdf", "--output", pdf_path.name], cwd=str(REPORT_DIR), check=True, timeout=90)
            output = pdf_path
        except Exception:
            try:
                self.generate_pdf_fallback(pdf_path, report_type, dashboard)
                output = pdf_path
                status = "generated-pdf-fallback"
            except Exception:
                report_qmd.with_suffix(".html").write_text(report_qmd.read_text(encoding="utf-8").replace("\n", "<br/>"), encoding="utf-8")
                status = "generated-html"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO report_history (id, report_type, period_start, period_end, file_path, status, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (report_id, report_type, period_start.isoformat(), period_end.isoformat(), str(output), status, "Weekly report covering the last 7 days."),
            )
        return {"id": report_id, "status": status, "file_path": str(output), "download_url": f"/api/v1/intelligence/reports/{report_id}/download"}

    def generate_pdf_fallback(self, output_path: Path, report_type: str, dashboard: Dict[str, Any]) -> None:
        if fitz is None:
            raise RuntimeError("PyMuPDF is not available for PDF fallback")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        y = 48

        def write(text: str, size: int = 10, gap: int = 16) -> None:
            nonlocal y, page
            if y > 790:
                page = doc.new_page(width=595, height=842)
                y = 48
            page.insert_text((42, y), text[:115], fontsize=size, fontname="helv", color=(0.07, 0.09, 0.13))
            y += gap

        write(f"Data Centre Project Intelligence {report_type.title()} Report", 16, 24)
        write(f"Period generated: {date.today().isoformat()}", 10, 22)
        write("Executive Metrics", 13, 20)
        for key, value in dashboard["kpis"].items():
            write(f"- {key.replace('_', ' ').title()}: {value}")
        y += 8
        write("Critical Schedule Risks", 13, 20)
        for row in dashboard["critical_tasks"] or [{"name": "No active schedule risks"}]:
            write(f"- {row.get('id', '')} {row.get('name', '')}: {row.get('risk', '')} {row.get('delay_probability', '')}")
            if row.get("mitigation"):
                write(f"  Mitigation: {row.get('mitigation')}", 9)
        y += 8
        write("Procurement Risks", 13, 20)
        for row in dashboard["top_procurement_risks"] or [{"material": "No active procurement risks"}]:
            write(f"- {row.get('id', '')} {row.get('material', '')}: {row.get('supplier', '')} ETA {row.get('eta', '')} {row.get('risk', '')}")
        y += 8
        write("Compliance Categories", 13, 20)
        for row in dashboard["compliance_by_category"]:
            write(f"- {row.get('category')}: {row.get('value')} issue(s)")
        doc.save(str(output_path))
        doc.close()

    def reports(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM report_history ORDER BY created_at DESC").fetchall()]

    def read_csv_dicts(self, path: Path) -> List[Dict[str, str]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            return list(csv.DictReader(handle))

    def parse_date(self, value: str) -> Optional[date]:
        try:
            return datetime.fromisoformat(str(value)[:10]).date()
        except Exception:
            return None

    def default_tasks(self) -> List[Dict[str, Any]]:
        names = ["UPS Hall 3 installation", "Chiller delivery and placement", "Busway energization", "Containment inspection"]
        return [
            {"id": f"T-{i+1:03d}", "name": name, "start": (date.today() + timedelta(days=i * 5)).isoformat(), "finish": (date.today() + timedelta(days=i * 5 + 12)).isoformat(), "percent_complete": 45 + i * 10, "delay_probability": 0.28 + i * 0.12, "risk": ["green", "yellow", "red", "yellow"][i], "mitigation": self.mitigation(["green", "yellow", "red", "yellow"][i], name)}
            for i, name in enumerate(names)
        ]

    def default_schedule_rows(self) -> List[Dict[str, Any]]:
        base = date.today()
        return [
            {"activity_id": "CP-101", "activity_name": "UPS Hall 3 installation", "start_date": base.isoformat(), "finish_date": (base + timedelta(days=14)).isoformat(), "percent_complete": "38", "dependencies": "PO-1001", "duration": "14"},
            {"activity_id": "CP-102", "activity_name": "Chiller delivery and placement", "start_date": (base + timedelta(days=3)).isoformat(), "finish_date": (base + timedelta(days=21)).isoformat(), "percent_complete": "22", "dependencies": "PO-1002", "duration": "18"},
            {"activity_id": "CP-103", "activity_name": "Busway energization", "start_date": (base + timedelta(days=10)).isoformat(), "finish_date": (base + timedelta(days=26)).isoformat(), "percent_complete": "48", "dependencies": "CP-101", "duration": "16"},
            {"activity_id": "CP-104", "activity_name": "Containment inspection", "start_date": (base + timedelta(days=15)).isoformat(), "finish_date": (base + timedelta(days=23)).isoformat(), "percent_complete": "64", "dependencies": "CP-103", "duration": "8"},
        ]

    def default_orders(self) -> List[Dict[str, Any]]:
        return [
            {"id": "PO-1001", "material": "UPS modules", "supplier": "VoltGrid", "status": "In Transit", "eta": (date.today() + timedelta(days=2)).isoformat(), "risk": "yellow", "lat": 17.42, "lng": 78.48, "score": 82},
            {"id": "PO-1002", "material": "Chillers", "supplier": "ThermaCore", "status": "Ordered", "eta": (date.today() - timedelta(days=4)).isoformat(), "risk": "red", "lat": 17.39, "lng": 78.50, "score": 68},
            {"id": "PO-1003", "material": "Fiber trunks", "supplier": "FiberSpan", "status": "Delivered", "eta": date.today().isoformat(), "risk": "green", "lat": 17.37, "lng": 78.46, "score": 93},
        ]

    def default_procurement_rows(self) -> List[Dict[str, Any]]:
        return [
            {"po_number": "PO-1001", "material": "UPS modules", "supplier": "VoltGrid", "status": "In Transit", "eta": (date.today() + timedelta(days=2)).isoformat()},
            {"po_number": "PO-1002", "material": "Chillers", "supplier": "ThermaCore", "status": "Ordered", "eta": (date.today() - timedelta(days=4)).isoformat()},
            {"po_number": "PO-1003", "material": "Fiber trunks", "supplier": "FiberSpan", "status": "Delivered", "eta": date.today().isoformat()},
            {"po_number": "PO-1004", "material": "Busway sections", "supplier": "PowerRail", "status": "In Transit", "eta": (date.today() + timedelta(days=5)).isoformat()},
        ]

    def risk_svg(self, rows: List[Dict[str, Any]]) -> str:
        points = []
        width, height = 760, 260
        for idx, row in enumerate(rows or []):
            x = 45 + idx * ((width - 80) / max(len(rows) - 1, 1))
            y = height - 40 - (float(row.get("risk") or 0) / 100) * (height - 80)
            points.append(f"{x:.1f},{y:.1f}")
        polyline = " ".join(points)
        labels = "".join(f"<text x='{45 + idx * ((width - 80) / max(len(rows) - 1, 1)):.1f}' y='240' font-size='10' text-anchor='middle' fill='#667085'>{row.get('date','')[-5:]}</text>" for idx, row in enumerate(rows or []))
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'><rect width='100%' height='100%' fill='#ffffff'/><text x='24' y='28' font-size='18' font-family='Arial' fill='#111827'>Risk over time</text><line x1='40' y1='220' x2='730' y2='220' stroke='#d9dee7'/><line x1='40' y1='40' x2='40' y2='220' stroke='#d9dee7'/><polyline fill='none' stroke='#e35d1b' stroke-width='4' points='{polyline}'/>{labels}</svg>"

    def compliance_svg(self, rows: List[Dict[str, Any]]) -> str:
        total = sum(float(row.get("value") or 0) for row in rows) or 1
        colors = ["#e35d1b", "#0f8a5f", "#2563eb", "#c0352b", "#b7791f", "#667085"]
        x = 40
        segments = []
        labels = []
        for idx, row in enumerate(rows):
            width = 520 * (float(row.get("value") or 0) / total)
            segments.append(f"<rect x='{x:.1f}' y='92' width='{width:.1f}' height='42' fill='{colors[idx % len(colors)]}'/>")
            labels.append(f"<text x='40' y='{165 + idx * 20}' font-size='12' font-family='Arial' fill='#111827'>{row.get('category')}: {row.get('value')}</text>")
            x += width
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='760' height='260' viewBox='0 0 760 260'><rect width='100%' height='100%' fill='#ffffff'/><text x='24' y='28' font-size='18' font-family='Arial' fill='#111827'>Compliance by category</text>{''.join(segments)}{''.join(labels)}</svg>"

    def mitigation(self, risk: str, name: str) -> str:
        if risk == "red":
            return f"Expedite procurement and resequence successor work around {name}."
        if risk == "yellow":
            return f"Confirm vendor ETA and add recovery float for {name}."
        return "Monitor through normal weekly controls."

    def normalize(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def markdown_table(self, rows: List[Dict[str, Any]], fields: List[str]) -> str:
        if not rows:
            return "No records."
        header = "| " + " | ".join(fields) + " |\n|" + "|".join(["---"] * len(fields)) + "|\n"
        body = "\n".join("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |" for row in rows)
        return header + body

    def summarize_sentence(self, sentence: str) -> str:
        return sentence.strip()[:220]

    def mime_type(self, path: Path) -> str:
        return {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }.get(path.suffix.lower(), "text/plain")

    def preview_payload(self, document_id: str) -> Optional[Dict[str, Any]]:
        doc = self.document(document_id)
        if not doc:
            return None
        path = Path(doc["stored_path"])
        payload: Dict[str, Any] = {"mime_type": doc["mime_type"], "file_name": doc["file_name"]}
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            payload["data_url"] = f"{doc['mime_type']};base64,{base64.b64encode(path.read_bytes()).decode()}"
        else:
            payload["text"] = (doc.get("extracted_text") or "")[:12000]
        return payload


hub = IntelligenceHub()
