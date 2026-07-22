"""
Recommendation Agent - Generates actionable recommendations based on risk and analysis data
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base_agent import BaseAgent
from app.models.database import Recommendation, Project
from app.core.logging import get_logger
from app.services.database import AsyncSessionLocal
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import uuid


class RecommendationAnalysis(BaseModel):
    """Recommendation analysis output model"""
    recommendations: list = Field(description="List of actionable recommendations")
    priority_actions: list = Field(description="Immediate priority actions")
    estimated_impact: dict = Field(description="Estimated impact of recommendations")
    explanation: str = Field(description="Explanation of recommendations")


class RecommendationAgent(BaseAgent):
    """Recommendation Agent"""
    
    def __init__(self):
        super().__init__()
    
    async def execute(
        self,
        project_id: str,
        execution_type: str,
        input_data: Dict[str, Any],
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None,
        risk_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute recommendation generation"""
        start_time = datetime.utcnow()
        
        try:
            async with AsyncSessionLocal() as session:
                # Get project data
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()
                
                # Generate recommendations
                analysis = await self.generate_recommendations(
                    project,
                    schedule_data,
                    procurement_data,
                    risk_data
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                await self.log_execution(
                    agent_name="recommendation_agent",
                    project_id=project_id,
                    execution_type=execution_type,
                    input_data=input_data,
                    output_data=analysis,
                    execution_time_ms=int(execution_time),
                    status="success"
                )
                
                return analysis
        
        except Exception as e:
            self.logger.error(f"Recommendation Agent execution error: {e}", exc_info=True)
            await self.log_execution(
                agent_name="recommendation_agent",
                project_id=project_id,
                execution_type=execution_type,
                input_data=input_data,
                output_data={"error": str(e)},
                execution_time_ms=0,
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def generate_recommendations(
        self,
        project: Project,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None,
        risk_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate actionable recommendations"""
        
        recommendations = []
        priority_actions = []
        
        try:
            # Generate schedule-based recommendations
            if schedule_data:
                schedule_recs = self.generate_schedule_recommendations(schedule_data)
                recommendations.extend(schedule_recs)
            
            # Generate procurement-based recommendations
            if procurement_data:
                procurement_recs = self.generate_procurement_recommendations(procurement_data)
                recommendations.extend(procurement_recs)
            
            # Generate risk-based recommendations
            if risk_data:
                risk_recs = self.generate_risk_recommendations(risk_data)
                recommendations.extend(risk_recs)
            
            # Prioritize recommendations
            priority_actions = self.prioritize_recommendations(recommendations)
            
            # Calculate estimated impact
            estimated_impact = self.calculate_estimated_impact(recommendations)
            
            # Generate explanation
            explanation = await self.generate_explanation(
                recommendations,
                priority_actions,
                estimated_impact
            )
            
            return {
                "recommendations": recommendations,
                "priority_actions": priority_actions,
                "estimated_impact": estimated_impact,
                "total_recommendations": len(recommendations),
                "high_priority_count": len([r for r in recommendations if r['priority'] == 'high']),
                "explanation": explanation
            }
        
        except Exception as e:
            self.logger.error(f"Recommendation generation error: {e}")
            return {
                "recommendations": [],
                "priority_actions": [],
                "estimated_impact": {},
                "explanation": f"Error generating recommendations: {str(e)}"
            }
    
    def generate_schedule_recommendations(self, schedule_data: Dict[str, Any]) -> list:
        """Generate schedule-based recommendations"""
        recommendations = []
        
        try:
            schedule_health = schedule_data.get('schedule_health_score', 100)
            delay_prediction = schedule_data.get('delay_prediction_days', 0)
            bottlenecks = schedule_data.get('bottlenecks', [])
            
            # Low schedule health recommendations
            if schedule_health < 60:
                recommendations.append({
                    'recommendation_code': f"SCH-{uuid.uuid4().hex[:8].upper()}",
                    'title': 'Improve Schedule Performance',
                    'description': f'Schedule health is at {schedule_health}/100. Immediate action required to improve schedule adherence.',
                    'recommendation_type': 'reschedule',
                    'priority': 'high' if schedule_health < 40 else 'medium',
                    'confidence': 85,
                    'estimated_days_saved': int(delay_prediction * 0.3),
                    'expected_impact': {
                        'schedule_health_improvement': min(20, 100 - schedule_health),
                        'delay_reduction': int(delay_prediction * 0.3)
                    },
                    'source': 'schedule_analysis'
                })
            
            # Bottleneck recommendations
            for bottleneck in bottlenecks[:3]:
                recommendations.append({
                    'recommendation_code': f"BTN-{uuid.uuid4().hex[:8].upper()}",
                    'title': f'Address Bottleneck: {bottleneck["name"]}',
                    'description': f'Activity {bottleneck["activity_id"]} is a bottleneck with {bottleneck["centrality"]:.2f} centrality and only {bottleneck["completion"]}% complete.',
                    'recommendation_type': 'resource_increase',
                    'priority': 'high',
                    'confidence': 80,
                    'estimated_days_saved': 5,
                    'expected_impact': {
                        'bottleneck_resolution': True,
                        'schedule_improvement': 10
                    },
                    'source': 'schedule_analysis'
                })
            
            # Delay mitigation recommendations
            if delay_prediction > 30:
                recommendations.append({
                    'recommendation_code': f"DLY-{uuid.uuid4().hex[:8].upper()}",
                    'title': 'Mitigate Project Delay',
                    'description': f'Project predicted to be delayed by {delay_prediction} days. Implement parallel execution and extra shifts.',
                    'recommendation_type': 'parallel_execution',
                    'priority': 'high' if delay_prediction > 60 else 'medium',
                    'confidence': 75,
                    'estimated_days_saved': int(delay_prediction * 0.4),
                    'expected_impact': {
                        'delay_reduction': int(delay_prediction * 0.4),
                        'cost_increase': 15  # 15% cost increase
                    },
                    'source': 'schedule_analysis'
                })
        
        except Exception as e:
            self.logger.error(f"Schedule recommendation generation error: {e}")
        
        return recommendations
    
    def generate_procurement_recommendations(self, procurement_data: Dict[str, Any]) -> list:
        """Generate procurement-based recommendations"""
        recommendations = []
        
        try:
            procurement_health = procurement_data.get('procurement_health_score', 100)
            material_shortages = procurement_data.get('material_shortage_risks', [])
            supplier_delays = procurement_data.get('supplier_delays_predicted', [])
            
            # Low procurement health recommendations
            if procurement_health < 60:
                recommendations.append({
                    'recommendation_code': f"PRC-{uuid.uuid4().hex[:8].upper()}",
                    'title': 'Improve Procurement Performance',
                    'description': f'Procurement health is at {procurement_health}/100. Review supplier performance and delivery processes.',
                    'recommendation_type': 'process_improvement',
                    'priority': 'high' if procurement_health < 40 else 'medium',
                    'confidence': 80,
                    'estimated_days_saved': 7,
                    'expected_impact': {
                        'procurement_health_improvement': min(25, 100 - procurement_health),
                        'delivery_improvement': 15
                    },
                    'source': 'procurement_analysis'
                })
            
            # Material shortage recommendations
            for shortage in material_shortages[:3]:
                recommendations.append({
                    'recommendation_code': f"MTL-{uuid.uuid4().hex[:8].upper()}",
                    'title': f'Address Material Shortage: {shortage["material_id"]}',
                    'description': f'Material {shortage["material_id"]} is at risk of shortage. Current stock: {shortage["current_stock"]}, Minimum: {shortage["minimum_level"]}.',
                    'recommendation_type': 'inventory_transfer',
                    'priority': 'high' if shortage['risk_level'] == 'high' else 'medium',
                    'confidence': 85,
                    'estimated_days_saved': 3,
                    'expected_impact': {
                        'shortage_avoided': True,
                        'schedule_protection': 5
                    },
                    'source': 'procurement_analysis'
                })
            
            # Supplier delay recommendations
            for delay in supplier_delays[:3]:
                recommendations.append({
                    'recommendation_code': f"SUP-{uuid.uuid4().hex[:8].upper()}",
                    'title': f'Mitigate Supplier Delay Risk: {delay["supplier_name"]}',
                    'description': f'Supplier {delay["supplier_name"]} has {delay["delay_risk_score"]:.1f}% delay risk with {delay["pending_orders"]} pending orders.',
                    'recommendation_type': 'supplier_change',
                    'priority': 'high' if delay['delay_risk_score'] > 70 else 'medium',
                    'confidence': 75,
                    'estimated_days_saved': 10,
                    'expected_impact': {
                        'delay_risk_reduction': delay['delay_risk_score'] * 0.5,
                        'alternative_supplier_required': True
                    },
                    'source': 'procurement_analysis'
                })
        
        except Exception as e:
            self.logger.error(f"Procurement recommendation generation error: {e}")
        
        return recommendations
    
    def generate_risk_recommendations(self, risk_data: Dict[str, Any]) -> list:
        """Generate risk-based recommendations"""
        recommendations = []
        
        try:
            overall_risk_score = risk_data.get('overall_risk_score', 0)
            high_priority_risks = risk_data.get('high_priority_risks', [])
            emerging_risks = risk_data.get('emerging_risks', [])
            
            # High overall risk recommendations
            if overall_risk_score > 70:
                recommendations.append({
                    'recommendation_code': f"RSK-{uuid.uuid4().hex[:8].upper()}",
                    'title': 'Implement Risk Mitigation Plan',
                    'description': f'Overall risk score is {overall_risk_score}/100. Comprehensive risk mitigation plan required.',
                    'recommendation_type': 'risk_mitigation',
                    'priority': 'high',
                    'confidence': 90,
                    'estimated_days_saved': 14,
                    'expected_impact': {
                        'risk_reduction': min(30, overall_risk_score * 0.4),
                        'project_stability_improvement': 20
                    },
                    'source': 'risk_analysis'
                })
            
            # High priority risk recommendations
            for risk in high_priority_risks[:3]:
                recommendations.append({
                    'recommendation_code': f"RSP-{uuid.uuid4().hex[:8].upper()}",
                    'title': f'Mitigate Risk: {risk["title"]}',
                    'description': f'High priority risk: {risk["title"]} (Score: {risk["risk_score"]}, Severity: {risk["severity"]}).',
                    'recommendation_type': 'risk_mitigation',
                    'priority': 'high',
                    'confidence': 80,
                    'estimated_days_saved': int(risk['impact'] * 0.2),
                    'expected_impact': {
                        'risk_score_reduction': risk['risk_score'] * 0.5,
                        'impact_reduction': risk['impact'] * 0.3
                    },
                    'source': 'risk_analysis'
                })
        
        except Exception as e:
            self.logger.error(f"Risk recommendation generation error: {e}")
        
        return recommendations
    
    def prioritize_recommendations(self, recommendations: list) -> list:
        """Prioritize recommendations by impact and urgency"""
        # Sort by priority and confidence
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        sorted_recommendations = sorted(
            recommendations,
            key=lambda x: (
                priority_order.get(x.get('priority', 'medium'), 2),
                -(x.get('confidence', 0)),
                -(x.get('estimated_days_saved', 0))
            )
        )
        
        return sorted_recommendations[:5]  # Return top 5 priority actions
    
    def calculate_estimated_impact(self, recommendations: list) -> dict:
        """Calculate estimated impact of all recommendations"""
        total_days_saved = sum(r.get('estimated_days_saved', 0) for r in recommendations)
        high_priority_count = len([r for r in recommendations if r.get('priority') == 'high'])
        
        return {
            'total_days_saved': total_days_saved,
            'high_priority_actions': high_priority_count,
            'schedule_improvement': min(30, total_days_saved * 0.5),
            'risk_reduction': min(25, high_priority_count * 5)
        }
    
    async def generate_explanation(
        self,
        recommendations: list,
        priority_actions: list,
        estimated_impact: dict
    ) -> str:
        """Generate AI explanation of recommendations"""
        
        prompt = ChatPromptTemplate.from_template(
            """You are a Recommendation Agent for construction project management.
            
            Analyze the following recommendations and provide a clear explanation:
            
            Total Recommendations: {total_count}
            High Priority Actions: {high_priority_count}
            Estimated Days Saved: {days_saved}
            
            Top Priority Actions:
            {priority_actions}
            
            Provide a concise explanation of:
            1. What are the most critical recommendations
            2. What impact these recommendations will have
            3. Which recommendations should be implemented first
            4. What resources are needed for implementation
            
            Keep the explanation professional and actionable.
            """
        )
        
        try:
            chain = prompt | self.llm
            result = await asyncio.wait_for(chain.ainvoke({
                "total_count": len(recommendations),
                "high_priority_count": len(priority_actions),
                "days_saved": estimated_impact.get('total_days_saved', 0),
                "priority_actions": "\n".join([
                    f"- {r['title']}: {r['description'][:100]}..."
                    for r in priority_actions[:3]
                ])
            }), timeout=8)
            
            return result.content
        except Exception as e:
            self.logger.error(f"Explanation generation error: {e}")
            return f"Generated {len(recommendations)} recommendations. Estimated {estimated_impact.get('total_days_saved', 0)} days can be saved."
