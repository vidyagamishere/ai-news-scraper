#!/usr/bin/env python3
"""
Minimal AI News Scraper API with Neon Database Support for testing
"""
import os
import logging
from datetime import datetime

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
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API with Neon Database - Minimal Version",
        "version": "2.0.0",
        "database": "Neon Postgres",
        "status": "running",
        "environment": {
            "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
            "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
            "google_client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "database": "Neon Postgres",
        "environment": {
            "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
            "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
            "google_client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
        }
    }

@app.get("/api/test-db")
async def test_database():
    """Test database connection"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = os.getenv("POSTGRES_URL")
        if not database_url:
            return {"error": "POSTGRES_URL not configured"}
        
        # Test connection
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        conn.close()
        
        return {
            "success": True,
            "message": "Database connection successful",
            "test_result": dict(result)
        }
        
    except ImportError:
        return {
            "error": "psycopg2 not available",
            "fallback": "Using minimal version without database"
        }
    except Exception as e:
        return {
            "error": f"Database connection failed: {str(e)}"
        }

# Basic digest endpoint for compatibility
@app.get("/api/digest")
async def get_digest():
    """Basic digest endpoint"""
    return {
        "summary": {
            "keyPoints": ["• Neon database migration in progress"],
            "metrics": {"totalUpdates": 0, "highImpact": 0, "newResearch": 0, "industryMoves": 0}
        },
        "topStories": [],
        "content": {"blog": [], "audio": [], "video": []},
        "timestamp": datetime.now().isoformat(),
        "badge": "Neon Testing"
    }

# For Vercel
handler = app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting minimal AI News Scraper API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)