import re
import asyncio
from typing import Tuple, Optional
from fastapi import HTTPException


class MermaidValidator:
    """Validates Mermaid diagram syntax and provides correction suggestions."""
    
    def __init__(self):
        # Basic Mermaid syntax patterns for validation
        self.diagram_patterns = {
            "sequenceDiagram": {
                "start": r"^sequenceDiagram\s*",
                "participant": r"participant\s+\w+(\s+as\s+[\"'][^\"']*[\"'])?\s*",
                "actor": r"actor\s+\w+(\s+as\s+[\"'][^\"']*[\"'])?\s*",
                "arrow": r"\w+\s*-{1,2}>{1,2}\s*\w+\s*:\s*.+",
                "note": r"Note\s+(over|left of|right of)\s+\w+(,\w+)?\s*:\s*.+",
                "activate": r"activate\s+\w+",
                "deactivate": r"deactivate\s+\w+"
            },
            "flowchart": {
                "start": r"^(flowchart|graph)\s+(TD|TB|BT|RL|LR)\s*",
                "node": r"\w+\[[^\]]+\]|\w+\([^\)]+\)|\w+\{[^\}]+\}|\w+>[^\]]+\]|\w+",
                "connection": r"\w+\s*--[>o]?\s*\w+|\w+\s*-\.\s*\w+|\w+\s*==>\s*\w+",
                "label": r"\w+\s*--\|[^\|]+\|\s*\w+",
                "subgraph": r"subgraph\s+[^\n]+",
                "end": r"^end\s*$"
            },
            "stateDiagram-v2": {
                "start": r"^stateDiagram-v2\s*",
                "state": r"\w+\s*:\s*.+|\[?\*\]?\s*-->\s*\w+|\w+\s*-->\s*\[?\*\]?",
                "transition": r"\w+\s*-->\s*\w+(\s*:\s*.+)?"
            },
            "classDiagram": {
                "start": r"^classDiagram\s*",
                "class": r"class\s+\w+\s*\{[^\}]*\}",
                "relationship": r"\w+\s*(<\|--|--\||--|\.\.|<\.\.|\.\.>|<\|\.\.)\s*\w+"
            },
            "erDiagram": {
                "start": r"^erDiagram\s*",
                "relationship": r"\w+\s*(\|\|--[o\|]\{|\|\|--o\||\}\|--\|\||\|o--\|\|)\s*\w+",
                "entity": r"\w+\s*\{[^\}]*\}"
            },
            "gantt": {
                "start": r"^gantt\s*",
                "title": r"title\s+.+",
                "section": r"section\s+.+",
                "task": r".+\s*:\s*(done|active|crit)?,?\s*\w*,?\s*[\d-]+,?\s*\d*[dhm]?"
            }
        }
    
    def validate_mermaid(self, mermaid_code: str, diagram_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Mermaid syntax.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not mermaid_code or not mermaid_code.strip():
            return False, "Empty Mermaid code provided"
        
        mermaid_code = mermaid_code.strip()
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        if not lines:
            return False, "No valid Mermaid content found"
        
        # Map diagram types to their validation patterns
        validation_type = diagram_type
        if diagram_type == "component":
            validation_type = "flowchart"
        elif diagram_type in ["sequential", "sequence"]:
            validation_type = "sequenceDiagram"
        elif diagram_type == "state":
            validation_type = "stateDiagram-v2"
        elif diagram_type == "class":
            validation_type = "classDiagram"
        elif diagram_type == "er":
            validation_type = "erDiagram"
        
        # Get the expected diagram type patterns
        if validation_type not in self.diagram_patterns:
            return False, f"Unsupported diagram type: {diagram_type}"
        
        patterns = self.diagram_patterns[validation_type]
        
        # Check if first line matches the diagram type
        first_line = lines[0]
        if not re.match(patterns["start"], first_line):
            return False, f"Invalid {diagram_type} start. Expected pattern: {patterns['start']}"
        
        # Validate specific syntax based on diagram type
        try:
            if validation_type == "sequenceDiagram":
                return self._validate_sequence_diagram(lines[1:], patterns)
            elif validation_type in ["flowchart"]:  # component uses flowchart syntax
                return self._validate_flowchart(lines[1:], patterns)
            elif validation_type == "stateDiagram-v2":
                return self._validate_state_diagram(lines[1:], patterns)
            elif validation_type == "classDiagram":
                return self._validate_class_diagram(lines[1:], patterns)
            elif validation_type == "erDiagram":
                return self._validate_er_diagram(lines[1:], patterns)
            elif validation_type == "gantt":
                return self._validate_gantt_diagram(lines[1:], patterns)
            else:
                return True, None  # Basic validation passed
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _validate_sequence_diagram(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate sequence diagram syntax."""
        for line in lines:
            if not line:
                continue
                
            # Check if line matches any valid pattern
            valid_patterns = [
                patterns["participant"],
                patterns["actor"], 
                patterns["arrow"],
                patterns["note"],
                patterns["activate"],
                patterns["deactivate"]
            ]
            
            if not any(re.match(pattern, line) for pattern in valid_patterns):
                return False, f"Invalid sequence diagram syntax: '{line}'"
        
        return True, None
    
    def _validate_flowchart(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate flowchart syntax."""
        subgraph_depth = 0
        
        for line in lines:
            if not line:
                continue
            
            # Handle subgraph nesting
            if re.match(patterns["subgraph"], line):
                subgraph_depth += 1
                continue
            elif re.match(patterns["end"], line):
                subgraph_depth -= 1
                continue
            
            # Check valid patterns
            valid_patterns = [
                patterns["node"],
                patterns["connection"],
                patterns["label"]
            ]
            
            # Allow more flexible matching for flowcharts
            if not any(re.search(pattern, line) for pattern in valid_patterns):
                # Check for basic node or connection patterns
                if not (re.search(r'\w+', line) and ('-->' in line or '->' in line or '[' in line or '(' in line)):
                    return False, f"Invalid flowchart syntax: '{line}'"
        
        if subgraph_depth != 0:
            return False, "Unmatched subgraph blocks (missing 'end' statements)"
        
        return True, None
    
    def _validate_state_diagram(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate state diagram syntax."""
        for line in lines:
            if not line:
                continue
                
            valid_patterns = [
                patterns["state"],
                patterns["transition"]
            ]
            
            # More permissive validation for state diagrams
            if not any(re.search(pattern, line) for pattern in valid_patterns):
                # Allow common state diagram elements
                if not (re.search(r'note\s+', line) or
                       re.search(r'state\s+\w+', line) or
                       re.search(r'\w+\s*-->\s*\w+', line) or
                       re.search(r'\[\*\]', line) or  # Start/end states
                       re.search(r'\w+\s*:\s*', line)):  # State descriptions
                    return False, f"Invalid state diagram syntax: '{line}'"
        
        return True, None
    
    def _validate_class_diagram(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate class diagram syntax."""
        for line in lines:
            if not line:
                continue
                
            valid_patterns = [
                patterns["class"],
                patterns["relationship"]
            ]
            
            # More permissive validation for class diagrams
            # Allow class definitions, relationships, and method/field definitions
            if not any(re.search(pattern, line) for pattern in valid_patterns):
                # Allow lines that look like class content (methods, fields, etc.)
                if not (re.search(r'\w+\s*\{', line) or 
                       re.search(r'[\+\-\#\~]?\w+.*', line) or
                       re.search(r'\}', line) or
                       re.search(r'class\s+\w+', line)):
                    return False, f"Invalid class diagram syntax: '{line}'"
        
        return True, None
    
    def _validate_er_diagram(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate ER diagram syntax."""
        for line in lines:
            if not line:
                continue
                
            valid_patterns = [
                patterns["relationship"],
                patterns["entity"]
            ]
            
            # More permissive validation for ER diagrams
            if not any(re.search(pattern, line) for pattern in valid_patterns):
                # Allow entity definitions and relationship syntax variations
                if not (re.search(r'\w+\s*\{', line) or
                       re.search(r'\}', line) or
                       re.search(r'\w+\s+\w+', line) or  # Field definitions
                       re.search(r'\w+\s*[\|\}\{o\-]+.*\w+', line)):  # Relationship variations
                    return False, f"Invalid ER diagram syntax: '{line}'"
        
        return True, None
    
    def _validate_gantt_diagram(self, lines, patterns) -> Tuple[bool, Optional[str]]:
        """Validate Gantt diagram syntax."""
        for line in lines:
            if not line:
                continue
                
            valid_patterns = [
                patterns["title"],
                patterns["section"],
                patterns["task"]
            ]
            
            # More permissive validation for Gantt diagrams
            if not any(re.search(pattern, line) for pattern in valid_patterns):
                # Allow common Gantt syntax like dateFormat, axisFormat, etc.
                if not (re.search(r'dateFormat\s+', line) or
                       re.search(r'axisFormat\s+', line) or
                       re.search(r'excludes\s+', line) or
                       re.search(r'todayMarker\s+', line) or
                       re.search(r'\w+\s*:\s*', line)):  # General task-like syntax
                    return False, f"Invalid Gantt diagram syntax: '{line}'"
        
        return True, None


class MermaidCorrector:
    """Uses LLM to correct invalid Mermaid diagrams."""
    
    def __init__(self, generator):
        self.generator = generator
        self.validator = MermaidValidator()
        self.max_retries = 3
    
    async def validate_and_correct(self, mermaid_code: str, diagram_type: str, 
                                 original_prompt: str = "") -> Tuple[str, bool]:
        """
        Validate Mermaid code and correct if invalid.
        
        Returns:
            Tuple[str, bool]: (corrected_mermaid_code, was_corrected)
        """
        # First validation attempt
        is_valid, error_message = self.validator.validate_mermaid(mermaid_code, diagram_type)
        
        if is_valid:
            return mermaid_code, False
        
        print(f"Mermaid validation failed: {error_message}")
        print(f"Attempting to correct with LLM (max {self.max_retries} retries)")
        
        current_mermaid = mermaid_code
        
        for attempt in range(self.max_retries):
            try:
                print(f"Correction attempt {attempt + 1}/{self.max_retries}")
                
                # Ask LLM to fix the Mermaid syntax
                corrected_mermaid = await self._get_llm_correction(
                    current_mermaid, diagram_type, error_message, original_prompt
                )
                
                # Validate the corrected version
                is_valid, error_message = self.validator.validate_mermaid(corrected_mermaid, diagram_type)
                
                if is_valid:
                    print(f"✅ Mermaid corrected successfully on attempt {attempt + 1}")
                    return corrected_mermaid, True
                
                current_mermaid = corrected_mermaid
                print(f"❌ Attempt {attempt + 1} still invalid: {error_message}")
                
            except Exception as e:
                print(f"❌ Correction attempt {attempt + 1} failed: {e}")
                continue
        
        # All correction attempts failed
        raise HTTPException(
            status_code=422,
            detail=f"Failed to generate valid Mermaid diagram after {self.max_retries} attempts. "
                   f"Last error: {error_message}"
        )
    
    async def _get_llm_correction(self, invalid_mermaid: str, diagram_type: str, 
                                error_message: str, original_prompt: str) -> str:
        """Get LLM to correct the invalid Mermaid syntax."""
        
        # Enhanced correction prompt with specific error guidance
        correction_prompt = f"""
You are a Mermaid diagram syntax expert. Fix the following invalid Mermaid diagram.

DIAGRAM TYPE: {diagram_type}
ORIGINAL PROMPT: {original_prompt}

INVALID MERMAID CODE:
```
{invalid_mermaid}
```

SPECIFIC VALIDATION ERROR: {error_message}

COMMON FIXES FOR THIS ERROR TYPE:
{self._get_error_specific_guidance(error_message, diagram_type)}

INSTRUCTIONS:
1. **FOCUS ON THE SPECIFIC ERROR**: The validation failed because: {error_message}
2. Fix the syntax errors while preserving the diagram's meaning and structure
3. Ensure the diagram type declaration is correct: {diagram_type}
4. Follow proper Mermaid syntax rules for {diagram_type}
5. Return ONLY the corrected Mermaid code with no explanations or backticks
6. Keep the content and logic of the original diagram intact
7. Double-check that your correction addresses the specific error mentioned above

CORRECTED MERMAID:
"""
        
        try:
            # Use the same generator but with a correction-specific system prompt
            if hasattr(self.generator, 'client') and self.generator.client:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._llm_correction_call, correction_prompt),
                    timeout=self.generator.timeout_s,
                )
            else:
                # Fallback: return original if no LLM available
                return invalid_mermaid
                
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Mermaid correction timeout")
    
    def _get_error_specific_guidance(self, error_message: str, diagram_type: str) -> str:
        """Provide specific guidance based on the validation error."""
        error_lower = error_message.lower()
        
        guidance = []
        
        # Common error patterns and their fixes
        if "invalid" in error_lower and "start" in error_lower:
            guidance.append(f"• Fix the diagram declaration: Start with '{diagram_type}' (case-sensitive)")
            guidance.append(f"• For flowcharts, use 'flowchart TD' or 'graph TD/LR/TB/BT'")
            guidance.append(f"• For sequence diagrams, use 'sequenceDiagram'")
        
        if "participant" in error_lower or "actor" in error_lower:
            guidance.append("• Use correct participant syntax: 'participant A as \"Description\"'")
            guidance.append("• Use correct actor syntax: 'actor A as \"Description\"'")
            guidance.append("• Participant/actor names should be valid identifiers (no spaces)")
        
        if "arrow" in error_lower or "-->" in error_lower:
            guidance.append("• Check arrow syntax: 'A->>B: message' for sequence diagrams")
            guidance.append("• Check connection syntax: 'A-->B' for flowcharts")
            guidance.append("• Ensure proper spacing around arrows")
        
        if "flowchart" in error_lower or "graph" in error_lower:
            guidance.append("• Start with 'flowchart TD' or 'graph LR/TD/TB/BT'")
            guidance.append("• Use node syntax: 'A[Label]', 'B(Label)', 'C{Decision}'")
            guidance.append("• Use connection syntax: 'A-->B', 'A-.->B', 'A==>B'")
        
        if "subgraph" in error_lower or "end" in error_lower:
            guidance.append("• Every 'subgraph' must have a matching 'end'")
            guidance.append("• Proper subgraph syntax: 'subgraph Title' followed by content and 'end'")
        
        if "syntax" in error_lower:
            guidance.append(f"• Review {diagram_type} specific syntax rules")
            guidance.append("• Check for typos in keywords and operators")
            guidance.append("• Ensure proper line breaks and indentation")
        
        if "empty" in error_lower:
            guidance.append("• Add actual diagram content after the declaration")
            guidance.append("• Remove empty lines that might be causing issues")
        
        if not guidance:
            # Generic guidance if no specific pattern matched
            guidance = [
                f"• Verify {diagram_type} syntax is correct",
                "• Check for typos in keywords and identifiers", 
                "• Ensure proper spacing and line breaks",
                "• Remove any invalid characters or formatting"
            ]
        
        return "\n".join(guidance)
    
    def _llm_correction_call(self, correction_prompt: str) -> str:
        """Make the actual LLM call for correction."""
        resp = self.generator.client.chat.completions.create(
            model=self.generator.model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a Mermaid diagram syntax expert. Fix invalid Mermaid code while preserving meaning. Return ONLY corrected Mermaid code."
                },
                {"role": "user", "content": correction_prompt}
            ],
            temperature=0.1,  # Lower temperature for more consistent corrections
            max_tokens=1000,
        )
        
        if not resp.choices:
            raise HTTPException(status_code=502, detail="No response from LLM for correction")
        
        corrected = (resp.choices[0].message.content or "").strip()
        # Clean up any accidental formatting
        corrected = corrected.strip("`\n ")
        corrected = corrected.replace("```mermaid", "").replace("```", "")
        return corrected
