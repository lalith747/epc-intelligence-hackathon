"""
Analytics endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.services.database import get_db
from app.models.database import Project, Risk, Recommendation, ProjectHealth
from app.models.schemas import DashboardMetrics, TrendData, ChartData
from app.core.security import get_current_user
from app.core.logging import get_logger
from datetime import date, timedelta

router = APIRouter()
logger = get_logger(__name__)


@router.get("/dashboard/{project_id}", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard metrics for a project"""
    # Get latest health metrics
    health_result = await db.execute(
        select(ProjectHealth)
        .where(ProjectHealth.project_id == project_id)
        .order_by(ProjectHealth.metric_date.desc())
        .limit(1)
    )
    health = health_result.scalar_one_or_none()
    
    # Count risks
    open_risks_result = await db.execute(
        select(func.count(Risk.id))
        .where(Risk.project_id == project_id)
        .where(Risk.status == 'open')
    )
    open_risks = open_risks_result.scalar() or 0
    
    critical_risks_result = await db.execute(
        select(func.count(Risk.id))
        .where(Risk.project_id == project_id)
        .where(Risk.status == 'open')
        .where(Risk.severity == 'critical')
    )
    critical_risks = critical_risks_result.scalar() or 0
    
    # Count active recommendations
    active_recommendations_result = await db.execute(
        select(func.count(Recommendation.id))
        .where(Recommendation.project_id == project_id)
        .where(Recommendation.status == 'pending')
    )
    active_recommendations = active_recommendations_result.scalar() or 0
    
    return DashboardMetrics(
        project_health=health.overall_health_score if health else 0,
        schedule_health=health.schedule_health_score if health else 0,
        procurement_health=health.procurement_health_score if health else 0,
        risk_score=health.risk_score if health else 0,
        supplier_health=health.supplier_health_score if health else 0,
        completion_percentage=health.completion_percentage if health else 0,
        open_risks=open_risks,
        critical_risks=critical_risks,
        active_recommendations=active_recommendations
    )


@router.get("/trend/{project_id}/{metric_type}")
async def get_metric_trend(
    project_id: str,
    metric_type: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get metric trend over time"""
    start_date = date.today() - timedelta(days=days)
    
    result = await db.execute(
        select(ProjectHealth)
        .where(ProjectHealth.project_id == project_id)
        .where(ProjectHealth.metric_date >= start_date)
        .order_by(ProjectHealth.metric_date.asc())
    )
    health_records = result.scalars().all()
    
    trend_data = []
    for record in health_records:
        value = getattr(record, f"{metric_type}_score", None)
        if value is not None:
            trend_data.append({
                "date": record.metric_date.isoformat(),
                "value": float(value)
            })
    
    return {"data": trend_data}


@router.get("/risk-trend/{project_id}")
async def get_risk_trend(
    project_id: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get risk trend over time"""
    start_date = date.today() - timedelta(days=days)
    
    result = await db.execute(
        select(ProjectHealth)
        .where(ProjectHealth.project_id == project_id)
        .where(ProjectHealth.metric_date >= start_date)
        .order_by(ProjectHealth.metric_date.asc())
    )
    health_records = result.scalars().all()
    
    trend_data = []
    for record in health_records:
        trend_data.append({
            "date": record.metric_date.isoformat(),
            "risk_score": float(record.risk_score) if record.risk_score else 0,
            "open_risks": record.open_risks_count or 0,
            "critical_risks": record.critical_risks_count or 0
        })
    
    return {"data": trend_data}


@router.get("/schedule-progress/{project_id}")
async def get_schedule_progress(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get schedule progress data"""
    result = await db.execute(
        select(ProjectHealth)
        .where(ProjectHealth.project_id == project_id)
        .order_by(ProjectHealth.metric_date.desc())
        .limit(30)
    )
    health_records = result.scalars().all()
    
    progress_data = []
    for record in reversed(list(health_records)):
        progress_data.append({
            "date": record.metric_date.isoformat(),
            "completion": float(record.completion_percentage) if record.completion_percentage else 0,
            "on_time_percentage": float(record.on_time_activities_percentage) if record.on_time_activities_percentage else 0
        })
    
    return {"data": progress_data}
