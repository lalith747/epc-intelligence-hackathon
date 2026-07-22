"""
Procurement Intelligence Agent - Monitors suppliers, purchase orders, and predicts material shortages
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.agents.base_agent import BaseAgent
from app.models.database import PurchaseOrder, Supplier, PurchaseOrderItem, Material, Inventory
from app.core.logging import get_logger
from app.services.database import AsyncSessionLocal
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class ProcurementAnalysis(BaseModel):
    """Procurement analysis output model"""
    procurement_health_score: float = Field(description="Overall procurement health score (0-100)")
    supplier_health_score: float = Field(description="Average supplier health score (0-100)")
    material_shortage_risks: list = Field(description="Materials at risk of shortage")
    supplier_delays_predicted: list = Field(description="Suppliers predicted to have delays")
    on_time_delivery_rate: float = Field(description="Overall on-time delivery rate")
    explanation: str = Field(description="Explanation of the analysis")


class ProcurementAgent(BaseAgent):
    """Procurement Intelligence Agent"""
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, project_id: str, execution_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute procurement analysis"""
        start_time = datetime.utcnow()
        
        try:
            async with AsyncSessionLocal() as session:
                # Get purchase orders
                po_result = await session.execute(
                    select(PurchaseOrder).where(PurchaseOrder.project_id == project_id)
                )
                purchase_orders = po_result.scalars().all()
                
                # Get suppliers
                supplier_ids = [po.supplier_id for po in purchase_orders]
                suppliers_result = await session.execute(
                    select(Supplier).where(Supplier.id.in_(supplier_ids))
                )
                suppliers = suppliers_result.scalars().all()
                
                # Get PO items
                po_ids = [po.id for po in purchase_orders]
                items_result = await session.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id.in_(po_ids))
                )
                items = items_result.scalars().all()
                
                # Get inventory
                inventory_result = await session.execute(
                    select(Inventory).where(Inventory.project_id == project_id)
                )
                inventory = inventory_result.scalars().all()
                
                # Perform analysis
                analysis = await self.analyze_procurement(
                    purchase_orders, suppliers, items, inventory
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                await self.log_execution(
                    agent_name="procurement_agent",
                    project_id=project_id,
                    execution_type=execution_type,
                    input_data=input_data,
                    output_data=analysis,
                    execution_time_ms=int(execution_time),
                    status="success"
                )
                
                return analysis
        
        except Exception as e:
            self.logger.error(f"Procurement Agent execution error: {e}", exc_info=True)
            await self.log_execution(
                agent_name="procurement_agent",
                project_id=project_id,
                execution_type=execution_type,
                input_data=input_data,
                output_data={"error": str(e)},
                execution_time_ms=0,
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def analyze_procurement(
        self,
        purchase_orders: list,
        suppliers: list,
        items: list,
        inventory: list
    ) -> Dict[str, Any]:
        """Perform comprehensive procurement analysis"""
        
        # Convert to pandas for analysis
        po_df = pd.DataFrame([{
            'id': str(po.id),
            'po_number': po.po_number,
            'supplier_id': str(po.supplier_id),
            'issue_date': po.issue_date,
            'expected_delivery_date': po.expected_delivery_date,
            'actual_delivery_date': po.actual_delivery_date,
            'status': po.status,
            'priority': po.priority,
            'total_amount': float(po.total_amount) if po.total_amount else 0
        } for po in purchase_orders])
        
        supplier_df = pd.DataFrame([{
            'id': str(s.id),
            'supplier_code': s.supplier_code,
            'name': s.name,
            'category': s.category,
            'rating': float(s.rating) if s.rating else 0,
            'on_time_delivery_rate': float(s.on_time_delivery_rate) if s.on_time_delivery_rate else 0,
            'quality_score': float(s.quality_score) if s.quality_score else 0,
            'total_orders': s.total_orders
        } for s in suppliers])
        
        items_df = pd.DataFrame([{
            'id': str(item.id),
            'po_id': str(item.purchase_order_id),
            'material_id': str(item.material_id) if item.material_id else None,
            'description': item.description,
            'quantity': float(item.quantity) if item.quantity else 0,
            'quantity_received': float(item.quantity_received) if item.quantity_received else 0,
            'quantity_pending': float(item.quantity_pending) if item.quantity_pending else 0,
            'status': item.status
        } for item in items])
        
        inventory_df = pd.DataFrame([{
            'id': str(inv.id),
            'material_id': str(inv.material_id) if inv.material_id else None,
            'quantity_on_hand': float(inv.quantity_on_hand) if inv.quantity_on_hand else 0,
            'quantity_available': float(inv.quantity_available) if inv.quantity_available else 0,
            'minimum_stock_level': float(inv.minimum_stock_level) if inv.minimum_stock_level else 0
        } for inv in inventory])
        
        # Calculate procurement health
        procurement_health = self.calculate_procurement_health(po_df, supplier_df)
        
        # Calculate supplier health
        supplier_health = self.calculate_supplier_health(supplier_df)
        
        # Predict material shortages
        material_shortages = self.predict_material_shortages(inventory_df, items_df)
        
        # Predict supplier delays
        supplier_delays = self.predict_supplier_delays(po_df, supplier_df)
        
        # Calculate on-time delivery rate
        on_time_rate = self.calculate_on_time_delivery_rate(po_df)
        
        # Generate explanation
        explanation = await self.generate_explanation(
            procurement_health,
            supplier_health,
            material_shortages,
            supplier_delays,
            on_time_rate
        )
        
        return {
            "procurement_health_score": procurement_health,
            "supplier_health_score": supplier_health,
            "material_shortage_risks": material_shortages,
            "supplier_delays_predicted": supplier_delays,
            "on_time_delivery_rate": on_time_rate,
            "total_purchase_orders": len(purchase_orders),
            "total_suppliers": len(suppliers),
            "pending_orders": len(po_df[po_df['status'] == 'pending']),
            "delivered_orders": len(po_df[po_df['status'] == 'delivered']),
            "explanation": explanation
        }
    
    def calculate_procurement_health(self, po_df: pd.DataFrame, supplier_df: pd.DataFrame) -> float:
        """Calculate overall procurement health score"""
        try:
            if len(po_df) == 0:
                return 50.0
            
            # Factors affecting procurement health
            delivered_count = len(po_df[po_df['status'] == 'delivered'])
            total_count = len(po_df)
            delivery_rate = (delivered_count / total_count * 100) if total_count > 0 else 0
            
            # Average supplier rating
            if len(supplier_df) > 0:
                avg_rating = supplier_df['rating'].mean()
            else:
                avg_rating = 0
            
            # On-time delivery rate
            if len(po_df) > 0:
                on_time_df = po_df[po_df['actual_delivery_date'].notna()]
                if len(on_time_df) > 0:
                    on_time_count = len(on_time_df[on_time_df['actual_delivery_date'] <= on_time_df['expected_delivery_date']])
                    on_time_rate = (on_time_count / len(on_time_df) * 100)
                else:
                    on_time_rate = 0
            else:
                on_time_rate = 0
            
            # Calculate health score
            health_score = (delivery_rate * 0.4) + (avg_rating * 20 * 0.3) + (on_time_rate * 0.3)
            
            return max(0, min(100, health_score))
        
        except Exception as e:
            self.logger.error(f"Procurement health calculation error: {e}")
            return 50.0
    
    def calculate_supplier_health(self, supplier_df: pd.DataFrame) -> float:
        """Calculate average supplier health score"""
        try:
            if len(supplier_df) == 0:
                return 50.0
            
            # Calculate weighted supplier score
            supplier_df['health_score'] = (
                (supplier_df['rating'] / 5 * 100 * 0.4) +
                (supplier_df['on_time_delivery_rate'] * 0.3) +
                (supplier_df['quality_score'] * 0.3)
            )
            
            return supplier_df['health_score'].mean()
        
        except Exception as e:
            self.logger.error(f"Supplier health calculation error: {e}")
            return 50.0
    
    def predict_material_shortages(self, inventory_df: pd.DataFrame, items_df: pd.DataFrame) -> list:
        """Predict materials at risk of shortage"""
        try:
            shortages = []
            
            for _, inv in inventory_df.iterrows():
                if inv['quantity_available'] <= inv['minimum_stock_level']:
                    # Calculate pending orders for this material
                    pending_items = items_df[items_df['material_id'] == inv['material_id']]
                    pending_quantity = pending_items['quantity_pending'].sum() if len(pending_items) > 0 else 0
                    
                    shortage_risk = {
                        'material_id': inv['material_id'],
                        'current_stock': inv['quantity_available'],
                        'minimum_level': inv['minimum_stock_level'],
                        'pending_orders': pending_quantity,
                        'risk_level': 'high' if inv['quantity_available'] == 0 else 'medium'
                    }
                    shortages.append(shortage_risk)
            
            return shortages[:10]
        
        except Exception as e:
            self.logger.error(f"Material shortage prediction error: {e}")
            return []
    
    def predict_supplier_delays(self, po_df: pd.DataFrame, supplier_df: pd.DataFrame) -> list:
        """Predict suppliers at risk of delays"""
        try:
            delays = []
            
            # Group by supplier
            for supplier_id in po_df['supplier_id'].unique():
                supplier_pos = po_df[po_df['supplier_id'] == supplier_id]
                supplier_info = supplier_df[supplier_df['id'] == supplier_id]
                
                if len(supplier_info) > 0:
                    supplier_data = supplier_info.iloc[0]
                    
                    # Calculate delay risk based on:
                    # 1. Low on-time delivery rate
                    # 2. High number of pending orders
                    # 3. Low rating
                    pending_count = len(supplier_pos[supplier_pos['status'].isin(['pending', 'ordered', 'shipped'])])
                    
                    delay_risk = (
                        (100 - supplier_data['on_time_delivery_rate']) * 0.4 +
                        (5 - supplier_data['rating']) * 20 * 0.3 +
                        (min(pending_count, 10) / 10 * 100) * 0.3
                    )
                    
                    if delay_risk > 50:
                        delays.append({
                            'supplier_id': supplier_id,
                            'supplier_name': supplier_data['name'],
                            'delay_risk_score': delay_risk,
                            'pending_orders': pending_count,
                            'on_time_rate': supplier_data['on_time_delivery_rate']
                        })
            
            # Sort by delay risk
            delays.sort(key=lambda x: x['delay_risk_score'], reverse=True)
            
            return delays[:10]
        
        except Exception as e:
            self.logger.error(f"Supplier delay prediction error: {e}")
            return []
    
    def calculate_on_time_delivery_rate(self, po_df: pd.DataFrame) -> float:
        """Calculate overall on-time delivery rate"""
        try:
            if len(po_df) == 0:
                return 0.0
            
            delivered_df = po_df[po_df['actual_delivery_date'].notna()]
            
            if len(delivered_df) == 0:
                return 0.0
            
            on_time_count = len(
                delivered_df[delivered_df['actual_delivery_date'] <= delivered_df['expected_delivery_date']]
            )
            
            return (on_time_count / len(delivered_df) * 100)
        
        except Exception as e:
            self.logger.error(f"On-time delivery rate calculation error: {e}")
            return 0.0
    
    async def generate_explanation(
        self,
        procurement_health: float,
        supplier_health: float,
        material_shortages: list,
        supplier_delays: list,
        on_time_rate: float
    ) -> str:
        """Generate AI explanation of procurement analysis"""
        if not self.llm:
            return (
                f"Procurement health is {procurement_health:.1f}/100 and supplier health is "
                f"{supplier_health:.1f}/100. On-time delivery is running at {on_time_rate:.1f}%, with "
                f"{len(material_shortages)} shortage risks and {len(supplier_delays)} suppliers flagged for delay recovery."
            )
        
        prompt = ChatPromptTemplate.from_template(
            """You are a Procurement Intelligence Agent for construction project management.
            
            Analyze the following procurement data and provide a clear explanation:
            
            Procurement Health Score: {procurement_health}/100
            Supplier Health Score: {supplier_health}/100
            On-Time Delivery Rate: {on_time_rate}%
            Material Shortage Risks: {shortage_count}
            Supplier Delay Risks: {delay_count}
            
            Provide a concise explanation of:
            1. Why procurement health is at this level
            2. Which suppliers are most concerning
            3. What materials are at risk of shortage
            4. What immediate actions should be taken
            
            Keep the explanation professional and actionable.
            """
        )
        
        try:
            chain = prompt | self.llm
            result = await asyncio.wait_for(chain.ainvoke({
                "procurement_health": procurement_health,
                "supplier_health": supplier_health,
                "on_time_rate": on_time_rate,
                "shortage_count": len(material_shortages),
                "delay_count": len(supplier_delays)
            }), timeout=8)
            
            return result.content
        except Exception as e:
            self.logger.error(f"Explanation generation error: {e}")
            return f"Procurement analysis complete. Health: {procurement_health}/100, On-time rate: {on_time_rate}%."
