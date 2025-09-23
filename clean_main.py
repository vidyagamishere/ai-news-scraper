#!/usr/bin/env python3
"""
Clean main entry point for AI News Scraper API
PostgreSQL CRUD operations only - no migration code
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import simple database service
from simple_db_service import get_database_service, close_database_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting AI News Scraper API with clean PostgreSQL")
    
    try:
        # Just test database connection - no migration
        db = get_database_service()
        logger.info("✅ PostgreSQL connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI News Scraper API")
    try:
        close_database_service()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Database shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title="AI News Scraper API",
    description="Clean PostgreSQL backend for AI news aggregation",
    version="4.0.0-clean-postgresql",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://ai-news-react.vercel.app",
    "https://www.vidyagam.com",
]

# Add environment origins
env_origins = os.getenv('ALLOWED_ORIGINS', '')
if env_origins:
    allowed_origins.extend([origin.strip() for origin in env_origins.split(',')])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
async def health():
    """Health check endpoint with comprehensive table stats"""
    try:
        db = get_database_service()
        
        # Check all tables that the backend uses
        table_stats = {}
        
        # Check ai_sources table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM ai_sources")
            table_stats["ai_sources"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["ai_sources"] = f"Error: {str(e)}"
        
        # Check articles table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM articles")
            table_stats["articles"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["articles"] = f"Error: {str(e)}"
        
        # Check ai_topics table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM ai_topics")
            table_stats["ai_topics"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["ai_topics"] = f"Error: {str(e)}"
        
        # Check article_topics table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM article_topics")
            table_stats["article_topics"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["article_topics"] = f"Error: {str(e)}"
        
        # Check users table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM users")
            table_stats["users"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["users"] = f"Error: {str(e)}"
        
        return {
            "status": "healthy",
            "version": "4.0.0-clean-postgresql",
            "database": "postgresql",
            "timestamp": "2025-09-23T16:45:00Z",
            "database_stats": table_stats,
            "connection_pool": "active"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "database": "postgresql"
            }
        )

# Database schema endpoint
@app.get("/db-schema")
async def get_database_schema():
    """Get database schema and table information"""
    try:
        db = get_database_service()
        
        # Get all tables
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """
        tables_result = db.execute_query(tables_query)
        tables = [row['table_name'] for row in tables_result]
        
        # Get table details for each table
        table_details = {}
        for table in tables:
            try:
                # Get column information
                columns_query = f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """
                columns = db.execute_query(columns_query)
                
                # Get row count
                count_query = f"SELECT COUNT(*) as count FROM {table}"
                count_result = db.execute_query(count_query)
                row_count = count_result[0]['count'] if count_result else 0
                
                table_details[table] = {
                    "columns": columns,
                    "row_count": row_count
                }
            except Exception as e:
                table_details[table] = {"error": str(e)}
        
        return {
            "database": "postgresql",
            "total_tables": len(tables),
            "tables": tables,
            "table_details": table_details,
            "backend_usage": {
                "ai_sources": "Used by /sources endpoint for content source configuration",
                "articles": "Used by /digest endpoint for news content",
                "ai_topics": "Not currently used in clean backend",
                "article_topics": "Not currently used in clean backend", 
                "users": "Not currently used in clean backend (auth endpoints missing)",
                "daily_archives": "Not currently used in clean backend"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Database schema endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get database schema',
                'message': str(e)
            }
        )

# Sources endpoint  
@app.get("/sources")
async def get_sources():
    """Get all content sources"""
    try:
        db = get_database_service()
        
        sources_query = """
            SELECT name, rss_url, website, content_type, category, priority, enabled
            FROM ai_sources
            WHERE enabled = TRUE
            ORDER BY priority ASC, name ASC
        """
        
        sources = db.execute_query(sources_query)
        
        processed_sources = []
        for source in sources:
            processed_sources.append({
                'name': source['name'],
                'rss_url': source['rss_url'],
                'website': source.get('website', ''),
                'content_type': source['content_type'],
                'category': source.get('category', 'general'),
                'priority': source['priority'],
                'enabled': source['enabled']
            })
        
        return {
            'sources': processed_sources,
            'total_count': len(processed_sources),
            'enabled_count': len([s for s in processed_sources if s['enabled']]),
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get sources',
                'message': str(e),
                'database': 'postgresql'
            }
        )

# Digest endpoint
@app.get("/digest")
async def get_digest():
    """Get news digest"""
    try:
        db = get_database_service()
        
        articles_query = """
            SELECT source, title, url, published_at, description, 
                   significance_score, category, reading_time, image_url
            FROM articles
            WHERE published_at > NOW() - INTERVAL '7 days'
            ORDER BY published_at DESC, significance_score DESC
            LIMIT 50
        """
        
        articles = db.execute_query(articles_query)
        
        processed_articles = []
        for article in articles:
            article_dict = dict(article)
            
            # Convert timestamp to ISO format
            if article_dict.get('published_at'):
                article_dict['published_at'] = article_dict['published_at'].isoformat()
            
            processed_articles.append(article_dict)
        
        # Get top stories (high significance score)
        top_stories = [article for article in processed_articles if article.get('significance_score', 0) >= 8][:10]
        
        return {
            'topStories': top_stories,
            'content': {
                'blog': [a for a in processed_articles if a.get('category') == 'blogs'][:20],
                'audio': [a for a in processed_articles if a.get('category') == 'podcasts'][:10],
                'video': [a for a in processed_articles if a.get('category') == 'videos'][:10],
            },
            'summary': {
                'total_articles': len(processed_articles),
                'top_stories_count': len(top_stories),
                'latest_update': "2025-09-23T12:40:00Z"
            },
            'personalized': False,
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Digest endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get digest',
                'message': str(e),
                'database': 'postgresql'
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API - Clean PostgreSQL Version",
        "version": "4.0.0-clean-postgresql",
        "database": "postgresql",
        "status": "operational"
    }

# For Railway deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting Clean AI News Scraper API on port {port}")
    uvicorn.run(
        "clean_main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )