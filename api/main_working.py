"""
AI News Scraper API - Working version with content scraping
"""
import os
import sqlite3
import json
import requests
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
import asyncio

import feedparser
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import uvicorn
import logging

# Embedded AI sources configuration (subset for testing)
AI_SOURCES = [
    {
        "name": "OpenAI",
        "rss_url": "https://openai.com/blog/rss.xml",
        "website": "https://openai.com/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Anthropic",
        "rss_url": "https://www.anthropic.com/news/rss.xml",
        "website": "https://www.anthropic.com/news",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Google DeepMind",
        "rss_url": "https://deepmind.google/discover/blog/rss.xml",
        "website": "https://deepmind.google/discover/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Hugging Face",
        "rss_url": "https://huggingface.co/blog/feed.xml",
        "website": "https://huggingface.co/blog",
        "enabled": True,
        "priority": 1,
        "category": "platform"
    },
    {
        "name": "AI News",
        "rss_url": "https://artificialintelligence-news.com/feed/",
        "website": "https://artificialintelligence-news.com",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "VentureBeat AI",
        "rss_url": "https://venturebeat.com/ai/feed/",
        "website": "https://venturebeat.com/ai/",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "MIT Technology Review",
        "rss_url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "website": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "The Gradient",
        "rss_url": "https://thegradient.pub/rss/",
        "website": "https://thegradient.pub",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },
    # Audio/Video Sources
    {
        "name": "AI Podcast by NVIDIA",
        "rss_url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed/",
        "website": "https://blogs.nvidia.com/blog/category/artificial-intelligence/",
        "enabled": True,
        "priority": 2,
        "category": "audio",
        "content_type": "audio"
    },
    {
        "name": "Lex Fridman Podcast",
        "rss_url": "https://lexfridman.com/feed/podcast/",
        "website": "https://lexfridman.com/podcast/",
        "enabled": True,
        "priority": 2,
        "category": "audio",
        "content_type": "audio"
    },
    {
        "name": "AI YouTube - Two Minute Papers",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg",
        "website": "https://www.youtube.com/c/KárolyZsolnai",
        "enabled": True,
        "priority": 2,
        "category": "video",
        "content_type": "video"
    },
    {
        "name": "AI Explained YouTube",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw",
        "website": "https://www.youtube.com/c/aiexplained-official",
        "enabled": True,
        "priority": 2,
        "category": "video",
        "content_type": "video"
    }
]

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
    "RETRY_DELAY": 2,
    "AUTO_UPDATE_INTERVAL_HOURS": int(os.getenv("AUTO_UPDATE_INTERVAL_HOURS", "8"))  # 8 hours default
}

# Global variables for app state
db_manager = None
scraper = None
processor = None
cache_manager = None
scraping_status = {"in_progress": False, "last_run": None, "errors": [], "auto_update_enabled": True}

class CacheManager:
    def __init__(self):
        self.memory_cache = {}
        self.cache_enabled = CONFIG["CACHE_ENABLED"]
        logger.info("Using memory cache")
    
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
    global db_manager, scraper, processor, cache_manager
    
    # Startup
    logger.info("Starting AI News Scraper API")
    
    # Initialize components
    cache_manager = CacheManager()
    db_manager = DatabaseManager(os.getenv("DATABASE_PATH", "/tmp/ai_news.db"))
    scraper = AINewsScraper(db_manager, cache_manager)
    processor = ContentProcessor(cache_manager)
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI News Scraper API")

