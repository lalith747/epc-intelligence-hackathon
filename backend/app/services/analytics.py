"""
Analytics service for calculating health scores, critical paths, and project metrics
"""
from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import pandas as pd
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import (
    Project, Activity, Dependency, Risk, Recommendation,
    PurchaseOrder, Supplier, ProjectHealth
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Service for calculating project analytics and health metrics"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def calculate_project_health(self, project_id: str, session: AsyncSession) -> Dict[str, Any]:
        """Calculate comprehensive health metrics for a project"""
        try:
            # Get project data
            project_result = await session.execute(select(Project).where(Project.id == project_id))
            project = project_result.scalar_one_or_none()
            
            if not project:
                return {"error": "Project not found"}
            
            # Get latest schedule
            schedule_result = await session.execute(
                select(Activity.schedule_id)
                .where(Activity.schedule_id.isnot(None))
                .distinct()
                .limit(1)
            )
            schedule_id = schedule_result.scalar_one_or_none()
            
            # Get activities
            if schedule_id:
                activities_result = await session.execute(
                    select(Activity).where(Activity.schedule_id == schedule_id)
                )
                activities = activities_result.scalars().all()
            else:
                activities = []
            
            # Get risks
            risks_result = await session.execute(
                select(Risk).where(Risk.project_id == project_id, Risk.status == 'open')
            )
            risks = risks_result.scalars().all()
            
            # Get recommendations
            recommendations_result = await session.execute(
                select(Recommendation).where(Recommendation.project_id == project_id, Recommendation.status == 'pending')
            )
            recommendations = recommendations_result.scalars().all()
            
            # Get purchase orders
            pos_result = await session.execute(
                select(PurchaseOrder).where(PurchaseOrder.project_id == project_id)
            )
            purchase_orders = pos_result.scalars().all()
            
            # Calculate individual health scores
            schedule_health = await self.calculate_schedule_health(activities, project)
            procurement_health = await self.calculate_procurement_health(purchase_orders)
            supplier_health = await self.calculate_supplier_health(purchase_orders)
            risk_score = await self.calculate_risk_score(risks)
            
            # Calculate overall health
            overall_health = (
                schedule_health * 0.35 +
                procurement_health * 0.25 +
                supplier_health * 0.20 +
                (100 - risk_score) * 0.20
            )
            
            # Calculate additional metrics
            completion_percentage = await self.calculate_completion_percentage(activities, project)
            on_time_activities_percentage = await self.calculate_on_time_percentage(activities)
            on_budget_percentage = await self.calculate_on_budget_percentage(project)
            
            return {
                "overall_health_score": round(overall_health, 2),
                "schedule_health_score": round(schedule_health, 2),
                "procurement_health_score": round(procurement_health, 2),
                "supplier_health_score": round(supplier_health, 2),
                "risk_score": round(risk_score, 2),
                "cost_performance_index": 1.0,  # Placeholder - needs cost tracking
                "schedule_performance_index": schedule_health / 100,
                "completion_percentage": round(completion_percentage, 2),
                "on_time_activities_percentage": round(on_time_activities_percentage, 2),
                "on_budget_percentage": round(on_budget_percentage, 2),
                "open_risks_count": len(risks),
                "critical_risks_count": len([r for r in risks if r.severity == 'critical']),
                "open_recommendations_count": len(recommendations),
                "total_activities": len(activities),
                "completed_activities": len([a for a in activities if a.percent_complete >= 100])
            }
        
        except Exception as e:
            self.logger.error(f"Project health calculation error: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def calculate_schedule_health(self, activities: List[Activity], project: Project) -> float:
        """Calculate schedule health score"""
        try:
            if not activities:
                return 50.0
            
            # Calculate average completion
            avg_completion = sum(a.percent_complete or 0 for a in activities) / len(activities)
            
            # Calculate expected completion based on time
            total_days = (project.planned_end_date - project.start_date).days if project.planned_end_date and project.start_date else 365
            elapsed_days = (date.today() - project.start_date).days if project.start_date <= date.today() else 0
            
            if total_days > 0:
                expected_completion = (elapsed_days / total_days * 100)
            else:
                expected_completion = 0
            
            # Calculate variance
            completion_variance = abs(avg_completion - expected_completion)
            
            # Critical activities completion
            critical_activities = [a for a in activities if a.is_critical]
            if critical_activities:
                critical_completion = sum(a.percent_complete or 0 for a in critical_activities) / len(critical_activities)
            else:
                critical_completion = avg_completion
            
            # Calculate health score
            health_score = 100 - (completion_variance * 0.5)
            health_score = health_score * (critical_completion / 100) if critical_completion > 0 else health_score
            
            return max(0, min(100, health_score))
        
        except Exception as e:
            self.logger.error(f"Schedule health calculation error: {e}")
            return 50.0
    
    async def calculate_procurement_health(self, purchase_orders: List[PurchaseOrder]) -> float:
        """Calculate procurement health score"""
        try:
            if not purchase_orders:
                return 50.0
            
            # Delivery rate
            delivered_count = len([po for po in purchase_orders if po.status == 'delivered'])
            total_count = len(purchase_orders)
            delivery_rate = (delivered_count / total_count * 100) if total_count > 0 else 0
            
            # On-time delivery rate
            delivered_with_dates = [po for po in purchase_orders if po.status == 'delivered' and po.actual_delivery_date and po.expected_delivery_date]
            if delivered_with_dates:
                on_time_count = len([po for po in delivered_with_dates if po.actual_delivery_date <= po.expected_delivery_date])
                on_time_rate = (on_time_count / len(delivered_with_dates) * 100)
            else:
                on_time_rate = 0
            
            # Calculate health score
            health_score = (delivery_rate * 0.5) + (on_time_rate * 0.5)
            
            return max(0, min(100, health_score))
        
        except Exception as e:
            self.logger.error(f"Procurement health calculation error: {e}")
            return 50.0
    
    async def calculate_supplier_health(self, purchase_orders: List[PurchaseOrder]) -> float:
        """Calculate supplier health score"""
        try:
            if not purchase_orders:
                return 50.0
            
            # Group by supplier
            supplier_performance = {}
            for po in purchase_orders:
                if po.supplier_id not in supplier_performance:
                    supplier_performance[po.supplier_id] = {
                        'total': 0,
                        'on_time': 0,
                        'delivered': 0
                    }
                supplier_performance[po.supplier_id]['total'] += 1
                if po.status == 'delivered':
                    supplier_performance[po.supplier_id]['delivered'] += 1
                    if po.actual_delivery_date and po.expected_delivery_date:
                        if po.actual_delivery_date <= po.expected_delivery_date:
                            supplier_performance[po.supplier_id]['on_time'] += 1
            
            # Calculate average supplier score
            supplier_scores = []
            for supplier_id, metrics in supplier_performance.items():
                if metrics['delivered'] > 0:
                    supplier_score = (metrics['on_time'] / metrics['delivered'] * 100)
                    supplier_scores.append(supplier_score)
            
            if supplier_scores:
                return sum(supplier_scores) / len(supplier_scores)
            
            return 50.0
        
        except Exception as e:
            self.logger.error(f"Supplier health calculation error: {e}")
            return 50.0
    
    async def calculate_risk_score(self, risks: List[Risk]) -> float:
        """Calculate overall risk score"""
        try:
            if not risks:
                return 25.0  # Low risk baseline
            
            # Calculate average risk score
            avg_risk_score = sum(r.risk_score or 0 for r in risks) / len(risks)
            
            # Weight by severity
            critical_risks = [r for r in risks if r.severity == 'critical']
            high_risks = [r for r in risks if r.severity == 'high']
            
            severity_weight = 1.0
            if critical_risks:
                severity_weight = 1.5
            elif high_risks:
                severity_weight = 1.2
            
            weighted_risk_score = avg_risk_score * severity_weight
            
            return max(0, min(100, weighted_risk_score))
        
        except Exception as e:
            self.logger.error(f"Risk score calculation error: {e}")
            return 25.0
    
    async def calculate_completion_percentage(self, activities: List[Activity], project: Project) -> float:
        """Calculate overall project completion percentage"""
        try:
            if not activities:
                return project.progress_percentage or 0
            
            avg_completion = sum(a.percent_complete or 0 for a in activities) / len(activities)
            
            return avg_completion
        
        except Exception as e:
            self.logger.error(f"Completion percentage calculation error: {e}")
            return 0.0
    
    async def calculate_on_time_percentage(self, activities: List[Activity]) -> float:
        """Calculate percentage of activities on time"""
        try:
            if not activities:
                return 85.0  # Default assumption
            
            # Activities that are on or ahead of schedule
            on_time_count = 0
            for activity in activities:
                if activity.percent_complete >= 100:
                    # Completed activities - check if finished on time
                    if activity.actual_finish and activity.early_finish:
                        if activity.actual_finish <= activity.early_finish:
                            on_time_count += 1
                    else:
                        on_time_count += 1
                elif activity.percent_complete > 0:
                    # In progress - check if ahead of expected
                    on_time_count += 1
                else:
                    # Not started - check if should have started
                    if activity.early_start and activity.early_start > date.today():
                        on_time_count += 1
            
            return (on_time_count / len(activities) * 100)
        
        except Exception as e:
            self.logger.error(f"On-time percentage calculation error: {e}")
            return 85.0
    
    async def calculate_on_budget_percentage(self, project: Project) -> float:
        """Calculate percentage on budget"""
        try:
            if not project.total_budget or project.total_budget == 0:
                return 90.0  # Default assumption
            
            if not project.budget_consumed:
                return 100.0
            
            budget_variance = (project.budget_consumed / project.total_budget) * 100
            
            # Expected budget consumption based on progress
            expected_consumption = project.progress_percentage or 0
            
            if budget_variance <= expected_consumption:
                return 100.0
            else:
                return max(0, 100 - (budget_variance - expected_consumption))
        
        except Exception as e:
            self.logger.error(f"On-budget percentage calculation error: {e}")
            return 90.0
    
    async def calculate_critical_path(self, schedule_id: str, session: AsyncSession) -> List[Dict[str, Any]]:
        """Calculate critical path using NetworkX"""
        try:
            # Get activities
            activities_result = await session.execute(
                select(Activity).where(Activity.schedule_id == schedule_id)
            )
            activities = activities_result.scalars().all()
            
            # Get dependencies
            dependencies_result = await session.execute(
                select(Dependency).where(Dependency.schedule_id == schedule_id)
            )
            dependencies = dependencies_result.scalars().all()
            
            # Build graph
            G = nx.DiGraph()
            
            for activity in activities:
                G.add_node(str(activity.id), **{
                    'name': activity.activity_name,
                    'duration': activity.original_duration or 0,
                    'percent_complete': activity.percent_complete or 0,
                    'early_start': activity.early_start,
                    'early_finish': activity.early_finish,
                    'is_critical': activity.is_critical
                })
            
            for dep in dependencies:
                G.add_edge(str(dep.predecessor_id), str(dep.successor_id), **{
                    'type': dep.dependency_type,
                    'lag': dep.lag or 0
                })
            
            # Calculate critical path
            if len(G) == 0:
                return []
            
            # Use existing critical flag if available
            critical_activities = [a for a in activities if a.is_critical]
            
            if critical_activities:
                return [
                    {
                        'activity_id': a.activity_id,
                        'name': a.activity_name,
                        'duration': a.original_duration,
                        'percent_complete': a.percent_complete,
                        'early_start': a.early_start.isoformat() if a.early_start else None,
                        'early_finish': a.early_finish.isoformat() if a.early_finish else None
                    }
                    for a in critical_activities
                ]
            
            # Fallback: calculate longest path
            try:
                longest_path = nx.dag_longest_path(G)
                critical_path = []
                for node_id in longest_path:
                    if node_id in G.nodes:
                        node_data = G.nodes[node_id]
                        critical_path.append({
                            'activity_id': node_id,
                            'name': node_data.get('name', ''),
                            'duration': node_data.get('duration', 0),
                            'percent_complete': node_data.get('percent_complete', 0)
                        })
                return critical_path
            except:
                return []
        
        except Exception as e:
            self.logger.error(f"Critical path calculation error: {e}", exc_info=True)
            return []
    
    async def calculate_delay_forecast(self, project_id: str, session: AsyncSession) -> Dict[str, Any]:
        """Calculate delay forecast using historical data and current trends"""
        try:
            # Get historical health data
            health_result = await session.execute(
                select(ProjectHealth)
                .where(ProjectHealth.project_id == project_id)
                .order_by(ProjectHealth.metric_date.desc())
                .limit(30)
            )
            health_history = health_result.scalars().all()
            
            if len(health_history) < 2:
                return {
                    "predicted_delay_days": 0,
                    "confidence": 0,
                    "trend": "insufficient_data"
                }
            
            # Calculate trend
            recent_scores = [h.schedule_health_score for h in health_history[:7]]
            older_scores = [h.schedule_health_score for h in health_history[7:14]] if len(health_history) >= 14 else recent_scores
            
            recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 50
            older_avg = sum(older_scores) / len(older_scores) if older_scores else 50
            
            trend = recent_avg - older_avg
            
            # Predict delay based on trend
            if trend < -5:  # Declining health
                predicted_delay = int(abs(trend) * 2)
                confidence = 70
            elif trend < 0:  # Slight decline
                predicted_delay = int(abs(trend))
                confidence = 60
            elif trend > 5:  # Improving health
                predicted_delay = 0
                confidence = 65
            else:  # Stable
                predicted_delay = 0
                confidence = 50
            
            return {
                "predicted_delay_days": predicted_delay,
                "confidence": confidence,
                "trend": "declining" if trend < -5 else "stable" if abs(trend) <= 5 else "improving",
                "recent_health": recent_avg,
                "health_change": round(trend, 2)
            }
        
        except Exception as e:
            self.logger.error(f"Delay forecast calculation error: {e}", exc_info=True)
            return {
                "predicted_delay_days": 0,
                "confidence": 0,
                "trend": "error"
            }
