import asyncio
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_diagram_generator
from app.services.diagram_service import QueryRequest, QueryResponse, DiagramGenerator

router = APIRouter(prefix="", tags=["Basic Diagram Generation"])


@router.post(
    "/query", 
    response_model=QueryResponse,
    summary="Generate diagrams from prompt",
    description="""
    Generate one or more Mermaid diagrams based on a natural language prompt.
    
    This endpoint is perfect for:
    - Quick diagram generation without chat functionality
    - Batch generation of multiple diagram types
    - Integration with other systems
    
    **Note**: This endpoint doesn't require a database connection and works even if MySQL is unavailable.
    """,
    response_description="Dictionary mapping diagram types to generated Mermaid code",
    responses={
        200: {
            "description": "Successfully generated diagrams",
            "content": {
                "application/json": {
                    "example": {
                        "sequential": "sequenceDiagram\\n    participant A as User\\n    participant B as System\\n    A->>B: Request\\n    B-->>A: Response",
                        "component": "flowchart TD\\n    A[Input] --> B[Process]\\n    B --> C[Output]"
                    }
                }
            }
        },
        502: {"description": "LLM generation failed"},
        504: {"description": "LLM generation timeout"}
    }
)
async def query(req: QueryRequest) -> QueryResponse:
    """Generate diagrams from a natural language prompt."""
    generator = get_diagram_generator()
    
    # Generate all diagrams concurrently with validation and feedback enhancement
    # For basic query, we use 'anonymous' as user identifier
    user_identifier = "anonymous"
    
    tasks = [
        generator.generate_with_validation(
            diagram_type=t, 
            prompt=req.prompt,
            user_identifier=user_identifier,
            db_session=None
        ) for t in req.diagram_types
    ]
    try:
        outputs = await asyncio.gather(*tasks)
    except HTTPException:
        raise
    except Exception as e:  # unexpected errors
        raise HTTPException(status_code=502, detail=f"generation failed: {e}")

    # Map back to requested keys
    return {t: out for t, out in zip(req.diagram_types, outputs)}
