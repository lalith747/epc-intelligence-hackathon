"""
Supplier management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Supplier
from app.models.schemas import SupplierCreate, SupplierUpdate, SupplierResponse
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new supplier"""
    # Check if supplier code already exists
    result = await db.execute(select(Supplier).where(Supplier.supplier_code == supplier_data.supplier_code))
    existing_supplier = result.scalar_one_or_none()
    
    if existing_supplier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier code already exists"
        )
    
    new_supplier = Supplier(**supplier_data.dict())
    
    db.add(new_supplier)
    await db.commit()
    await db.refresh(new_supplier)
    
    logger.info(f"Supplier created: {supplier_data.supplier_code}")
    return new_supplier


@router.get("/", response_model=List[SupplierResponse])
async def list_suppliers(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all suppliers"""
    query = select(Supplier)
    
    if category:
        query = query.where(Supplier.category == category)
    
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(Supplier.rating.desc())
    )
    suppliers = result.scalars().all()
    
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get supplier by ID"""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    supplier_update: SupplierUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update supplier"""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    update_data = supplier_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    await db.commit()
    await db.refresh(supplier)
    
    logger.info(f"Supplier updated: {supplier_id}")
    return supplier
