#!/usr/bin/env python3
"""
AI News Scraper API with optimized Neon Database connection pooling
Following serverless best practices with global connection pool
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import our optimized database and auth services
from api.database_pool import init_pool, get_database_health, get_topics, close_pool
from api.auth_service_pool import PooledAuthService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services (created once per serverless instance)
auth_service = None
db_initialized = False

async def init_services():
    """Initialize global services (called once per serverless instance)"""
    global auth_service, db_initialized
    
    if not db_initialized:
        try:
            # Initialize database pool
            await init_pool()
            
            # Initialize auth service
            auth_service = PooledAuthService(
                jwt_secret=os.getenv("JWT_SECRET", "ai-news-jwt-secret-2025-production-secure"),
                google_client_id=os.getenv("GOOGLE_CLIENT_ID", "")
            )
            
            db_initialized = True
            logger.info("✅ Global services initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            db_initialized = False

# Create FastAPI app
app = FastAPI(
    title="AI News Scraper API - Optimized Neon Connection Pooling", 
    version="2.0.0"
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if "*" not in allowed_origins:
    allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    await init_services()
    
    return {
        "message": "AI News Scraper API with Optimized Neon Connection Pooling",
        "version": "2.0.0",
        "database": "Neon Postgres (asyncpg with connection pooling)",
        "status": "running",
        "database_initialized": db_initialized,
        "auth_service_available": auth_service is not None,
        "python_version": "3.12",
        "optimization": "Global connection pool for serverless"
    }

@app.get("/api/health")
async def health_check():
    """Health check with database pool information"""
    await init_services()
    
    # Get database health
    db_health = await get_database_health()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_health": db_health,
        "auth_service": auth_service is not None,
        "services_initialized": db_initialized,
        "environment": {
            "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
            "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
            "google_client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
        }
    }

@app.get("/api/test-pool")
async def test_connection_pool():
    """Test connection pool directly (similar to your example)"""
    await init_services()
    
    try:
        from api.database_pool import execute_single
        
        # Test query using the global pool
        result = await execute_single("SELECT NOW() as current_time")
        
        return {
            "success": True,
            "message": "Connection pool working correctly",
            "current_time": str(result["current_time"]) if result else None,
            "pool_status": "active"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pool_status": "error"
        }

@app.get("/api/auth/topics")
async def get_auth_topics():
    """Get all available AI topics using optimized pool"""
    await init_services()
    
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not available")
    
    try:
        topics = await auth_service.get_available_topics()
        
        topics_list = []
        for topic in topics:
            topics_list.append({
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "category": topic.category.value,
                "selected": topic.selected
            })
        
        return {
            "topics": topics_list,
            "total_count": len(topics_list),
            "database_type": "PostgreSQL (asyncpg with connection pooling)",
            "pool_optimized": True
        }
        
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@app.get("/api/database/info")
async def get_database_info():
    """Get detailed database information using optimized pool"""
    await init_services()
    
    try:
        from api.database_pool import execute_query
        
        # Get table counts using optimized queries
        table_counts = {}
        tables_to_check = ['users', 'ai_topics', 'articles', 'audio_content', 'video_content', 'daily_archives']
        
        for table in tables_to_check:
            try:
                result = await execute_single(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = result['count'] if result else 0
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        # Get topic categories
        topics_data = await get_topics()
        categories = {}
        for topic in topics_data:
            cat = topic['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        # Get database health
        db_health = await get_database_health()
        
        return {
            "success": True,
            "database_type": "PostgreSQL (asyncpg with optimized connection pooling)",
            "table_counts": table_counts,
            "topics_count": len(topics_data),
            "categories": categories,
            "pool_info": {
                "pool_size": db_health.get("pool_size", "unknown"),
                "pool_available": db_health.get("pool_available", "unknown"),
                "optimization": "global_pool_per_instance"
            },
            "sample_topics": [
                {
                    "name": topic['name'], 
                    "category": topic['category']
                } for topic in topics_data[:5]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database info: {str(e)}")

@app.get("/api/digest")
async def get_digest():
    """Basic digest endpoint for compatibility"""
    await init_services()
    
    return {
        "summary": {
            "keyPoints": [
                "• Neon PostgreSQL connected with optimized connection pooling",
                "• Global pool initialized once per serverless instance",
                "• High-performance async operations with asyncpg",
                "• Python 3.12 runtime for optimal compatibility"
            ],
            "metrics": {
                "totalUpdates": 0,
                "highImpact": 0, 
                "newResearch": 0,
                "industryMoves": 0
            }
        },
        "topStories": [],
        "content": {
            "blog": [],
            "audio": [],
            "video": []
        },
        "timestamp": datetime.now().isoformat(),
        "badge": "Optimized Connection Pool",
        "database_status": "connected" if db_initialized else "not connected",
        "optimization": {
            "driver": "asyncpg",
            "pool_strategy": "global_per_instance",
            "runtime": "python-3.12"
        }
    }

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    await close_pool()
    logger.info("Application shutdown complete")

# Handler function for serverless environments
def handler(request):
    """Serverless handler function (if needed)"""
    try:
        # This would be used in a pure serverless setup
        # For Vercel, FastAPI handles this automatically
        return app
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AI News Scraper API with optimized connection pooling on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)