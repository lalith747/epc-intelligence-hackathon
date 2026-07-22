"""
Schedule Intelligence Agent - Analyzes project schedules, dependencies, and predicts delays
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base_agent import BaseAgent
from app.models.database import Activity, Dependency, Schedule, Project
from app.core.logging import get_logger
from app.services.database import AsyncSessionLocal
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class ScheduleAnalysis(BaseModel):
    """Schedule analysis output model"""
    schedule_health_score: float = Field(description="Overall schedule health score (0-100)")
    critical_activities_count: int = Field(description="Number of critical activities")
    delay_prediction_days: int = Field(description="Predicted delay in days")
    completion_date_estimate: str = Field(description="Estimated completion date")
    bottlenecks: list = Field(description="List of bottleneck activities")
    variance_activities: list = Field(description="Activities with significant variance")
    explanation: str = Field(description="Explanation of the analysis")


class ScheduleAgent(BaseAgent):
    """Schedule Intelligence Agent"""
    
    def __init__(self):
        super().__init__()
        self.parser = PydanticOutputParser(pydantic_object=ScheduleAnalysis)
    
    async def execute(self, project_id: str, execution_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute schedule analysis"""
        start_time = datetime.utcnow()
        
        try:
            async with AsyncSessionLocal() as session:
                # Get project data
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()
                
                if not project:
                    return {"error": "Project not found"}
                
                # Get latest schedule
                schedule_result = await session.execute(
                    select(Schedule)
                    .where(Schedule.project_id == project_id)
                    .order_by(Schedule.created_at.desc())
                    .limit(1)
                )
                schedule = schedule_result.scalar_one_or_none()
                
                if not schedule:
                    return {"error": "No schedule found for project"}
                
                # Get activities
                activities_result = await session.execute(
                    select(Activity).where(Activity.schedule_id == schedule.id)
                )
                activities = activities_result.scalars().all()
                
                # Get dependencies
                dependencies_result = await session.execute(
                    select(Dependency).where(Dependency.schedule_id == schedule.id)
                )
                dependencies = dependencies_result.scalars().all()
                
                # Perform analysis
                analysis = await self.analyze_schedule(
                    project, schedule, activities, dependencies
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                await self.log_execution(
                    agent_name="schedule_agent",
                    project_id=project_id,
                    execution_type=execution_type,
                    input_data=input_data,
                    output_data=analysis,
                    execution_time_ms=int(execution_time),
                    status="success"
                )
                
                return analysis
        
        except Exception as e:
            self.logger.error(f"Schedule Agent execution error: {e}", exc_info=True)
            await self.log_execution(
                agent_name="schedule_agent",
                project_id=project_id,
                execution_type=execution_type,
                input_data=input_data,
                output_data={"error": str(e)},
                execution_time_ms=0,
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def analyze_schedule(
        self,
        project: Project,
        schedule: Schedule,
        activities: list,
        dependencies: list
    ) -> Dict[str, Any]:
        """Perform comprehensive schedule analysis"""
        
        # Convert to pandas for analysis
        activities_df = pd.DataFrame([{
            'id': str(a.id),
            'activity_id': a.activity_id,
            'name': a.activity_name,
            'duration': a.original_duration or 0,
            'remaining_duration': a.remaining_duration or 0,
            'percent_complete': float(a.percent_complete) if a.percent_complete else 0,
            'early_start': a.early_start,
            'early_finish': a.early_finish,
            'late_start': a.late_start,
            'late_finish': a.late_finish,
            'is_critical': a.is_critical,
            'is_milestone': a.is_milestone
        } for a in activities])
        
        # Build dependency graph
        G = nx.DiGraph()
        for activity in activities:
            G.add_node(str(activity.id), **{
                'name': activity.activity_name,
                'duration': activity.original_duration or 0,
                'percent_complete': float(activity.percent_complete) if activity.percent_complete else 0
            })
        
        for dep in dependencies:
            G.add_edge(str(dep.predecessor_id), str(dep.successor_id), type=dep.dependency_type)
        
        # Calculate critical path
        critical_path = self.calculate_critical_path(G, activities_df)
        
        # Calculate schedule health
        schedule_health = self.calculate_schedule_health(activities_df, project)
        
        # Predict delays
        delay_prediction = self.predict_delays(activities_df, project, schedule)
        
        # Identify bottlenecks
        bottlenecks = self.identify_bottlenecks(activities_df, G)
        
        # Identify variance activities
        variance_activities = self.identify_variance_activities(activities_df)
        
        # Generate explanation using LLM
        explanation = await self.generate_explanation(
            schedule_health,
            delay_prediction,
            bottlenecks,
            variance_activities,
            critical_path
        )
        
        return {
            "schedule_health_score": schedule_health,
            "critical_activities_count": len(critical_path),
            "delay_prediction_days": delay_prediction,
            "completion_date_estimate": (project.planned_end_date + timedelta(days=delay_prediction)).isoformat() if delay_prediction > 0 else project.planned_end_date.isoformat(),
            "bottlenecks": bottlenecks,
            "variance_activities": variance_activities,
            "critical_path": critical_path,
            "explanation": explanation,
            "total_activities": len(activities),
            "completed_activities": len(activities_df[activities_df['percent_complete'] >= 100]),
            "in_progress_activities": len(activities_df[(activities_df['percent_complete'] > 0) & (activities_df['percent_complete'] < 100)]),
            "not_started_activities": len(activities_df[activities_df['percent_complete'] == 0])
        }
    
    def calculate_critical_path(self, G: nx.DiGraph, activities_df: pd.DataFrame) -> list:
        """Calculate critical path using NetworkX"""
        try:
            # Find longest path (critical path)
            if len(G) == 0:
                return []
            
            # Simple critical path calculation based on duration
            critical_activities = activities_df[activities_df['is_critical'] == True]
            return critical_activities['activity_id'].tolist()
        except Exception as e:
            self.logger.error(f"Critical path calculation error: {e}")
            return []
    
    def calculate_schedule_health(self, activities_df: pd.DataFrame, project: Project) -> float:
        """Calculate overall schedule health score"""
        try:
            if len(activities_df) == 0:
                return 50.0
            
            # Factors affecting schedule health
            avg_completion = activities_df['percent_complete'].mean()
            
            # Expected completion based on time elapsed
            total_days = (project.planned_end_date - project.start_date).days
            elapsed_days = (date.today() - project.start_date).days if project.start_date <= date.today() else 0
            expected_completion = (elapsed_days / total_days * 100) if total_days > 0 else 0
            
            # Variance from expected
            completion_variance = abs(avg_completion - expected_completion)
            
            # Critical activities completion
            critical_activities = activities_df[activities_df['is_critical'] == True]
            if len(critical_activities) > 0:
                critical_completion = critical_activities['percent_complete'].mean()
            else:
                critical_completion = avg_completion
            
            # Calculate health score (0-100)
            health_score = 100 - (completion_variance * 0.5)
            health_score = health_score * (critical_completion / 100) if critical_completion > 0 else health_score
            
            return max(0, min(100, health_score))
        
        except Exception as e:
            self.logger.error(f"Schedule health calculation error: {e}")
            return 50.0
    
    def predict_delays(self, activities_df: pd.DataFrame, project: Project, schedule: Schedule) -> int:
        """Predict project delay in days"""
        try:
            if len(activities_df) == 0:
                return 0
            
            # Calculate average delay based on activity progress
            avg_completion = activities_df['percent_complete'].mean()
            
            total_days = (project.planned_end_date - project.start_date).days
            elapsed_days = (date.today() - project.start_date).days if project.start_date <= date.today() else 0
            
            if elapsed_days == 0:
                return 0
            
            expected_completion = (elapsed_days / total_days * 100)
            
            if avg_completion < expected_completion:
                # Behind schedule
                delay_factor = (expected_completion - avg_completion) / 100
                predicted_delay = int(delay_factor * total_days)
                return predicted_delay
            
            return 0
        
        except Exception as e:
            self.logger.error(f"Delay prediction error: {e}")
            return 0
    
    def identify_bottlenecks(self, activities_df: pd.DataFrame, G: nx.DiGraph) -> list:
        """Identify bottleneck activities"""
        try:
            bottlenecks = []
            
            # Activities with low progress but high centrality in dependency graph
            if len(G) > 0:
                centrality = nx.degree_centrality(G)
                
                for activity_id, centrality_score in centrality.items():
                    activity = activities_df[activities_df['id'] == activity_id]
                    if len(activity) > 0:
                        activity_data = activity.iloc[0]
                        if (activity_data['percent_complete'] < 50 and 
                            centrality_score > 0.5 and
                            not activity_data['is_milestone']):
                            bottlenecks.append({
                                'activity_id': activity_data['activity_id'],
                                'name': activity_data['name'],
                                'centrality': centrality_score,
                                'completion': activity_data['percent_complete']
                            })
            
            return bottlenecks[:10]  # Return top 10 bottlenecks
        
        except Exception as e:
            self.logger.error(f"Bottleneck identification error: {e}")
            return []
    
    def identify_variance_activities(self, activities_df: pd.DataFrame) -> list:
        """Identify activities with significant variance"""
        try:
            variance_activities = []
            
            # Activities with significant deviation from expected progress
            for _, activity in activities_df.iterrows():
                if activity['remaining_duration'] and activity['duration']:
                    variance = (activity['remaining_duration'] / activity['duration']) if activity['duration'] > 0 else 0
                    if variance > 0.5:  # More than 50% remaining when should be done
                        variance_activities.append({
                            'activity_id': activity['activity_id'],
                            'name': activity['name'],
                            'variance': variance,
                            'percent_complete': activity['percent_complete']
                        })
            
            return variance_activities[:10]
        
        except Exception as e:
            self.logger.error(f"Variance identification error: {e}")
            return []
    
    async def generate_explanation(
        self,
        schedule_health: float,
        delay_prediction: int,
        bottlenecks: list,
        variance_activities: list,
        critical_path: list
    ) -> str:
        """Generate AI explanation of schedule analysis"""
        if not self.llm:
            return (
                f"Schedule health is {schedule_health:.1f}/100 with a projected delay of "
                f"{delay_prediction} days. Critical path pressure is concentrated on "
                f"{len(critical_path)} critical activities, with {len(bottlenecks)} active bottlenecks "
                f"and {len(variance_activities)} variance activities requiring recovery action."
            )
        
        prompt = ChatPromptTemplate.from_template(
            """You are a Schedule Intelligence Agent for construction project management.
            
            Analyze the following schedule data and provide a clear explanation:
            
            Schedule Health Score: {health_score}/100
            Predicted Delay: {delay_days} days
            Critical Activities: {critical_count}
            Bottlenecks: {bottlenecks}
            Variance Activities: {variance_count}
            
            Provide a concise explanation of:
            1. Why the schedule health is at this level
            2. What is causing the predicted delay
            3. Which activities are most critical
            4. What immediate actions should be taken
            
            Keep the explanation professional and actionable.
            """
        )
        
        try:
            chain = prompt | self.llm
            result = await asyncio.wait_for(chain.ainvoke({
                "health_score": schedule_health,
                "delay_days": delay_prediction,
                "critical_count": len(critical_path),
                "bottlenecks": str(bottlenecks[:3]),
                "variance_count": len(variance_activities)
            }), timeout=8)
            
            return result.content
        except Exception as e:
            self.logger.error(f"Explanation generation error: {e}")
            return f"Schedule analysis complete. Health: {schedule_health}/100, Predicted delay: {delay_prediction} days."
