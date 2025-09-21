from fastapi import FastAPI

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import diagrams, chat, feedback

# FastAPI App
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    contact=settings.CONTACT_INFO,
    license_info=settings.LICENSE_INFO,
    servers=settings.SERVERS
)

# Include routers
app.include_router(diagrams.router)
app.include_router(chat.router)
app.include_router(feedback.router)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Diagram Generator API is running",
        "version": settings.API_VERSION,
        "docs_url": "/docs"
    }


# ----------------------------
# Local run helper:
# ----------------------------
# uvicorn app.main:app --reload --port 8080
