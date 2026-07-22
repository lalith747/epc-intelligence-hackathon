"""
Risk Assessment Agent - Combines data from all agents to generate comprehensive risk analysis
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, date
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base_agent import BaseAgent
from app.models.database import Risk, Project
from app.core.logging import get_logger
from app.services.database import AsyncSessionLocal
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class RiskAnalysis(BaseModel):
    """Risk analysis output model"""
    overall_risk_score: float = Field(description="Overall risk score (0-100)")
    high_priority_risks: list = Field(description="List of high-priority risks")
    emerging_risks: list = Field(description="Newly identified risks")
    risk_trend: str = Field(description="Risk trend direction")
    confidence: float = Field(description="Confidence in risk assessment (0-100)")
    explanation: str = Field(description="Explanation of the risk analysis")


class RiskAgent(BaseAgent):
    """Risk Assessment Agent"""
    
    def __init__(self):
        super().__init__()
    
    async def execute(
        self,
        project_id: str,
        execution_type: str,
        input_data: Dict[str, Any],
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute risk assessment"""
        start_time = datetime.utcnow()
        
        try:
            async with AsyncSessionLocal() as session:
                # Get existing risks
                risks_result = await session.execute(
                    select(Risk).where(Risk.project_id == project_id)
                )
                existing_risks = risks_result.scalars().all()
                
                # Get project data
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()
                
                # Perform risk analysis
                analysis = await self.analyze_risks(
                    project,
                    existing_risks,
                    schedule_data,
                    procurement_data
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                await self.log_execution(
                    agent_name="risk_agent",
                    project_id=project_id,
                    execution_type=execution_type,
                    input_data=input_data,
                    output_data=analysis,
                    execution_time_ms=int(execution_time),
                    status="success"
                )
                
                return analysis
        
        except Exception as e:
            self.logger.error(f"Risk Agent execution error: {e}", exc_info=True)
            await self.log_execution(
                agent_name="risk_agent",
                project_id=project_id,
                execution_type=execution_type,
                input_data=input_data,
                output_data={"error": str(e)},
                execution_time_ms=0,
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def analyze_risks(
        self,
        project: Project,
        existing_risks: list,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive risk analysis"""
        
        # Convert existing risks to DataFrame
        risks_df = pd.DataFrame([{
            'id': str(r.id),
            'risk_code': r.risk_code,
            'title': r.title,
            'category': r.category,
            'probability': float(r.probability) if r.probability else 0,
            'impact': float(r.impact) if r.impact else 0,
            'risk_score': float(r.risk_score) if r.risk_score else 0,
            'severity': r.severity,
            'status': r.status,
            'confidence': float(r.confidence) if r.confidence else 0
        } for r in existing_risks])
        
        # Analyze existing risks
        high_priority_risks = self.identify_high_priority_risks(risks_df)
        
        # Generate new risks based on schedule and procurement data
        emerging_risks = await self.identify_emerging_risks(
            project,
            schedule_data,
            procurement_data
        )
        
        # Calculate overall risk score
        overall_risk_score = self.calculate_overall_risk_score(risks_df, schedule_data, procurement_data)
        
        # Determine risk trend
        risk_trend = self.determine_risk_trend(risks_df)
        
        # Calculate confidence
        confidence = self.calculate_confidence(risks_df, schedule_data, procurement_data)
        
        # Generate explanation
        explanation = await self.generate_explanation(
            overall_risk_score,
            high_priority_risks,
            emerging_risks,
            risk_trend,
            confidence
        )
        
        return {
            "overall_risk_score": overall_risk_score,
            "high_priority_risks": high_priority_risks,
            "emerging_risks": emerging_risks,
            "risk_trend": risk_trend,
            "confidence": confidence,
            "total_risks": len(existing_risks),
            "open_risks": len(risks_df[risks_df['status'] == 'open']),
            "critical_risks": len(risks_df[risks_df['severity'] == 'critical']),
            "explanation": explanation
        }
    
    def identify_high_priority_risks(self, risks_df: pd.DataFrame) -> list:
        """Identify high-priority existing risks"""
        try:
            if len(risks_df) == 0:
                return []
            
            # Filter for open risks with high risk scores
            high_risks = risks_df[
                (risks_df['status'] == 'open') &
                (risks_df['risk_score'] >= 50)
            ].sort_values('risk_score', ascending=False)
            
            return [
                {
                    'risk_id': r['id'],
                    'risk_code': r['risk_code'],
                    'title': r['title'],
                    'category': r['category'],
                    'risk_score': r['risk_score'],
                    'severity': r['severity'],
                    'probability': r['probability'],
                    'impact': r['impact']
                }
                for _, r in high_risks.head(10).iterrows()
            ]
        
        except Exception as e:
            self.logger.error(f"High priority risk identification error: {e}")
            return []
    
    async def identify_emerging_risks(
        self,
        project: Project,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None
    ) -> list:
        """Identify new risks based on schedule and procurement analysis"""
        emerging_risks = []
        
        try:
            # Analyze schedule-based risks
            if schedule_data:
                schedule_health = schedule_data.get('schedule_health_score', 100)
                delay_prediction = schedule_data.get('delay_prediction_days', 0)
                
                if schedule_health < 60:
                    emerging_risks.append({
                        'type': 'schedule',
                        'title': 'Schedule Performance Risk',
                        'description': f'Low schedule health ({schedule_health}/100) indicates potential delays',
                        'category': 'schedule',
                        'probability': min(90, 100 - schedule_health),
                        'impact': delay_prediction * 2,
                        'severity': 'high' if schedule_health < 40 else 'medium',
                        'source': 'schedule_analysis'
                    })
                
                if delay_prediction > 30:
                    emerging_risks.append({
                        'type': 'schedule',
                        'title': 'Project Delay Risk',
                        'description': f'Project predicted to be delayed by {delay_prediction} days',
                        'category': 'schedule',
                        'probability': 80,
                        'impact': delay_prediction,
                        'severity': 'critical' if delay_prediction > 60 else 'high',
                        'source': 'schedule_analysis'
                    })
            
            # Analyze procurement-based risks
            if procurement_data:
                procurement_health = procurement_data.get('procurement_health_score', 100)
                material_shortages = procurement_data.get('material_shortage_risks', [])
                supplier_delays = procurement_data.get('supplier_delays_predicted', [])
                
                if procurement_health < 60:
                    emerging_risks.append({
                        'type': 'procurement',
                        'title': 'Procurement Performance Risk',
                        'description': f'Low procurement health ({procurement_health}/100)',
                        'category': 'procurement',
                        'probability': min(85, 100 - procurement_health),
                        'impact': 70,
                        'severity': 'high' if procurement_health < 40 else 'medium',
                        'source': 'procurement_analysis'
                    })
                
                if len(material_shortages) > 0:
                    emerging_risks.append({
                        'type': 'procurement',
                        'title': 'Material Shortage Risk',
                        'description': f'{len(material_shortages)} materials at risk of shortage',
                        'category': 'procurement',
                        'probability': 75,
                        'impact': len(material_shortages) * 10,
                        'severity': 'high',
                        'source': 'procurement_analysis'
                    })
                
                if len(supplier_delays) > 0:
                    emerging_risks.append({
                        'type': 'procurement',
                        'title': 'Supplier Delay Risk',
                        'description': f'{len(supplier_delays)} suppliers at risk of delays',
                        'category': 'procurement',
                        'probability': 70,
                        'impact': len(supplier_delays) * 15,
                        'severity': 'high',
                        'source': 'procurement_analysis'
                    })
        
        except Exception as e:
            self.logger.error(f"Emerging risk identification error: {e}")
        
        return emerging_risks[:10]
    
    def calculate_overall_risk_score(
        self,
        risks_df: pd.DataFrame,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None
    ) -> float:
        """Calculate overall project risk score"""
        try:
            risk_factors = []
            
            # Existing risks contribution
            if len(risks_df) > 0:
                avg_risk_score = risks_df['risk_score'].mean()
                risk_factors.append(avg_risk_score * 0.4)
            
            # Schedule risk contribution
            if schedule_data:
                schedule_health = schedule_data.get('schedule_health_score', 100)
                schedule_risk = (100 - schedule_health) * 0.3
                risk_factors.append(schedule_risk)
            
            # Procurement risk contribution
            if procurement_data:
                procurement_health = procurement_data.get('procurement_health_score', 100)
                procurement_risk = (100 - procurement_health) * 0.3
                risk_factors.append(procurement_risk)
            
            if not risk_factors:
                return 50.0
            
            overall_risk = sum(risk_factors)
            
            return max(0, min(100, overall_risk))
        
        except Exception as e:
            self.logger.error(f"Overall risk score calculation error: {e}")
            return 50.0
    
    def determine_risk_trend(self, risks_df: pd.DataFrame) -> str:
        """Determine risk trend direction"""
        try:
            if len(risks_df) == 0:
                return "stable"
            
            # Calculate average risk score
            avg_risk = risks_df['risk_score'].mean()
            
            if avg_risk >= 70:
                return "increasing"
            elif avg_risk >= 40:
                return "stable"
            else:
                return "decreasing"
        
        except Exception as e:
            self.logger.error(f"Risk trend determination error: {e}")
            return "stable"
    
    def calculate_confidence(
        self,
        risks_df: pd.DataFrame,
        schedule_data: Dict[str, Any] = None,
        procurement_data: Dict[str, Any] = None
    ) -> float:
        """Calculate confidence in risk assessment"""
        try:
            confidence_factors = []
            
            # Data availability
            if len(risks_df) > 0:
                confidence_factors.append(30)
            if schedule_data:
                confidence_factors.append(35)
            if procurement_data:
                confidence_factors.append(35)
            
            if not confidence_factors:
                return 50.0
            
            return sum(confidence_factors)
        
        except Exception as e:
            self.logger.error(f"Confidence calculation error: {e}")
            return 50.0
    
    async def generate_explanation(
        self,
        overall_risk_score: float,
        high_priority_risks: list,
        emerging_risks: list,
        risk_trend: str,
        confidence: float
    ) -> str:
        """Generate AI explanation of risk analysis"""
        if not self.llm:
            return (
                f"Overall project risk is {overall_risk_score:.1f}/100 and trend is {risk_trend}. "
                f"There are {len(high_priority_risks)} high-priority risks and {len(emerging_risks)} "
                f"emerging risks, with confidence assessed at {confidence:.1f}%."
            )
        
        prompt = ChatPromptTemplate.from_template(
            """You are a Risk Assessment Agent for construction project management.
            
            Analyze the following risk data and provide a clear explanation:
            
            Overall Risk Score: {risk_score}/100
            Risk Trend: {risk_trend}
            High Priority Risks: {high_risk_count}
            Emerging Risks: {emerging_risk_count}
            Confidence: {confidence}%
            
            Provide a concise explanation of:
            1. Why the overall risk score is at this level
            2. Which risks are most concerning
            3. What new risks have emerged
            4. What immediate actions should be taken to mitigate risks
            
            Keep the explanation professional and actionable.
            """
        )
        
        try:
            chain = prompt | self.llm
            result = await asyncio.wait_for(chain.ainvoke({
                "risk_score": overall_risk_score,
                "risk_trend": risk_trend,
                "high_risk_count": len(high_priority_risks),
                "emerging_risk_count": len(emerging_risks),
                "confidence": confidence
            }), timeout=8)
            
            return result.content
        except Exception as e:
            self.logger.error(f"Explanation generation error: {e}")
            return f"Risk analysis complete. Overall risk: {overall_risk_score}/100, Trend: {risk_trend}."
