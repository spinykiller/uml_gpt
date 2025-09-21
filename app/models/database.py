from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT
import enum

Base = declarative_base()


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FeedbackTypeEnum(enum.Enum):
    DIAGRAM_QUALITY = "diagram_quality"
    DIAGRAM_ACCURACY = "diagram_accuracy"
    EDIT_SATISFACTION = "edit_satisfaction"
    OVERALL_EXPERIENCE = "overall_experience"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True)
    original_prompt = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    diagrams = relationship("DiagramState", back_populates="session", cascade="all, delete-orphan")
    
    def is_expired(self, ttl_hours: int = 24) -> bool:
        """Check if session has expired"""
        expiry_time = self.created_at + timedelta(hours=ttl_hours)
        return datetime.utcnow() > expiry_time
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ChatSession", back_populates="messages")


class DiagramState(Base):
    __tablename__ = "diagram_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    diagram_type = Column(String(50), nullable=False)
    current_mermaid = Column(LONGTEXT, nullable=False)
    version = Column(Integer, default=1)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ChatSession", back_populates="diagrams")


class DiagramFeedback(Base):
    __tablename__ = "diagram_feedback"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=True)
    diagram_type = Column(String(50), nullable=False)
    diagram_content = Column(LONGTEXT, nullable=False)
    user_prompt = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5 scale
    feedback_type = Column(Enum(FeedbackTypeEnum), nullable=False)
    comment = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ChatSession")


class GeneralFeedback(Base):
    __tablename__ = "general_feedback"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=True)
    feedback_type = Column(Enum(FeedbackTypeEnum), nullable=False)
    rating = Column(Integer, nullable=True)  # Optional for general feedback
    comment = Column(Text, nullable=False)
    feature_area = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ChatSession")


class UserPreferencesModel(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_identifier = Column(String(100), nullable=False, unique=True)  # Could be IP, session, or user ID
    preferred_diagram_styles = Column(Text, nullable=True)  # JSON string
    common_complaints = Column(Text, nullable=True)  # JSON string
    preferred_detail_level = Column(String(20), default="medium")
    favorite_diagram_types = Column(Text, nullable=True)  # JSON string
    improvement_focus_areas = Column(Text, nullable=True)  # JSON string
    last_updated = Column(DateTime, default=datetime.utcnow)
    feedback_count = Column(Integer, default=0)
    average_rating = Column(Float, nullable=True)
