"""
Report management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Report
from app.models.schemas import ReportCreate, ReportResponse
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: ReportCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new report"""
    new_report = Report(
        **report_data.dict(),
        generated_by_agent="manual"
    )
    
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    logger.info(f"Report created: {report_data.report_name}")
    return new_report


@router.get("/project/{project_id}", response_model=List[ReportResponse])
async def get_project_reports(
    project_id: str,
    report_type: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reports for a project"""
    query = select(Report).where(Report.project_id == project_id)
    
    if report_type:
        query = query.where(Report.report_type == report_type)
    
    result = await db.execute(
        query.order_by(Report.report_date.desc())
    )
    reports = result.scalars().all()
    
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get report by ID"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return report
