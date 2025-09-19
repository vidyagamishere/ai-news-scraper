# main.py - Fixed indentation with multimedia support
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
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv
import uvicorn
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import multimedia components
from multimedia_scraper import (
    MultimediaDatabaseManager, 
    MultimediaScraper, 
    MultimediaContentProcessor,
    MULTIMEDIA_SOURCES
)

# Import authentication components
from api.auth_endpoints import auth_router, subscription_router, admin_router, init_auth_service
from api.auth_service_postgres import AuthService

# Import comprehensive AI sources configuration
from ai_sources_config import AI_SOURCES, FALLBACK_SCRAPING, CATEGORIES

# Load environment variables
load_dotenv()

# Configure logging
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
logging.basicConfig(
    level=log_level,
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
    "RETRY_DELAY": 2
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
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def wait_time(self) -> float:
        if not self.requests:
            return 0
        oldest_request = min(self.requests)
        return max(0, self.window - (time.time() - oldest_request))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db_manager, scraper, processor, cache_manager, scheduler, auth_service
    global multimedia_db_manager, multimedia_scraper, multimedia_processor
    
    # Startup
    logger.info("Starting AI News Scraper API with multimedia support")
    
    # Initialize components
    cache_manager = CacheManager()
    db_manager = DatabaseManager(os.getenv("DATABASE_PATH", "ai_news.db"))
    scraper = AINewsScraper(db_manager, cache_manager)
    
    # Initialize authentication service
    # Use POSTGRES_URL if available, otherwise fallback to DATABASE_PATH
    database_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_PATH", "ai_news.db")
    auth_service = AuthService(
        database_url=database_url,
        jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID")
    )
    init_auth_service(auth_service)
    
    # Initialize multimedia components
    multimedia_db_manager = MultimediaDatabaseManager(os.getenv("DATABASE_PATH", "ai_news.db"))
    rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])
    multimedia_scraper = MultimediaScraper(multimedia_db_manager, cache_manager, rate_limiter)
    
    # Initialize Anthropic client
    claude_client = None
    api_key = os.getenv("CLAUDE_API_KEY")
    
    if api_key:
        try:
            claude_client = anthropic.Anthropic(api_key=api_key)
            # Test the client
            test_response = claude_client.messages.create(
                model=CONFIG["CLAUDE_MODEL"],
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            logger.info("Claude API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            claude_client = None
    else:
        logger.warning("No CLAUDE_API_KEY found - using fallback processing")
    
    processor = ContentProcessor(claude_client, cache_manager)
    multimedia_processor = MultimediaContentProcessor(claude_client, cache_manager)
    
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
    
    scheduler.start()
    logger.info("Scheduler started for automatic updates")
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown()
    logger.info("Shutting down AI News Scraper API")

app = FastAPI(
    title="AI News Scraper API - Optimized", 
    version="1.1.0",
    lifespan=lifespan
)

# Production CORS configuration
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

# Include authentication routers
app.include_router(auth_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")  
app.include_router(admin_router, prefix="/api")

# Database verification endpoint for debugging
@app.get("/api/db-info")
async def get_database_info():
    """Get database information for verification"""
    try:
        db_type = "PostgreSQL" if hasattr(auth_service, 'db') and auth_service.db.is_postgres else "SQLite"
        print(f"🔍 [DB-INFO] Database type: {db_type}")
        
        if hasattr(auth_service, 'db'):
            db_url = auth_service.db.database_url
            print(f"🔍 [DB-INFO] Database URL: {db_url[:50]}..." if len(db_url) > 50 else f"🔍 [DB-INFO] Database URL: {db_url}")
            
            # Test database connection
            try:
                with auth_service.db.get_connection() as conn:
                    print(f"✅ [DB-INFO] Database connection test successful")
                    return {
                        "database_type": db_type,
                        "database_url_prefix": db_url[:50] + "..." if len(db_url) > 50 else db_url,
                        "connection_test": "success",
                        "is_postgres": auth_service.db.is_postgres
                    }
            except Exception as e:
                print(f"❌ [DB-INFO] Database connection test failed: {str(e)}")
                return {
                    "database_type": db_type,
                    "connection_test": "failed",
                    "error": str(e)
                }
        else:
            return {"error": "Auth service not initialized properly"}
    except Exception as e:
        print(f"❌ [DB-INFO] Database info check failed: {str(e)}")
        return {"error": str(e)}


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    summary TEXT,
                    url TEXT UNIQUE,
                    url_hash TEXT UNIQUE,
                    published_date TEXT,
                    significance_score REAL DEFAULT 0.0,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
            logger.error(f"Database initialization error: {e}")
            raise
    
    def save_article(self, article: Dict) -> bool:
        """Save article with deduplication"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            url_hash = hashlib.md5(article['url'].encode()).hexdigest()
            
            published_date = article.get('published_date')
            if isinstance(published_date, datetime):
                published_date = published_date.isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (source, title, content, url, url_hash, published_date, significance_score, processed, summary, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['source'],
                article['title'], 
                article['content'],
                article['url'],
                url_hash,
                published_date,
                article.get('significance_score', 0.0),
                article.get('processed', False),
                article.get('summary', ''),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return False
    
    def get_recent_articles(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent articles"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT * FROM articles 
                WHERE created_at > ? 
                ORDER BY significance_score DESC, published_date DESC
                LIMIT ?
            ''', (since_date, limit))
            
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
    
    def get_all_subscribers(self) -> List[Dict]:
        """Get all active subscribers"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM subscribers WHERE is_active = 1
                ORDER BY created_at DESC
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            subscribers = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return subscribers
            
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return []

class AINewsScraper:
    def __init__(self, db_manager: DatabaseManager, cache_manager: CacheManager):
        self.db = db_manager
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])
        
    async def fetch_rss_feed(self, source: Dict) -> List[Dict]:
        """Fetch RSS feed with caching"""
        cache_key = f"rss_feed_{source['name']}"
        
        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                logger.info(f"Using cached data for {source['name']}")
                return json.loads(cached_data)
            except json.JSONDecodeError:
                pass
        
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.wait_time()
            logger.warning(f"Rate limit hit, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        try:
            logger.info(f"Fetching RSS feed for {source['name']}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(source['rss_url'], headers=headers, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            articles = []
            entries = getattr(feed, 'entries', [])
            
            for entry in entries[:CONFIG["MAX_ARTICLES_PER_SOURCE"]]:
                try:
                    published_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_date = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            pass
                    
                    content = ""
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text().strip()[:2000]
                    
                    if not content or len(content) < 50:
                        continue
                    
                    article = {
                        'source': source['name'],
                        'title': getattr(entry, 'title', 'No title'),
                        'content': content,
                        'url': getattr(entry, 'link', ''),
                        'published_date': published_date,
                        'processed': False,
                        'priority': source.get('priority', 3)
                    }
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error processing entry: {e}")
                    continue
            
            self.cache.set(cache_key, json.dumps(articles, default=str), CONFIG["CACHE_TTL"])
            logger.info(f"Fetched {len(articles)} articles from {source['name']}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS for {source['name']}: {e}")
            return []
    
    async def scrape_all_sources(self) -> List[Dict]:
        """Scrape all sources"""
        all_articles = []
        
        sorted_sources = sorted(
            [s for s in AI_SOURCES if s.get('enabled', True)],
            key=lambda x: x.get('priority', 3)
        )
        
        for source in sorted_sources:
            articles = await self.fetch_rss_feed(source)
            for article in articles:
                if self.db.save_article(article):
                    all_articles.append(article)
        
        logger.info(f"Scraped {len(all_articles)} total articles")
        return all_articles

class ContentProcessor:
    def __init__(self, claude_client, cache_manager: CacheManager):
        self.claude = claude_client
        self.cache = cache_manager
        self.has_claude = claude_client is not None
        self.rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])
    
    async def summarize_article(self, article: Dict) -> Dict:
        """Summarize article with caching"""
        cache_key = f"summary_{hashlib.md5(article['url'].encode()).hexdigest()}"
        
        cached_summary = self.cache.get(cache_key)
        if cached_summary:
            try:
                cached_data = json.loads(cached_summary)
                article.update(cached_data)
                return article
            except json.JSONDecodeError:
                pass
        
        if not self.has_claude:
            return self._fallback_processing(article)
        
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.wait_time()
            await asyncio.sleep(wait_time)
        
        try:
            prompt = f"""
            Analyze this AI news article:
            
            Title: {article['title']}
            Content: {article['content'][:1500]}
            
            Provide:
            1. A concise 5-sentence summary
            2. A significance score from 1-10
            
            Format:
            SUMMARY: [summary]
            SCORE: [number]
            """
            
            message = self.claude.messages.create(
                model=CONFIG["CLAUDE_MODEL"],
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            summary = ""
            score = 5.0
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('SUMMARY:'):
                    summary = line.replace('SUMMARY:', '').strip()
                elif line.startswith('SCORE:'):
                    try:
                        score = float(line.replace('SCORE:', '').strip())
                        score = max(1.0, min(10.0, score))
                    except ValueError:
                        score = 5.0
            
            if not summary:
                summary = article['content'][:200] + "..."
            
            processed_data = {
                'summary': summary,
                'significance_score': score,
                'processed': True
            }
            
            self.cache.set(cache_key, json.dumps(processed_data), CONFIG["CACHE_TTL"] * 24)
            article.update(processed_data)
            
            logger.info(f"Processed: {article['title'][:50]}... (Score: {score})")
            return article
            
        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            return self._fallback_processing(article)
    
    def _fallback_processing(self, article: Dict) -> Dict:
        """Fallback processing"""
        content_lower = article['content'].lower()
        title_lower = article['title'].lower()
        
        high_impact_terms = ['breakthrough', 'launch', 'gpt', 'openai', 'google', 'microsoft']
        medium_impact_terms = ['update', 'research', 'model', 'ai']
        
        score = 5.0
        
        for term in high_impact_terms:
            if term in title_lower:
                score += 1.5
        
        for term in medium_impact_terms:
            if term in title_lower:
                score += 0.5
        
        score = max(1.0, min(10.0, score))
        
        sentences = [s.strip() for s in article['content'].split('.') if len(s.strip()) > 20]
        summary = '. '.join(sentences[:2])
        if len(summary) > 200:
            summary = summary[:200] + "..."
        
        article['summary'] = summary
        article['significance_score'] = score
        article['processed'] = True
        
        return article
    
    async def create_daily_digest(self, articles: List[Dict]) -> Dict:
        """Create daily digest"""
        try:
            if not articles:
                return self._get_fallback_digest()
            
            top_articles = sorted(articles, key=lambda x: x.get('significance_score', 0), reverse=True)[:15]
            
            if self.has_claude and len(top_articles) > 0:
                try:
                    summaries = [f"• {article['summary']}" for article in top_articles[:6]]
                    
                    prompt = f"""
                    Create 5-6 bullet points for today's AI digest:
                    
                    {chr(10).join(summaries)}
                    
                    Each bullet starts with '•' and is informative.
                    """
                    
                    message = self.claude.messages.create(
                        model=CONFIG["CLAUDE_MODEL"],
                        max_tokens=400,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    summary_points = message.content[0].text.strip().split('\n')
                    summary_points = [point.strip() for point in summary_points if point.strip().startswith('•')]
                    
                except Exception as e:
                    logger.error(f"Error creating summary: {e}")
                    summary_points = [f"• {article['title']}" for article in top_articles[:6]]
            else:
                summary_points = [f"• {article['title'][:80]}" for article in top_articles[:6]]
            
            metrics = {
                "totalUpdates": len(articles),
                "highImpact": len([a for a in articles if a.get('significance_score', 0) >= 7]),
                "newResearch": len([a for a in articles if 'research' in a.get('content', '').lower()]),
                "industryMoves": len([a for a in articles if any(c in a.get('content', '').lower() for c in ['openai', 'google', 'microsoft'])])
            }
            
            digest = {
                "summary": {
                    "keyPoints": summary_points,
                    "metrics": metrics
                },
                "topStories": [
                    {
                        "title": article['title'],
                        "source": article['source'],
                        "significanceScore": round(article.get('significance_score', 0), 1),
                        "url": article['url']
                    }
                    for article in top_articles[:3]
                ],
                "content": {
                    "blog": [
                        {
                            "title": article['title'],
                            "description": article.get('summary', article['content'][:200] + "..."),
                            "source": article['source'],
                            "time": self._format_time_ago(article.get('published_date')),
                            "impact": self._get_impact_level(article.get('significance_score', 0)),
                            "type": "blog",
                            "url": article['url'],
                            "readTime": "5 min read",
                            "significanceScore": round(article.get('significance_score', 0), 1)
                        }
                        for article in top_articles[:12]
                    ],
                    "audio": [],
                    "video": []
                },
                "timestamp": datetime.now().isoformat(),
                "badge": f"{'Morning' if datetime.now().hour < 14 else 'Evening'} Digest"
            }
            
            return digest
            
        except Exception as e:
            logger.error(f"Error creating digest: {e}")
            return self._get_fallback_digest()
    
    def _format_time_ago(self, published_date) -> str:
        """Format time ago"""
        if not published_date:
            return "Recently"
        
        try:
            if isinstance(published_date, str):
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            
            diff = datetime.now() - published_date
            hours = diff.total_seconds() / 3600
            
            if hours < 1:
                return "Just now"
            elif hours < 24:
                return f"{int(hours)}h ago"
            else:
                return f"{int(hours/24)}d ago"
        except Exception:
            return "Recently"
    
    def _get_impact_level(self, score: float) -> str:
        """Get impact level"""
        if score >= 7:
            return "high"
        elif score >= 5:
            return "medium"
        else:
            return "low"
    
    def _get_fallback_digest(self) -> Dict:
        """Fallback digest"""
        return {
            "summary": {
                "keyPoints": ["• AI news system is updating"],
                "metrics": {"totalUpdates": 0, "highImpact": 0, "newResearch": 0, "industryMoves": 0}
            },
            "topStories": [],
            "content": {"blog": [], "audio": [], "video": []},
            "timestamp": datetime.now().isoformat(),
            "badge": "System Update"
        }

async def scheduled_scrape():
    """Scheduled scraping task including multimedia"""
    global scraping_status
    
    if scraping_status["in_progress"]:
        return
    
    try:
        scraping_status["in_progress"] = True
        logger.info("Starting scheduled scraping (articles + multimedia)")
        
        # Scrape articles
        articles = await scraper.scrape_all_sources()
        
        for article in articles:
            if not article.get('processed'):
                processed_article = await processor.summarize_article(article)
                db_manager.save_article(processed_article)
        
        # Scrape multimedia content
        multimedia_results = await multimedia_scraper.scrape_all_multimedia()
        
        # Process audio content
        for audio in multimedia_results.get("audio", []):
            if not audio.get('processed'):
                processed_audio = await multimedia_processor.process_audio_content(audio)
                multimedia_db_manager.save_audio_content(processed_audio)
        
        # Process video content
        for video in multimedia_results.get("video", []):
            if not video.get('processed'):
                processed_video = await multimedia_processor.process_video_content(video)
                multimedia_db_manager.save_video_content(processed_video)
        
        scraping_status["last_run"] = datetime.now().isoformat()
        logger.info(f"Scheduled scraping completed - Articles: {len(articles)}, Audio: {multimedia_results.get('total_audio', 0)}, Video: {multimedia_results.get('total_video', 0)}")
        
    except Exception as e:
        logger.error(f"Scheduled scraping failed: {e}")
    finally:
        scraping_status["in_progress"] = False

def ensure_initialization():
    """Ensure all components are initialized"""
    global db_manager, scraper, processor, cache_manager
    global multimedia_db_manager, multimedia_scraper, multimedia_processor
    
    if db_manager is None:
        logger.info("Initializing components on-demand...")
        cache_manager = CacheManager()
        db_manager = DatabaseManager(os.getenv("DATABASE_PATH", "/tmp/ai_news.db"))
        scraper = AINewsScraper(db_manager, cache_manager)
        
        # Initialize multimedia components
        multimedia_db_manager = MultimediaDatabaseManager(os.getenv("DATABASE_PATH", "/tmp/ai_news.db"))
        rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])
        multimedia_scraper = MultimediaScraper(multimedia_db_manager, cache_manager, rate_limiter)
        
        # Initialize Anthropic client
        claude_client = None
        api_key = os.getenv("CLAUDE_API_KEY")
        if api_key:
            try:
                claude_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                claude_client = None
        else:
            logger.warning("No CLAUDE_API_KEY found - using fallback processing")
        
        processor = ContentProcessor(claude_client, cache_manager)
        multimedia_processor = MultimediaContentProcessor(claude_client, cache_manager)
        logger.info("On-demand initialization completed")

@app.get("/")
async def root():
    ensure_initialization()
    return {
        "message": "AI News Scraper API - Optimized", 
        "status": "running",
        "version": "1.1.0",
        "claude_enabled": processor.has_claude if processor else False
    }

@app.get("/api/digest")
async def get_digest(refresh: Optional[int] = None):
    """Get AI news digest"""
    try:
        ensure_initialization()
        if refresh:
            logger.info("Quick refresh requested - scraping top priority sources only")
            # Only scrape priority 1 and 2 sources for quick refresh
            priority_sources = [s for s in AI_SOURCES if s.get('enabled', True) and s.get('priority', 5) <= 2]
            logger.info(f"Scraping {len(priority_sources)} priority sources for quick refresh")
            
            articles = []
            for source in priority_sources[:10]:  # Limit to top 10 sources
                try:
                    source_articles = await scraper.fetch_rss_feed(source)
                    for article in source_articles[:5]:  # Only get 5 newest from each
                        if db_manager.save_article(article):
                            articles.append(article)
                except Exception as e:
                    logger.warning(f"Error scraping {source['name']}: {e}")
                    continue
            
            logger.info(f"Quick refresh completed: {len(articles)} new articles")
        
        recent_articles = db_manager.get_recent_articles(24, 50)
        recent_audio = multimedia_db_manager.get_recent_audio_content(24, 10)
        recent_video = multimedia_db_manager.get_recent_video_content(24, 10)
        
        if not recent_articles:
            logger.info("No recent articles, scraping")
            articles = await scraper.scrape_all_sources()
            
            processed_articles = []
            for article in articles:
                processed_article = await processor.summarize_article(article)
                db_manager.save_article(processed_article)
                processed_articles.append(processed_article)
            
            recent_articles = processed_articles
        
        if not recent_audio or not recent_video:
            logger.info("No recent multimedia content, scraping")
            multimedia_results = await multimedia_scraper.scrape_all_multimedia()
            
            # Process and save audio content
            for audio in multimedia_results.get("audio", []):
                processed_audio = await multimedia_processor.process_audio_content(audio)
                multimedia_db_manager.save_audio_content(processed_audio)
            
            # Process and save video content  
            for video in multimedia_results.get("video", []):
                processed_video = await multimedia_processor.process_video_content(video)
                multimedia_db_manager.save_video_content(processed_video)
            
            recent_audio = multimedia_db_manager.get_recent_audio_content(24, 10)
            recent_video = multimedia_db_manager.get_recent_video_content(24, 10)
        
        digest = await processor.create_daily_digest(recent_articles)
        
        # Add multimedia content to digest
        digest["content"]["audio"] = [
            {
                "title": audio['title'],
                "description": audio.get('summary', audio['description'][:200] + "..."),
                "source": audio['source'],
                "time": processor._format_time_ago(audio.get('published_date')),
                "impact": processor._get_impact_level(audio.get('significance_score', 0)),
                "type": "audio",
                "url": audio['url'],
                "audio_url": audio.get('audio_url', ''),
                "duration": audio.get('duration', 0),
                "significanceScore": round(audio.get('significance_score', 0), 1)
            }
            for audio in recent_audio[:6]
        ]
        
        digest["content"]["video"] = [
            {
                "title": video['title'],
                "description": video.get('summary', video['description'][:200] + "..."),
                "source": video['source'],
                "time": processor._format_time_ago(video.get('published_date')),
                "impact": processor._get_impact_level(video.get('significance_score', 0)),
                "type": "video",
                "url": video['url'],
                "thumbnail_url": video.get('thumbnail_url', ''),
                "duration": video.get('duration', 0),
                "significanceScore": round(video.get('significance_score', 0), 1)
            }
            for video in recent_video[:6]
        ]
        logger.info(f"Returning digest with {len(recent_articles)} articles")
        
        return digest
        
    except Exception as e:
        logger.error(f"Error in get_digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape")
async def manual_scrape(priority_only: Optional[bool] = False):
    """Manual scraping - full or priority sources only"""
    try:
        ensure_initialization()
        
        if priority_only:
            sources_to_scrape = [s for s in AI_SOURCES if s.get('enabled', True) and s.get('priority', 5) <= 2]
            logger.info(f"Scraping {len(sources_to_scrape)} priority sources only")
        else:
            sources_to_scrape = [s for s in AI_SOURCES if s.get('enabled', True)]
            logger.info(f"Scraping all {len(sources_to_scrape)} sources")
        
        articles = []
        for source in sources_to_scrape:
            try:
                source_articles = await scraper.fetch_rss_feed(source)
                articles.extend(source_articles)
            except Exception as e:
                logger.warning(f"Error scraping {source['name']}: {e}")
                continue
        
        processed_count = 0
        for article in articles:
            if not article.get('processed'):
                processed_article = await processor.summarize_article(article)
                if db_manager.save_article(processed_article):
                    processed_count += 1
        
        return {
            "message": "Scraping completed",
            "articles_found": len(articles),
            "articles_processed": processed_count,
            "sources": [s['name'] for s in AI_SOURCES if s.get('enabled', True)],
            "claude_available": processor.has_claude
        }
        
    except Exception as e:
        logger.error(f"Error in manual_scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources")
async def get_sources():
    """Get sources"""
    return {
        "sources": AI_SOURCES,
        "enabled_count": len([s for s in AI_SOURCES if s.get('enabled', True)]),
        "claude_available": processor.has_claude if processor else False
    }

@app.get("/api/multimedia/scrape")
async def scrape_multimedia():
    """Manual multimedia scraping"""
    try:
        multimedia_results = await multimedia_scraper.scrape_all_multimedia()
        
        # Process audio content
        processed_audio = 0
        for audio in multimedia_results.get("audio", []):
            processed_audio_content = await multimedia_processor.process_audio_content(audio)
            if multimedia_db_manager.save_audio_content(processed_audio_content):
                processed_audio += 1
        
        # Process video content
        processed_video = 0
        for video in multimedia_results.get("video", []):
            processed_video_content = await multimedia_processor.process_video_content(video)
            if multimedia_db_manager.save_video_content(processed_video_content):
                processed_video += 1
        
        return {
            "message": "Multimedia scraping completed",
            "audio_found": multimedia_results.get("total_audio", 0),
            "video_found": multimedia_results.get("total_video", 0),
            "audio_processed": processed_audio,
            "video_processed": processed_video,
            "audio_sources": [s['name'] for s in MULTIMEDIA_SOURCES["audio"] if s.get('enabled', True)],
            "video_sources": [s['name'] for s in MULTIMEDIA_SOURCES["video"] if s.get('enabled', True)],
            "claude_available": multimedia_processor.has_claude
        }
        
    except Exception as e:
        logger.error(f"Error in multimedia scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multimedia/audio")
async def get_audio_content(hours: int = 24, limit: int = 20):
    """Get recent audio content"""
    try:
        audio_content = multimedia_db_manager.get_recent_audio_content(hours, limit)
        
        formatted_content = [
            {
                "title": audio['title'],
                "description": audio.get('summary', audio['description'][:200] + "..."),
                "source": audio['source'],
                "url": audio['url'],
                "audio_url": audio.get('audio_url', ''),
                "duration": audio.get('duration', 0),
                "published_date": audio.get('published_date'),
                "significance_score": round(audio.get('significance_score', 0), 1),
                "processed": audio.get('processed', False)
            }
            for audio in audio_content
        ]
        
        return {
            "audio_content": formatted_content,
            "total_count": len(formatted_content),
            "hours_range": hours
        }
        
    except Exception as e:
        logger.error(f"Error getting audio content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multimedia/video")
async def get_video_content(hours: int = 24, limit: int = 20):
    """Get recent video content"""
    try:
        video_content = multimedia_db_manager.get_recent_video_content(hours, limit)
        
        formatted_content = [
            {
                "title": video['title'],
                "description": video.get('summary', video['description'][:200] + "..."),
                "source": video['source'],
                "url": video['url'],
                "thumbnail_url": video.get('thumbnail_url', ''),
                "duration": video.get('duration', 0),
                "published_date": video.get('published_date'),
                "significance_score": round(video.get('significance_score', 0), 1),
                "processed": video.get('processed', False)
            }
            for video in video_content
        ]
        
        return {
            "video_content": formatted_content,
            "total_count": len(formatted_content),
            "hours_range": hours
        }
        
    except Exception as e:
        logger.error(f"Error getting video content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multimedia/sources")
async def get_multimedia_sources():
    """Get multimedia sources"""
    return {
        "sources": MULTIMEDIA_SOURCES,
        "audio_sources": len([s for s in MULTIMEDIA_SOURCES["audio"] if s.get('enabled', True)]),
        "video_sources": len([s for s in MULTIMEDIA_SOURCES["video"] if s.get('enabled', True)]),
        "claude_available": multimedia_processor.has_claude if multimedia_processor else False
    }

@app.get("/api/migrate-neon")
async def migrate_neon_database():
    """Initialize and setup Neon Postgres database"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")
    
    if not auth_service.db.is_postgres:
        raise HTTPException(status_code=400, detail="Migration endpoint only works with PostgreSQL")
    
    try:
        # Test database connection
        with auth_service.db.get_connection() as conn:
            pass
        
        # Get topics to verify setup
        topics = auth_service.get_available_topics()
        
        # Get category statistics
        categories = {}
        for topic in topics:
            cat = topic.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        # Check table counts
        table_counts = {}
        tables_to_check = ['users', 'ai_topics', 'articles', 'audio_content', 'video_content', 'daily_archives']
        for table in tables_to_check:
            try:
                result = auth_service.db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = result[0]['count']
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        return {
            "success": True,
            "message": "Neon Postgres database initialized successfully",
            "database_type": "PostgreSQL",
            "database_url": auth_service.db.database_url[:50] + "...",
            "topics_count": len(topics),
            "categories": categories,
            "table_counts": table_counts,
            "sample_topics": [{"name": t.name, "category": t.category.value} for t in topics[:5]]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check"""
    # Get database info from auth service
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
        "components": {
            "database": db_manager is not None,
            "scraper": scraper is not None,
            "processor": processor is not None,
            "multimedia_database": multimedia_db_manager is not None,
            "multimedia_scraper": multimedia_scraper is not None,
            "multimedia_processor": multimedia_processor is not None,
            "authentication": auth_service is not None,
            "claude_api": processor.has_claude if processor else False,
            "scheduler": scheduler.running if scheduler else False
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AI News Scraper API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)