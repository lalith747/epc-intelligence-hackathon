"""
Executive Summary Agent - Generates executive summaries and management reports
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, date
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base_agent import BaseAgent
from app.models.database import Report, Project, ProjectHealth
from app.core.logging import get_logger
from app.services.database import AsyncSessionLocal
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    """Executive summary output model"""
    summary: str = Field(description="Executive summary")
    key_insights: list = Field(description="Key insights from analysis")
    root_causes: list = Field(description="Identified root causes")
    future_risks: list = Field(description="Future risk predictions")
    recommended_actions: list = Field(description="Recommended actions for management")
    project_health_assessment: str = Field(description="Overall project health assessment")


class ExecutiveAgent(BaseAgent):
    """Executive Summary Agent"""
    
    def __init__(self):
        super().__init__()
    
    async def execute(
        self,
        project_id: str,
        execution_type: str,
        input_data: Dict[str, Any],
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None,
        risk_data: Dict[str, Any] = None,
        recommendations: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute executive summary generation"""
        start_time = datetime.utcnow()
        
        try:
            async with AsyncSessionLocal() as session:
                # Get project data
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()
                
                # Get latest health metrics
                health_result = await session.execute(
                    select(ProjectHealth)
                    .where(ProjectHealth.project_id == project_id)
                    .order_by(ProjectHealth.metric_date.desc())
                    .limit(1)
                )
                health = health_result.scalar_one_or_none()
                
                # Generate executive summary
                summary = await self.generate_executive_summary(
                    project,
                    health,
                    schedule_data,
                    procurement_data,
                    risk_data,
                    recommendations
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                await self.log_execution(
                    agent_name="executive_agent",
                    project_id=project_id,
                    execution_type=execution_type,
                    input_data=input_data,
                    output_data=summary,
                    execution_time_ms=int(execution_time),
                    status="success"
                )
                
                return summary
        
        except Exception as e:
            self.logger.error(f"Executive Agent execution error: {e}", exc_info=True)
            await self.log_execution(
                agent_name="executive_agent",
                project_id=project_id,
                execution_type=execution_type,
                input_data=input_data,
                output_data={"error": str(e)},
                execution_time_ms=0,
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def generate_executive_summary(
        self,
        project: Project,
        health: ProjectHealth,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None,
        risk_data: Dict[str, Any] = None,
        recommendations: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive executive summary"""
        
        try:
            # Compile all analysis data
            analysis_summary = {
                "project_name": project.name if project else "Unknown",
                "project_code": project.code if project else "Unknown",
                "project_status": project.status if project else "Unknown",
                "progress_percentage": float(project.progress_percentage) if project and project.progress_percentage else 0,
                "overall_health_score": float(health.overall_health_score) if health and health.overall_health_score else 50,
                "schedule_health_score": float(health.schedule_health_score) if health and health.schedule_health_score else 50,
                "procurement_health_score": float(health.procurement_health_score) if health and health.procurement_health_score else 50,
                "risk_score": float(health.risk_score) if health and health.risk_score else 50,
                "completion_percentage": float(health.completion_percentage) if health and health.completion_percentage else 0
            }
            
            # Add schedule data
            if schedule_data:
                analysis_summary.update({
                    "schedule_health": schedule_data.get('schedule_health_score', 0),
                    "delay_prediction": schedule_data.get('delay_prediction_days', 0),
                    "critical_activities": schedule_data.get('critical_activities_count', 0),
                    "bottlenecks": len(schedule_data.get('bottlenecks', []))
                })
            
            # Add procurement data
            if procurement_data:
                analysis_summary.update({
                    "procurement_health": procurement_data.get('procurement_health_score', 0),
                    "supplier_health": procurement_data.get('supplier_health_score', 0),
                    "on_time_delivery_rate": procurement_data.get('on_time_delivery_rate', 0),
                    "material_shortages": len(procurement_data.get('material_shortage_risks', [])),
                    "supplier_delays": len(procurement_data.get('supplier_delays_predicted', []))
                })
            
            # Add risk data
            if risk_data:
                analysis_summary.update({
                    "overall_risk_score": risk_data.get('overall_risk_score', 0),
                    "open_risks": risk_data.get('open_risks', 0),
                    "critical_risks": risk_data.get('critical_risks', 0),
                    "risk_trend": risk_data.get('risk_trend', 'stable')
                })
            
            # Add recommendations
            if recommendations:
                analysis_summary.update({
                    "total_recommendations": recommendations.get('total_recommendations', 0),
                    "high_priority_count": recommendations.get('high_priority_count', 0),
                    "estimated_days_saved": recommendations.get('estimated_impact', {}).get('total_days_saved', 0)
                })
            
            # Generate AI-powered summary
            executive_summary = await self.generate_ai_summary(analysis_summary)
            
            # Extract key insights
            key_insights = self.extract_key_insights(analysis_summary)
            
            # Identify root causes
            root_causes = self.identify_root_causes(analysis_summary, schedule_data, procurement_data, risk_data)
            
            # Predict future risks
            future_risks = self.predict_future_risks(analysis_summary, risk_data)
            
            # Compile recommended actions
            recommended_actions = self.compile_recommended_actions(recommendations)
            
            # Generate health assessment
            health_assessment = self.generate_health_assessment(analysis_summary)
            
            return {
                "summary": executive_summary,
                "key_insights": key_insights,
                "root_causes": root_causes,
                "future_risks": future_risks,
                "recommended_actions": recommended_actions,
                "project_health_assessment": health_assessment,
                "analysis_summary": analysis_summary,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Executive summary generation error: {e}")
            return {
                "summary": f"Error generating executive summary: {str(e)}",
                "key_insights": [],
                "root_causes": [],
                "future_risks": [],
                "recommended_actions": [],
                "project_health_assessment": "Unable to assess"
            }
    
    async def generate_ai_summary(self, analysis_summary: Dict[str, Any]) -> str:
        """Generate AI-powered executive summary"""
        
        prompt = ChatPromptTemplate.from_template(
            """You are an Executive Summary Agent for construction project management.
            
            Generate a professional executive summary for project management based on the following data:
            
            Project: {project_name} ({project_code})
            Status: {project_status}
            Progress: {progress}%
            
            Health Scores:
            - Overall Health: {overall_health}/100
            - Schedule Health: {schedule_health}/100
            - Procurement Health: {procurement_health}/100
            - Risk Score: {risk_score}/100
            
            Key Metrics:
            - Delay Prediction: {delay_days} days
            - Critical Activities: {critical_activities}
            - Open Risks: {open_risks}
            - Critical Risks: {critical_risks}
            - Recommendations: {total_recommendations}
            - Estimated Days Saved: {days_saved}
            
            Generate a concise executive summary (200-300 words) that includes:
            1. Current project status and health
            2. Key challenges and risks
            3. Performance highlights or concerns
            4. Overall assessment for management
            
            Keep it professional, concise, and actionable.
            """
        )
        
        try:
            chain = prompt | self.llm
            result = await asyncio.wait_for(chain.ainvoke({
                "project_name": analysis_summary.get('project_name', 'Unknown'),
                "project_code": analysis_summary.get('project_code', 'Unknown'),
                "project_status": analysis_summary.get('project_status', 'Unknown'),
                "progress": analysis_summary.get('progress_percentage', 0),
                "overall_health": analysis_summary.get('overall_health_score', 0),
                "schedule_health": analysis_summary.get('schedule_health_score', 0),
                "procurement_health": analysis_summary.get('procurement_health_score', 0),
                "risk_score": analysis_summary.get('risk_score', 0),
                "delay_days": analysis_summary.get('delay_prediction', 0),
                "critical_activities": analysis_summary.get('critical_activities', 0),
                "open_risks": analysis_summary.get('open_risks', 0),
                "critical_risks": analysis_summary.get('critical_risks', 0),
                "total_recommendations": analysis_summary.get('total_recommendations', 0),
                "days_saved": analysis_summary.get('estimated_days_saved', 0)
            }), timeout=8)
            
            return result.content
        except Exception as e:
            self.logger.error(f"AI summary generation error: {e}")
            return self.generate_fallback_summary(analysis_summary)
    
    def generate_fallback_summary(self, analysis_summary: Dict[str, Any]) -> str:
        """Generate fallback summary if AI generation fails"""
        health = analysis_summary.get('overall_health_score', 50)
        
        if health >= 80:
            status = "performing well"
        elif health >= 60:
            status = "performing adequately with some concerns"
        elif health >= 40:
            status = "facing significant challenges"
        else:
            status = "in critical condition requiring immediate attention"
        
        return (f"Project {analysis_summary.get('project_name', 'Unknown')} is {status}. "
                f"Overall health score is {health}/100. "
                f"Schedule health is {analysis_summary.get('schedule_health_score', 0)}/100, "
                f"procurement health is {analysis_summary.get('procurement_health_score', 0)}/100, "
                f"and risk score is {analysis_summary.get('risk_score', 0)}/100. "
                f"Project is {analysis_summary.get('progress_percentage', 0)}% complete.")
    
    def extract_key_insights(self, analysis_summary: Dict[str, Any]) -> list:
        """Extract key insights from analysis"""
        insights = []
        
        # Health insights
        overall_health = analysis_summary.get('overall_health_score', 0)
        if overall_health >= 80:
            insights.append("Project is performing well across all metrics")
        elif overall_health >= 60:
            insights.append("Project performance is adequate with room for improvement")
        elif overall_health >= 40:
            insights.append("Project is experiencing significant performance issues")
        else:
            insights.append("Project is in critical condition requiring immediate intervention")
        
        # Schedule insights
        delay_prediction = analysis_summary.get('delay_prediction', 0)
        if delay_prediction > 30:
            insights.append(f"Project predicted to be delayed by {delay_prediction} days")
        elif delay_prediction > 0:
            insights.append(f"Minor delay of {delay_prediction} days predicted")
        else:
            insights.append("Project is on schedule or ahead of schedule")
        
        # Risk insights
        critical_risks = analysis_summary.get('critical_risks', 0)
        if critical_risks > 5:
            insights.append(f"High number of critical risks ({critical_risks}) require attention")
        elif critical_risks > 0:
            insights.append(f"{critical_risks} critical risks identified")
        else:
            insights.append("No critical risks currently identified")
        
        # Procurement insights
        material_shortages = analysis_summary.get('material_shortages', 0)
        if material_shortages > 0:
            insights.append(f"{material_shortages} materials at risk of shortage")
        
        return insights[:5]
    
    def identify_root_causes(
        self,
        analysis_summary: Dict[str, Any],
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None,
        risk_data: Dict[str, Any] = None
    ) -> list:
        """Identify root causes of current issues"""
        root_causes = []
        
        # Schedule root causes
        if schedule_data:
            bottlenecks = schedule_data.get('bottlenecks', [])
            if len(bottlenecks) > 0:
                root_causes.append({
                    'category': 'schedule',
                    'cause': 'Activity bottlenecks',
                    'description': f'{len(bottlenecks)} bottleneck activities identified causing schedule delays'
                })
        
        # Procurement root causes
        if procurement_data:
            supplier_delays = procurement_data.get('supplier_delays_predicted', [])
            if len(supplier_delays) > 0:
                root_causes.append({
                    'category': 'procurement',
                    'cause': 'Supplier performance issues',
                    'description': f'{len(supplier_delays)} suppliers at risk of delivery delays'
                })
            
            material_shortages = procurement_data.get('material_shortage_risks', [])
            if len(material_shortages) > 0:
                root_causes.append({
                    'category': 'procurement',
                    'cause': 'Material shortages',
                    'description': f'{len(material_shortages)} materials at risk of shortage'
                })
        
        # Risk root causes
        if risk_data:
            high_priority_risks = risk_data.get('high_priority_risks', [])
            if len(high_priority_risks) > 0:
                root_causes.append({
                    'category': 'risk',
                    'cause': 'High-priority risks',
                    'description': f'{len(high_priority_risks)} high-priority risks require mitigation'
                })
        
        return root_causes[:5]
    
    def predict_future_risks(self, analysis_summary: Dict[str, Any], risk_data: Dict[str, Any] = None) -> list:
        """Predict future risks based on current analysis"""
        future_risks = []
        
        # Schedule-based future risks
        if analysis_summary.get('delay_prediction', 0) > 30:
            future_risks.append({
                'risk_type': 'schedule',
                'description': 'Continued schedule delays may impact project completion date',
                'probability': 'high',
                'timeframe': '1-3 months'
            })
        
        # Procurement-based future risks
        if analysis_summary.get('material_shortages', 0) > 0:
            future_risks.append({
                'risk_type': 'procurement',
                'description': 'Material shortages may escalate if not addressed',
                'probability': 'medium',
                'timeframe': '2-4 weeks'
            })
        
        # Risk-based future risks
        if risk_data and risk_data.get('risk_trend') == 'increasing':
            future_risks.append({
                'risk_type': 'risk',
                'description': 'Risk profile is trending upward, indicating potential escalation',
                'probability': 'high',
                'timeframe': 'ongoing'
            })
        
        return future_risks[:5]
    
    def compile_recommended_actions(self, recommendations: Dict[str, Any] = None) -> list:
        """Compile recommended actions for management"""
        if not recommendations:
            return []
        
        priority_actions = recommendations.get('priority_actions', [])
        
        return [
            {
                'action': action['title'],
                'priority': action['priority'],
                'impact': action.get('expected_impact', {}),
                'days_saved': action.get('estimated_days_saved', 0)
            }
            for action in priority_actions[:5]
        ]
    
    def generate_health_assessment(self, analysis_summary: Dict[str, Any]) -> str:
        """Generate overall health assessment"""
        overall_health = analysis_summary.get('overall_health_score', 50)
        
        if overall_health >= 90:
            return "Excellent - Project is performing exceptionally well"
        elif overall_health >= 75:
            return "Good - Project is performing well with minor issues"
        elif overall_health >= 60:
            return "Fair - Project is performing adequately with some concerns"
        elif overall_health >= 40:
            return "Poor - Project is experiencing significant challenges"
        else:
            return "Critical - Project requires immediate intervention"
