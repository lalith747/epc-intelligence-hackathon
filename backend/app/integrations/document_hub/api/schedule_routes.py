from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule")
service = ScheduleService()
STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/import")
def import_schedule(file: UploadFile = File(...)) -> dict:
    try:
        destination = STORAGE_DIR / (file.filename or "schedule.csv")
        with destination.open("wb") as handle:
            handle.write(file.file.read())
        rows = service.ingest_schedule(str(destination))
        return {"status": "processed", "records": len(rows)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
