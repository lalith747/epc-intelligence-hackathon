import sqlite3
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.database.init_db import DB_PATH
from backend.schemas.models import DocumentCreate, SearchRequest, ChatRequest, ComplianceRequest, ComplianceReport
from backend.services.document_service import DocumentService
from backend.services.rag_service import RAGService
from backend.services.compliance_service import ComplianceService
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api")
service = DocumentService()
rag_service = RAGService()
compliance_service = ComplianceService()
audit_service = AuditService()
REPORTS_DIR = Path(__file__).resolve().parents[1] / "storage" / "reports"


@router.get("/documents")
def list_documents() -> List[dict]:
    return service.list_documents()


@router.get("/documents/{document_id}")
def get_document(document_id: int) -> dict:
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/download")
def download_document(document_id: int):
    file_path = service.get_file_path(document_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not available for this document")
    return FileResponse(str(file_path), filename=file_path.name)


@router.post("/upload")
def upload_document(file: UploadFile = File(...), title: str = Form(...)) -> dict:
    try:
        return service.upload_document(file, title)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict:
    return service.delete_document(document_id)


@router.get("/metadata")
def metadata() -> dict:
    return service.get_metadata()


@router.get("/dashboard")
def dashboard() -> dict:
    return service.get_dashboard()


@router.post("/search")
def search(request: SearchRequest) -> dict:
    audit_service.log("search", request.query or "(filter only)")
    return service.search_documents(request)


@router.post("/chat")
def chat(request: ChatRequest) -> dict:
    audit_service.log("ai_query", request.prompt)
    return rag_service.answer(request)


@router.post("/compliance", response_model=ComplianceReport)
async def check_compliance(request: ComplianceRequest, background_tasks: BackgroundTasks):
    audit_service.log(
        "compliance_run",
        f"spec={request.specification_document_id} vendor={request.vendor_document_id}",
    )
    return compliance_service.run(request, background_tasks=background_tasks)


@router.get("/compliance/reports")
def list_compliance_reports() -> List[dict]:
    return compliance_service.list_reports()


@router.get("/compliance/reports/{report_id}/download")
def download_compliance_report(report_id: str):
    file_path = REPORTS_DIR / f"{report_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(str(file_path), filename=file_path.name)


@router.get("/audit-logs")
def list_audit_logs() -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, action, document, user, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
