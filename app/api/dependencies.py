"""
API dependencies for the diagram generator
"""
from app.core.database import get_db
from app.services.diagram_service import get_diagram_generator

# Export dependencies
__all__ = ["get_db", "get_diagram_generator"]
