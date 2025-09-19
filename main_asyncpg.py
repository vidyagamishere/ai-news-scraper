#!/usr/bin/env python3
"""
AI News Scraper API with Neon Database Support using asyncpg
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
db_available = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global auth_service, db_available
    
    # Startup
    logger.info("Starting AI News Scraper API with Neon Database (asyncpg)")
    
    try:
        # Try to initialize the database service
        database_url = os.getenv("POSTGRES_URL")
        if database_url:
            # Try to import and initialize asyncpg support
            try:
                from api.auth_service_asyncpg import AsyncAuthService
                
                auth_service = AsyncAuthService(
                    database_url=database_url,
                    jwt_secret=os.getenv("JWT_SECRET", "ai-news-jwt-secret-2025-production-secure"),
                    google_client_id=os.getenv("GOOGLE_CLIENT_ID", "")
                )
                
                # Initialize the auth service
                await auth_service.initialize()
                
                # Test the connection
                topics = await auth_service.get_available_topics()
                logger.info(f"✅ Neon database connected with asyncpg - {len(topics)} topics available")
                db_available = True
                
            except ImportError as e:
                logger.warning(f"asyncpg libraries not available: {e}")
                db_available = False
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                db_available = False
        else:
            logger.warning("POSTGRES_URL not configured")
            db_available = False
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
        db_available = False
    
    yield
    
    # Shutdown
    if auth_service:
        try:
            await auth_service.close()
        except:
            pass
    logger.info("Shutting down AI News Scraper API")

# Create FastAPI app
app = FastAPI(
    title="AI News Scraper API - Neon Database with asyncpg", 
    version="2.0.0",
    lifespan=lifespan
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
    return {
        "message": "AI News Scraper API with Neon Database using asyncpg",
        "version": "2.0.0",
        "database": "Neon Postgres (asyncpg)" if db_available else "Not Connected",
        "status": "running",
        "database_available": db_available,
        "auth_service_available": auth_service is not None
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    db_info = {
        "available": db_available,
        "driver": "asyncpg" if db_available else "none",
        "type": "PostgreSQL" if db_available else "None",
        "connection_status": "connected" if db_available else "not connected"
    }
    
    if auth_service and hasattr(auth_service, 'db'):
        try:
            # Test connection by trying to get topics
            topics = await auth_service.get_available_topics()
            db_info.update({
                "connection_test": "successful",
                "topics_count": len(topics),
                "database_url": auth_service.db.database_url[:50] + "..." if len(auth_service.db.database_url) > 50 else auth_service.db.database_url
            })
        except Exception as e:
            db_info.update({
                "connection_test": "failed",
                "error": str(e)
            })
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_info": db_info,
        "auth_service": auth_service is not None,
        "environment": {
            "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
            "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
            "google_client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
        }
    }

@app.get("/api/test-asyncpg")
async def test_asyncpg_connection():
    """Test asyncpg connection directly"""
    try:
        import asyncpg
        
        database_url = os.getenv("POSTGRES_URL")
        if not database_url:
            return {"error": "POSTGRES_URL not configured"}
        
        # Test direct connection
        conn = await asyncpg.connect(database_url)
        
        # Test query
        result = await conn.fetchval("SELECT 1")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        await conn.close()
        
        return {
            "success": True,
            "message": "asyncpg connection successful",
            "test_result": result,
            "tables_count": len(tables),
            "tables": [t['table_name'] for t in tables]
        }
        
    except ImportError:
        return {
            "error": "asyncpg not available",
            "fallback": "Using basic version without asyncpg"
        }
    except Exception as e:
        return {
            "error": f"asyncpg connection failed: {str(e)}"
        }

@app.get("/api/auth/topics")
async def get_topics():
    """Get all available AI topics"""
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
            "database_type": "PostgreSQL (asyncpg)" if auth_service.db.is_postgres else "SQLite"
        }
        
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@app.get("/api/database/info")
async def get_database_info():
    """Get detailed database information"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not available")
    
    try:
        # Get table counts
        table_counts = {}
        tables_to_check = ['users', 'ai_topics', 'articles', 'audio_content', 'video_content', 'daily_archives']
        
        for table in tables_to_check:
            try:
                result = await auth_service.db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = result[0]['count']
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        # Get topic categories
        topics = await auth_service.get_available_topics()
        categories = {}
        for topic in topics:
            cat = topic.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "success": True,
            "database_type": "PostgreSQL (asyncpg)" if auth_service.db.is_postgres else "SQLite",
            "database_url": auth_service.db.database_url[:50] + "...",
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

# Basic digest endpoint for compatibility
@app.get("/api/digest")
async def get_digest():
    """Basic digest endpoint for compatibility"""
    return {
        "summary": {
            "keyPoints": [
                "• Neon PostgreSQL database connected with asyncpg",
                "• Async authentication service operational",
                "• High-performance database operations enabled"
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
        "badge": "asyncpg Powered",
        "database_status": "connected" if db_available else "not connected",
        "driver": "asyncpg"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AI News Scraper API with asyncpg on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)