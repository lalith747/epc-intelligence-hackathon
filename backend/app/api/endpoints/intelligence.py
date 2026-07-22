from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.intelligence_hub import hub

router = APIRouter()


class ChatPayload(BaseModel):
    message: str
    session_id: Optional[str] = None


class ReportPayload(BaseModel):
    report_type: str = "weekly"
    days: int = 7


class IntegrationPayload(BaseModel):
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None
    ALERT_RECIPIENT_PHONE: Optional[str] = None
    ALERT_RECIPIENT_EMAIL: Optional[str] = None


class AppointmentPayload(BaseModel):
    engineer_name: Optional[str] = None
    engineer_email: Optional[str] = None
    discipline: Optional[str] = None
    appointment_type: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    scheduled_for: Optional[str] = None
    notes: Optional[str] = None


@router.post("/initialize")
async def initialize_hub():
    hub.initialize()
    return {"status": "ready"}


@router.get("/dashboard")
async def dashboard():
    hub.initialize()
    return hub.dashboard()


@router.get("/documents")
async def documents():
    hub.initialize()
    return hub.documents()


@router.get("/documents/{document_id}")
async def document(document_id: str):
    hub.initialize()
    doc = hub.document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/preview")
async def document_preview(document_id: str):
    hub.initialize()
    payload = hub.preview_payload(document_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Document not found")
    return payload


@router.get("/documents/{document_id}/download")
async def document_download(document_id: str):
    hub.initialize()
    doc = hub.document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=doc["file_name"], media_type=doc["mime_type"])


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), title: Optional[str] = Form(None)):
    hub.initialize()
    return hub.ingest_upload(file, title)


@router.post("/documents/preview-upload")
async def preview_upload(file: UploadFile = File(...)):
    hub.initialize()
    return hub.preview_upload(file)


@router.post("/documents/{document_id}/recheck")
async def recheck_document(document_id: str):
    hub.initialize()
    issues = hub.run_compliance(document_id)
    hub.rebuild_vector_store()
    hub.refresh_notifications()
    return {"document_id": document_id, "issues": issues, "count": len(issues)}


@router.get("/compliance")
async def compliance():
    hub.initialize()
    return hub.compliance()


@router.get("/compliance/rule-evaluations")
async def rule_evaluations():
    hub.initialize()
    return hub.rule_evaluations()


@router.get("/equipment")
async def equipment():
    hub.initialize()
    return hub.equipment()


@router.get("/vendors")
async def vendors():
    hub.initialize()
    return hub.vendors()


@router.get("/requirements")
async def requirements():
    hub.initialize()
    return hub.requirements()


@router.get("/standards")
async def standards():
    hub.initialize()
    return hub.standards()


@router.get("/schedule-risk")
async def schedule_risk():
    hub.initialize()
    return hub.schedule_risk()


@router.get("/procurement")
async def procurement():
    hub.initialize()
    return hub.procurement()


@router.get("/communications")
async def communications():
    hub.initialize()
    return hub.communications()


@router.get("/notifications")
async def notifications(unread_only: bool = False):
    hub.initialize()
    return hub.notifications(unread_only=unread_only)


@router.post("/notifications/dispatch")
async def dispatch_notifications():
    hub.initialize()
    return hub.dispatch_notifications()


@router.get("/system-status")
async def system_status():
    hub.initialize()
    return hub.system_status()


@router.get("/integrations")
async def integrations():
    hub.initialize()
    return hub.integrations()


@router.post("/integrations/configure")
async def configure_integrations(payload: IntegrationPayload):
    hub.initialize()
    return hub.configure_integrations(payload.model_dump(exclude_none=True))


@router.post("/communications/import-gmail")
async def import_gmail(query: str = "from:vendor@example.com OR subject:RFI", max_results: int = 10):
    hub.initialize()
    return hub.import_gmail_messages(query=query, max_results=max_results)


@router.get("/appointments")
async def appointments():
    hub.initialize()
    return hub.appointments()


@router.post("/appointments")
async def create_appointment(payload: AppointmentPayload):
    hub.initialize()
    return hub.create_appointment(payload.model_dump(exclude_none=True))


@router.get("/sustainability")
async def sustainability():
    hub.initialize()
    return hub.sustainability()


@router.post("/chat")
async def chat(payload: ChatPayload):
    hub.initialize()
    return hub.chat(payload.message, payload.session_id)


@router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    hub.initialize()
    with hub.connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM rag_chat_history WHERE session_id=? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        ]


@router.post("/reports/generate")
async def generate_report(payload: ReportPayload):
    hub.initialize()
    return hub.generate_report(payload.report_type, payload.days)


@router.get("/reports")
async def reports():
    hub.initialize()
    return hub.reports()


@router.get("/reports/{report_id}/download")
async def report_download(report_id: str):
    hub.initialize()
    with hub.connect() as conn:
        row = conn.execute("SELECT * FROM report_history WHERE id=?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html"
    return FileResponse(path, filename=path.name, media_type=media_type)
