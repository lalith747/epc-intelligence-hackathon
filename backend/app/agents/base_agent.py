"""
Base agent class with common functionality
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database import AsyncSessionLocal
from app.core.logging import get_logger
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import get_settings

settings = get_settings()


class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.llm = None
        if settings.google_api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.google_model,
                temperature=settings.google_temperature,
                max_output_tokens=settings.google_max_tokens,
                google_api_key=settings.google_api_key,
                # REST transport fails fast on network/SSL issues instead of
                # gRPC's native SSL stack retrying for minutes before giving up.
                transport="rest",
                max_retries=1
            )
    
    @abstractmethod
    async def execute(self, project_id: str, execution_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's primary function"""
        pass
    
    async def get_db_session(self) -> AsyncSession:
        """Get database session"""
        async with AsyncSessionLocal() as session:
            yield session
    
    async def log_execution(
        self,
        agent_name: str,
        project_id: str,
        execution_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        execution_time_ms: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Log agent execution to database"""
        from app.models.database import AgentLog
        from uuid import uuid4
        
        async with AsyncSessionLocal() as session:
            log_entry = AgentLog(
                id=str(uuid4()),
                agent_name=agent_name,
                project_id=project_id,
                execution_type=execution_type,
                input_data=str(input_data),
                output_data=str(output_data),
                execution_time_ms=execution_time_ms,
                status=status,
                error_message=error_message
            )
            session.add(log_entry)
            await session.commit()
    
    async def store_memory(
        self,
        agent_name: str,
        project_id: str,
        memory_type: str,
        memory_key: str,
        memory_value: str,
        confidence: float = 0.0
    ):
        """Store agent memory"""
        from app.models.database import AgentMemory
        from uuid import uuid4
        
        async with AsyncSessionLocal() as session:
            memory = AgentMemory(
                id=str(uuid4()),
                agent_name=agent_name,
                project_id=project_id,
                memory_type=memory_type,
                memory_key=memory_key,
                memory_value=memory_value,
                confidence=confidence
            )
            session.add(memory)
            await session.commit()
    
    async def retrieve_memory(
        self,
        agent_name: str,
        project_id: str,
        memory_type: str,
        memory_key: Optional[str] = None
    ) -> list:
        """Retrieve agent memory"""
        from app.models.database import AgentMemory
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            query = select(AgentMemory).where(
                AgentMemory.agent_name == agent_name,
                AgentMemory.project_id == project_id,
                AgentMemory.memory_type == memory_type
            )
            
            if memory_key:
                query = query.where(AgentMemory.memory_key == memory_key)
            
            result = await session.execute(query)
            memories = result.scalars().all()
            
            return [
                {
                    "key": m.memory_key,
                    "value": m.memory_value,
                    "confidence": m.confidence
                }
                for m in memories
            ]
