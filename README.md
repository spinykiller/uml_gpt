# Diagram Generator API

A FastAPI-based service that generates Mermaid diagrams using Groq AI, with chat-based editing capabilities.

## Features

- 🎨 **Multiple Diagram Types**: Sequential, Component, State, Class, ER, and Gantt diagrams
- 🤖 **Groq AI Integration**: Powered by Llama 3.3 70B model
- 💬 **Chat-Based Editing**: Interactive diagram modification through conversation
- ✅ **Mermaid Validation**: Automatic syntax validation with AI-powered error correction
- 🗄️ **MySQL Storage**: Persistent chat sessions and diagram history
- 🚀 **Easy Management**: Makefile for common operations

## Quick Start

### 1. Setup Environment

Create a `.env` file with your configuration:

```bash
# Groq Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Database Configuration
DB_USER=root
DB_PASSWORD=your_password_here
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=diagram_chat
```

### 2. Install Dependencies

```bash
make install
```

### 3. Setup Database (Optional)

```bash
make setup-db
```

### 4. Start the Server

```bash
make run
```

The API will be available at `http://localhost:8080` with **comprehensive interactive documentation** at `http://localhost:8080/docs`.

## Available Commands

| Command | Description |
|---------|-------------|
| `make run` | Start the API server |
| `make stop` | Stop the API server |
| `make restart` | Restart the API server |
| `make status` | Show server status |
| `make test` | Test API endpoints |
| `make logs` | Show server logs |
| `make setup-db` | Setup MySQL database |
| `make clean` | Clean up processes and temp files |
| `make quick-test` | Run a quick diagram generation test |

## 📚 Interactive Documentation

Visit `http://localhost:8080/docs` for the **comprehensive Swagger UI** featuring:

- 🎯 **Organized by Categories**: Endpoints grouped into "Basic Diagram Generation" and "Chat-Based Editing"
- 📝 **Detailed Descriptions**: Each endpoint includes purpose, use cases, and pro tips
- 🔍 **Live Examples**: Pre-filled request examples you can try immediately
- 📊 **Response Samples**: See exactly what each endpoint returns
- ⚡ **Try It Out**: Test endpoints directly from the browser
- 🔧 **Schema Validation**: Interactive request/response schema documentation

## API Endpoints

### Basic Diagram Generation

```bash
curl -X POST localhost:8080/query \
  -H 'content-type: application/json' \
  -d '{
    "prompt": "SEBI compliance monitoring system",
    "diagram_types": ["sequential", "component"]
  }'
```

### Chat-Based Editing (Requires Database)

**Start a chat session:**
```bash
curl -X POST localhost:8080/chat/start \
  -H 'content-type: application/json' \
  -d '{
    "initial_prompt": "SEBI compliance monitoring system",
    "diagram_types": ["sequential", "component"]
  }'
```

**Send editing message:**
```bash
curl -X POST localhost:8080/chat/{session_id}/message \
  -H 'content-type: application/json' \
  -d '{
    "message": "Add a notification service for alerts",
    "target_diagrams": ["component"]
  }'
```

**Get chat history:**
```bash
curl localhost:8080/chat/{session_id}/history
```

## Supported Diagram Types

- `sequential` - Sequence diagrams for process flows
- `component` - Component/flowchart diagrams for system architecture
- `state` - State diagrams for state machines
- `class` - Class diagrams for object relationships
- `er` - Entity-relationship diagrams for database design
- `gantt` - Gantt charts for project timelines

## Architecture

- **FastAPI**: Web framework for the REST API
- **Groq**: LLM provider for diagram generation
- **SQLAlchemy**: ORM for database operations
- **MySQL**: Database for chat sessions and diagram history
- **Pydantic**: Data validation and serialization

## Error Handling

The API gracefully handles various scenarios:
- **No Groq API Key**: Returns stub diagrams for testing
- **Database Unavailable**: Basic diagram generation still works, chat features return 503
- **Invalid Requests**: Proper validation errors with helpful messages

## Development

**Run in development mode:**
```bash
make dev-run
```

**View logs:**
```bash
make logs
```

**Check status:**
```bash
make status
```

## Requirements

- Python 3.11+
- MySQL 8.0+ (optional, for chat features)
- Groq API key (optional, for AI-generated diagrams)

## License

This project is for educational and development purposes.
