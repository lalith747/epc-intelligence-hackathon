"""
Celery background tasks
"""
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.celery_app import celery_app
from app.services.database import AsyncSessionLocal
from app.models.database import Project, ProjectHealth
from app.agents.supervisor import supervisor_graph
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_agent_analysis_task():
    """Run agent analysis for all active projects"""
    import asyncio
    
    async def _run_analysis():
        try:
            async with AsyncSessionLocal() as session:
                # Get all active projects
                result = await session.execute(
                    select(Project).where(Project.status == 'active')
                )
                projects = result.scalars().all()
                
                logger.info(f"Running agent analysis for {len(projects)} active projects")
                
                for project in projects:
                    try:
                        # Execute supervisor graph for each project
                        await supervisor_graph.ainvoke({
                            "project_id": str(project.id),
                            "execution_type": "scheduled_analysis",
                            "input_data": {}
                        })
                        logger.info(f"Agent analysis completed for project {project.code}")
                    except Exception as e:
                        logger.error(f"Agent analysis failed for project {project.code}: {e}")
                
                return {"status": "success", "projects_analyzed": len(projects)}
        
        except Exception as e:
            logger.error(f"Agent analysis task error: {e}")
            return {"status": "error", "message": str(e)}
    
    return asyncio.run(_run_analysis())


def update_project_health_task():
    """Update health metrics for all active projects"""
    import asyncio
    
    async def _update_health():
        try:
            async with AsyncSessionLocal() as session:
                # Get all active projects
                result = await session.execute(
                    select(Project).where(Project.status == 'active')
                )
                projects = result.scalars().all()
                
                logger.info(f"Updating health metrics for {len(projects)} active projects")
                
                for project in projects:
                    try:
                        # Calculate health metrics
                        health_metrics = await calculate_project_health(project.id, session)
                        
                        # Check if health record already exists for today
                        existing_result = await session.execute(
                            select(ProjectHealth).where(
                                ProjectHealth.project_id == project.id,
                                ProjectHealth.metric_date == date.today()
                            )
                        )
                        existing_health = existing_result.scalar_one_or_none()
                        
                        if existing_health:
                            # Update existing record
                            for key, value in health_metrics.items():
                                setattr(existing_health, key, value)
                        else:
                            # Create new health record
                            from uuid import uuid4
                            new_health = ProjectHealth(
                                id=uuid4(),
                                project_id=project.id,
                                metric_date=date.today(),
                                **health_metrics
                            )
                            session.add(new_health)
                        
                        await session.commit()
                        logger.info(f"Health metrics updated for project {project.code}")
                    
                    except Exception as e:
                        logger.error(f"Health update failed for project {project.code}: {e}")
                
                return {"status": "success", "projects_updated": len(projects)}
        
        except Exception as e:
            logger.error(f"Health update task error: {e}")
            return {"status": "error", "message": str(e)}
    
    return asyncio.run(_update_health())


def generate_daily_reports_task():
    """Generate daily reports for all active projects"""
    import asyncio
    
    async def _generate_reports():
        try:
            async with AsyncSessionLocal() as session:
                # Get all active projects
                result = await session.execute(
                    select(Project).where(Project.status == 'active')
                )
                projects = result.scalars().all()
                
                logger.info(f"Generating daily reports for {len(projects)} active projects")
                
                for project in projects:
                    try:
                        # Generate executive summary
                        from app.agents.executive_agent import ExecutiveAgent
                        from app.models.database import Report
                        from uuid import uuid4
                        
                        agent = ExecutiveAgent()
                        summary = await agent.execute(
                            project_id=str(project.id),
                            execution_type="daily_report",
                            input_data={}
                        )
                        
                        # Create report record
                        report = Report(
                            id=uuid4(),
                            project_id=project.id,
                            report_type="daily",
                            report_name=f"Daily Report - {project.code}",
                            report_date=date.today(),
                            period_start=date.today(),
                            period_end=date.today(),
                            generated_by_agent="executive_agent",
                            content=summary,
                            summary=summary.get("summary", ""),
                            key_insights=summary.get("key_insights", [])
                        )
                        session.add(report)
                        await session.commit()
                        
                        logger.info(f"Daily report generated for project {project.code}")
                    
                    except Exception as e:
                        logger.error(f"Daily report generation failed for project {project.code}: {e}")
                
                return {"status": "success", "reports_generated": len(projects)}
        
        except Exception as e:
            logger.error(f"Daily report task error: {e}")
            return {"status": "error", "message": str(e)}
    
    return asyncio.run(_generate_reports())


async def calculate_project_health(project_id: str, session: AsyncSession) -> dict:
    """Calculate comprehensive health metrics for a project"""
    from app.models.database import Risk, Recommendation, Activity, Schedule
    
    # Get latest schedule
    schedule_result = await session.execute(
        select(Schedule)
        .where(Schedule.project_id == project_id)
        .order_by(Schedule.created_at.desc())
        .limit(1)
    )
    schedule = schedule_result.scalar_one_or_none()
    
    # Get activities
    activities_result = await session.execute(
        select(Activity).where(Activity.schedule_id == schedule.id)
    )
    activities = activities_result.scalars().all()
    
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
    
    # Calculate metrics
    overall_health = 75.0  # Default
    schedule_health = 75.0
    procurement_health = 75.0
    supplier_health = 75.0
    risk_score = 25.0
    
    if activities:
        avg_completion = sum(a.percent_complete or 0 for a in activities) / len(activities)
        schedule_health = avg_completion
    
    if risks:
        avg_risk_score = sum(r.risk_score or 0 for r in risks) / len(risks)
        risk_score = avg_risk_score
        overall_health = max(0, 100 - risk_score)
    
    # Calculate overall health
    overall_health = (schedule_health * 0.4) + (procurement_health * 0.3) + ((100 - risk_score) * 0.3)
    
    return {
        "overall_health_score": round(overall_health, 2),
        "schedule_health_score": round(schedule_health, 2),
        "procurement_health_score": round(procurement_health, 2),
        "supplier_health_score": round(supplier_health, 2),
        "risk_score": round(risk_score, 2),
        "cost_performance_index": 1.0,
        "schedule_performance_index": 1.0,
        "completion_percentage": round(schedule_health, 2),
        "on_time_activities_percentage": 85.0,
        "on_budget_percentage": 90.0,
        "open_risks_count": len(risks),
        "critical_risks_count": len([r for r in risks if r.severity == 'critical']),
        "open_recommendations_count": len(recommendations)
    }


@celery_app.task(bind=True)
def process_file_upload(self, file_path: str, project_id: str, file_type: str):
    """Process uploaded file in background"""
    import asyncio
    
    async def _process_file():
        try:
            from app.services.file_processor import FileProcessor
            
            processor = FileProcessor()
            result = await processor.process_file(file_path, project_id, file_type)
            
            return {"status": "success", "result": result}
        
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    return asyncio.run(_process_file())
