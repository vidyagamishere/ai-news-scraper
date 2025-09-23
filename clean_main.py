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
    """Health check endpoint"""
    try:
        db = get_database_service()
        
        # Test database connection
        result = db.execute_query("SELECT COUNT(*) as count FROM ai_sources")
        sources_count = result[0]['count'] if result else 0
        
        return {
            "status": "healthy",
            "version": "4.0.0-clean-postgresql",
            "database": "postgresql",
            "timestamp": "2025-09-23T12:40:00Z",
            "database_stats": {
                "ai_sources": sources_count,
                "connection_pool": "active"
            }
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

# Migration endpoint (temporary)
@app.post("/migrate-sources")
async def migrate_sources():
    """Create ai_sources table with comprehensive data"""
    try:
        db = get_database_service()
        
        # Drop and recreate ai_sources table
        db.execute_query("DROP TABLE IF EXISTS ai_sources CASCADE;", fetch_results=False)
        
        # Create ai_sources table
        create_table_query = """
            CREATE TABLE ai_sources (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                rss_url TEXT NOT NULL,
                website TEXT,
                content_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) DEFAULT 'general',
                enabled BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 5,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        db.execute_query(create_table_query, fetch_results=False)
        
        # Insert comprehensive AI sources
        ai_sources = [
            ("OpenAI Blog", "https://openai.com/blog/rss.xml", "https://openai.com", "blogs", "research", True, 1, "Official OpenAI blog and announcements"),
            ("Anthropic", "https://www.anthropic.com/news", "https://www.anthropic.com", "blogs", "research", True, 1, "Anthropic AI safety and research updates"),
            ("Google AI Blog", "https://ai.googleblog.com/feeds/posts/default", "https://ai.googleblog.com", "blogs", "research", True, 1, "Google AI research and developments"),
            ("DeepMind", "https://deepmind.google/discover/blog/", "https://deepmind.google", "blogs", "research", True, 1, "DeepMind research and breakthroughs"),
            ("Meta AI", "https://ai.meta.com/blog/", "https://ai.meta.com", "blogs", "research", True, 1, "Meta AI research and product updates"),
            ("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "https://www.technologyreview.com", "blogs", "business", True, 2, "MIT Technology Review AI coverage"),
            ("VentureBeat AI", "https://venturebeat.com/ai/feed/", "https://venturebeat.com", "blogs", "business", True, 2, "AI business news and trends"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "https://techcrunch.com", "blogs", "business", True, 2, "AI startup and business news"),
            ("AI News", "https://www.artificialintelligence-news.com/feed/", "https://www.artificialintelligence-news.com", "blogs", "business", True, 2, "AI industry news and analysis"),
            ("Towards Data Science", "https://towardsdatascience.com/feed", "https://towardsdatascience.com", "blogs", "technical", True, 3, "Data science and ML tutorials"),
            ("Machine Learning Mastery", "https://machinelearningmastery.com/feed/", "https://machinelearningmastery.com", "blogs", "technical", True, 3, "Practical ML tutorials and guides"),
            ("Papers with Code", "https://paperswithcode.com/feeds/papers/", "https://paperswithcode.com", "blogs", "technical", True, 3, "Latest ML papers with code implementations"),
            ("Distill", "https://distill.pub/rss.xml", "https://distill.pub", "blogs", "technical", True, 3, "Visual explanations of ML concepts"),
            ("Lex Fridman Podcast", "https://lexfridman.com/feed/podcast/", "https://lexfridman.com", "podcasts", "education", True, 4, "AI conversations with leading researchers"),
            ("NVIDIA AI Podcast", "https://blogs.nvidia.com/ai-podcast/feed/", "https://blogs.nvidia.com", "podcasts", "technical", True, 4, "NVIDIA AI developments and applications"),
            ("Two Minute Papers", "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", "https://www.youtube.com/c/TwoMinutePapers", "videos", "education", True, 5, "AI research paper explanations"),
            ("AI Explained", "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw", "https://www.youtube.com/c/AIExplained", "videos", "education", True, 5, "AI developments and explanations"),
        ]
        
        for source in ai_sources:
            insert_query = """
                INSERT INTO ai_sources (name, rss_url, website, content_type, category, enabled, priority, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_query(insert_query, source, fetch_results=False)
        
        # Create indexes
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_enabled ON ai_sources(enabled);", fetch_results=False)
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_priority ON ai_sources(priority);", fetch_results=False)
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_category ON ai_sources(category);", fetch_results=False)
        
        logger.info(f"✅ ai_sources table created successfully with {len(ai_sources)} sources")
        
        return {
            "success": True,
            "message": f"ai_sources table created successfully with {len(ai_sources)} sources",
            "sources_count": len(ai_sources)
        }
        
    except Exception as e:
        logger.error(f"❌ Migration endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Migration failed',
                'message': str(e)
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