# main_with_auth.py - Enhanced main.py with authentication support
import os
import sqlite3
import json
import requests
import sys
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from contextlib import asynccontextmanager
import asyncio

# Handle cgi module removal in Python 3.13
try:
    import cgi
except ImportError:
    import urllib.parse as cgi
    if not hasattr(cgi, 'parse_header'):
        def parse_header(line):
            parts = line.split(';')
            main_type = parts[0].strip()
            params = {}
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key.strip()] = value.strip(' "')
            return main_type, params
        cgi.parse_header = parse_header

import feedparser
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv
import uvicorn
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import jwt

# Import authentication modules
from auth_service import AuthService
from auth_endpoints import auth_router, subscription_router, admin_router, init_auth_service

# Import multimedia components
try:
    from multimedia_scraper import (
        MultimediaDatabaseManager, 
        MultimediaScraper, 
        MultimediaContentProcessor
    )
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False
    print("Warning: Multimedia components not available. Running in basic mode.")

# Import enhanced source configuration
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from ai_sources_config import CONTENT_TYPES, get_sources_by_content_type, get_enabled_sources_by_type

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ai_news_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration with authentication support
CONFIG = {
    "DATABASE_PATH": os.getenv("DATABASE_PATH", "/Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper/ai_news.db"),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    "MAX_ARTICLES_PER_SOURCE": int(os.getenv("MAX_ARTICLES_PER_SOURCE", "10")),
    "CACHE_ENABLED": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "CACHE_TTL": int(os.getenv("CACHE_TTL", "3600")),
    "REQUEST_DELAY": float(os.getenv("REQUEST_DELAY", "1.0")),
    "MAX_RETRIES": int(os.getenv("MAX_RETRIES", "3")),
    "RETRY_DELAY": int(os.getenv("RETRY_DELAY", "2")),
    "JWT_SECRET": os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production"),
    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
    "EMAIL_ENABLED": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
    "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "*").split(",")
}

# Global variables for app state
db_manager = None
scraper = None
processor = None
cache_manager = None
scheduler = None
multimedia_db_manager = None
multimedia_scraper = None
multimedia_processor = None
email_service = None
auth_service = None
scraping_status = {"in_progress": False, "last_run": None, "errors": []}

class CacheManager:
    def __init__(self):
        self.memory_cache = {}
        self.cache_enabled = CONFIG["CACHE_ENABLED"]
        logger.info("Using memory cache (Redis not required)")
    
    def get(self, key: str) -> Optional[str]:
        if not self.cache_enabled:
            return None
        return self.memory_cache.get(key)
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        if not self.cache_enabled:
            return False
        self.memory_cache[key] = value
        # Simple TTL for memory cache
        asyncio.create_task(self._expire_memory_key(key, ttl or CONFIG["CACHE_TTL"]))
        return True
    
    async def _expire_memory_key(self, key: str, ttl: int):
        await asyncio.sleep(ttl)
        self.memory_cache.pop(key, None)

