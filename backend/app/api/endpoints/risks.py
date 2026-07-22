"""
Risk management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Risk
from app.models.schemas import RiskCreate, RiskUpdate, RiskResponse
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=RiskResponse, status_code=status.HTTP_201_CREATED)
async def create_risk(
    risk_data: RiskCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new risk"""
    # Calculate risk score
    risk_score = risk_data.probability * risk_data.impact / 100
    
    # Determine severity
    if risk_score >= 70:
        severity = "critical"
    elif risk_score >= 50:
        severity = "high"
    elif risk_score >= 30:
        severity = "medium"
    else:
        severity = "low"
    
    new_risk = Risk(
        **risk_data.dict(),
        risk_score=risk_score,
        severity=severity
    )
    
    db.add(new_risk)
    await db.commit()
    await db.refresh(new_risk)
    
    logger.info(f"Risk created: {risk_data.risk_code}")
    return new_risk


@router.get("/project/{project_id}", response_model=List[RiskResponse])
async def get_project_risks(
    project_id: str,
    category: str = None,
    severity: str = None,
    status: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all risks for a project"""
    query = select(Risk).where(Risk.project_id == project_id)
    
    if category:
        query = query.where(Risk.category == category)
    if severity:
        query = query.where(Risk.severity == severity)
    if status:
        query = query.where(Risk.status == status)
    
    result = await db.execute(
        query.order_by(Risk.risk_score.desc())
    )
    risks = result.scalars().all()
    
    return risks


@router.get("/{risk_id}", response_model=RiskResponse)
async def get_risk(
    risk_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get risk by ID"""
    result = await db.execute(select(Risk).where(Risk.id == risk_id))
    risk = result.scalar_one_or_none()
    
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found"
        )
    
    return risk


@router.put("/{risk_id}", response_model=RiskResponse)
async def update_risk(
    risk_id: str,
    risk_update: RiskUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update risk"""
    result = await db.execute(select(Risk).where(Risk.id == risk_id))
    risk = result.scalar_one_or_none()
    
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found"
        )
    
    update_data = risk_update.dict(exclude_unset=True)
    
    # Recalculate risk score if probability or impact changed
    if 'probability' in update_data or 'impact' in update_data:
        probability = update_data.get('probability', risk.probability)
        impact = update_data.get('impact', risk.impact)
        risk_score = probability * impact / 100
        update_data['risk_score'] = risk_score
        
        if risk_score >= 70:
            update_data['severity'] = "critical"
        elif risk_score >= 50:
            update_data['severity'] = "high"
        elif risk_score >= 30:
            update_data['severity'] = "medium"
        else:
            update_data['severity'] = "low"
    
    for field, value in update_data.items():
        setattr(risk, field, value)
    
    await db.commit()
    await db.refresh(risk)
    
    logger.info(f"Risk updated: {risk_id}")
    return risk
