"""
Project management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.services.database import get_db
from app.models.database import Project, ProjectHealth, Schedule, PurchaseOrder
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectSummary
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    # Check if project code already exists
    result = await db.execute(select(Project).where(Project.code == project_data.code))
    existing_project = result.scalar_one_or_none()
    
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project code already exists"
        )
    
    # Create new project
    new_project = Project(
        **project_data.dict(),
        owner_id=current_user["user_id"]
    )
    
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    
    logger.info(f"Project created: {project_data.code}")
    return new_project


@router.get("/", response_model=List[ProjectSummary])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all projects with their latest health metrics"""
    result = await db.execute(
        select(Project)
        .offset(skip)
        .limit(limit)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    summaries = []
    for project in projects:
        health_result = await db.execute(
            select(ProjectHealth)
            .where(ProjectHealth.project_id == project.id)
            .order_by(ProjectHealth.metric_date.desc())
            .limit(1)
        )
        health = health_result.scalar_one_or_none()

        total_schedules = await db.scalar(
            select(func.count(Schedule.id)).where(Schedule.project_id == project.id)
        )
        total_purchase_orders = await db.scalar(
            select(func.count(PurchaseOrder.id)).where(PurchaseOrder.project_id == project.id)
        )

        summaries.append(ProjectSummary(
            id=project.id,
            name=project.name,
            code=project.code,
            status=project.status,
            progress_percentage=project.progress_percentage,
            location=project.location,
            start_date=project.start_date,
            planned_end_date=project.planned_end_date,
            overall_health_score=health.overall_health_score if health else None,
            schedule_health_score=health.schedule_health_score if health else None,
            procurement_health_score=health.procurement_health_score if health else None,
            risk_score=health.risk_score if health else None,
            open_risks_count=health.open_risks_count if health else 0,
            critical_risks_count=health.critical_risks_count if health else 0,
            total_schedules=total_schedules or 0,
            total_purchase_orders=total_purchase_orders or 0,
        ))

    return summaries


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update project fields
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Project updated: {project_id}")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete project"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    await db.delete(project)
    await db.commit()
    
    logger.info(f"Project deleted: {project_id}")
