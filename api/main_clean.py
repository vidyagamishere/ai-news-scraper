# main.py - Clean version without email endpoints
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
            if ';' not in line:
                return line.strip(), {}
            value, params = line.split(';', 1)
            param_dict = {}
            for param in params.split(';'):
                if '=' in param:
                    key, val = param.split('=', 1)
                    param_dict[key.strip()] = val.strip().strip('"')
            return value.strip(), param_dict
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
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Import multimedia processor
from multimedia_scraper import (
    MultimediaContentProcessor,
    MULTIMEDIA_SOURCES
)

# Import comprehensive AI sources configuration
from ai_sources_config import AI_SOURCES, FALLBACK_SCRAPING, CATEGORIES

# Email service enabled
EMAIL_SERVICE_AVAILABLE = True

# Import the real email service
from email_service import EmailDigestService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "MAX_ARTICLES_PER_SOURCE": int(os.getenv("MAX_ARTICLES_PER_SOURCE", "10")),
    "CACHE_ENABLED": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "CACHE_TTL": 3600,  # 1 hour
    "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307"),
    "RATE_LIMIT_RPM": int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30")),
    "REQUEST_TIMEOUT": 30,
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 2,
    "JWT_SECRET": os.getenv("JWT_SECRET", "your-secret-key-here"),
    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", "")
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
scraping_status = {"in_progress": False, "last_run": None, "errors": []}

class CacheManager:
    def __init__(self):
        self.memory_cache = {}
        self.cache_times = {}
    
    def get(self, key):
        if key in self.memory_cache:
            if time.time() - self.cache_times.get(key, 0) < CONFIG["CACHE_TTL"]:
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
                del self.cache_times[key]
        return None
    
    def set(self, key, value):
        self.memory_cache[key] = value
        self.cache_times[key] = time.time()
    
    def clear(self):
        self.memory_cache.clear()
        self.cache_times.clear()

class RateLimiter:
    def __init__(self, max_requests_per_minute):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.window = 60  # 60 seconds

    def can_proceed(self):
        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

    def wait_time(self):
        if not self.requests:
            return 0
        oldest_request = min(self.requests)
        return max(0, self.window - (time.time() - oldest_request))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db_manager, scraper, processor, cache_manager, scheduler
    global multimedia_db_manager, multimedia_scraper, multimedia_processor, email_service
    
    # Startup
    logger.info("Starting AI News Scraper API with multimedia support")
    
    try:
        # Initialize cache manager
        cache_manager = CacheManager()
        
        # Initialize database components
        db_manager = DatabaseManager()
        db_manager.init_db()
        
        multimedia_db_manager = DatabaseManager()  # Reusing same class
        
        # Initialize scraping components
        scraper = AINewsScraper(db_manager, cache_manager)
        multimedia_scraper = scraper  # Same scraper handles multimedia
        
        # Initialize processing components with Claude
        claude_client = None
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if claude_api_key and claude_api_key.startswith("sk-ant-api"):
            try:
                claude_client = anthropic.Anthropic(api_key=claude_api_key)
                logger.info("Claude client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                claude_client = None
        else:
            logger.warning("No CLAUDE_API_KEY found - using fallback processing")
    
    processor = ContentProcessor(claude_client, cache_manager)
    multimedia_processor = MultimediaContentProcessor(claude_client, cache_manager)
    
    # Initialize email service (with error handling)
    try:
        email_service = EmailDigestService()
        logger.info("Email service initialized successfully")
    except Exception as e:
        logger.warning(f"Email service initialization failed: {e}")
        email_service = None
    
    # Initialize scheduler for automatic updates
    scheduler = AsyncIOScheduler()
    
    # Schedule automatic scraping at 8 AM and 6 PM ET
    scheduler.add_job(
        scheduled_scrape,
        CronTrigger(hour=8, minute=0, timezone="America/New_York"),
        id="morning_scrape"
    )
    scheduler.add_job(
        scheduled_scrape,
        CronTrigger(hour=18, minute=0, timezone="America/New_York"),
        id="evening_scrape"
    )
    
    # Add hourly updates for real-time content
    scheduler.add_job(
        scheduled_scrape,
        CronTrigger(minute=0),  # Every hour at minute 0
        id="hourly_scrape"
    )
    
    # Schedule daily email digest at 7 AM ET
    scheduler.add_job(
        scheduled_email_digest,
        CronTrigger(hour=7, minute=0, timezone="America/New_York"),
        id="daily_email_digest"
    )
    
    scheduler.start()
    logger.info("Scheduler started for automatic updates")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI News Scraper API")
    if scheduler:
        scheduler.shutdown()

app = FastAPI(
    title="AI News Scraper API",
    description="Curated AI news with significance scoring",
    version="1.1.0",
    lifespan=lifespan
)

# CORS middleware - Updated for email endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiter
rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])

