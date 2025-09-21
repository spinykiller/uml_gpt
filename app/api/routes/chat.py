import asyncio
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_diagram_generator
from app.services.chat_service import ChatService
from app.models.chat import (
    StartChatRequest, ChatMessageRequest, StartChatResponse,
    SendMessageResponse, ChatHistoryResponse
)

router = APIRouter(prefix="/chat", tags=["Chat-Based Editing"])


@router.post(
    "/start", 
    response_model=StartChatResponse,
    summary="Start a new chat session",
    description="""
    Create a new chat session with initial diagrams that can be edited through conversation.
    
    **Features:**
    - Generates initial diagrams based on your prompt
    - Creates a persistent session for conversation history
    - Returns a session ID for future interactions
    
    **Requirements:**
    - Database connection must be available
    - At least one diagram type must be specified
    
    **Use this when:**
    - You want to iteratively improve diagrams
    - You need to maintain conversation context
    - You want to track diagram versions
    """,
    responses={
        200: {
            "description": "Chat session created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "a805700f-73b2-4125-8920-52623884babd",
                        "diagrams": {
                            "sequential": "sequenceDiagram\\n    participant A\\n    participant B\\n    A->>B: Message",
                            "component": "flowchart TD\\n    A[Start] --> B[Process] --> C[End]"
                        },
                        "message": "Chat session started. You can now ask for modifications to your diagrams."
                    }
                }
            }
        },
        503: {"description": "Database not available"},
        502: {"description": "Diagram generation failed"}
    }
)
async def start_chat(req: StartChatRequest, db: Session = Depends(get_db)) -> StartChatResponse:
    """Start a new chat session with initial diagrams"""
    generator = get_diagram_generator()
    chat_service = ChatService(db)
    
    # Generate initial diagrams with validation and feedback enhancement
    # Use session_id as user identifier for chat sessions
    user_identifier = None  # Will be set after session creation
    
    tasks = [
        generator.generate_with_validation(
            diagram_type=t, 
            prompt=req.initial_prompt,
            user_identifier=user_identifier,
            db_session=db
        ) 
        for t in req.diagram_types
    ]
    
    try:
        outputs = await asyncio.gather(*tasks)
        diagrams = {t: out for t, out in zip(req.diagram_types, outputs)}
        
        # Create chat session with diagrams
        response = chat_service.create_chat_session(req, diagrams)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"generation failed: {e}")


@router.post(
    "/{session_id}/message", 
    response_model=SendMessageResponse,
    summary="Send message to edit diagrams",
    description="""
    Send a natural language message to modify existing diagrams in a chat session.
    
    **How it works:**
    1. Analyzes your message for editing instructions
    2. Applies changes to specified diagrams (or all if none specified)
    3. Maintains conversation context for better understanding
    4. Returns both updated and complete diagram sets
    
    **Example messages:**
    - "Add a database component to store user data"
    - "Remove the authentication step from the sequence"
    - "Change the color scheme to be more modern"
    - "Add error handling to the flow"
    
    **Pro Tips:**
    - Be specific about what you want to change
    - Reference existing components by name when possible
    - Use `target_diagrams` to edit only specific diagram types
    """,
    responses={
        200: {
            "description": "Message processed and diagrams updated",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "a805700f-73b2-4125-8920-52623884babd",
                        "response": "Updated 1 diagram(s) based on your request.",
                        "updated_diagrams": {
                            "component": "flowchart TD\\n    A[Input] --> B[Process]\\n    B --> C[Database]\\n    C --> D[Output]"
                        },
                        "all_diagrams": {
                            "sequential": "sequenceDiagram\\n    participant A\\n    A->>B: Request",
                            "component": "flowchart TD\\n    A[Input] --> B[Process]\\n    B --> C[Database]\\n    C --> D[Output]"
                        }
                    }
                }
            }
        },
        404: {"description": "Chat session not found"},
        503: {"description": "Database not available"}
    }
)
async def send_message(
    session_id: str, 
    req: ChatMessageRequest, 
    db: Session = Depends(get_db)
) -> SendMessageResponse:
    """Send a message to modify diagrams in an existing chat"""
    generator = get_diagram_generator()
    chat_service = ChatService(db)
    
    # Check if session exists
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Add user message to session
    chat_service.add_user_message(session_id, req.message)
    
    # Get current diagrams
    current_diagrams = chat_service.get_session_diagrams(session_id)
    
    # Determine which diagrams to update
    target_diagrams = req.target_diagrams or list(current_diagrams.keys())
    updated_diagrams = {}
    
    # Build conversation context
    context = chat_service.get_conversation_context(session_id, limit=5)
    
    # Update each target diagram
    for diagram_type in target_diagrams:
        if diagram_type in current_diagrams:
            current_diagram = current_diagrams[diagram_type]
            
            try:
                updated_mermaid = await generator.edit_diagram_with_validation(
                    diagram_type=diagram_type,
                    current_diagram=current_diagram,
                    edit_instruction=req.message,
                    conversation_context=context,
                    user_identifier=session_id,  # Use session_id as user identifier
                    db_session=db
                )
                
                # Update diagram in database
                chat_service.update_diagram(session_id, diagram_type, updated_mermaid)
                updated_diagrams[diagram_type] = updated_mermaid
                
            except Exception as e:
                # If edit fails, keep original diagram
                print(f"Failed to edit diagram {diagram_type}: {e}")
                updated_diagrams[diagram_type] = current_diagram
    
    # Get all current diagrams after updates
    all_current_diagrams = chat_service.get_session_diagrams(session_id)
    
    # Add assistant response
    response_text = f"Updated {len(updated_diagrams)} diagram(s) based on your request."
    chat_service.add_assistant_message(session_id, response_text)
    
    return SendMessageResponse(
        session_id=session_id,
        response=response_text,
        updated_diagrams=updated_diagrams,
        all_diagrams=all_current_diagrams
    )


