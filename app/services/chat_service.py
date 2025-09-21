import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import ChatSession, ChatMessage, DiagramState, MessageRole
from app.models.chat import (
    StartChatRequest, ChatMessageRequest, StartChatResponse, 
    SendMessageResponse, ChatHistoryResponse, ChatSessionResponse,
    ChatMessageResponse, DiagramStateResponse
)


class ChatService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_chat_session(self, request: StartChatRequest, initial_diagrams: Dict[str, str]) -> StartChatResponse:
        """Create a new chat session with initial diagrams"""
        # Create session
        session_id = str(uuid.uuid4())
        db_session = ChatSession(
            id=session_id,
            original_prompt=request.initial_prompt
        )
        self.db.add(db_session)
        
        # Add initial system message
        system_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=f"Created diagrams for: {', '.join(request.diagram_types)}"
        )
        self.db.add(system_message)
        
        # Store initial diagrams
        for diagram_type, mermaid_code in initial_diagrams.items():
            diagram_state = DiagramState(
                session_id=session_id,
                diagram_type=diagram_type,
                current_mermaid=mermaid_code,
                version=1
            )
            self.db.add(diagram_state)
        
        self.db.commit()
        
        return StartChatResponse(
            session_id=session_id,
            diagrams=initial_diagrams
        )
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by ID"""
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    def add_user_message(self, session_id: str, message: str) -> ChatMessage:
        """Add user message to session"""
        db_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=message
        )
        self.db.add(db_message)
        
        # Update session activity
        session = self.get_session(session_id)
        if session:
            session.update_activity()
        
        self.db.commit()
        return db_message
    
    def add_assistant_message(self, session_id: str, content: str) -> ChatMessage:
        """Add assistant message to session"""
        db_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content
        )
        self.db.add(db_message)
        
        # Update session activity
        session = self.get_session(session_id)
        if session:
            session.update_activity()
        
        self.db.commit()
        return db_message
    
    def update_diagram(self, session_id: str, diagram_type: str, mermaid_code: str) -> DiagramState:
        """Update or create diagram in session"""
        # Try to find existing diagram
        existing = self.db.query(DiagramState).filter(
            DiagramState.session_id == session_id,
            DiagramState.diagram_type == diagram_type
        ).first()
        
        if existing:
            existing.current_mermaid = mermaid_code
            existing.version += 1
            existing.last_updated = datetime.utcnow()
            diagram_state = existing
        else:
            diagram_state = DiagramState(
                session_id=session_id,
                diagram_type=diagram_type,
                current_mermaid=mermaid_code,
                version=1
            )
            self.db.add(diagram_state)
        
        self.db.commit()
        return diagram_state
    
    def get_session_diagrams(self, session_id: str) -> Dict[str, str]:
        """Get all current diagrams for a session"""
        diagrams = self.db.query(DiagramState).filter(
            DiagramState.session_id == session_id
        ).all()
        
        return {d.diagram_type: d.current_mermaid for d in diagrams}
    
    def get_conversation_context(self, session_id: str, limit: int = 5) -> List[str]:
        """Get recent conversation context"""
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(desc(ChatMessage.timestamp)).limit(limit).all()
        
        # Reverse to get chronological order
        messages.reverse()
        return [msg.content for msg in messages]
    
    def get_chat_history(self, session_id: str) -> Optional[ChatHistoryResponse]:
        """Get complete chat history for a session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Get messages
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()
        
        # Get current diagrams
        diagrams = self.db.query(DiagramState).filter(
            DiagramState.session_id == session_id
        ).all()
        
        return ChatHistoryResponse(
            session_id=session_id,
            session_info=ChatSessionResponse.from_orm(session),
            messages=[ChatMessageResponse.from_orm(msg) for msg in messages],
            current_diagrams=[DiagramStateResponse.from_orm(diag) for diag in diagrams]
        )
    
    def cleanup_expired_sessions(self, ttl_hours: int = 24):
        """Remove expired sessions"""
        cutoff_time = datetime.utcnow() - timedelta(hours=ttl_hours)
        
        expired_sessions = self.db.query(ChatSession).filter(
            ChatSession.created_at < cutoff_time
        ).all()
        
        for session in expired_sessions:
            self.db.delete(session)
        
        self.db.commit()
        return len(expired_sessions)
