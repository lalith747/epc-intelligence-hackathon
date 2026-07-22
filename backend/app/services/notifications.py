"""
Smart Notification Engine.

Scans a project's current risks, procurement, recommendations, and health
score for conditions worth alerting a stakeholder about, and creates
Notification rows (deduplicated so repeated scans don't spam). Critical/high
notifications are also emailed to the project owner if SMTP is configured.
"""
from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

from sqlalchemy import select

from app.core.logging import get_logger
from app.models.database import (
    Inventory,
    Material,
    Notification,
    Project,
    ProjectHealth,
    PurchaseOrder,
    Recommendation,
    Risk,
    User,
)
from app.services.database import AsyncSessionLocal
from app.services.email import send_notification_email

logger = get_logger(__name__)

DEDUP_WINDOW_HOURS = 24


async def _already_notified(session, project_id: str, notification_type: str, related_entity_id: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(hours=DEDUP_WINDOW_HOURS)
    result = await session.execute(
        select(Notification.id).where(
            Notification.project_id == project_id,
            Notification.notification_type == notification_type,
            Notification.related_entity_id == related_entity_id,
            Notification.created_at >= cutoff,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


def _create(session, project_id: str, notification_type: str, severity: str, title: str,
            message: str, source: str, related_entity_type: str, related_entity_id: str) -> Notification:
    notification = Notification(
        id=str(uuid4()),
        project_id=project_id,
        notification_type=notification_type,
        severity=severity,
        title=title,
        message=message,
        source=source,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        channels=["dashboard"],
        is_read=False,
    )
    session.add(notification)
    return notification


async def scan_project(project_id: str) -> List[Notification]:
    """Rule-based scan for notify-worthy conditions. Returns newly created notifications."""
    created: List[Notification] = []

    async with AsyncSessionLocal() as session:
        project_result = await session.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            return created

        risks_result = await session.execute(
            select(Risk).where(
                Risk.project_id == project_id,
                Risk.status == "open",
                Risk.severity.in_(["critical", "high"]),
            )
        )
        for risk in risks_result.scalars().all():
            if await _already_notified(session, project_id, "risk_alert", risk.id):
                continue
            created.append(_create(
                session, project_id, "risk_alert", risk.severity,
                title=f"{risk.severity.title()} risk: {risk.title}",
                message=risk.explanation or risk.description or f"Risk {risk.risk_code} requires attention.",
                source="risk_agent",
                related_entity_type="risk",
                related_entity_id=risk.id,
            ))

        po_result = await session.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.project_id == project_id,
                PurchaseOrder.status == "delayed",
            )
        )
        for po in po_result.scalars().all():
            if await _already_notified(session, project_id, "procurement_issue", po.id):
                continue
            created.append(_create(
                session, project_id, "procurement_issue", "high",
                title=f"Delayed delivery: {po.po_number}",
                message=f"Purchase order {po.po_number} is delayed"
                        + (f" (expected {po.expected_delivery_date})." if po.expected_delivery_date else "."),
                source="procurement_agent",
                related_entity_type="purchase_order",
                related_entity_id=po.id,
            ))

        rec_result = await session.execute(
            select(Recommendation).where(
                Recommendation.project_id == project_id,
                Recommendation.status == "pending",
                Recommendation.priority == "high",
            )
        )
        for rec in rec_result.scalars().all():
            if await _already_notified(session, project_id, "pending_approval", rec.id):
                continue
            created.append(_create(
                session, project_id, "pending_approval", "medium",
                title=f"Recommendation awaiting approval: {rec.title}",
                message=rec.description,
                source="recommendation_agent",
                related_entity_type="recommendation",
                related_entity_id=rec.id,
            ))

        inventory_result = await session.execute(
            select(Inventory, Material)
            .join(Material, Inventory.material_id == Material.id)
            .where(Inventory.project_id == project_id)
        )
        for inventory, material in inventory_result.all():
            available = float(inventory.quantity_available or 0)
            reorder_point = float(inventory.reorder_point) if inventory.reorder_point is not None else None
            if reorder_point is None or available > reorder_point:
                continue
            if await _already_notified(session, project_id, "procurement_issue", inventory.id):
                continue
            shortfall = max(reorder_point * 1.25 - available, 0)
            lead = f" Lead time is {material.lead_time} days." if material.lead_time else ""
            created.append(_create(
                session, project_id, "procurement_issue", "high",
                title=f"Low stock: {material.name}",
                message=f"Only {available:g} {material.unit or 'units'} available (reorder point "
                        f"{reorder_point:g}). Order ~{shortfall:g} {material.unit or 'units'} now.{lead}",
                source="inventory_monitor",
                related_entity_type="purchase_order",
                related_entity_id=inventory.id,
            ))

        health_result = await session.execute(
            select(ProjectHealth)
            .where(ProjectHealth.project_id == project_id)
            .order_by(ProjectHealth.metric_date.desc())
            .limit(1)
        )
        health = health_result.scalar_one_or_none()
        if health and health.overall_health_score is not None and float(health.overall_health_score) < 50:
            dedup_key = f"health-{health.metric_date}"
            if not await _already_notified(session, project_id, "schedule_delay", dedup_key):
                score = round(float(health.overall_health_score))
                created.append(_create(
                    session, project_id, "schedule_delay", "critical",
                    title=f"Project health critical: {score}/100",
                    message=f"{project.name} overall health has dropped to {score}/100. Immediate review recommended.",
                    source="executive_agent",
                    related_entity_type="project",
                    related_entity_id=dedup_key,
                ))

        if created:
            await session.commit()
            for n in created:
                await session.refresh(n)

    if created:
        await _dispatch_email(project_id, created)

    return created


async def _dispatch_email(project_id: str, notifications: List[Notification]) -> None:
    """Best-effort email delivery for critical/high notifications to the project owner."""
    urgent = [n for n in notifications if n.severity in ("critical", "high")]
    if not urgent:
        return

    async with AsyncSessionLocal() as session:
        project_result = await session.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project or not project.owner_id:
            return

        user_result = await session.execute(select(User).where(User.id == project.owner_id))
        owner = user_result.scalar_one_or_none()
        if not owner:
            return

        sent = await send_notification_email(owner.email, project.name, urgent)
        if sent:
            ids = [n.id for n in urgent]
            await session.execute(
                Notification.__table__.update().where(Notification.id.in_(ids)).values(email_sent=True)
            )
            await session.commit()