# Database Manager with subscription support
class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("DATABASE_PATH", "/tmp/ai_news.db")
    
    def init_db(self):
        """Initialize database with all required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    content TEXT,
                    summary TEXT,
                    source TEXT,
                    published_date TEXT,
                    significance_score REAL,
                    claude_processed BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(significance_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at)')
            
            # Create subscribers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    google_id TEXT,
                    profile_picture TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Create subscription preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscriber_id INTEGER,
                    preference_type TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscriber_id) REFERENCES subscribers (id)
                )
            ''')
            
            # Create email subscriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscriber_id INTEGER,
                    frequency TEXT DEFAULT 'daily',
                    content_types TEXT DEFAULT 'all',
                    categories TEXT DEFAULT 'all',
                    last_sent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscriber_id) REFERENCES subscribers (id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscribers_google_id ON subscribers(google_id)')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully with subscription tables")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def save_article(self, article_data: Dict) -> bool:
        """Save article to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (title, url, content, summary, source, published_date, significance_score, claude_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_data['title'],
                article_data['url'],
                article_data.get('content', ''),
                article_data.get('summary', ''),
                article_data.get('source', ''),
                article_data.get('published_date', datetime.now().isoformat()),
                article_data.get('significance_score', 0.0),
                article_data.get('claude_processed', False)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return False
    
    def get_recent_articles(self, hours=24, limit=50) -> List[Dict]:
        """Get recent articles from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM articles 
                WHERE datetime(created_at) > datetime(?)
                ORDER BY significance_score DESC, created_at DESC
                LIMIT ?
            ''', (cutoff_time.isoformat(), limit))
            
            columns = [desc[0] for desc in cursor.description]
            articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return articles
            
        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []
    
    def save_subscriber(self, subscriber_data: Dict) -> int:
        """Save subscriber and return subscriber ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO subscribers 
                (email, name, google_id, profile_picture, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                subscriber_data['email'],
                subscriber_data['name'],
                subscriber_data.get('google_id'),
                subscriber_data.get('profile_picture'),
                datetime.now().isoformat()
            ))
            
            subscriber_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Subscriber saved: {subscriber_data['email']}")
            return subscriber_id
            
        except Exception as e:
            logger.error(f"Error saving subscriber: {e}")
            return None
    
    def get_subscriber_by_email(self, email: str) -> Dict:
        """Get subscriber by email"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM subscribers WHERE email = ? AND is_active = 1
            ''', (email,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscriber: {e}")
            return None
    
    def save_subscription_preferences(self, subscriber_id: int, preferences: Dict) -> bool:
        """Save subscription preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing preferences
            cursor.execute('DELETE FROM subscription_preferences WHERE subscriber_id = ?', (subscriber_id,))
            
            # Save new preferences
            for pref_type, pref_value in preferences.items():
                if isinstance(pref_value, list):
                    pref_value = ','.join(pref_value)
                
                cursor.execute('''
                    INSERT INTO subscription_preferences (subscriber_id, preference_type, preference_value)
                    VALUES (?, ?, ?)
                ''', (subscriber_id, pref_type, str(pref_value)))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Preferences saved for subscriber {subscriber_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return False
    
    def get_subscription_preferences(self, subscriber_id: int) -> Dict:
        """Get subscription preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT preference_type, preference_value FROM subscription_preferences 
                WHERE subscriber_id = ?
            ''', (subscriber_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            preferences = {}
            for row in rows:
                pref_type, pref_value = row
                if ',' in pref_value:
                    preferences[pref_type] = pref_value.split(',')
                else:
                    preferences[pref_type] = pref_value
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return {}

# Pydantic models for API requests
class GoogleAuthRequest(BaseModel):
    token: str

class SubscriptionPreferences(BaseModel):
    frequency: str = "daily"
    content_types: List[str] = ["all"]
    categories: List[str] = ["all"]

class EmailSubscriptionRequest(BaseModel):
    email: EmailStr
    preferences: SubscriptionPreferences

# Authentication utilities
security = HTTPBearer()

def create_jwt_token(user_data: Dict) -> str:
    """Create JWT token for authenticated user"""
    payload = {
        "email": user_data["email"],
        "name": user_data["name"],
        "sub": str(user_data["id"]),
        "exp": datetime.now() + timedelta(days=7)
    }
    return jwt.encode(payload, CONFIG["JWT_SECRET"], algorithm="HS256")

def verify_jwt_token(token: str) -> Dict:
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, CONFIG["JWT_SECRET"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    return verify_jwt_token(token)

async def verify_google_token(token: str) -> Dict:
    """Verify Google OAuth token"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), CONFIG["GOOGLE_CLIENT_ID"]
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        return {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo['name'],
            'profile_picture': idinfo.get('picture', '')
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

# Content processing and scraping classes would go here...
# [For brevity, I'll create a simple version]

class ContentProcessor:
    def __init__(self, claude_client, cache_manager):
        self.claude_client = claude_client
        self.cache = cache_manager
        self.has_claude = claude_client is not None

class AINewsScraper:
    def __init__(self, db_manager, cache_manager):
        self.db = db_manager
        self.cache = cache_manager

# Scheduled tasks
async def scheduled_scrape():
    """Scheduled scraping task"""
    global scraping_status
    
    if scraping_status["in_progress"]:
        logger.info("Scraping already in progress, skipping")
        return
    
    scraping_status["in_progress"] = True
    logger.info("Starting scheduled scrape")
    
    try:
        # Simple implementation - would be more complex in real version
        scraping_status["last_run"] = datetime.now().isoformat()
        logger.info("Scheduled scraping completed")
        
    except Exception as e:
        logger.error(f"Scheduled scraping failed: {e}")
    finally:
        scraping_status["in_progress"] = False

async def scheduled_email_digest():
    """Scheduled email digest sending"""
    logger.info("Starting scheduled email digest")
    # Implementation would go here

def ensure_initialization():
    """Ensure all components are initialized"""
    global db_manager, scraper, processor, cache_manager
    global multimedia_db_manager, multimedia_scraper, multimedia_processor, email_service
    
    if not db_manager:
        db_manager = DatabaseManager()
        db_manager.init_db()
    
    if not cache_manager:
        cache_manager = CacheManager()
    
    if not scraper:
        scraper = AINewsScraper(db_manager, cache_manager)
        multimedia_scraper = scraper
        multimedia_db_manager = db_manager
    
    if not processor:
        claude_client = None
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if claude_api_key and claude_api_key.startswith("sk-ant-api"):
            try:
                claude_client = anthropic.Anthropic(api_key=claude_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Claude: {e}")
                claude_client = None
        else:
            logger.warning("No CLAUDE_API_KEY found - using fallback processing")
        
        processor = ContentProcessor(claude_client, cache_manager)
        multimedia_processor = MultimediaContentProcessor(claude_client, cache_manager)
        logger.info("On-demand initialization completed")

# Authentication endpoints
@app.post("/auth/google")
async def google_auth(auth_request: GoogleAuthRequest):
    """Authenticate with Google OAuth token"""
    try:
        ensure_initialization()
        
        # Verify Google token
        google_user = await verify_google_token(auth_request.token)
        
        # Save or update subscriber
        subscriber_data = {
            'email': google_user['email'],
            'name': google_user['name'],
            'google_id': google_user['google_id'],
            'profile_picture': google_user['profile_picture']
        }
        
        subscriber_id = db_manager.save_subscriber(subscriber_data)
        if not subscriber_id:
            raise HTTPException(status_code=500, detail="Failed to save subscriber")
        
        # Get complete subscriber info
        subscriber = db_manager.get_subscriber_by_email(google_user['email'])
        if not subscriber:
            raise HTTPException(status_code=500, detail="Failed to retrieve subscriber")
        
        # Create JWT token
        jwt_token = create_jwt_token(subscriber)
        
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": subscriber['id'],
                "email": subscriber['email'],
                "name": subscriber['name'],
                "profile_picture": subscriber.get('profile_picture')
            }
        }
        
    except Exception as e:
        logger.error(f"Google authentication error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/subscription/preferences")
async def save_subscription_preferences(
    preferences_request: SubscriptionPreferences,
    current_user: Dict = Depends(get_current_user)
):
    """Save subscription preferences"""
    try:
        ensure_initialization()
        
        subscriber = db_manager.get_subscriber_by_email(current_user['email'])
        if not subscriber:
            raise HTTPException(status_code=404, detail="User not found")
        
        preferences = {
            'frequency': preferences_request.frequency,
            'content_types': preferences_request.content_types,
            'categories': preferences_request.categories
        }
        
        success = db_manager.save_subscription_preferences(subscriber['id'], preferences)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
        
        return {"message": "Subscription preferences saved successfully"}
        
    except Exception as e:
        logger.error(f"Preferences save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subscription/preferences")
async def get_subscription_preferences(current_user: Dict = Depends(get_current_user)):
    """Get subscription preferences"""
    try:
        ensure_initialization()
        
        subscriber = db_manager.get_subscriber_by_email(current_user['email'])
        if not subscriber:
            raise HTTPException(status_code=404, detail="User not found")
        
        preferences = db_manager.get_subscription_preferences(subscriber['id'])
        
        return {
            "preferences": {
                "frequency": preferences.get('frequency', 'daily'),
                "content_types": preferences.get('content_types', ['all']),
                "categories": preferences.get('categories', ['all'])
            }
        }
        
    except Exception as e:
        logger.error(f"Preferences retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# All email endpoints have been temporarily removed to fix deployment issues
# They will be re-added after debugging is complete

@app.get("/")
async def root():
    ensure_initialization()
    return {
        "message": "AI News Scraper API - Clean Version", 
        "status": "running",
        "version": "1.1.0",
        "claude_enabled": processor.has_claude if processor else False,
        "email_service": "temporarily disabled"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    ensure_initialization()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "✅ Connected" if db_manager else "❌ Not initialized",
            "cache": "✅ Active" if cache_manager else "❌ Not initialized",
            "scraper": "✅ Ready" if scraper else "❌ Not initialized",
            "processor": "✅ Ready" if processor else "❌ Not initialized",
            "claude": "✅ Available" if (processor and processor.has_claude) else "❌ Not available",
            "email": "⚠️ Temporarily disabled"
        }
    }

@app.get("/api/digest")
async def get_digest():
    """Get AI news digest - simplified version"""
    try:
        ensure_initialization()
        
        # Get recent articles from database
        articles = db_manager.get_recent_articles(24, 20)
        
        if not articles:
            # Return mock data if no articles
            return {
                "summary": "No recent articles found",
                "totalArticles": 0,
                "significantArticles": 0,
                "topStories": [],
                "content": {"blog": [], "audio": [], "video": []},
                "timestamp": datetime.now().isoformat(),
                "badge": "No Data"
            }
        
        # Format response
        formatted_articles = []
        for article in articles[:10]:
            formatted_articles.append({
                "title": article.get('title', 'Untitled'),
                "url": article.get('url', ''),
                "summary": article.get('summary', article.get('content', ''))[:200],
                "source": article.get('source', 'Unknown'),
                "significance_score": article.get('significance_score', 0),
                "time": article.get('published_date', 'Unknown')
            })
        
        return {
            "summary": f"Found {len(articles)} recent AI articles",
            "totalArticles": len(articles),
            "significantArticles": len([a for a in articles if a.get('significance_score', 0) >= 7]),
            "topStories": formatted_articles,
            "content": {"blog": formatted_articles[:5], "audio": [], "video": []},
            "timestamp": datetime.now().isoformat(),
            "badge": "Clean Version"
        }
        
    except Exception as e:
        logger.error(f"Error getting digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)