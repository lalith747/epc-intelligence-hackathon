"""
Smart Notification System endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.services.database import get_db
from app.models.database import Notification
from app.models.schemas import NotificationResponse, NotificationCountResponse
from app.services.notifications import scan_project
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/project/{project_id}", response_model=List[NotificationResponse])
async def list_notifications(
    project_id: str,
    unread_only: bool = False,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List notifications for a project, most recent first"""
    query = select(Notification).where(Notification.project_id == project_id)
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712

    result = await db.execute(query.order_by(Notification.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.get("/project/{project_id}/count", response_model=NotificationCountResponse)
async def get_unread_count(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unread and critical-unread notification counts for a project"""
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.project_id == project_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    critical_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.project_id == project_id,
            Notification.is_read == False,  # noqa: E712
            Notification.severity == "critical",
        )
    )
    return NotificationCountResponse(
        unread=unread_result.scalar() or 0,
        critical=critical_result.scalar() or 0,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a single notification as read"""
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post("/project/{project_id}/read-all")
async def mark_all_read(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all of a project's notifications as read"""
    await db.execute(
        update(Notification)
        .where(Notification.project_id == project_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.post("/project/{project_id}/scan", response_model=List[NotificationResponse])
async def scan_now(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Run the notification engine against current project data right now"""
    try:
        created = await scan_project(project_id)
        return created
    except Exception as e:
        logger.error(f"Notification scan error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Notification scan failed: {str(e)}"
        )
