#!/usr/bin/env python3
"""
Working AI News Scraper API with Neon Database Support
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI News Scraper API - Neon Database", 
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API with Neon Database",
        "version": "2.0.0",
        "status": "working"
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    # Test basic imports
    import_status = {}
    
    try:
        import psycopg2
        import_status["psycopg2"] = "✅ Available"
    except ImportError as e:
        import_status["psycopg2"] = f"❌ {str(e)}"
    
    try:
        import requests
        import_status["requests"] = "✅ Available"
    except ImportError as e:
        import_status["requests"] = f"❌ {str(e)}"
    
    try:
        import email_validator
        import_status["email_validator"] = "✅ Available"
    except ImportError as e:
        import_status["email_validator"] = f"❌ {str(e)}"
    
    return {
        "status": "healthy",
        "imports": import_status,
        "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
        "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
        "google_client_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
    }

@app.get("/api/test-db")
async def test_database():
    """Test database connection"""
    try:
        from api.database_service import DatabaseService
        
        database_url = os.getenv("POSTGRES_URL")
        if not database_url:
            return {"error": "POSTGRES_URL not configured"}
        
        db = DatabaseService(database_url)
        
        # Test connection
        with db.get_connection() as conn:
            result = {"connection": "success", "type": "PostgreSQL" if db.is_postgres else "SQLite"}
        
        return result
        
    except Exception as e:
        return {"error": str(e), "type": "database_connection_failed"}

@app.get("/api/test-auth")
async def test_auth_service():
    """Test auth service initialization"""
    try:
        from api.auth_service_postgres import AuthService
        
        database_url = os.getenv("POSTGRES_URL")
        jwt_secret = os.getenv("JWT_SECRET", "test-secret")
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        
        if not database_url:
            return {"error": "POSTGRES_URL not configured"}
        
        auth_service = AuthService(
            database_url=database_url,
            jwt_secret=jwt_secret,
            google_client_id=google_client_id
        )
        
        # Test getting topics
        topics = auth_service.get_available_topics()
        
        return {
            "auth_service": "initialized",
            "topics_count": len(topics),
            "database_type": "PostgreSQL" if auth_service.db.is_postgres else "SQLite"
        }
        
    except Exception as e:
        return {"error": str(e), "type": "auth_service_failed"}