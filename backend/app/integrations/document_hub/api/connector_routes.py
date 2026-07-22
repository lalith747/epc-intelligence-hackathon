from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/connectors")
service = OrchestratorService()
STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/ingest")
def ingest(file: UploadFile = File(...), source_type: str = Form("procurement")) -> dict:
    try:
        destination = STORAGE_DIR / (file.filename or "imported.csv")
        with destination.open("wb") as handle:
            handle.write(file.file.read())
        return service.ingest_path(str(destination), source_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
