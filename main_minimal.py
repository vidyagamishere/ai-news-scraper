#!/usr/bin/env python3
"""
Minimal AI News Scraper API - Auth and Topics only
"""
import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
auth_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global auth_service
    
    # Startup
    logger.info("Starting minimal AI News Scraper API")
    
    try:
        # Initialize authentication service
        from api.auth_service_postgres import AuthService
        
        database_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_PATH", "ai_news.db")
        auth_service = AuthService(
            database_url=database_url,
            jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID")
        )
        logger.info("✅ Authentication service initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize auth service: {e}")
        auth_service = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down minimal AI News Scraper API")

# Create FastAPI app
app = FastAPI(
    title="AI News Scraper API - Minimal", 
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API - Minimal Version",
        "version": "1.0.0",
        "auth_available": auth_service is not None
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    db_info = {}
    if auth_service and hasattr(auth_service, 'db'):
        db_info = {
            "database_type": "PostgreSQL" if auth_service.db.is_postgres else "SQLite",
            "database_url": auth_service.db.database_url if not auth_service.db.is_postgres else "[PostgreSQL connection]"
        }
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_info": db_info,
        "auth_service": auth_service is not None
    }

@app.get("/api/auth/topics")
async def get_topics():
    """Get all available AI topics"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        topics = auth_service.get_available_topics()
        return topics
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@app.get("/api/topics")
async def get_topics_alt():
    """Alternative topics endpoint"""
    return await get_topics()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting minimal AI News Scraper API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)