import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration"""
    
    # API Settings
    API_TITLE: str = "Diagram Generator API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = """
    🎨 **AI-Powered Diagram Generator with Chat-Based Editing**
    
    Generate and edit Mermaid diagrams using Groq AI with natural language prompts.
    
    ## Features
    
    * 🎯 **Multiple Diagram Types**: Sequential, Component, State, Class, ER, and Gantt diagrams
    * 🤖 **AI-Powered**: Uses Groq's Llama 3.3 70B model for intelligent diagram generation
    * 💬 **Chat-Based Editing**: Interactive diagram modification through conversation
    * ✅ **Mermaid Validation**: Automatic syntax validation with AI-powered error correction (max 3 retry attempts)
    * 🗄️ **Persistent Sessions**: MySQL storage for chat history and diagram versions
    * 🚀 **Easy Integration**: RESTful API with comprehensive documentation
    
    ## Quick Start
    
    1. **Generate Basic Diagrams**: Use `/query` endpoint with your prompt
    2. **Start Interactive Chat**: Use `/chat/start` to begin a conversation
    3. **Edit Diagrams**: Send messages to `/chat/{session_id}/message` to modify diagrams
    4. **View History**: Get complete chat history with `/chat/{session_id}/history`
    
    ## Supported Diagram Types
    
    - `sequential` - Sequence diagrams for process flows
    - `component` - Component/flowchart diagrams for system architecture  
    - `state` - State diagrams for state machines
    - `class` - Class diagrams for object relationships
    - `er` - Entity-relationship diagrams for database design
    - `gantt` - Gantt charts for project timelines
    """
    
    # Server Settings
    SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8080"))
    
    # Groq API Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TIMEOUT: float = float(os.getenv("GROQ_TIMEOUT", "45.0"))
    
    # Database Settings
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "your_password_here")
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "diagram_chat")
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # Mermaid Settings
    ALLOWED_DIAGRAM_TYPES: Dict[str, str] = {
        "sequential": "sequenceDiagram",
        "sequence": "sequenceDiagram",
        "component": "flowchart",         # we render components with flowchart
        "flowchart": "flowchart",
        "state": "stateDiagram-v2",
        "class": "classDiagram",
        "er": "erDiagram",
        "gantt": "gantt",
    }
    
    # Validation Settings
    MAX_CORRECTION_RETRIES: int = 3
    
    # Contact and License Information
    CONTACT_INFO: Dict[str, str] = {
        "name": "API Support",
        "url": "https://github.com/your-repo/diagram-api",
    }
    
    LICENSE_INFO: Dict[str, str] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # Server Configuration
    SERVERS: list = [
        {
            "url": f"http://{SERVER_HOST}:{SERVER_PORT}",
            "description": "Development server"
        }
    ]


# Create global settings instance
settings = Settings()
