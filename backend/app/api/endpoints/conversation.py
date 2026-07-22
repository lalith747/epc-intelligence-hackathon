"""
Conversation endpoints for AI assistant
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.models.database import Conversation
from app.models.schemas import ConversationCreate, ConversationResponse
from app.core.security import get_current_user
from app.core.logging import get_logger
from app.agents.conversation_agent import ConversationAgent
from uuid import uuid4

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation message and get AI response"""
    # Generate session ID if not provided
    session_id = conversation_data.session_id or uuid4()
    
    # Save user message
    user_message = Conversation(
        user_id=current_user["user_id"],
        project_id=conversation_data.project_id,
        session_id=session_id,
        message=conversation_data.message,
        role="user"
    )
    db.add(user_message)
    await db.commit()
    
    # Get AI response
    try:
        conversation_agent = ConversationAgent()
        ai_response = await conversation_agent.respond(
            user_message=conversation_data.message,
            project_id=str(conversation_data.project_id) if conversation_data.project_id else None,
            session_id=str(session_id),
            user_id=str(current_user["user_id"])
        )
        
        # Save AI response
        assistant_message = Conversation(
            user_id=current_user["user_id"],
            project_id=conversation_data.project_id,
            session_id=session_id,
            message=ai_response["message"],
            role="assistant",
            context=ai_response.get("context"),
            citations=ai_response.get("citations")
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)
        
        return assistant_message
    
    except Exception as e:
        logger.error(f"Conversation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=List[ConversationResponse])
async def get_conversation_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a session"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .where(Conversation.user_id == current_user["user_id"])
        .order_by(Conversation.created_at.asc())
    )
    conversations = result.scalars().all()
    
    return conversations
