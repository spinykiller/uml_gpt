import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.database import DiagramFeedback, GeneralFeedback, UserPreferencesModel, FeedbackTypeEnum
from app.models.feedback import (
    DiagramFeedbackRequest, GeneralFeedbackRequest, FeedbackResponse,
    FeedbackSummaryResponse, UserPreferences, FeedbackHistoryResponse
)


class FeedbackService:
    def __init__(self, db: Session):
        self.db = db
    
    def submit_diagram_feedback(self, request: DiagramFeedbackRequest, user_identifier: str = None) -> FeedbackResponse:
        """Submit feedback for a specific diagram."""
        feedback_id = str(uuid.uuid4())
        
        # Create feedback record
        db_feedback = DiagramFeedback(
            id=feedback_id,
            session_id=request.session_id,
            diagram_type=request.diagram_type,
            diagram_content=request.diagram_content,
            user_prompt=request.user_prompt,
            rating=request.rating.value,
            feedback_type=FeedbackTypeEnum(request.feedback_type.value),
            comment=request.comment,
            improvement_suggestions=request.improvement_suggestions
        )
        
        self.db.add(db_feedback)
        
        # Update user preferences if user_identifier is provided
        if user_identifier:
            self._update_user_preferences(user_identifier, request)
        
        self.db.commit()
        
        # Analyze feedback for suggestions
        suggestions_applied = self._analyze_feedback_for_suggestions(request)
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            suggestions_applied=suggestions_applied
        )
    
    def submit_general_feedback(self, request: GeneralFeedbackRequest, user_identifier: str = None) -> FeedbackResponse:
        """Submit general feedback about the system."""
        feedback_id = str(uuid.uuid4())
        
        # Create feedback record
        db_feedback = GeneralFeedback(
            id=feedback_id,
            session_id=request.session_id,
            feedback_type=FeedbackTypeEnum(request.feedback_type.value),
            rating=request.rating.value if request.rating else None,
            comment=request.comment,
            feature_area=request.feature_area
        )
        
        self.db.add(db_feedback)
        self.db.commit()
        
        return FeedbackResponse(feedback_id=feedback_id)
    
    def get_feedback_summary(self, days: int = 30) -> FeedbackSummaryResponse:
        """Get summary of feedback over the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get diagram feedback stats
        diagram_feedback = self.db.query(DiagramFeedback).filter(
            DiagramFeedback.created_at >= cutoff_date
        ).all()
        
        total_count = len(diagram_feedback)
        
        if total_count == 0:
            return FeedbackSummaryResponse(
                total_feedback_count=0,
                average_rating=0.0,
                rating_distribution={},
                common_suggestions=[],
                improvement_areas=[],
                recent_feedback_trends={}
            )
        
        # Calculate rating distribution and average
        ratings = [f.rating for f in diagram_feedback]
        average_rating = sum(ratings) / len(ratings)
        
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[str(i)] = ratings.count(i)
        
        # Extract common suggestions and improvement areas
        common_suggestions = self._extract_common_suggestions(diagram_feedback)
        improvement_areas = self._extract_improvement_areas(diagram_feedback)
        
        # Recent trends
        recent_trends = self._analyze_recent_trends(diagram_feedback)
        
        return FeedbackSummaryResponse(
            total_feedback_count=total_count,
            average_rating=round(average_rating, 2),
            rating_distribution=rating_distribution,
            common_suggestions=common_suggestions,
            improvement_areas=improvement_areas,
            recent_feedback_trends=recent_trends
        )
    
    def get_user_preferences(self, user_identifier: str) -> Optional[UserPreferences]:
        """Get user preferences based on feedback history."""
        db_prefs = self.db.query(UserPreferencesModel).filter(
            UserPreferencesModel.user_identifier == user_identifier
        ).first()
        
        if not db_prefs:
            return None
        
        return UserPreferences(
            preferred_diagram_styles=json.loads(db_prefs.preferred_diagram_styles or "[]"),
            common_complaints=json.loads(db_prefs.common_complaints or "[]"),
            preferred_detail_level=db_prefs.preferred_detail_level,
            favorite_diagram_types=json.loads(db_prefs.favorite_diagram_types or "[]"),
            improvement_focus_areas=json.loads(db_prefs.improvement_focus_areas or "[]")
        )
    
    def get_feedback_for_adaptation(self, diagram_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent feedback for LLM adaptation."""
        query = self.db.query(DiagramFeedback)
        
        if diagram_type:
            query = query.filter(DiagramFeedback.diagram_type == diagram_type)
        
        recent_feedback = query.filter(
            DiagramFeedback.rating <= 3  # Focus on feedback that needs improvement
        ).order_by(desc(DiagramFeedback.created_at)).limit(limit).all()
        
        return [
            {
                "diagram_type": f.diagram_type,
                "rating": f.rating,
                "comment": f.comment,
                "improvement_suggestions": f.improvement_suggestions,
                "user_prompt": f.user_prompt,
                "created_at": f.created_at.isoformat()
            }
            for f in recent_feedback
        ]
    
    def _update_user_preferences(self, user_identifier: str, request: DiagramFeedbackRequest):
        """Update user preferences based on feedback."""
        # Get or create user preferences
        db_prefs = self.db.query(UserPreferencesModel).filter(
            UserPreferencesModel.user_identifier == user_identifier
        ).first()
        
        if not db_prefs:
            db_prefs = UserPreferencesModel(
                user_identifier=user_identifier,
                preferred_diagram_styles="[]",
                common_complaints="[]",
                favorite_diagram_types="[]",
                improvement_focus_areas="[]"
            )
            self.db.add(db_prefs)
        
        # Update preferences based on feedback
        favorite_types = json.loads(db_prefs.favorite_diagram_types or "[]")
        complaints = json.loads(db_prefs.common_complaints or "[]")
        focus_areas = json.loads(db_prefs.improvement_focus_areas or "[]")
        
        # If rating is high, add to favorites
        if request.rating.value >= 4:
            if request.diagram_type not in favorite_types:
                favorite_types.append(request.diagram_type)
        
        # If rating is low, track complaints
        if request.rating.value <= 2 and request.comment:
            complaints.append(request.comment)
            # Keep only recent complaints (last 10)
            complaints = complaints[-10:]
        
        # Track improvement suggestions
        if request.improvement_suggestions:
            focus_areas.append(request.improvement_suggestions)
            focus_areas = focus_areas[-10:]  # Keep recent suggestions
        
        # Update database
        db_prefs.favorite_diagram_types = json.dumps(favorite_types)
        db_prefs.common_complaints = json.dumps(complaints)
        db_prefs.improvement_focus_areas = json.dumps(focus_areas)
        db_prefs.feedback_count = (db_prefs.feedback_count or 0) + 1
        db_prefs.last_updated = datetime.utcnow()
        
        # Update average rating
        avg_rating = self.db.query(func.avg(DiagramFeedback.rating)).filter(
            DiagramFeedback.session_id.in_(
                self.db.query(DiagramFeedback.session_id).distinct()
            )
        ).scalar()
        
        db_prefs.average_rating = float(avg_rating) if avg_rating else request.rating.value
    
    def _analyze_feedback_for_suggestions(self, request: DiagramFeedbackRequest) -> List[str]:
        """Analyze feedback and return applicable suggestions."""
        suggestions = []
        
        if request.rating.value <= 2:
            suggestions.append("Low rating feedback will be used to improve future diagram generation")
        
        if request.improvement_suggestions:
            suggestions.append("Your improvement suggestions have been noted for future enhancements")
        
        if request.feedback_type.value == "diagram_accuracy":
            suggestions.append("Accuracy feedback will help improve diagram content relevance")
        
        return suggestions
    
    def _extract_common_suggestions(self, feedback_list: List[DiagramFeedback]) -> List[str]:
        """Extract common suggestions from feedback."""
        suggestions = []
        
        for feedback in feedback_list:
            if feedback.improvement_suggestions:
                suggestions.append(feedback.improvement_suggestions)
        
        # Simple frequency analysis (in a real system, you'd use NLP)
        suggestion_words = {}
        for suggestion in suggestions:
            words = suggestion.lower().split()
            for word in words:
                if len(word) > 3:  # Filter short words
                    suggestion_words[word] = suggestion_words.get(word, 0) + 1
        
        # Return top suggestions
        sorted_suggestions = sorted(suggestion_words.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_suggestions[:5]]
    
    def _extract_improvement_areas(self, feedback_list: List[DiagramFeedback]) -> List[str]:
        """Extract improvement areas from feedback."""
        low_rating_feedback = [f for f in feedback_list if f.rating <= 2]
        
        areas = []
        diagram_type_issues = {}
        
        for feedback in low_rating_feedback:
            diagram_type_issues[feedback.diagram_type] = diagram_type_issues.get(feedback.diagram_type, 0) + 1
        
        # Identify problematic diagram types
        for diagram_type, count in diagram_type_issues.items():
            if count >= 2:  # Multiple complaints about same type
                areas.append(f"{diagram_type} diagram quality")
        
        return areas
    
    def _analyze_recent_trends(self, feedback_list: List[DiagramFeedback]) -> Dict[str, Any]:
        """Analyze recent feedback trends."""
        if not feedback_list:
            return {}
        
        # Group by week
        weekly_ratings = {}
        for feedback in feedback_list:
            week_key = feedback.created_at.strftime("%Y-W%U")
            if week_key not in weekly_ratings:
                weekly_ratings[week_key] = []
            weekly_ratings[week_key].append(feedback.rating)
        
        # Calculate weekly averages
        weekly_averages = {
            week: sum(ratings) / len(ratings)
            for week, ratings in weekly_ratings.items()
        }
        
        return {
            "weekly_rating_trend": weekly_averages,
            "total_feedback_this_period": len(feedback_list),
            "improvement_trend": "improving" if len(weekly_averages) > 1 and 
                               list(weekly_averages.values())[-1] > list(weekly_averages.values())[0] 
                               else "stable"
        }
