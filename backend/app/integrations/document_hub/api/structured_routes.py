from fastapi import APIRouter
from backend.services.structured_service import StructuredService

router = APIRouter(prefix="/structured")
service = StructuredService()

@router.get("/records")
def list_records() -> list:
    return service.list_structured_records()
