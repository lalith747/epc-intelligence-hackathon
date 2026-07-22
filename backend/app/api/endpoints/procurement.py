"""
Procurement management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import PurchaseOrder, Inventory, Material
from app.models.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    InventoryStatusResponse,
)
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/inventory/{project_id}", response_model=List[InventoryStatusResponse])
async def get_inventory_status(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Material stock position with reorder guidance for a project"""
    result = await db.execute(
        select(Inventory, Material)
        .join(Material, Inventory.material_id == Material.id)
        .where(Inventory.project_id == project_id)
    )

    statuses = []
    for inventory, material in result.all():
        available = float(inventory.quantity_available or 0)
        reorder_point = float(inventory.reorder_point) if inventory.reorder_point is not None else None
        minimum = float(inventory.minimum_stock_level) if inventory.minimum_stock_level is not None else None

        # Order enough to get back above the reorder point with a 25% buffer,
        # or at least back to minimum stock - whichever is larger.
        reorder_quantity = 0.0
        if reorder_point is not None and available <= reorder_point:
            reorder_quantity = max(reorder_point * 1.25 - available, 0)
        if minimum is not None and available < minimum:
            reorder_quantity = max(reorder_quantity, minimum - available)

        if minimum is not None and available < minimum:
            stock_status = "critical"
        elif reorder_point is not None and available <= reorder_point:
            stock_status = "reorder"
        else:
            stock_status = "ok"

        statuses.append(InventoryStatusResponse(
            inventory_id=inventory.id,
            material_code=material.material_code,
            material_name=material.name,
            category=material.category,
            unit=material.unit,
            unit_cost=float(material.unit_cost) if material.unit_cost is not None else None,
            lead_time_days=material.lead_time,
            warehouse_location=inventory.warehouse_location,
            quantity_on_hand=float(inventory.quantity_on_hand or 0),
            quantity_reserved=float(inventory.quantity_reserved or 0),
            quantity_available=available,
            minimum_stock_level=minimum,
            reorder_point=reorder_point,
            reorder_quantity=round(reorder_quantity, 2),
            stock_status=stock_status,
        ))

    # Most urgent first
    order = {"critical": 0, "reorder": 1, "ok": 2}
    statuses.sort(key=lambda s: order.get(s.stock_status, 3))
    return statuses


@router.post("/", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_data: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new purchase order"""
    # Check if PO number already exists
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == po_data.po_number))
    existing_po = result.scalar_one_or_none()
    
    if existing_po:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase order number already exists"
        )
    
    new_po = PurchaseOrder(**po_data.dict())
    
    db.add(new_po)
    await db.commit()
    await db.refresh(new_po)
    
    logger.info(f"Purchase order created: {po_data.po_number}")
    return new_po


@router.get("/project/{project_id}", response_model=List[PurchaseOrderResponse])
async def get_project_purchase_orders(
    project_id: str,
    status: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all purchase orders for a project"""
    query = select(PurchaseOrder).where(PurchaseOrder.project_id == project_id)
    
    if status:
        query = query.where(PurchaseOrder.status == status)
    
    result = await db.execute(
        query.order_by(PurchaseOrder.created_at.desc())
    )
    purchase_orders = result.scalars().all()
    
    return purchase_orders


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get purchase order by ID"""
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    return po


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: str,
    po_update: PurchaseOrderUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update purchase order"""
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    update_data = po_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(po, field, value)
    
    await db.commit()
    await db.refresh(po)
    
    logger.info(f"Purchase order updated: {po_id}")
    return po
