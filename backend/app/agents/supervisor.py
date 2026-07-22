"""
Supervisor agent that coordinates all other agents using LangGraph
"""
from typing import Dict, Any, TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import get_settings
from app.core.logging import get_logger
import operator

settings = get_settings()
logger = get_logger(__name__)


class AgentState(TypedDict):
    """State for the multi-agent system"""
    project_id: str
    execution_type: str
    input_data: Dict[str, Any]
    messages: Annotated[Sequence[str], operator.add]
    schedule_analysis: Dict[str, Any]
    procurement_analysis: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    recommendations: Dict[str, Any]
    executive_summary: Dict[str, Any]
    current_agent: str


class SupervisorAgent:
    """Supervisor agent that coordinates all other agents"""
    
    def __init__(self):
        self.llm = None
        if settings.google_api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.google_model,
                temperature=0.3,
                google_api_key=settings.google_api_key,
                transport="rest",
                max_retries=1
            )
    
    def route_to_next_agent(self, state: AgentState) -> str:
        """Determine which agent should execute next"""
        current = state.get("current_agent", "start")
        
        # Sequential execution order
        agent_sequence = [
            "schedule_agent",
            "procurement_agent", 
            "risk_agent",
            "recommendation_agent",
            "executive_agent",
            "end"
        ]
        
        try:
            current_index = agent_sequence.index(current)
            next_agent = agent_sequence[current_index + 1]
            logger.info(f"Routing from {current} to {next_agent}")
            return next_agent
        except (ValueError, IndexError):
            logger.info("Ending agent sequence")
            return "end"


async def schedule_agent_node(state: AgentState) -> AgentState:
    """Schedule Intelligence Agent node"""
    from app.agents.schedule_agent import ScheduleAgent
    
    logger.info("Executing Schedule Intelligence Agent")
    agent = ScheduleAgent()
    
    try:
        result = await agent.execute(
            project_id=state["project_id"],
            execution_type=state["execution_type"],
            input_data=state["input_data"]
        )
        state["schedule_analysis"] = result
        state["messages"].append(f"Schedule Agent: Analysis completed")
        state["current_agent"] = "schedule_agent"
    except Exception as e:
        logger.error(f"Schedule Agent error: {e}")
        state["schedule_analysis"] = {"error": str(e)}
        state["messages"].append(f"Schedule Agent: Error - {str(e)}")
    
    return state


async def procurement_agent_node(state: AgentState) -> AgentState:
    """Procurement Intelligence Agent node"""
    from app.agents.procurement_agent import ProcurementAgent
    
    logger.info("Executing Procurement Intelligence Agent")
    agent = ProcurementAgent()
    
    try:
        result = await agent.execute(
            project_id=state["project_id"],
            execution_type=state["execution_type"],
            input_data=state["input_data"]
        )
        state["procurement_analysis"] = result
        state["messages"].append(f"Procurement Agent: Analysis completed")
        state["current_agent"] = "procurement_agent"
    except Exception as e:
        logger.error(f"Procurement Agent error: {e}")
        state["procurement_analysis"] = {"error": str(e)}
        state["messages"].append(f"Procurement Agent: Error - {str(e)}")
    
    return state


async def risk_agent_node(state: AgentState) -> AgentState:
    """Risk Assessment Agent node"""
    from app.agents.risk_agent import RiskAgent
    
    logger.info("Executing Risk Assessment Agent")
    agent = RiskAgent()
    
    try:
        result = await agent.execute(
            project_id=state["project_id"],
            execution_type=state["execution_type"],
            input_data=state["input_data"],
            schedule_data=state.get("schedule_analysis", {}),
            procurement_data=state.get("procurement_analysis", {})
        )
        state["risk_analysis"] = result
        state["messages"].append(f"Risk Agent: Analysis completed")
        state["current_agent"] = "risk_agent"
    except Exception as e:
        logger.error(f"Risk Agent error: {e}")
        state["risk_analysis"] = {"error": str(e)}
        state["messages"].append(f"Risk Agent: Error - {str(e)}")
    
    return state


async def recommendation_agent_node(state: AgentState) -> AgentState:
    """Recommendation Agent node"""
    from app.agents.recommendation_agent import RecommendationAgent
    
    logger.info("Executing Recommendation Agent")
    agent = RecommendationAgent()
    
    try:
        result = await agent.execute(
            project_id=state["project_id"],
            execution_type=state["execution_type"],
            input_data=state["input_data"],
            schedule_data=state.get("schedule_analysis", {}),
            procurement_data=state.get("procurement_analysis", {}),
            risk_data=state.get("risk_analysis", {})
        )
        state["recommendations"] = result
        state["messages"].append(f"Recommendation Agent: Analysis completed")
        state["current_agent"] = "recommendation_agent"
    except Exception as e:
        logger.error(f"Recommendation Agent error: {e}")
        state["recommendations"] = {"error": str(e)}
        state["messages"].append(f"Recommendation Agent: Error - {str(e)}")
    
    return state


async def executive_agent_node(state: AgentState) -> AgentState:
    """Executive Summary Agent node"""
    from app.agents.executive_agent import ExecutiveAgent
    
    logger.info("Executing Executive Summary Agent")
    agent = ExecutiveAgent()
    
    try:
        result = await agent.execute(
            project_id=state["project_id"],
            execution_type=state["execution_type"],
            input_data=state["input_data"],
            schedule_data=state.get("schedule_analysis", {}),
            procurement_data=state.get("procurement_analysis", {}),
            risk_data=state.get("risk_analysis", {}),
            recommendations=state.get("recommendations", {})
        )
        state["executive_summary"] = result
        state["messages"].append(f"Executive Agent: Summary completed")
        state["current_agent"] = "executive_agent"
    except Exception as e:
        logger.error(f"Executive Agent error: {e}")
        state["executive_summary"] = {"error": str(e)}
        state["messages"].append(f"Executive Agent: Error - {str(e)}")
    
    return state


# Build the LangGraph
def build_supervisor_graph():
    """Build the supervisor graph with all agents"""
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes for each agent
    workflow.add_node("schedule_agent", schedule_agent_node)
    workflow.add_node("procurement_agent", procurement_agent_node)
    workflow.add_node("risk_agent", risk_agent_node)
    workflow.add_node("recommendation_agent", recommendation_agent_node)
    workflow.add_node("executive_agent", executive_agent_node)
    
    # Set entry point
    workflow.set_entry_point("schedule_agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "schedule_agent",
        lambda state: "procurement_agent" if state.get("schedule_analysis") else END,
        {"procurement_agent": "procurement_agent", END: END}
    )

    workflow.add_conditional_edges(
        "procurement_agent",
        lambda state: "risk_agent" if state.get("procurement_analysis") else END,
        {"risk_agent": "risk_agent", END: END}
    )

    workflow.add_conditional_edges(
        "risk_agent",
        lambda state: "recommendation_agent" if state.get("risk_analysis") else END,
        {"recommendation_agent": "recommendation_agent", END: END}
    )

    workflow.add_conditional_edges(
        "recommendation_agent",
        lambda state: "executive_agent" if state.get("recommendations") else END,
        {"executive_agent": "executive_agent", END: END}
    )

    workflow.add_edge("executive_agent", END)
    
    # Compile the graph
    return workflow.compile()


# Create the supervisor graph instance
supervisor_graph = build_supervisor_graph()
