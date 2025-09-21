import os
import asyncio
from typing import List, Dict
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.utils.mermaid_validator import MermaidCorrector
from app.services.feedback_service import FeedbackService
from app.services.feedback_adapter import FeedbackAdapter

# Groq SDK
try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore


# Request / Response Schemas
class QueryRequest(BaseModel):
    prompt: str = Field(
        ..., 
        min_length=1,
        description="Natural language description of what you want to diagram",
        example="SEBI compliance monitoring system with automated report generation"
    )
    diagram_types: List[str] = Field(
        ..., 
        min_items=1,
        description="List of diagram types to generate. Supported: sequential, component, state, class, er, gantt",
        example=["sequential", "component"]
    )

    @field_validator("diagram_types")
    def normalize_types(cls, v: List[str]) -> List[str]:
        norm = []
        for t in v:
            key = t.strip().lower()
            if key not in settings.ALLOWED_DIAGRAM_TYPES:
                raise ValueError(f"unsupported diagram type: {t}. Supported types: {list(settings.ALLOWED_DIAGRAM_TYPES.keys())}")
            norm.append(key)
        return norm

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "SEBI compliance monitoring system with automated report generation and real-time alerts",
                "diagram_types": ["sequential", "component"]
            }
        }


QueryResponse = Dict[str, str]  # { "diagram_type": "<mermaid>" }


# LLM Abstraction
class DiagramGenerator:
    def __init__(self):
        self.corrector = None  # Will be set after initialization
    
    async def generate(self, *, diagram_type: str, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError
    
    async def edit_diagram(self, *, diagram_type: str, current_diagram: str, 
                          edit_instruction: str, conversation_context: List[str]) -> str:  # pragma: no cover - interface
        raise NotImplementedError
    
    async def generate_with_validation(self, *, diagram_type: str, prompt: str, 
                                     user_identifier: str = None, db_session = None) -> str:
        """Generate diagram with Mermaid validation and correction, enhanced with feedback."""
        # Enhance prompt with feedback if available
        enhanced_prompt = prompt
        if db_session and user_identifier:
            try:
                feedback_service = FeedbackService(db_session)
                feedback_adapter = FeedbackAdapter(feedback_service)
                enhanced_prompt = feedback_adapter.enhance_generation_prompt(
                    prompt, diagram_type, user_identifier
                )
                print(f"🎯 Enhanced prompt with user feedback for {diagram_type}")
            except Exception as e:
                print(f"⚠️ Could not enhance prompt with feedback: {e}")
        
        # Generate with enhanced prompt
        raw_mermaid = await self.generate(diagram_type=diagram_type, prompt=enhanced_prompt)
        
        if self.corrector:
            corrected_mermaid, was_corrected = await self.corrector.validate_and_correct(
                raw_mermaid, diagram_type, enhanced_prompt
            )
            if was_corrected:
                print(f"✅ Mermaid diagram corrected for type: {diagram_type}")
            return corrected_mermaid
        
        return raw_mermaid
    
    async def edit_diagram_with_validation(self, *, diagram_type: str, current_diagram: str, 
                                         edit_instruction: str, conversation_context: List[str],
                                         user_identifier: str = None, db_session = None) -> str:
        """Edit diagram with Mermaid validation and correction, enhanced with feedback."""
        # Enhance edit instruction with feedback if available
        enhanced_instruction = edit_instruction
        if db_session and user_identifier:
            try:
                feedback_service = FeedbackService(db_session)
                feedback_adapter = FeedbackAdapter(feedback_service)
                enhanced_instruction = feedback_adapter.enhance_edit_prompt(
                    edit_instruction, diagram_type, edit_instruction, user_identifier
                )
                print(f"🎯 Enhanced edit instruction with user feedback for {diagram_type}")
            except Exception as e:
                print(f"⚠️ Could not enhance edit instruction with feedback: {e}")
        
        raw_mermaid = await self.edit_diagram(
            diagram_type=diagram_type,
            current_diagram=current_diagram,
            edit_instruction=enhanced_instruction,
            conversation_context=conversation_context
        )
        
        if self.corrector:
            corrected_mermaid, was_corrected = await self.corrector.validate_and_correct(
                raw_mermaid, diagram_type, enhanced_instruction
            )
            if was_corrected:
                print(f"✅ Mermaid diagram corrected after edit for type: {diagram_type}")
            return corrected_mermaid
        
        return raw_mermaid


class GroqDiagramGenerator(DiagramGenerator):
    def __init__(self, model: str = None, timeout_s: float = 45.0):
        super().__init__()
        self.api_key = settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout_s = timeout_s
        self.client = Groq(api_key=self.api_key) if (Groq and self.api_key) else None
        # Initialize the corrector after the client is set up
        self.corrector = MermaidCorrector(self)

    async def generate(self, *, diagram_type: str, prompt: str) -> str:
        mermaid_kind = settings.ALLOWED_DIAGRAM_TYPES[diagram_type]

        # Stub output if no key or SDK unavailable
        if self.client is None:
            return stub_mermaid(mermaid_kind)

        sys = (
            "You generate ONLY raw Mermaid code with no backticks or commentary. "
            "Return valid Mermaid for the requested kind."
        )
        user = build_mermaid_instruction(mermaid_kind, prompt)

        # Run the blocking SDK call in a thread with timeout
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._chat_completion, sys, user),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="LLM generation timeout")

    def _chat_completion(self, sys: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        if not resp.choices:
            raise HTTPException(status_code=502, detail="No choices from LLM")
        out = (resp.choices[0].message.content or "").strip()
        # scrub accidental fences
        out = out.strip("`\n ")
        out = out.replace("```mermaid", "").replace("```", "")
        return out
    
    async def edit_diagram(self, *, diagram_type: str, current_diagram: str, 
                          edit_instruction: str, conversation_context: List[str]) -> str:
        """Edit an existing diagram based on user instruction"""
        mermaid_kind = settings.ALLOWED_DIAGRAM_TYPES[diagram_type]
        
        # Stub output if no key or SDK unavailable
        if self.client is None:
            return current_diagram  # Return unchanged if no client
        
        sys = (
            "You are a Mermaid diagram editor. You receive an existing diagram "
            "and modification instructions. Return ONLY the updated raw Mermaid code "
            "with no backticks or commentary. Preserve the original structure "
            "while applying the requested changes."
        )
        
        context_str = "\n".join(conversation_context[-3:]) if conversation_context else ""
        user = (
            f"Current {mermaid_kind} diagram:\n```\n{current_diagram}\n```\n\n"
            f"Recent conversation context:\n{context_str}\n\n"
            f"Modification request: {edit_instruction}\n\n"
            f"Please update the diagram according to the request."
        )
        
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._chat_completion, sys, user),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="LLM generation timeout")


