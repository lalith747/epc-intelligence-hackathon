"""
Schedule management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Schedule, Activity
from app.models.schemas import ScheduleCreate, ScheduleResponse, ActivityResponse
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new schedule"""
    new_schedule = Schedule(**schedule_data.dict())
    
    db.add(new_schedule)
    await db.commit()
    await db.refresh(new_schedule)
    
    logger.info(f"Schedule created for project: {schedule_data.project_id}")
    return new_schedule


@router.get("/project/{project_id}", response_model=List[ScheduleResponse])
async def get_project_schedules(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all schedules for a project"""
    result = await db.execute(
        select(Schedule)
        .where(Schedule.project_id == project_id)
        .order_by(Schedule.created_at.desc())
    )
    schedules = result.scalars().all()
    
    return schedules


@router.get("/{schedule_id}/activities", response_model=List[ActivityResponse])
async def get_schedule_activities(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all activities for a schedule, ordered by start date"""
    result = await db.execute(
        select(Activity)
        .where(Activity.schedule_id == schedule_id)
        .order_by(Activity.start_date.asc().nullslast(), Activity.early_start.asc().nullslast())
    )
    return result.scalars().all()


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get schedule by ID"""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    return schedule
