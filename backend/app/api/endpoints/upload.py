"""
File upload endpoints for data ingestion
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import get_current_user
from app.core.logging import get_logger
from app.services.file_processor import FileProcessor
from app.services.tasks import process_file_upload
from app.core.config import get_settings
from pathlib import Path
import uuid
import shutil

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload and process file for data ingestion"""
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"File uploaded: {file.filename} -> {unique_filename}")
        
        # Process file in background
        task = process_file_upload.delay(str(file_path), project_id, file_extension)
        
        return {
            "status": "uploaded",
            "filename": file.filename,
            "file_path": str(file_path),
            "task_id": task.id,
            "message": "File uploaded successfully. Processing started in background."
        }
    
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        # Clean up file if upload failed
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get status of background file processing task"""
    from app.services.celery_app import celery_app
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
            "error": str(task.info) if task.failed() else None
        }
    
    except Exception as e:
        logger.error(f"Task status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.post("/process-sync")
async def process_file_sync(
    file: UploadFile = File(...),
    project_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Process file synchronously (for smaller files)"""
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not allowed"
        )
    
    # Create upload directory
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    try:
        file_content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Process file
        processor = FileProcessor()
        result = await processor.process_file(str(file_path), project_id, file_extension)
        
        # Clean up file
        if file_path.exists():
            file_path.unlink()
        
        return result
    
    except Exception as e:
        logger.error(f"Synchronous file processing error: {e}", exc_info=True)
        
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File processing failed: {str(e)}"
        )
