#!/usr/bin/env python3
"""
Simple AI News Scraper API with Neon Database Support - No lifespan
"""
import os
import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global auth service - will be initialized on first request
auth_service = None

def get_auth_service():
    """Initialize auth service on demand"""
    global auth_service
    if auth_service is None:
        try:
            # Initialize authentication service with Neon Postgres
            from api.auth_service_postgres import AuthService
            
            database_url = os.getenv("POSTGRES_URL")
            if not database_url:
                raise ValueError("POSTGRES_URL environment variable is required")
            
            auth_service = AuthService(
                database_url=database_url,
                jwt_secret=os.getenv("JWT_SECRET", "ai-news-jwt-secret-2025-production-secure"),
                google_client_id=os.getenv("GOOGLE_CLIENT_ID")
            )
            logger.info("✅ Authentication service initialized with Neon Postgres")
            
            # Test database connection
            topics = auth_service.get_available_topics()
            logger.info(f"✅ Database connection verified - {len(topics)} topics available")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize auth service: {e}")
            auth_service = None
    
    return auth_service

@app.get("/")
async def root():
    """Root endpoint"""
    service = get_auth_service()
    return {
        "message": "AI News Scraper API with Neon Database",
        "version": "2.0.0",
        "database": "Neon Postgres",
        "auth_available": service is not None
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    service = get_auth_service()
    db_info = {"available": False}
    
    if service and hasattr(service, 'db'):
        try:
            with service.db.get_connection() as conn:
                db_info = {
                    "available": True,
                    "connected": True,
                    "type": "PostgreSQL" if service.db.is_postgres else "SQLite",
                    "database_url": service.db.database_url[:50] + "..." if len(service.db.database_url) > 50 else service.db.database_url
                }
        except Exception as e:
            db_info = {
                "available": True,
                "connected": False,
                "error": str(e)
            }
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_info": db_info,
        "auth_service": service is not None
    }

@app.get("/api/auth/topics")
async def get_topics():
    """Get all available AI topics with new categories"""
    service = get_auth_service()
    if not service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        topics = service.get_available_topics()
        
        # Convert to dict format for JSON response
        topics_list = []
        for topic in topics:
            topics_list.append({
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "category": topic.category.value,  # Extract string value from enum
                "selected": topic.selected
            })
        
        return topics_list
        
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@app.get("/api/topics")
async def get_topics_alt():
    """Alternative topics endpoint for compatibility"""
    return await get_topics()

@app.get("/api/database/info")
async def get_database_info():
    """Get detailed database information"""
    service = get_auth_service()
    if not service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        # Get table counts
        table_counts = {}
        tables_to_check = ['users', 'ai_topics', 'articles', 'audio_content', 'video_content', 'daily_archives']
        
        for table in tables_to_check:
            try:
                result = service.db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = result[0]['count']
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        # Get topic categories
        topics = service.get_available_topics()
        categories = {}
        for topic in topics:
            cat = topic.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "database_type": "PostgreSQL" if service.db.is_postgres else "SQLite",
            "database_url": service.db.database_url[:50] + "...",
            "table_counts": table_counts,
            "topics_count": len(topics),
            "categories": categories,
            "sample_topics": [
                {
                    "name": topic.name, 
                    "category": topic.category.value
                } for topic in topics[:5]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database info: {str(e)}")

@app.post("/api/database/init")
async def initialize_database():
    """Initialize database with updated topics (for testing)"""
    service = get_auth_service()
    if not service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        # This will trigger table creation and default topic initialization
        topics = service.get_available_topics()
        
        return {
            "message": "Database initialized successfully",
            "topics_created": len(topics),
            "database_type": "PostgreSQL" if service.db.is_postgres else "SQLite"
        }
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AI News Scraper API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)