"""
Enhanced AI News Scraper with current day filtering and admin features
"""
import os
import json
import sqlite3
import requests
import feedparser
import anthropic
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Union
import pytz
from bs4 import BeautifulSoup
import hashlib
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

class EnhancedContentScraper:
    def __init__(self, db_path: str = "ai_news.db"):
        self.db_path = db_path
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.claude_api_key) if self.claude_api_key else None
        self._init_database()
        
    def _init_database(self):
        """Initialize enhanced database with admin and scraping tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced articles table with scraping metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                content_summary TEXT,
                url TEXT NOT NULL UNIQUE,
                source TEXT,
                category TEXT,
                content_type TEXT DEFAULT 'article',
                significance_score REAL DEFAULT 0.0,
                impact_level TEXT DEFAULT 'medium',
                published_date DATETIME,
                scraped_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_current_day BOOLEAN DEFAULT 0,
                admin_validated BOOLEAN DEFAULT 0,
                admin_notes TEXT,
                llm_processed BOOLEAN DEFAULT 0,
                image_url TEXT,
                read_time TEXT,
                source_priority INTEGER DEFAULT 5
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                permissions TEXT DEFAULT 'content_admin'
            )
        ''')
        
        # Scraping sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_sessions (
                id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                status TEXT DEFAULT 'running',
                articles_found INTEGER DEFAULT 0,
                articles_processed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_details TEXT,
                initiated_by TEXT,
                is_scheduled BOOLEAN DEFAULT 0
            )
        ''')
        
        # Content validation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_validation (
                id TEXT PRIMARY KEY,
                article_id TEXT NOT NULL,
                admin_id TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                validation_notes TEXT,
                validated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles (id),
                FOREIGN KEY (admin_id) REFERENCES admin_users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_current_day_ist(self) -> str:
        """Get current day in IST timezone"""
        now_ist = datetime.now(IST)
        return now_ist.strftime('%Y-%m-%d')
    
    def is_article_from_today(self, published_date: Union[str, datetime]) -> bool:
        """Check if article is from current day in IST"""
        try:
            if isinstance(published_date, str):
                # Try to parse different date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                    try:
                        pub_date = datetime.strptime(published_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return False
            else:
                pub_date = published_date
                
            # Convert to IST if timezone aware
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            pub_date_ist = pub_date.astimezone(IST)
            current_day_ist = self.get_current_day_ist()
            article_day = pub_date_ist.strftime('%Y-%m-%d')
            
            return article_day == current_day_ist
            
        except Exception as e:
            logger.error(f"Error checking article date: {e}")
            return False
    
    def scrape_with_llm_filtering(self, sources: List[Dict], filter_current_day: bool = True) -> Dict:
        """Enhanced scraping with LLM filtering and current day validation"""
        session_id = f"session_{int(time.time())}"
        
        # Start scraping session
        self._start_scraping_session(session_id, "llm_filtered", False)
        
        try:
            articles_found = 0
            articles_processed = 0
            current_day = self.get_current_day_ist()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for source in sources:
                if not source.get('enabled', True):
                    continue
                    
                try:
                    logger.info(f"Scraping source: {source['name']}")
                    
                    # Fetch RSS feed
                    feed = feedparser.parse(source['rss_url'])
                    
                    for entry in feed.entries[:10]:  # Limit per source
                        articles_found += 1
                        
                        # Check if article is from current day
                        published_date = getattr(entry, 'published_parsed', None)
                        if published_date:
                            pub_datetime = datetime(*published_date[:6])
                        else:
                            pub_datetime = datetime.now()
                        
                        is_current_day = self.is_article_from_today(pub_datetime)
                        
                        # Skip if filtering for current day and article is not from today
                        if filter_current_day and not is_current_day:
                            logger.debug(f"Skipping article from {pub_datetime}: not from current day")
                            continue
                        
                        # Create article record
                        article_id = hashlib.md5(entry.link.encode()).hexdigest()
                        
                        # Check if already exists
                        cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
                        if cursor.fetchone():
                            continue
                        
                        # Get content summary and analysis from LLM
                        if self.client:
                            llm_analysis = self._analyze_with_llm(entry)
                        else:
                            llm_analysis = self._create_default_analysis(entry)
                        
                        # Insert article
                        cursor.execute('''
                            INSERT INTO articles (
                                id, title, description, content_summary, url, source,
                                significance_score, impact_level, published_date,
                                is_current_day, llm_processed
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            article_id,
                            entry.title,
                            getattr(entry, 'summary', ''),
                            llm_analysis['summary'],
                            entry.link,
                            source['name'],
                            llm_analysis['significance_score'],
                            llm_analysis['impact_level'],
                            pub_datetime.isoformat(),
                            is_current_day,
                            bool(self.client)
                        ))
                        
                        articles_processed += 1
                        
                except Exception as e:
                    logger.error(f"Error scraping {source['name']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            # Complete scraping session
            self._complete_scraping_session(session_id, articles_found, articles_processed)
            
            return {
                "success": True,
                "session_id": session_id,
                "articles_found": articles_found,
                "articles_processed": articles_processed,
                "current_day": current_day,
                "message": f"Scraping completed. Found {articles_processed} current day articles."
            }
            
        except Exception as e:
            self._fail_scraping_session(session_id, str(e))
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    def _analyze_with_llm(self, entry) -> Dict:
        """Analyze article content with Claude LLM"""
        try:
            prompt = f"""
            Analyze this AI news article and provide:
            1. A concise 2-sentence summary
            2. Significance score (0-10, where 10 is breakthrough news)
            3. Impact level (low/medium/high)
            
            Title: {entry.title}
            Description: {getattr(entry, 'summary', 'No description')}
            
            Respond in JSON format:
            {{
                "summary": "Your 2-sentence summary",
                "significance_score": 7.5,
                "impact_level": "high"
            }}
            """
            
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = json.loads(message.content[0].text)
            return response
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._create_default_analysis(entry)
    
    def _create_default_analysis(self, entry) -> Dict:
        """Create default analysis when LLM is not available"""
        return {
            "summary": f"{entry.title}. {getattr(entry, 'summary', '')[:100]}...",
            "significance_score": 5.0,
            "impact_level": "medium"
        }
    
    def _start_scraping_session(self, session_id: str, session_type: str, is_scheduled: bool):
        """Start a scraping session record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scraping_sessions (id, session_type, is_scheduled)
            VALUES (?, ?, ?)
        ''', (session_id, session_type, is_scheduled))
        conn.commit()
        conn.close()
    
    def _complete_scraping_session(self, session_id: str, articles_found: int, articles_processed: int):
        """Complete a scraping session record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE scraping_sessions 
            SET completed_at = CURRENT_TIMESTAMP, status = 'completed',
                articles_found = ?, articles_processed = ?
            WHERE id = ?
        ''', (articles_found, articles_processed, session_id))
        conn.commit()
        conn.close()
    
    def _fail_scraping_session(self, session_id: str, error_details: str):
        """Mark a scraping session as failed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE scraping_sessions 
            SET completed_at = CURRENT_TIMESTAMP, status = 'failed',
                errors_count = 1, error_details = ?
            WHERE id = ?
        ''', (error_details, session_id))
        conn.commit()
        conn.close()
    
    def get_current_day_articles(self, limit: int = 50) -> List[Dict]:
        """Get articles from current day"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, description, content_summary, url, source,
                   significance_score, impact_level, published_date, admin_validated
            FROM articles 
            WHERE is_current_day = 1
            ORDER BY significance_score DESC, published_date DESC
            LIMIT ?
        ''', (limit,))
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "content_summary": row[3],
                "url": row[4],
                "source": row[5],
                "significance_score": row[6],
                "impact_level": row[7],
                "published_date": row[8],
                "admin_validated": bool(row[9])
            })
        
        conn.close()
        return articles
    
    def get_scraping_sessions(self, limit: int = 20) -> List[Dict]:
        """Get recent scraping sessions for admin dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, session_type, started_at, completed_at, status,
                   articles_found, articles_processed, errors_count,
                   is_scheduled
            FROM scraping_sessions
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row[0],
                "session_type": row[1],
                "started_at": row[2],
                "completed_at": row[3],
                "status": row[4],
                "articles_found": row[5],
                "articles_processed": row[6],
                "errors_count": row[7],
                "is_scheduled": bool(row[8])
            })
        
        conn.close()
        return sessions


class AdminManager:
    def __init__(self, db_path: str = "ai_news.db"):
        self.db_path = db_path
    
    def create_admin_user(self, email: str, name: str, password: str) -> str:
        """Create admin user with hashed password"""
        import hashlib
        
        admin_id = f"admin_{int(time.time())}"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO admin_users (id, email, name, password_hash)
                VALUES (?, ?, ?, ?)
            ''', (admin_id, email, name, password_hash))
            conn.commit()
            return admin_id
        except sqlite3.IntegrityError:
            raise ValueError("Admin user with this email already exists")
        finally:
            conn.close()
    
    def validate_admin_credentials(self, email: str, password: str) -> Optional[Dict]:
        """Validate admin login credentials"""
        import hashlib
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, name, permissions
            FROM admin_users
            WHERE email = ? AND password_hash = ?
        ''', (email, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "email": result[1], 
                "name": result[2],
                "permissions": result[3]
            }
        return None
    
    def validate_article(self, admin_id: str, article_id: str, status: str, notes: str = "") -> bool:
        """Admin validation of article content"""
        validation_id = f"val_{int(time.time())}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert validation record
            cursor.execute('''
                INSERT INTO content_validation (id, article_id, admin_id, validation_status, validation_notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (validation_id, article_id, admin_id, status, notes))
            
            # Update article admin validation status
            cursor.execute('''
                UPDATE articles 
                SET admin_validated = ?, admin_notes = ?
                WHERE id = ?
            ''', (status == 'approved', notes, article_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error validating article: {e}")
            return False
        finally:
            conn.close()


# Initialize default admin user
def init_default_admin():
    """Initialize default admin user for first-time setup"""
    admin_manager = AdminManager()
    try:
        admin_manager.create_admin_user(
            email="admin@vidyagam.com",
            name="Admin User", 
            password="AdminPass123!"
        )
        logger.info("Default admin user created")
    except ValueError:
        logger.info("Default admin user already exists")