class RateLimiter:
    def __init__(self, max_requests: int = 30, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = []
    
    def can_make_request(self) -> bool:
        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True

# Database and core classes (importing from existing implementation)
from ai_sources_config import AI_SOURCES

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced articles table with user association
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                description TEXT,
                published_date TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT UNIQUE,
                importance_score REAL DEFAULT 0.5,
                category TEXT,
                tags TEXT,
                summary TEXT,
                processed BOOLEAN DEFAULT 0,
                visible_to_free BOOLEAN DEFAULT 1,
                premium_only BOOLEAN DEFAULT 0
            )
        ''')
        
        # Digest cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digest_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                user_tier TEXT DEFAULT 'free'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_article(self, article_data: Dict, premium_only: bool = False) -> bool:
        """Add article to database with premium/free designation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            content_hash = hashlib.md5(
                f"{article_data['title']}{article_data['url']}".encode()
            ).hexdigest()
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (title, url, source, description, published_date, content_hash, 
                 importance_score, category, tags, premium_only, visible_to_free)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_data['title'],
                article_data['url'],
                article_data['source'],
                article_data.get('description', ''),
                article_data.get('published_date', ''),
                content_hash,
                article_data.get('importance_score', 0.5),
                article_data.get('category', 'general'),
                json.dumps(article_data.get('tags', [])),
                premium_only,
                not premium_only
            ))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding article: {e}")
            return False
        finally:
            conn.close()
    
    def get_recent_articles(self, hours: int = 24, user_tier: str = 'free') -> List[Dict]:
        """Get recent articles based on user subscription tier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Filter articles based on subscription tier
        if user_tier == 'premium':
            tier_filter = ""
        else:
            tier_filter = "AND visible_to_free = 1"
        
        cursor.execute(f'''
            SELECT id, title, url, source, content, published_date, 
                   significance_score, category, '' as tags, CASE WHEN significance_score > 0.7 THEN 1 ELSE 0 END as premium_only
            FROM articles 
            WHERE created_at > datetime('now', '-{hours} hours')
            ORDER BY significance_score DESC, created_at DESC
            LIMIT 100
        ''')
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'source': row[3],
                'description': row[4],
                'published_date': row[5],
                'significanceScore': row[6],
                'category': row[7],
                'tags': json.loads(row[8]) if row[8] else [],
                'premium_only': bool(row[9])
            })
        
        conn.close()
        return articles

# Enhanced FastAPI app with authentication
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global db_manager, scraper, processor, cache_manager, scheduler
    global multimedia_db_manager, multimedia_scraper, multimedia_processor
    global email_service, auth_service
    
    logger.info("Starting AI News Scraper API with Authentication...")
    
    try:
        # Initialize core components
        db_manager = DatabaseManager(CONFIG["DATABASE_PATH"])
        cache_manager = CacheManager()
        
        # Initialize authentication service
        auth_service = AuthService(
            db_path=CONFIG["DATABASE_PATH"],
            jwt_secret=CONFIG["JWT_SECRET"],
            google_client_id=CONFIG["GOOGLE_CLIENT_ID"]
        )
        init_auth_service(auth_service)
        
        # Initialize multimedia components if available
        # Temporarily disabled for testing
        if False and MULTIMEDIA_AVAILABLE:
            multimedia_db_manager = MultimediaDatabaseManager(CONFIG["DATABASE_PATH"])
            multimedia_scraper = MultimediaScraper()
            multimedia_processor = MultimediaContentProcessor(
                anthropic_api_key=CONFIG["ANTHROPIC_API_KEY"]
            )
        
        # Initialize email service if enabled
        if CONFIG["EMAIL_ENABLED"]:
            try:
                from email_service import EmailService
                email_service = EmailService()
            except ImportError:
                logger.warning("Email service not available")
        
        # Initialize scheduler for automated tasks
        scheduler = AsyncIOScheduler()
        
        # Schedule automatic scraping (less frequent for free users)
        scheduler.add_job(
            scheduled_scraping,
            CronTrigger(hour="*/4"),  # Every 4 hours
            id="auto_scraping",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Cleanup
        if scheduler:
            scheduler.shutdown()
        logger.info("Services shut down")

# Create FastAPI app with authentication
app = FastAPI(
    title="AI News Scraper API with Authentication",
    description="Enhanced AI News aggregation and digest API with user authentication and subscription tiers",
    version="2.0.0",
    lifespan=lifespan
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["CORS_ORIGINS"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include authentication routers
app.include_router(auth_router)
app.include_router(subscription_router)
app.include_router(admin_router)

# Enhanced models with user context
class DigestRequest(BaseModel):
    refresh: bool = False
    user_tier: str = 'free'
    personalized: bool = False

class PersonalizedDigestRequest(BaseModel):
    refresh: bool = False
    topics: Optional[List[str]] = None
    content_types: Optional[List[str]] = None

# Helper functions
async def get_current_user_tier(authorization: Optional[str] = None) -> str:
    """Get current user's subscription tier from token"""
    if not authorization or not auth_service:
        return 'free'
    
    try:
        # Remove 'Bearer ' prefix
        token = authorization.replace('Bearer ', '')
        user = auth_service.get_user_by_token(token)
        return user.subscription_tier.value if user else 'free'
    except:
        return 'free'

async def scheduled_scraping():
    """Scheduled scraping task"""
    try:
        logger.info("Starting scheduled scraping...")
        # Implementation would go here
        logger.info("Scheduled scraping completed")
    except Exception as e:
        logger.error(f"Scheduled scraping failed: {e}")

# Enhanced API endpoints
@app.get("/health")
async def health_check():
    """Enhanced health check with authentication status"""
    components = {
        "database": "healthy" if db_manager else "unavailable",
        "cache": "healthy" if cache_manager else "unavailable",
        "auth": "healthy" if auth_service else "unavailable",
        "multimedia": "healthy" if MULTIMEDIA_AVAILABLE and multimedia_db_manager else "unavailable",
        "email": "healthy" if email_service else "disabled",
    }
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "components": components,
        "features": {
            "authentication": True,
            "subscription_tiers": True,
            "multimedia": MULTIMEDIA_AVAILABLE,
            "email_service": CONFIG["EMAIL_ENABLED"]
        }
    }

@app.get("/api/digest")
async def get_digest(
    refresh: bool = False,
    authorization: Optional[str] = None
):
    """Get AI news digest with subscription tier filtering"""
    try:
        # Determine user tier
        user_tier = await get_current_user_tier(authorization)
        
        # Check cache first
        cache_key = f"digest_{user_tier}_{datetime.now().strftime('%Y%m%d%H')}"
        if not refresh and cache_manager:
            cached_digest = cache_manager.get(cache_key)
            if cached_digest:
                return json.loads(cached_digest)
        
        # Get articles based on user tier
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        articles = db_manager.get_recent_articles(hours=168, user_tier=user_tier)  # 7 days
        
        if not articles:
            return {
                "error": "No recent articles found",
                "articles": [],
                "total": 0,
                "user_tier": user_tier,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Create digest based on subscription tier
        digest = await create_tiered_digest(articles, user_tier)
        
        # Cache the result
        if cache_manager:
            cache_manager.set(cache_key, json.dumps(digest), ttl=3600)
        
        return digest
        
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate digest: {str(e)}")

def categorize_articles_by_content_type(articles: List[Dict], content_type: str) -> List[Dict]:
    """Intelligently categorize articles by content type using keywords and patterns"""
    
    # Keywords for each content type - Enhanced for new categories
    categorization_keywords = {
        "events": [
            "conference", "workshop", "summit", "meetup", "webinar", "symposium",
            "event", "registration", "attend", "speaker", "presentation", "talk",
            "hackathon", "competition", "expo", "fair", "gathering", "forum",
            "neurips", "icml", "iclr", "aaai", "ijcai", "cvpr", "eccv", "iccv"
        ],
        "learn": [
            "course", "tutorial", "learn", "training", "education", "teach",
            "guide", "how to", "beginner", "advanced", "certification", "bootcamp",
            "lesson", "curriculum", "study", "skill", "knowledge", "master",
            "coursera", "edx", "udacity", "udemy", "khan academy", "fast.ai",
            "deeplearning.ai", "stanford", "mit", "berkeley", "carnegie mellon"
        ],
        "blogs": [
            "blog", "opinion", "insight", "analysis", "perspective", "commentary",
            "thoughts", "reflection", "review", "critique", "discussion", "essay",
            "medium", "substack", "towards data science", "gradient", "distill"
        ],
        "podcasts": [
            "podcast", "episode", "interview", "conversation", "discussion", "talk show",
            "audio", "listen", "lex fridman", "machine learning street talk", "twiml",
            "gradient dissent", "spotify", "apple podcasts", "anchor"
        ],
        "videos": [
            "video", "youtube", "watch", "presentation", "demo", "tutorial video",
            "webinar", "livestream", "recording", "two minute papers", "3blue1brown",
            "yannic kilcher", "ai explained", "deeplearning.ai"
        ],
        "all_sources": [
            # All sources - this will be handled differently
        ]
    }
    
    # Handle "all_sources" - return all articles
    if content_type == "all_sources":
        return articles
    
    # Get keywords for the specific content type
    keywords = categorization_keywords.get(content_type, [])
    
    # If no keywords defined, return empty list
    if not keywords:
        return []
    
    filtered_articles = []
    for article in articles:
        title_lower = article.get('title', '').lower()
        description_lower = article.get('description', '').lower()
        source_lower = article.get('source', '').lower()
        content_text = f"{title_lower} {description_lower} {source_lower}"
        
        # Check if article matches content type keywords
        if any(keyword in content_text for keyword in keywords):
            # Update the category field to match content type
            article_copy = article.copy()
            article_copy['category'] = content_type
            filtered_articles.append(article_copy)
    
    return filtered_articles

async def create_tiered_digest(articles: List[Dict], user_tier: str) -> Dict:
    """Create digest based on user subscription tier"""
    
    # Base digest structure
    digest = {
        "badge": f"{'Premium ' if user_tier == 'premium' else ''}AI Digest",
        "timestamp": datetime.utcnow().isoformat(),
        "user_tier": user_tier,
        "total_articles": len(articles),
        "summary": {
            "metrics": {
                "totalStories": len(articles),
                "highImpact": len([a for a in articles if a.get('importance_score', 0) > 0.8]),
                "categories": len(set(a.get('category', 'general') for a in articles))
            },
            "keyPoints": [
                "AI news aggregated from trusted sources",
                f"{'Premium content included' if user_tier == 'premium' else 'Free tier access'}",
                f"Updated {datetime.now().strftime('%B %d, %Y')}"
            ]
        },
        "topStories": articles[:10 if user_tier == 'premium' else 5],
        "content": {
            "blog": articles[:20 if user_tier == 'premium' else 10],
            "audio": articles[:10 if user_tier == 'premium' else 3],
            "video": articles[:10 if user_tier == 'premium' else 3]
        }
    }
    
    # Add premium-specific features
    if user_tier == 'premium':
        digest["premium_features"] = {
            "daily_digest": True,
            "ai_events": True,
            "learning_resources": True,
            "export_pdf": True
        }
    
    return digest

@app.get("/api/content-types")
async def get_content_types():
    """Get available content types with descriptions"""
    return {"content_types": CONTENT_TYPES}

@app.get("/topics")
async def get_topics():
    """Get available AI topics for user preferences"""
    topics = [
        {"id": "machine_learning", "name": "Machine Learning", "description": "ML algorithms and techniques", "category": "technology", "selected": False},
        {"id": "nlp", "name": "Natural Language Processing", "description": "Text and language AI", "category": "technology", "selected": False},
        {"id": "computer_vision", "name": "Computer Vision", "description": "Image and video AI", "category": "technology", "selected": False},
        {"id": "robotics", "name": "Robotics", "description": "AI-powered robotics", "category": "technology", "selected": False},
        {"id": "ai_ethics", "name": "AI Ethics", "description": "Ethical AI development", "category": "ethics", "selected": False},
        {"id": "ai_research", "name": "AI Research", "description": "Latest AI research papers", "category": "research", "selected": False},
        {"id": "ai_industry", "name": "AI Industry", "description": "Industry applications", "category": "industry", "selected": False},
        {"id": "ai_startups", "name": "AI Startups", "description": "AI startup ecosystem", "category": "industry", "selected": False}
    ]
    return topics

@app.get("/content-types")
async def get_content_types_alt():
    """Get available content types - alternative endpoint without /api prefix"""
    return {"content_types": CONTENT_TYPES}

@app.get("/content/{content_type}")
async def get_content_by_type_alt(
    content_type: str,
    authorization: Optional[str] = None,
    refresh: bool = False
):
    """Get content filtered by type - alternative endpoint without /api prefix"""
    return await get_content_by_type(content_type, authorization, refresh)

@app.get("/api/content/{content_type}")
async def get_content_by_type(
    content_type: str,
    authorization: Optional[str] = None,
    refresh: bool = False
):
    """Get content filtered by type (articles, events, learning)"""
    try:
        # Validate content type
        if content_type not in CONTENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid content type. Available types: {list(CONTENT_TYPES.keys())}"
            )
        
        # Determine user tier
        user_tier = await get_current_user_tier(authorization)
        
        # Check cache first
        cache_key = f"content_{content_type}_{user_tier}_{datetime.now().strftime('%Y%m%d%H')}"
        if not refresh and cache_manager:
            cached_content = cache_manager.get(cache_key)
            if cached_content:
                return json.loads(cached_content)
        
        # Get sources for this content type
        sources = get_enabled_sources_by_type(content_type)
        
        if not sources:
            return {
                "content_type": content_type,
                "content_info": CONTENT_TYPES[content_type],
                "articles": [],
                "total": 0,
                "sources_available": 0,
                "user_tier": user_tier,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get articles from database filtered by content type sources
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get articles and intelligently categorize by content
        all_articles = db_manager.get_recent_articles(hours=168, user_tier='free')  # 7 days, all users
        
        # Intelligent content categorization
        articles = categorize_articles_by_content_type(all_articles, content_type)
        
        # If no recent articles found, try older content as fallback
        if not articles and content_type in ["events", "learning"]:
            older_articles = db_manager.get_recent_articles(hours=720, user_tier='free')  # 30 days
            articles = categorize_articles_by_content_type(older_articles, content_type)
        
        # Limit based on subscription tier (but make events/learning available to all)
        if content_type in ["events", "learning"]:
            max_articles = 10  # Available to all users
        else:
            max_articles = 20 if user_tier == 'premium' else 10
            
        limited_articles = articles[:max_articles]
        
        result = {
            "content_type": content_type,
            "content_info": CONTENT_TYPES[content_type],
            "articles": limited_articles,
            "total": len(limited_articles),
            "total_available": len(articles),
            "sources_available": len(sources),
            "user_tier": user_tier,
            "timestamp": datetime.utcnow().isoformat(),
            "featured_sources": [{"name": s["name"], "website": s["website"]} for s in sources[:5]]
        }
        
        # Cache the result
        if cache_manager:
            cache_manager.set(cache_key, json.dumps(result), ttl=1800)  # 30 minutes
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting content by type {content_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get {content_type} content: {str(e)}")

@app.get("/api/user-preferences")
async def get_user_content_preferences(
    authorization: Optional[str] = None
):
    """Get user's content preferences based on their selected topics and subscription"""
    try:
        user_tier = await get_current_user_tier(authorization)
        
        # Get user's topic preferences if authenticated
        user_preferences = {}
        if authorization:
            # In a real implementation, you'd get this from the user's profile
            user_preferences = {
                "selected_topics": ["AI & Robotics", "Machine Learning", "Natural Language Processing"],
                "content_types": ["articles", "events", "learning"],
                "notification_frequency": "daily" if user_tier == "premium" else "weekly"
            }
        
        # Get recommended content types based on user tier
        recommended_content_types = ["articles"]
        if user_tier == "premium":
            recommended_content_types.extend(["events", "learning"])
        
        return {
            "user_tier": user_tier,
            "preferences": user_preferences,
            "recommended_content_types": recommended_content_types,
            "available_content_types": CONTENT_TYPES,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user preferences: {str(e)}")

@app.post("/api/scrape")
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = None
):
    """Trigger manual scraping (premium users get priority)"""
    user_tier = await get_current_user_tier(authorization)
    
    if scraping_status["in_progress"]:
        return {
            "message": "Scraping already in progress",
            "status": "in_progress",
            "estimated_completion": "2-5 minutes"
        }
    
    background_tasks.add_task(perform_scraping, user_tier)
    
    return {
        "message": "Scraping started",
        "status": "started",
        "user_tier": user_tier,
        "priority": "high" if user_tier == "premium" else "normal"
    }

async def perform_scraping(user_tier: str):
    """Perform the actual scraping with tier-based priorities"""
    global scraping_status
    
    try:
        scraping_status["in_progress"] = True
        scraping_status["errors"] = []
        
        logger.info(f"Starting scraping for {user_tier} tier")
        
        # Implementation would include the actual scraping logic
        # For now, this is a placeholder
        await asyncio.sleep(2)  # Simulate scraping time
        
        scraping_status["last_run"] = datetime.utcnow().isoformat()
        logger.info(f"Scraping completed for {user_tier} tier")
        
    except Exception as e:
        error_msg = f"Scraping failed: {str(e)}"
        logger.error(error_msg)
        scraping_status["errors"].append(error_msg)
    finally:
        scraping_status["in_progress"] = False

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main_with_auth:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )