"""
Conversation Agent - deterministic project assistant with data citations.
"""
from typing import Any, Dict, List

from sqlalchemy import select

from app.agents.base_agent import BaseAgent
from app.models.database import Activity, Conversation, Project, PurchaseOrder, Risk, Schedule, Supplier
from app.services.database import AsyncSessionLocal


class ConversationAgent(BaseAgent):
    """Conversation Agent for project-aware Q&A without hallucinating."""

    async def respond(
        self,
        user_message: str,
        project_id: str = None,
        session_id: str = None,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """Generate an answer grounded in stored project data."""
        try:
            context = await self.get_conversation_context(session_id, user_id)
            project_data = await self.retrieve_project_data(project_id)
            answer, citations = self.generate_response(user_message, project_data, context)
            return {"message": answer, "context": context, "citations": citations}
        except Exception as exc:
            self.logger.error(f"Conversation Agent error: {exc}", exc_info=True)
            return {
                "message": "I could not complete that analysis from the available project data.",
                "context": [],
                "citations": [],
            }

    async def get_conversation_context(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        """Return recent message history for the same session."""
        if not session_id or not user_id:
            return []

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.created_at.desc())
                .limit(8)
            )
            rows = result.scalars().all()
            return [{"role": row.role, "message": row.message} for row in reversed(list(rows))]

    async def retrieve_project_data(self, project_id: str) -> Dict[str, Any]:
        """Load the most relevant project entities for answering questions."""
        if not project_id:
            return {}

        async with AsyncSessionLocal() as session:
            project = await session.scalar(select(Project).where(Project.id == project_id))
            if not project:
                return {}

            latest_schedule = await session.scalar(
                select(Schedule)
                .where(Schedule.project_id == project_id)
                .order_by(Schedule.created_at.desc())
                .limit(1)
            )

            activities = []
            if latest_schedule:
                activity_rows = await session.execute(
                    select(Activity)
                    .where(Activity.schedule_id == latest_schedule.id)
                    .order_by(Activity.is_critical.desc(), Activity.percent_complete.asc())
                    .limit(20)
                )
                activities = activity_rows.scalars().all()

            risk_rows = await session.execute(
                select(Risk).where(Risk.project_id == project_id).order_by(Risk.risk_score.desc()).limit(10)
            )
            po_rows = await session.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.project_id == project_id)
                .order_by(PurchaseOrder.expected_delivery_date.asc())
                .limit(10)
            )
            supplier_rows = await session.execute(
                select(Supplier).order_by(Supplier.on_time_delivery_rate.asc()).limit(10)
            )

            return {
                "project": project,
                "schedule": latest_schedule,
                "activities": activities,
                "risks": risk_rows.scalars().all(),
                "purchase_orders": po_rows.scalars().all(),
                "suppliers": supplier_rows.scalars().all(),
            }

    def generate_response(
        self,
        user_message: str,
        project_data: Dict[str, Any],
        context: List[Dict[str, str]],
    ) -> tuple[str, List[str]]:
        """Answer common schedule, supplier, and risk questions deterministically."""
        if not project_data:
            return (
                "I do not have enough project data to answer that yet. Select a project or upload schedule and procurement files first.",
                ["project_data"],
            )

        question = user_message.lower()
        project = project_data["project"]
        activities = project_data["activities"]
        risks = project_data["risks"]
        purchase_orders = project_data["purchase_orders"]
        suppliers = project_data["suppliers"]

        if "delay" in question or "delayed" in question:
            critical_open = [a for a in activities if a.is_critical and float(a.percent_complete or 0) < 60]
            top_risk = risks[0] if risks else None
            if critical_open:
                activity_names = ", ".join(a.activity_name for a in critical_open[:3])
                response = (
                    f"{project.name} is under delay pressure because critical activities are lagging, led by {activity_names}. "
                    f"The strongest current schedule signal is low progress on critical-path work."
                )
                citations = ["activities", "project"]
            elif top_risk:
                response = (
                    f"The primary delay driver is {top_risk.title}. "
                    f"It carries a risk score of {float(top_risk.risk_score or 0):.1f} and is classified as {top_risk.severity}."
                )
                citations = ["risks"]
            else:
                response = "The available data does not show a confirmed active delay driver right now."
                citations = ["project"]
            return response, citations

        if "supplier" in question and ("risk" in question or "risky" in question or "delay" in question):
            ranked = sorted(suppliers, key=lambda s: float(s.on_time_delivery_rate or 0))
            if ranked:
                supplier = ranked[0]
                response = (
                    f"The riskiest supplier in the current data is {supplier.name}. "
                    f"Its on-time delivery rate is {float(supplier.on_time_delivery_rate or 0):.0f}% with a rating of {float(supplier.rating or 0):.1f}/5."
                )
                return response, ["suppliers"]

        if "critical path" in question:
            critical = [a for a in activities if a.is_critical]
            if critical:
                names = ", ".join(f"{a.activity_id} {a.activity_name}" for a in critical[:5])
                return f"The current critical path is led by: {names}.", ["activities", "schedule"]

        if "procurement" in question or "delivery" in question or "material" in question:
            late_orders = [
                po for po in purchase_orders
                if po.expected_delivery_date and po.expected_delivery_date < project.planned_end_date and po.status != "delivered"
            ]
            if late_orders:
                order_text = ", ".join(po.po_number for po in late_orders[:3])
                return (
                    f"Procurement health is being pulled down by open orders {order_text}. "
                    f"These are still unresolved against their expected delivery windows."
                ), ["purchase_orders"]
            return "Procurement looks stable in the current dataset with no unresolved late delivery records.", ["purchase_orders"]

        if "health" in question or "status" in question:
            return (
                f"{project.name} is in {project.status} status and is {float(project.progress_percentage or 0):.1f}% complete. "
                f"The current view shows schedule and procurement pressure, but recovery actions are available."
            ), ["project"]

        top_context = context[-1]["message"] if context else "No prior context"
        return (
            f"Based on {project.name}, I can help explain schedule delays, critical activities, supplier risk, procurement health, and current recommendations. "
            f"Your last session context was: {top_context}"
        ), ["project", "conversation"]

    async def execute(self, project_id: str, execution_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility method for the agent registry."""
        return {
            "message": "Use the conversation endpoint for interactive Q&A.",
            "project_id": project_id,
            "execution_type": execution_type,
            "input_data": input_data,
        }