app = FastAPI(
    title="AI News Scraper API - Working", 
    version="1.2.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Explicit OPTIONS handler for CORS preflight
@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    """Handle CORS preflight requests"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age": "3600"
        }
    )

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
                    content_type TEXT DEFAULT 'blog',
                    category TEXT DEFAULT 'blog',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add new columns if they don't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN content_type TEXT DEFAULT "blog"')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN category TEXT DEFAULT "blog"')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN url_hash TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            # Create unique index on url_hash if it doesn't exist
            try:
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash)')
            except sqlite3.OperationalError:
                pass  # Index already exists
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(significance_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at)')
            
            # Create archives table for daily digest snapshots
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_archives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    archive_date TEXT NOT NULL UNIQUE,
                    digest_data TEXT NOT NULL,
                    articles_count INTEGER DEFAULT 0,
                    top_stories_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_archives_date ON daily_archives(archive_date)')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
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
            
            # Use INSERT OR IGNORE to avoid constraint errors, then UPDATE if exists
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (source, title, content, url, url_hash, published_date, significance_score, processed, summary, content_type, category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                article.get('content_type', 'blog'),
                article.get('category', 'blog'),
                datetime.now().isoformat()
            ))
            
            # Update existing records
            cursor.execute('''
                UPDATE articles SET 
                    content = ?, significance_score = ?, processed = ?, summary = ?, content_type = ?, category = ?
                WHERE url_hash = ?
            ''', (
                article['content'],
                article.get('significance_score', 0.0),
                article.get('processed', False),
                article.get('summary', ''),
                article.get('content_type', 'blog'),
                article.get('category', 'blog'),
                url_hash
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
    
    def save_daily_archive(self, archive_date: str, digest_data: Dict) -> bool:
        """Save daily digest to archive"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            articles_count = 0
            top_stories_count = 0
            
            if digest_data.get('content'):
                content = digest_data['content']
                articles_count = len(content.get('blog', [])) + len(content.get('audio', [])) + len(content.get('video', []))
            
            if digest_data.get('topStories'):
                top_stories_count = len(digest_data['topStories'])
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_archives 
                (archive_date, digest_data, articles_count, top_stories_count, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                archive_date,
                json.dumps(digest_data, default=str),
                articles_count,
                top_stories_count,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Archived daily digest for {archive_date}")
            return True
        except Exception as e:
            logger.error(f"Error saving daily archive: {e}")
            return False
    
    def get_archive_list(self, limit: int = 30) -> List[Dict]:
        """Get list of archived digests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT archive_date, articles_count, top_stories_count, created_at 
                FROM daily_archives 
                ORDER BY archive_date DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            archives = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return archives
        except Exception as e:
            logger.error(f"Error getting archive list: {e}")
            return []
    
    def get_archived_digest(self, archive_date: str) -> Optional[Dict]:
        """Get specific archived digest"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT digest_data FROM daily_archives 
                WHERE archive_date = ?
            ''', (archive_date,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            logger.error(f"Error getting archived digest: {e}")
            return None

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
                        'priority': source.get('priority', 3),
                        'content_type': source.get('content_type', 'blog'),
                        'category': source.get('category', 'blog')
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
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(CONFIG["RATE_LIMIT_RPM"])
    
    def _fallback_processing(self, article: Dict) -> Dict:
        """Fallback processing without Claude"""
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
            
            # Process articles with fallback scoring
            processed_articles = []
            for article in articles:
                if not article.get('processed'):
                    processed_article = self._fallback_processing(article)
                    processed_articles.append(processed_article)
                else:
                    processed_articles.append(article)
            
            # Enhanced ranking: combine recency and significance score
            def calculate_ranking_score(article):
                significance = article.get('significance_score', 0)
                
                # Calculate time score (more recent = higher score)
                time_score = 0
                published_date = article.get('published_date')
                if published_date:
                    try:
                        if isinstance(published_date, str):
                            published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        
                        # Calculate hours since publication
                        hours_ago = (datetime.now() - published_date).total_seconds() / 3600
                        
                        # Time decay: articles lose 0.1 points per hour, min 0
                        time_score = max(0, 5.0 - (hours_ago * 0.1))
                    except Exception:
                        time_score = 1.0  # Default for unparseable dates
                
                # Priority boost for high-priority sources
                priority_boost = 0
                if article.get('priority', 5) <= 2:
                    priority_boost = 1.0
                
                # Combine scores: significance (60%) + time (30%) + priority (10%)
                final_score = (significance * 0.6) + (time_score * 0.3) + (priority_boost * 0.1)
                return final_score
            
            # Sort by combined ranking score
            top_articles = sorted(processed_articles, key=calculate_ranking_score, reverse=True)[:15]
            
            summary_points = [f"• {article['title'][:80]}" for article in top_articles[:6]]
            
            metrics = {
                "totalUpdates": len(processed_articles),
                "highImpact": len([a for a in processed_articles if a.get('significance_score', 0) >= 7]),
                "newResearch": len([a for a in processed_articles if 'research' in a.get('content', '').lower()]),
                "industryMoves": len([a for a in processed_articles if any(c in a.get('content', '').lower() for c in ['openai', 'google', 'microsoft'])])
            }
            
            # Categorize articles by content type while preserving ranking order
            blog_articles = []
            audio_articles = []
            video_articles = []
            
            for article in top_articles[:20]:  # Increased to 20 for better category distribution
                content_type = article.get('content_type', 'blog')
                ranking_score = calculate_ranking_score(article)
                
                article_data = {
                    "title": article['title'],
                    "description": article.get('summary', article['content'][:200] + "..."),
                    "source": article['source'],
                    "time": self._format_time_ago(article.get('published_date')),
                    "impact": self._get_impact_level(article.get('significance_score', 0)),
                    "type": content_type,
                    "url": article['url'],
                    "readTime": "5 min read" if content_type == 'blog' else "Listen" if content_type == 'audio' else "Watch",
                    "significanceScore": round(article.get('significance_score', 0), 1),
                    "rankingScore": round(ranking_score, 2),
                    "priority": article.get('priority', 5)
                }
                
                if content_type == 'audio':
                    audio_articles.append(article_data)
                elif content_type == 'video':
                    video_articles.append(article_data)
                else:
                    blog_articles.append(article_data)
            
            # Sort each category by ranking score to maintain quality order
            blog_articles = sorted(blog_articles, key=lambda x: x['rankingScore'], reverse=True)[:8]
            audio_articles = sorted(audio_articles, key=lambda x: x['rankingScore'], reverse=True)[:6]
            video_articles = sorted(video_articles, key=lambda x: x['rankingScore'], reverse=True)[:6]
            
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
                    "blog": blog_articles,
                    "audio": audio_articles,
                    "video": video_articles
                },
                "timestamp": datetime.now().isoformat(),
                "badge": f"{'Morning' if datetime.now().hour < 14 else 'Evening'} Digest"
            }
            
            return digest
            
        except Exception as e:
            logger.error(f"Error creating digest: {e}")
            return self._get_fallback_digest()
    
    def _format_time_ago(self, published_date) -> str:
        """Format time ago with better timezone handling"""
        if not published_date:
            return "Recently"
        
        try:
            # Handle different datetime formats
            if isinstance(published_date, str):
                # Try to parse different formats
                if published_date.endswith('Z'):
                    published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                elif '+' in published_date or published_date.endswith('00'):
                    published_date = datetime.fromisoformat(published_date)
                else:
                    # Assume UTC if no timezone info
                    published_date = datetime.fromisoformat(published_date)
            elif not isinstance(published_date, datetime):
                return "Recently"
            
            # Calculate time difference
            now = datetime.now()
            
            # If published_date is timezone-aware but now is not, make now UTC
            if published_date.tzinfo is not None and now.tzinfo is None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            
            diff = now - published_date
            hours = diff.total_seconds() / 3600
            
            if hours < 0:
                return "Just now"  # Future dates
            elif hours < 1:
                minutes = int(diff.total_seconds() / 60)
                return f"{minutes}m ago" if minutes > 0 else "Just now"
            elif hours < 24:
                return f"{int(hours)}h ago"
            elif hours < 168:  # Less than a week
                return f"{int(hours/24)}d ago"
            else:
                return f"{int(hours/168)}w ago"
        except Exception as e:
            logger.debug(f"Time formatting error: {e}")
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

def ensure_initialization():
    """Ensure all components are initialized"""
    global db_manager, scraper, processor, cache_manager
    
    if db_manager is None:
        logger.info("Initializing components on-demand...")
        cache_manager = CacheManager()
        db_manager = DatabaseManager(os.getenv("DATABASE_PATH", "/tmp/ai_news.db"))
        scraper = AINewsScraper(db_manager, cache_manager)
        processor = ContentProcessor(cache_manager)
        logger.info("On-demand initialization completed")

async def background_scrape_update():
    """Background task for scraping updates"""
    global scraping_status
    
    if scraping_status["in_progress"]:
        logger.info("Scraping already in progress, skipping background update")
        return
    
    try:
        scraping_status["in_progress"] = True
        scraping_status["errors"] = []
        logger.info("Starting background scraping update")
        
        ensure_initialization()
        
        # Scrape priority sources for quick updates
        priority_sources = [s for s in AI_SOURCES if s.get('enabled', True) and s.get('priority', 5) <= 2]
        
        new_articles = []
        for source in priority_sources:
            try:
                source_articles = await scraper.fetch_rss_feed(source)
                for article in source_articles[:3]:  # Limit to 3 newest per source for background updates
                    processed_article = processor._fallback_processing(article)
                    if db_manager.save_article(processed_article):
                        new_articles.append(processed_article)
            except Exception as e:
                error_msg = f"Error scraping {source['name']}: {e}"
                logger.warning(error_msg)
                scraping_status["errors"].append(error_msg)
                continue
        
        scraping_status["last_run"] = datetime.now().isoformat()
        logger.info(f"Background scraping completed: {len(new_articles)} new articles")
        
    except Exception as e:
        error_msg = f"Background scraping failed: {e}"
        logger.error(error_msg)
        scraping_status["errors"].append(error_msg)
    finally:
        scraping_status["in_progress"] = False

def should_auto_update() -> bool:
    """Check if auto-update should run based on last run time"""
    if not scraping_status.get("auto_update_enabled", True):
        return False
    
    if not scraping_status.get("last_run"):
        return True
    
    try:
        last_run = datetime.fromisoformat(scraping_status["last_run"])
        time_since_last = datetime.now() - last_run
        # Auto-update based on configurable interval (default 8 hours)
        interval_seconds = CONFIG["AUTO_UPDATE_INTERVAL_HOURS"] * 3600
        return time_since_last.total_seconds() > interval_seconds
    except Exception:
        return True

@app.get("/")
async def root(background_tasks: BackgroundTasks = None):
    ensure_initialization()
    
    # Trigger background update if needed  
    if should_auto_update() and background_tasks:
        logger.info("Triggering auto-update from root endpoint")
        background_tasks.add_task(background_scrape_update)
    
    return {
        "message": "AI News Scraper API - Working Version", 
        "status": "running",
        "version": "1.2.0",
        "ai_sources_count": len([s for s in AI_SOURCES if s.get('enabled', True)])
    }

@app.get("/api/digest")
async def get_digest(refresh: Optional[int] = None, background_tasks: BackgroundTasks = None):
    """Get AI news digest with auto-update functionality"""
    try:
        ensure_initialization()
        
        # Trigger background update if needed
        if should_auto_update() and background_tasks:
            logger.info("Triggering auto-update in background")
            background_tasks.add_task(background_scrape_update)
        
        if refresh:
            logger.info("Refresh requested - scraping priority sources")
            priority_sources = [s for s in AI_SOURCES if s.get('enabled', True) and s.get('priority', 5) <= 2]
            
            articles = []
            for source in priority_sources[:10]:
                try:
                    source_articles = await scraper.fetch_rss_feed(source)
                    for article in source_articles[:5]:
                        if db_manager.save_article(article):
                            articles.append(article)
                except Exception as e:
                    logger.warning(f"Error scraping {source['name']}: {e}")
                    continue
            
            logger.info(f"Refresh completed: {len(articles)} new articles")
        
        recent_articles = db_manager.get_recent_articles(24, 50)
        
        if not recent_articles:
            logger.info("No recent articles, scraping all sources")
            articles = await scraper.scrape_all_sources()
            
            processed_articles = []
            for article in articles:
                processed_article = processor._fallback_processing(article)
                db_manager.save_article(processed_article)
                processed_articles.append(processed_article)
            
            recent_articles = processed_articles
        
        digest = await processor.create_daily_digest(recent_articles)
        
        # Auto-archive daily digest (only once per day)
        today_date = datetime.now().strftime('%Y-%m-%d')
        try:
            if len(recent_articles) > 0:
                db_manager.save_daily_archive(today_date, digest)
        except Exception as archive_error:
            logger.warning(f"Failed to archive daily digest: {archive_error}")
        
        logger.info(f"Returning digest with {len(recent_articles)} articles")
        return digest
        
    except Exception as e:
        logger.error(f"Error in get_digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape")
async def manual_scrape(priority_only: Optional[bool] = False):
    """Manual scraping"""
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
                processed_article = processor._fallback_processing(article)
                if db_manager.save_article(processed_article):
                    processed_count += 1
        
        return {
            "message": "Scraping completed",
            "articles_found": len(articles),
            "articles_processed": processed_count,
            "sources": [s['name'] for s in AI_SOURCES if s.get('enabled', True)],
            "total_sources": len([s for s in AI_SOURCES if s.get('enabled', True)])
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
        "total_count": len(AI_SOURCES)
    }

# Simple subscription endpoints for CORS testing
@app.get("/subscription/preferences")
async def get_subscription_preferences():
    """Test endpoint for preferences"""
    return {
        "message": "Subscription preferences endpoint working",
        "preferences": {
            "frequency": "daily",
            "categories": ["all"],
            "content_types": ["all"]
        }
    }

@app.post("/subscription/preferences")
async def save_subscription_preferences():
    """Test endpoint for saving preferences"""
    return {"message": "Preferences saved successfully"}

@app.get("/email/preview-digest")
async def preview_digest():
    """Test endpoint for email preview"""
    return {
        "message": "Email preview endpoint working",
        "html": "<p>Email service setup required</p>"
    }

@app.post("/email/send-digest")
async def send_digest():
    """Test endpoint for sending digest"""
    return {"message": "Email service setup required"}

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": db_manager is not None,
            "scraper": scraper is not None,
            "processor": processor is not None,
            "ai_sources": len([s for s in AI_SOURCES if s.get('enabled', True)])
        },
        "auto_update": scraping_status
    }

@app.post("/api/auto-update/trigger")
async def trigger_auto_update(background_tasks: BackgroundTasks):
    """Manually trigger auto-update"""
    background_tasks.add_task(background_scrape_update)
    return {
        "message": "Auto-update triggered",
        "status": scraping_status
    }

@app.get("/api/auto-update/status")
async def get_auto_update_status():
    """Get auto-update status"""
    return {
        "auto_update_status": scraping_status,
        "should_update": should_auto_update(),
        "update_frequency": f"Every {CONFIG['AUTO_UPDATE_INTERVAL_HOURS']} hours + Daily at 8 AM UTC",
        "update_interval_hours": CONFIG["AUTO_UPDATE_INTERVAL_HOURS"],
        "time_since_last_update": f"{int((datetime.now() - datetime.fromisoformat(scraping_status['last_run'])).total_seconds() / 3600)} hours" if scraping_status.get('last_run') else "Never"
    }

@app.post("/api/auto-update/enable")
async def enable_auto_update():
    """Enable auto-update"""
    scraping_status["auto_update_enabled"] = True
    return {"message": "Auto-update enabled", "status": scraping_status}

@app.post("/api/auto-update/disable") 
async def disable_auto_update():
    """Disable auto-update"""
    scraping_status["auto_update_enabled"] = False
    return {"message": "Auto-update disabled", "status": scraping_status}

@app.post("/api/cron/update")
async def cron_update():
    """Cron endpoint for Vercel Cron Jobs"""
    try:
        logger.info("Cron update triggered")
        await background_scrape_update()
        return {
            "message": "Cron update completed",
            "status": scraping_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Cron update failed: {e}")
        return {
            "error": str(e),
            "status": scraping_status,
            "timestamp": datetime.now().isoformat()
        }

# Archive endpoints
@app.get("/api/archives")
async def get_archive_list(limit: Optional[int] = 30):
    """Get list of archived daily digests"""
    try:
        ensure_initialization()
        archives = db_manager.get_archive_list(limit)
        
        # Format the archive list for frontend display
        formatted_archives = []
        for archive in archives:
            formatted_archives.append({
                "date": archive["archive_date"],
                "articles_count": archive["articles_count"],
                "top_stories_count": archive["top_stories_count"],
                "created_at": archive["created_at"],
                "formatted_date": datetime.fromisoformat(archive["archive_date"]).strftime('%B %d, %Y'),
                "url": f"/api/archives/{archive['archive_date']}"
            })
        
        return {
            "archives": formatted_archives,
            "total_count": len(formatted_archives)
        }
    except Exception as e:
        logger.error(f"Error getting archive list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archives/{archive_date}")
async def get_archived_digest(archive_date: str):
    """Get specific archived digest"""
    try:
        ensure_initialization()
        
        # Validate date format
        try:
            datetime.strptime(archive_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        archived_digest = db_manager.get_archived_digest(archive_date)
        
        if not archived_digest:
            raise HTTPException(status_code=404, detail=f"No archived digest found for {archive_date}")
        
        # Add archive metadata
        archived_digest["archive_date"] = archive_date
        archived_digest["formatted_date"] = datetime.fromisoformat(archive_date).strftime('%B %d, %Y')
        archived_digest["is_archived"] = True
        
        return archived_digest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting archived digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# For Vercel deployment - export the FastAPI app directly
handler = app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AI News Scraper API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)