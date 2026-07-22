"""
Agent execution endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import AgentExecutionRequest, AgentExecutionResponse
from app.core.security import get_current_user
from app.core.logging import get_logger
from app.agents.supervisor import supervisor_graph
from app.services.notifications import scan_project
from uuid import uuid4
from datetime import datetime


async def _scan_best_effort(project_id: str):
    """Run the notification engine after an agent execution; never let a scan
    failure affect the agent execution response."""
    try:
        await scan_project(project_id)
    except Exception as e:
        logger.error(f"Post-execution notification scan failed: {e}")

router = APIRouter()
logger = get_logger(__name__)


@router.post("/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    execution_request: AgentExecutionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute an agent analysis"""
    try:
        # Route to appropriate agent based on agent_name
        if execution_request.agent_name == "supervisor":
            # Execute supervisor which coordinates all agents
            result = await supervisor_graph.ainvoke({
                "project_id": str(execution_request.project_id),
                "execution_type": execution_request.execution_type,
                "input_data": execution_request.input_data or {},
                "messages": []
            })
        else:
            # Execute specific agent
            result = await execute_specific_agent(execution_request)

        await _scan_best_effort(str(execution_request.project_id))

        return AgentExecutionResponse(
            execution_id=uuid4(),
            agent_name=execution_request.agent_name,
            project_id=execution_request.project_id,
            execution_type=execution_request.execution_type,
            status="success",
            output_data=result,
            execution_time_ms=0,
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


async def execute_specific_agent(execution_request: AgentExecutionRequest):
    """Execute a specific agent based on request"""
    from app.agents.schedule_agent import ScheduleAgent
    from app.agents.procurement_agent import ProcurementAgent
    from app.agents.risk_agent import RiskAgent
    from app.agents.recommendation_agent import RecommendationAgent
    from app.agents.executive_agent import ExecutiveAgent
    
    agents = {
        "schedule_agent": ScheduleAgent(),
        "procurement_agent": ProcurementAgent(),
        "risk_agent": RiskAgent(),
        "recommendation_agent": RecommendationAgent(),
        "executive_agent": ExecutiveAgent()
    }
    
    agent = agents.get(execution_request.agent_name)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown agent: {execution_request.agent_name}"
        )
    
    return await agent.execute(
        project_id=str(execution_request.project_id),
        execution_type=execution_request.execution_type,
        input_data=execution_request.input_data or {}
    )


@router.post("/trigger-all/{project_id}")
async def trigger_all_agents(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Trigger all agents for a project"""
    try:
        # Execute supervisor which coordinates all agents
        result = await supervisor_graph.ainvoke({
            "project_id": project_id,
            "execution_type": "full_analysis",
            "input_data": {},
            "messages": []
        })

        await _scan_best_effort(project_id)

        return {
            "status": "success",
            "project_id": project_id,
            "message": "All agents executed successfully",
            "results": result
        }
    
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )
