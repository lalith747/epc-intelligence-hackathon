from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str
    file_name: str
    document_type: Optional[str] = None
    vendor: Optional[str] = None
    project: Optional[str] = None
    revision: Optional[str] = None
    issue_date: Optional[str] = None
    approval_status: Optional[str] = None
    equipment_ids: Optional[str] = None
    drawing_numbers: Optional[str] = None
    spec_references: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    document_type: Optional[str] = None
    vendor: Optional[str] = None
    revision: Optional[str] = None
    date: Optional[str] = None
    equipment: Optional[str] = None
    approval_status: Optional[str] = None


class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[dict]] = None
    conversation_id: Optional[str] = None


class ComplianceRequest(BaseModel):
    specification_document_id: int
    vendor_document_id: int
    shop_drawing_id: Optional[int] = None


class Deviation(BaseModel):
    severity: str = "warning"
    description: str = ""
    evidence: str = ""
    recommendation: str = ""
    document_ref: str = "Unknown"
    page_number: int = 1
    spec_clause: str = "N/A"


class ComplianceReport(BaseModel):
    overall_score: str = "Fail"
    summary: str = ""
    deviations: List[Deviation] = Field(default_factory=list)
    report_pdf_url: Optional[str] = None
