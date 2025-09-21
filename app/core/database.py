from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.core.config import settings
from app.models.database import Base


def build_database_url() -> str:
    """Build database URL with proper encoding for special characters"""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Build URL from individual components with proper encoding
    # URL encode the password to handle special characters like @
    encoded_password = quote_plus(settings.DB_PASSWORD)
    
    return f"mysql+mysqlconnector://{settings.DB_USER}:{encoded_password}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


def create_database_engine():
    """Create database engine with error handling"""
    # Check if database should be disabled
    if not settings.DATABASE_URL and not settings.DB_PASSWORD:
        print("No database configuration found - running without database")
        return None, None, False
        
    if settings.DB_PASSWORD == "your_password_here":
        print("Default password detected - running without database")
        print("To enable database: set proper DB_PASSWORD in .env file")
        return None, None, False
    
    database_url = build_database_url()
    
    try:
        # Test connection first
        test_engine = create_engine(database_url, echo=False)
        test_connection = test_engine.connect()
        test_connection.close()
        
        # If successful, create actual engine
        engine = create_engine(database_url, echo=False)  # Reduced verbosity
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        print("✅ Database connection successful")
        return engine, SessionLocal, True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("🔄 Running without database - chat functionality will be disabled")
        print("💡 To fix: Update database credentials in .env file or run 'make setup-db'")
        return None, None, False


# Initialize database
engine, SessionLocal, DB_AVAILABLE = create_database_engine()


def create_tables():
    """Create all database tables"""
    if DB_AVAILABLE and Base and engine:
        Base.metadata.create_all(bind=engine)
    else:
        print("Skipping table creation - database not available")


def get_db():
    """Dependency to get database session"""
    if not DB_AVAILABLE or not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
