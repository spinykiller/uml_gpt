from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.feedback_service import FeedbackService
from app.services.feedback_adapter import FeedbackAdapter
from app.models.feedback import (
    DiagramFeedbackRequest, GeneralFeedbackRequest, FeedbackResponse,
    FeedbackSummaryResponse
)

router = APIRouter(prefix="/feedback", tags=["Feedback System"])


@router.post(
    "/diagram",
    response_model=FeedbackResponse,
    summary="Submit diagram feedback",
    description="""
    Submit feedback for a specific diagram to help improve future generations.
    
    **Feedback helps the system learn:**
    - Low ratings trigger improvements for similar diagrams
    - Comments and suggestions are incorporated into future prompts
    - User preferences are learned and applied to subsequent generations
    - System adapts to provide better diagrams over time
    
    **Rating Scale:**
    - 1: Very Poor - Major issues, unusable
    - 2: Poor - Significant problems, needs major improvements  
    - 3: Average - Acceptable but could be better
    - 4: Good - Minor improvements needed
    - 5: Excellent - Perfect, exactly what was needed
    
    **Pro Tips:**
    - Be specific in comments about what could be improved
    - Use improvement_suggestions for actionable feedback
    - Include the original prompt for context
    """,
    responses={
        200: {
            "description": "Feedback submitted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "feedback_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                        "message": "Thank you for your feedback! We'll use it to improve the system.",
                        "suggestions_applied": [
                            "Low rating feedback will be used to improve future diagram generation",
                            "Your improvement suggestions have been noted for future enhancements"
                        ]
                    }
                }
            }
        }
    }
)
async def submit_diagram_feedback(
    request: DiagramFeedbackRequest,
    db: Session = Depends(get_db),
    user_ip: str = None  # In a real app, you'd get this from the request
) -> FeedbackResponse:
    """Submit feedback for a diagram to improve future generations."""
    feedback_service = FeedbackService(db)
    
    # Use IP address as user identifier (in production, use proper user auth)
    user_identifier = user_ip or "anonymous"
    
    return feedback_service.submit_diagram_feedback(request, user_identifier)


@router.post(
    "/general",
    response_model=FeedbackResponse,
    summary="Submit general feedback",
    description="""
    Submit general feedback about the system, features, or overall experience.
    
    **Feedback Types:**
    - `feature_request`: Suggest new features or capabilities
    - `bug_report`: Report issues or problems
    - `overall_experience`: General satisfaction feedback
    - `edit_satisfaction`: Feedback about chat-based editing
    
    **Use this for:**
    - Feature requests and suggestions
    - Bug reports and issues
    - General system feedback
    - User experience improvements
    """,
    responses={
        200: {
            "description": "Feedback submitted successfully"
        }
    }
)
async def submit_general_feedback(
    request: GeneralFeedbackRequest,
    db: Session = Depends(get_db)
) -> FeedbackResponse:
    """Submit general feedback about the system."""
    feedback_service = FeedbackService(db)
    return feedback_service.submit_general_feedback(request)


@router.get(
    "/summary",
    response_model=FeedbackSummaryResponse,
    summary="Get feedback summary and analytics",
    description="""
    Get comprehensive feedback analytics and trends.
    
    **Includes:**
    - Total feedback count and average ratings
    - Rating distribution (1-5 stars)
    - Common improvement suggestions
    - Areas needing attention
    - Recent feedback trends and patterns
    
    **Useful for:**
    - Understanding system performance
    - Identifying improvement priorities
    - Tracking user satisfaction trends
    - Making data-driven enhancements
    """,
    responses={
        200: {
            "description": "Feedback summary retrieved successfully"
        }
    }
)
async def get_feedback_summary(
    days: int = 30,
    db: Session = Depends(get_db)
) -> FeedbackSummaryResponse:
    """Get feedback summary and analytics."""
    feedback_service = FeedbackService(db)
    return feedback_service.get_feedback_summary(days)


@router.get(
    "/adaptation/{user_identifier}",
    summary="Get personalization summary",
    description="""
    See how the system is adapting to your feedback and preferences.
    
    **Shows:**
    - Personal preference adaptations
    - How your feedback is being applied
    - System learning from your usage patterns
    - Customizations based on your ratings
    
    **Privacy Note:**
    - User identifier can be any string (IP, session ID, etc.)
    - No personal information is stored
    - Only diagram preferences and feedback patterns
    """,
    responses={
        200: {
            "description": "Adaptation summary retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "adaptation_summary": "Based on 5 recent feedback items (avg rating: 4.2/5), I'm focusing on: sequential diagram quality. For you specifically, I'm optimizing for: detail level (high), favorite types (sequential, component)"
                    }
                }
            }
        }
    }
)
async def get_adaptation_summary(
    user_identifier: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Get how the system is adapting based on user feedback."""
    feedback_service = FeedbackService(db)
    feedback_adapter = FeedbackAdapter(feedback_service)
    
    adaptation_summary = feedback_adapter.get_adaptation_summary(user_identifier)
    
    return {"adaptation_summary": adaptation_summary}
