from pathlib import Path
from backend.services.connector_service import ConnectorService
from backend.services.document_service import DocumentService


class OrchestratorService:
    def __init__(self) -> None:
        self.connector_service = ConnectorService()
        self.document_service = DocumentService()

    def ingest_path(self, file_path: str, source_type: str = "procurement") -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)
        rows = self.connector_service.ingest_csv(file_path, source_type)
        return {
            "source_type": source_type,
            "file_path": str(path),
            "records_ingested": len(rows),
            "status": "processed",
        }
