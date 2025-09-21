from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class FeedbackType(str, Enum):
    DIAGRAM_QUALITY = "diagram_quality"
    DIAGRAM_ACCURACY = "diagram_accuracy"
    EDIT_SATISFACTION = "edit_satisfaction"
    OVERALL_EXPERIENCE = "overall_experience"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


class FeedbackRating(int, Enum):
    VERY_POOR = 1
    POOR = 2
    AVERAGE = 3
    GOOD = 4
    EXCELLENT = 5


class DiagramFeedbackRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Chat session ID if providing feedback on chat-generated diagram")
    diagram_type: str = Field(..., description="Type of diagram being rated")
    diagram_content: str = Field(..., description="The Mermaid diagram content being rated")
    rating: FeedbackRating = Field(..., description="Rating from 1 (Very Poor) to 5 (Excellent)")
    feedback_type: FeedbackType = Field(default=FeedbackType.DIAGRAM_QUALITY, description="Type of feedback")
    comment: Optional[str] = Field(None, description="Additional comments or suggestions")
    user_prompt: Optional[str] = Field(None, description="Original prompt that generated this diagram")
    improvement_suggestions: Optional[str] = Field(None, description="Specific suggestions for improvement")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a805700f-73b2-4125-8920-52623884babd",
                "diagram_type": "sequential",
                "diagram_content": "sequenceDiagram\\n    participant A\\n    A->>B: Message",
                "rating": 4,
                "feedback_type": "diagram_quality",
                "comment": "Good diagram but could use more detailed labels",
                "user_prompt": "Create a simple communication flow",
                "improvement_suggestions": "Add more descriptive participant names"
            }
        }


class GeneralFeedbackRequest(BaseModel):
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    rating: Optional[FeedbackRating] = Field(None, description="Overall rating if applicable")
    comment: str = Field(..., description="Feedback comment or suggestion")
    session_id: Optional[str] = Field(None, description="Related session if applicable")
    feature_area: Optional[str] = Field(None, description="Specific feature or area of feedback")
    
    class Config:
        json_schema_extra = {
            "example": {
                "feedback_type": "feature_request",
                "comment": "Would love to see support for mind maps",
                "feature_area": "diagram_types"
            }
        }


class FeedbackResponse(BaseModel):
    feedback_id: str
    message: str = "Thank you for your feedback! We'll use it to improve the system."
    suggestions_applied: Optional[List[str]] = None


class FeedbackSummaryResponse(BaseModel):
    total_feedback_count: int
    average_rating: float
    rating_distribution: Dict[str, int]  # "1": count, "2": count, etc.
    common_suggestions: List[str]
    improvement_areas: List[str]
    recent_feedback_trends: Dict[str, Any]


class UserPreferences(BaseModel):
    """User preferences derived from feedback history"""
    preferred_diagram_styles: List[str] = []
    common_complaints: List[str] = []
    preferred_detail_level: str = "medium"  # low, medium, high
    favorite_diagram_types: List[str] = []
    improvement_focus_areas: List[str] = []


# API Response Models
class FeedbackHistoryResponse(BaseModel):
    session_id: Optional[str]
    feedback_items: List[Dict[str, Any]]
    user_preferences: Optional[UserPreferences]
    adaptation_summary: Optional[str]
