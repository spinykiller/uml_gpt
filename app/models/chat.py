from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageResponse(BaseModel):
    id: int
    role: MessageRole
    content: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class DiagramStateResponse(BaseModel):
    id: int
    diagram_type: str
    current_mermaid: str
    version: int
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: str
    original_prompt: Optional[str]
    created_at: datetime
    last_activity: datetime
    
    class Config:
        from_attributes = True


# API Request Models
class StartChatRequest(BaseModel):
    initial_prompt: str = Field(
        ..., 
        min_length=1, 
        description="Natural language description of the system or process to diagram",
        example="SEBI compliance monitoring system that tracks regulatory requirements"
    )
    diagram_types: List[str] = Field(
        ..., 
        min_items=1, 
        description="List of diagram types to generate (sequential, component, state, class, er, gantt)",
        example=["sequential", "component"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "initial_prompt": "SEBI compliance monitoring system that tracks regulatory requirements and generates reports",
                "diagram_types": ["sequential", "component"]
            }
        }


class ChatMessageRequest(BaseModel):
    message: str = Field(
        ..., 
        min_length=1, 
        description="Natural language instruction for modifying the diagrams",
        example="Add a notification service that alerts users when new regulations are published"
    )
    target_diagrams: Optional[List[str]] = Field(
        None, 
        description="Specific diagram types to modify. If not provided, all diagrams will be updated",
        example=["component"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Add a notification service that alerts users when new regulations are published",
                "target_diagrams": ["component"]
            }
        }


# API Response Models
class StartChatResponse(BaseModel):
    session_id: str
    diagrams: Dict[str, str]  # diagram_type -> mermaid_code
    message: str = "Chat session started. You can now ask for modifications to your diagrams."


class SendMessageResponse(BaseModel):
    session_id: str
    response: str
    updated_diagrams: Dict[str, str]  # Only diagrams that were modified
    all_diagrams: Dict[str, str]  # All current diagrams


class ChatHistoryResponse(BaseModel):
    session_id: str
    session_info: ChatSessionResponse
    messages: List[ChatMessageResponse]
    current_diagrams: List[DiagramStateResponse]


class DiagramEditRequest(BaseModel):
    current_diagram: str
    edit_instruction: str
    conversation_context: List[str]
    diagram_type: str