@router.get(
    "/{session_id}/history", 
    response_model=ChatHistoryResponse,
    summary="Get chat history and current diagrams",
    description="""
    Retrieve complete conversation history and current state of all diagrams in a chat session.
    
    **Returns:**
    - Complete message history with timestamps
    - Current version of all diagrams
    - Session metadata (creation time, last activity)
    - Diagram version information
    
    **Useful for:**
    - Reviewing conversation flow
    - Getting current diagram states
    - Debugging diagram changes
    - Exporting session data
    """,
    responses={
        200: {
            "description": "Chat history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "a805700f-73b2-4125-8920-52623884babd",
                        "session_info": {
                            "id": "a805700f-73b2-4125-8920-52623884babd",
                            "original_prompt": "SEBI compliance system",
                            "created_at": "2025-09-20T21:00:00Z",
                            "last_activity": "2025-09-20T21:15:00Z"
                        },
                        "messages": [
                            {
                                "id": 1,
                                "role": "system",
                                "content": "Created diagrams for: sequential, component",
                                "timestamp": "2025-09-20T21:00:00Z"
                            }
                        ],
                        "current_diagrams": [
                            {
                                "id": 1,
                                "diagram_type": "sequential",
                                "current_mermaid": "sequenceDiagram...",
                                "version": 2,
                                "last_updated": "2025-09-20T21:15:00Z"
                            }
                        ]
                    }
                }
            }
        },
        404: {"description": "Chat session not found"},
        503: {"description": "Database not available"}
    }
)
async def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> ChatHistoryResponse:
    """Get chat history and current diagram states"""
    chat_service = ChatService(db)
    
    history = chat_service.get_chat_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    return history


@router.delete(
    "/{session_id}",
    summary="Delete a chat session",
    description="""
    Permanently delete a chat session and all associated data.
    
    **This will remove:**
    - All conversation messages
    - All diagram versions and history
    - Session metadata
    
    **⚠️ Warning:** This action cannot be undone!
    
    **Use cases:**
    - Cleaning up test sessions
    - Removing sensitive data
    - Managing storage space
    """,
    responses={
        200: {
            "description": "Session deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Chat session deleted successfully"
                    }
                }
            }
        },
        404: {"description": "Chat session not found"},
        503: {"description": "Database not available"}
    }
)
async def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session"""
    chat_service = ChatService(db)
    
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    db.delete(session)
    db.commit()
    
    return {"message": "Chat session deleted successfully"}
