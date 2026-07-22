"""
Recommendation management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Recommendation
from app.models.schemas import RecommendationCreate, RecommendationUpdate, RecommendationResponse
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
async def create_recommendation(
    recommendation_data: RecommendationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new recommendation"""
    new_recommendation = Recommendation(
        **recommendation_data.dict(),
        created_by_agent="manual"
    )
    
    db.add(new_recommendation)
    await db.commit()
    await db.refresh(new_recommendation)
    
    logger.info(f"Recommendation created: {recommendation_data.recommendation_code}")
    return new_recommendation


@router.get("/project/{project_id}", response_model=List[RecommendationResponse])
async def get_project_recommendations(
    project_id: str,
    recommendation_type: str = None,
    status: str = None,
    priority: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all recommendations for a project"""
    query = select(Recommendation).where(Recommendation.project_id == project_id)
    
    if recommendation_type:
        query = query.where(Recommendation.recommendation_type == recommendation_type)
    if status:
        query = query.where(Recommendation.status == status)
    if priority:
        query = query.where(Recommendation.priority == priority)
    
    result = await db.execute(
        query.order_by(Recommendation.created_at.desc())
    )
    recommendations = result.scalars().all()
    
    return recommendations


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recommendation by ID"""
    result = await db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
    recommendation = result.scalar_one_or_none()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    return recommendation


@router.put("/{recommendation_id}", response_model=RecommendationResponse)
async def update_recommendation(
    recommendation_id: str,
    recommendation_update: RecommendationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update recommendation status"""
    result = await db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
    recommendation = result.scalar_one_or_none()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    update_data = recommendation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recommendation, field, value)
    
    await db.commit()
    await db.refresh(recommendation)
    
    logger.info(f"Recommendation updated: {recommendation_id}")
    return recommendation
