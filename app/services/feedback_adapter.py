from typing import List, Dict, Any, Optional
from app.services.feedback_service import FeedbackService
from app.models.feedback import UserPreferences


class FeedbackAdapter:
    """Adapts LLM prompts based on user feedback and preferences."""
    
    def __init__(self, feedback_service: FeedbackService):
        self.feedback_service = feedback_service
    
    def enhance_generation_prompt(self, base_prompt: str, diagram_type: str, 
                                user_identifier: str = None) -> str:
        """Enhance the generation prompt with feedback-based improvements."""
        
        # Get user preferences if available
        user_prefs = None
        if user_identifier:
            user_prefs = self.feedback_service.get_user_preferences(user_identifier)
        
        # Get recent feedback for this diagram type
        recent_feedback = self.feedback_service.get_feedback_for_adaptation(
            diagram_type=diagram_type, limit=5
        )
        
        # Build enhanced prompt
        enhanced_prompt = base_prompt
        
        # Add user preference adaptations
        if user_prefs:
            enhanced_prompt += self._add_user_preference_guidance(user_prefs, diagram_type)
        
        # Add feedback-based improvements
        if recent_feedback:
            enhanced_prompt += self._add_feedback_improvements(recent_feedback, diagram_type)
        
        return enhanced_prompt
    
    def enhance_edit_prompt(self, base_prompt: str, diagram_type: str, 
                          edit_instruction: str, user_identifier: str = None) -> str:
        """Enhance the edit prompt with feedback-based improvements."""
        
        # Get user preferences
        user_prefs = None
        if user_identifier:
            user_prefs = self.feedback_service.get_user_preferences(user_identifier)
        
        enhanced_prompt = base_prompt
        
        # Add user-specific editing preferences
        if user_prefs:
            enhanced_prompt += self._add_edit_preference_guidance(user_prefs, edit_instruction)
        
        # Add common editing improvements from feedback
        edit_feedback = self.feedback_service.get_feedback_for_adaptation(
            diagram_type=diagram_type, limit=3
        )
        
        if edit_feedback:
            enhanced_prompt += self._add_edit_feedback_guidance(edit_feedback)
        
        return enhanced_prompt
    
    def get_adaptation_summary(self, user_identifier: str = None) -> str:
        """Get a summary of how the system is adapting based on feedback."""
        
        summary_parts = []
        
        # Global feedback summary
        feedback_summary = self.feedback_service.get_feedback_summary(days=7)
        
        if feedback_summary.total_feedback_count > 0:
            summary_parts.append(
                f"Based on {feedback_summary.total_feedback_count} recent feedback items "
                f"(avg rating: {feedback_summary.average_rating}/5), "
                f"I'm focusing on: {', '.join(feedback_summary.improvement_areas[:3])}"
            )
        
        # User-specific adaptations
        if user_identifier:
            user_prefs = self.feedback_service.get_user_preferences(user_identifier)
            if user_prefs:
                summary_parts.append(
                    f"For you specifically, I'm optimizing for: "
                    f"detail level ({user_prefs.preferred_detail_level}), "
                    f"favorite types ({', '.join(user_prefs.favorite_diagram_types[:2])})"
                )
        
        return " ".join(summary_parts) if summary_parts else "Learning from your feedback to improve!"
    
    def _add_user_preference_guidance(self, user_prefs: UserPreferences, diagram_type: str) -> str:
        """Add user preference guidance to the prompt."""
        guidance = "\n\nUSER PREFERENCE ADAPTATIONS:\n"
        
        # Detail level preference
        detail_guidance = {
            "low": "Keep the diagram simple and minimal with essential elements only.",
            "medium": "Include moderate detail with clear labels and logical flow.",
            "high": "Provide comprehensive detail with extensive labels, notes, and explanations."
        }
        
        guidance += f"- Detail Level: {detail_guidance.get(user_prefs.preferred_detail_level, detail_guidance['medium'])}\n"
        
        # Favorite diagram types (user has shown preference for these)
        if diagram_type in user_prefs.favorite_diagram_types:
            guidance += f"- This user particularly likes {diagram_type} diagrams - make it especially good!\n"
        
        # Address common complaints
        if user_prefs.common_complaints:
            guidance += "- Address these common user concerns: "
            guidance += ", ".join(user_prefs.common_complaints[-3:]) + "\n"
        
        # Focus areas from improvement suggestions
        if user_prefs.improvement_focus_areas:
            guidance += "- Incorporate these improvement areas: "
            guidance += ", ".join(user_prefs.improvement_focus_areas[-3:]) + "\n"
        
        return guidance
    
    def _add_feedback_improvements(self, recent_feedback: List[Dict[str, Any]], diagram_type: str) -> str:
        """Add improvements based on recent feedback."""
        if not recent_feedback:
            return ""
        
        guidance = f"\n\nRECENT FEEDBACK IMPROVEMENTS FOR {diagram_type.upper()} DIAGRAMS:\n"
        
        # Collect improvement suggestions
        suggestions = []
        common_issues = []
        
        for feedback in recent_feedback:
            if feedback.get("improvement_suggestions"):
                suggestions.append(feedback["improvement_suggestions"])
            
            if feedback.get("comment") and feedback.get("rating", 5) <= 2:
                common_issues.append(feedback["comment"])
        
        # Add specific improvements
        if suggestions:
            guidance += "- Recent improvement suggestions to incorporate:\n"
            for suggestion in suggestions[-3:]:  # Last 3 suggestions
                guidance += f"  * {suggestion}\n"
        
        # Address common issues
        if common_issues:
            guidance += "- Address these recent issues:\n"
            for issue in common_issues[-2:]:  # Last 2 issues
                guidance += f"  * Avoid: {issue}\n"
        
        # General quality improvements
        avg_rating = sum(f.get("rating", 5) for f in recent_feedback) / len(recent_feedback)
        if avg_rating < 3:
            guidance += f"- IMPORTANT: Recent {diagram_type} diagrams have low ratings ({avg_rating:.1f}/5). "
            guidance += "Focus extra attention on quality, accuracy, and user requirements.\n"
        
        return guidance
    
    def _add_edit_preference_guidance(self, user_prefs: UserPreferences, edit_instruction: str) -> str:
        """Add user-specific editing preferences."""
        guidance = "\n\nUSER EDITING PREFERENCES:\n"
        
        # Check if edit instruction relates to user's common complaints
        edit_lower = edit_instruction.lower()
        for complaint in user_prefs.common_complaints[-3:]:
            if any(word in edit_lower for word in complaint.lower().split()[:3]):
                guidance += f"- This edit relates to a previous concern: {complaint}\n"
                guidance += "- Pay special attention to addressing this properly.\n"
                break
        
        # Apply detail level to edits
        if user_prefs.preferred_detail_level == "high":
            guidance += "- This user prefers detailed diagrams - add comprehensive labels and explanations.\n"
        elif user_prefs.preferred_detail_level == "low":
            guidance += "- This user prefers simple diagrams - keep additions minimal and clean.\n"
        
        return guidance
    
    def _add_edit_feedback_guidance(self, edit_feedback: List[Dict[str, Any]]) -> str:
        """Add guidance based on edit-related feedback."""
        if not edit_feedback:
            return ""
        
        guidance = "\n\nEDIT IMPROVEMENT GUIDANCE:\n"
        
        # Look for edit-specific feedback
        edit_suggestions = []
        for feedback in edit_feedback:
            if feedback.get("improvement_suggestions"):
                suggestion = feedback["improvement_suggestions"]
                if any(word in suggestion.lower() for word in ["edit", "change", "modify", "update"]):
                    edit_suggestions.append(suggestion)
        
        if edit_suggestions:
            guidance += "- When making edits, consider these recent suggestions:\n"
            for suggestion in edit_suggestions[-2:]:
                guidance += f"  * {suggestion}\n"
        
        return guidance