def build_mermaid_instruction(kind: str, user_prompt: str) -> str:
    return (
        f"Generate a Mermaid diagram of kind: {kind}\n"
        "Constraints:\n"
        "- Output ONLY raw Mermaid source. No code fences, no prose.\n"
        "- Keep it compact but self-explanatory with labels.\n"
        "- If 'component', use a flowchart to depict components and interactions.\n"
        "- Use ASCII-safe characters only.\n\n"
        "Domain prompt:\n" + user_prompt
    )


def stub_mermaid(kind: str) -> str:
    if kind == "sequenceDiagram":
        return (
            "sequenceDiagram\n"
            "actor R as Requester\n"
            "participant API as /query\n"
            "participant LLM as Model\n"
            "R->>API: POST prompt + diagram_types\n"
            "API->>LLM: generate mermaid\n"
            "LLM-->>API: mermaid source\n"
            "API-->>R: {type: mermaid}"
        )
    if kind == "flowchart":
        return (
            "flowchart TD\n"
            "A[Client]-->B(API /query)\n"
            "B-->C{LLM}\n"
            "C-->D[Mermaid JSON]"
        )
    if kind == "stateDiagram-v2":
        return (
            "stateDiagram-v2\n[*] --> Idle\nIdle --> Generating: receive request\n"
            "Generating --> Responded: all diagrams ready\nResponded --> [*]"
        )
    if kind == "classDiagram":
        return (
            "classDiagram\n"
            "class QueryRequest{\n+string prompt\n+string[] diagram_types\n}\n"
            "class QueryResponse\n"
            "QueryRequest --> QueryResponse"
        )
    if kind == "erDiagram":
        return (
            "erDiagram\nREQUEST ||--o{ DIAGRAM : contains\n"
            "REQUEST {string prompt}\nDIAGRAM {string type}"
        )
    if kind == "gantt":
        return (
            "gantt\n"
            "title Diagram Generation\n"
            "section API\nValidate:done, 2025-09-20, 1d\nLLM:active, 2025-09-21, 1d"
        )
    return "flowchart LR\nStart-->Unknown[Unsupported diagram type]"


# Provider Selection
def get_diagram_generator() -> DiagramGenerator:
    """Get the Groq diagram generator."""
    return GroqDiagramGenerator()
