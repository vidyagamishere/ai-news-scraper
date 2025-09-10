"""
Archive Service for AI News Scraper
Handles daily digest archival and retrieval with configurable retention
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Union
import hashlib

class ArchiveService:
    def __init__(self, db_path: str = "/tmp/ai_news_archive.db"):
        self.db_path = db_path
        self.retention_days = int(os.getenv('ARCHIVE_RETENTION_DAYS', '30'))  # Default 30 days
        self.scraping_days = int(os.getenv('CONTENT_SCRAPING_DAYS', '7'))    # Default 7 days
        self._init_database()
    
    def _init_database(self):
        """Initialize archive database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Daily digests archive table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_archives (
                id TEXT PRIMARY KEY,
                archive_date DATE NOT NULL UNIQUE,
                digest_data TEXT NOT NULL,
                top_stories_count INTEGER DEFAULT 0,
                total_articles INTEGER DEFAULT 0,
                sources_processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Individual articles archive table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archived_articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT,
                content_type TEXT,
                significance_score REAL DEFAULT 0.0,
                summary TEXT,
                content_summary TEXT,
                image_url TEXT,
                published_date TIMESTAMP,
                archived_date DATE NOT NULL,
                is_top_story BOOLEAN DEFAULT 0,
                article_hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Archive metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archive_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_archive_date ON daily_archives(archive_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_archived_date ON archived_articles(archived_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_article_hash ON archived_articles(article_hash)')
        
        conn.commit()
        conn.close()
        
        # Initialize default settings
        self._init_default_settings()
    
    def _init_default_settings(self):
        """Initialize default archive settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        settings = [
            ('retention_days', str(self.retention_days)),
            ('scraping_days', str(self.scraping_days)),
            ('auto_archive_enabled', 'true'),
            ('last_cleanup', datetime.now().isoformat())
        ]
        
        for key, value in settings:
            cursor.execute('''
                INSERT OR IGNORE INTO archive_metadata (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def archive_daily_digest(self, digest_data: Dict) -> bool:
        """Archive a daily digest"""
        try:
            today = datetime.now().date()
            archive_id = f"digest_{today.isoformat()}"
            
            # Extract metadata
            top_stories_count = len(digest_data.get('topStories', []))
            total_articles = sum(len(articles) for articles in digest_data.get('content', {}).values())
            sources_processed = digest_data.get('summary', {}).get('metrics', {}).get('sourcesScraped', 0)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Archive the complete digest
            cursor.execute('''
                INSERT OR REPLACE INTO daily_archives 
                (id, archive_date, digest_data, top_stories_count, total_articles, sources_processed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                archive_id,
                today,
                json.dumps(digest_data, default=str),
                top_stories_count,
                total_articles,
                sources_processed,
                datetime.now().isoformat()
            ))
            
            # Archive individual articles
            self._archive_articles(cursor, digest_data, today)
            
            conn.commit()
            conn.close()
            
            # Cleanup old archives
            self._cleanup_old_archives()
            
            print(f"✅ Archived daily digest for {today} - {total_articles} articles, {top_stories_count} top stories")
            return True
            
        except Exception as e:
            print(f"❌ Failed to archive daily digest: {e}")
            return False
    
    def _archive_articles(self, cursor, digest_data: Dict, archive_date):
        """Archive individual articles from digest"""
        # Archive top stories
        for story in digest_data.get('topStories', []):
            article_hash = hashlib.md5(f"{story.get('url', '')}{story.get('title', '')}".encode()).hexdigest()
            
            cursor.execute('''
                INSERT OR REPLACE INTO archived_articles
                (id, title, url, source, content_type, significance_score, summary, content_summary,
                 image_url, archived_date, is_top_story, article_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"story_{archive_date}_{article_hash[:8]}",
                story.get('title', '')[:500],
                story.get('url', ''),
                story.get('source', ''),
                'top_story',
                story.get('significanceScore', 0.0),
                story.get('summary', '')[:1000],
                story.get('content_summary', '')[:2000],
                story.get('imageUrl', ''),
                archive_date,
                True,
                article_hash
            ))
        
        # Archive content articles
        for content_type, articles in digest_data.get('content', {}).items():
            for article in articles:
                article_hash = hashlib.md5(f"{article.get('url', '')}{article.get('title', '')}".encode()).hexdigest()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO archived_articles
                    (id, title, url, source, content_type, significance_score, summary, content_summary,
                     image_url, archived_date, is_top_story, article_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"article_{archive_date}_{article_hash[:8]}",
                    article.get('title', '')[:500],
                    article.get('url', ''),
                    article.get('source', ''),
                    content_type,
                    article.get('significanceScore', 0.0),
                    article.get('description', '')[:1000],
                    article.get('content_summary', '')[:2000],
                    article.get('imageUrl', ''),
                    archive_date,
                    False,
                    article_hash
                ))
    
    def get_archived_digests(self, days: Optional[int] = None) -> List[Dict]:
        """Get archived daily digests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if days:
                start_date = (datetime.now().date() - timedelta(days=days)).isoformat()
                cursor.execute('''
                    SELECT * FROM daily_archives 
                    WHERE archive_date >= ? 
                    ORDER BY archive_date DESC
                ''', (start_date,))
            else:
                cursor.execute('''
                    SELECT * FROM daily_archives 
                    ORDER BY archive_date DESC 
                    LIMIT 30
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            archives = []
            for row in results:
                archives.append({
                    'id': row[0],
                    'archive_date': row[1],
                    'digest_data': json.loads(row[2]),
                    'top_stories_count': row[3],
                    'total_articles': row[4],
                    'sources_processed': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            return archives
            
        except Exception as e:
            print(f"❌ Failed to retrieve archived digests: {e}")
            return []
    
    def get_digest_by_date(self, target_date: str) -> Optional[Dict]:
        """Get specific digest by date (YYYY-MM-DD)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT digest_data FROM daily_archives 
                WHERE archive_date = ?
            ''', (target_date,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
            
        except Exception as e:
            print(f"❌ Failed to retrieve digest for {target_date}: {e}")
            return None
    
    def search_archived_articles(self, query: str, days: int = 30, content_type: str = None) -> List[Dict]:
        """Search archived articles by title/content"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = (datetime.now().date() - timedelta(days=days)).isoformat()
            
            if content_type:
                cursor.execute('''
                    SELECT * FROM archived_articles 
                    WHERE archived_date >= ? 
                    AND content_type = ?
                    AND (title LIKE ? OR summary LIKE ?)
                    ORDER BY archived_date DESC, significance_score DESC
                    LIMIT 50
                ''', (start_date, content_type, f'%{query}%', f'%{query}%'))
            else:
                cursor.execute('''
                    SELECT * FROM archived_articles 
                    WHERE archived_date >= ? 
                    AND (title LIKE ? OR summary LIKE ?)
                    ORDER BY archived_date DESC, significance_score DESC
                    LIMIT 50
                ''', (start_date, f'%{query}%', f'%{query}%'))
            
            results = cursor.fetchall()
            conn.close()
            
            articles = []
            for row in results:
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'source': row[3],
                    'content_type': row[4],
                    'significance_score': row[5],
                    'summary': row[6],
                    'content_summary': row[7],
                    'image_url': row[8],
                    'published_date': row[9],
                    'archived_date': row[10],
                    'is_top_story': bool(row[11])
                })
            
            return articles
            
        except Exception as e:
            print(f"❌ Failed to search archived articles: {e}")
            return []
    
    def get_archive_statistics(self) -> Dict:
        """Get archive statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic stats
            cursor.execute('SELECT COUNT(*) FROM daily_archives')
            total_digests = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM archived_articles')
            total_articles = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM archived_articles WHERE is_top_story = 1')
            total_top_stories = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute('SELECT MIN(archive_date), MAX(archive_date) FROM daily_archives')
            date_range = cursor.fetchone()
            
            # Get content type distribution
            cursor.execute('''
                SELECT content_type, COUNT(*) 
                FROM archived_articles 
                GROUP BY content_type 
                ORDER BY COUNT(*) DESC
            ''')
            content_types = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_digests': total_digests,
                'total_articles': total_articles,
                'total_top_stories': total_top_stories,
                'date_range': {
                    'earliest': date_range[0] if date_range[0] else None,
                    'latest': date_range[1] if date_range[1] else None
                },
                'content_types': content_types,
                'retention_days': self.retention_days,
                'scraping_days': self.scraping_days
            }
            
        except Exception as e:
            print(f"❌ Failed to get archive statistics: {e}")
            return {}
    
    def _cleanup_old_archives(self):
        """Remove archives older than retention period"""
        try:
            cutoff_date = (datetime.now().date() - timedelta(days=self.retention_days)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old digests
            cursor.execute('DELETE FROM daily_archives WHERE archive_date < ?', (cutoff_date,))
            digests_deleted = cursor.rowcount
            
            # Delete old articles
            cursor.execute('DELETE FROM archived_articles WHERE archived_date < ?', (cutoff_date,))
            articles_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if digests_deleted > 0 or articles_deleted > 0:
                print(f"🧹 Cleaned up {digests_deleted} old digests and {articles_deleted} old articles")
                
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    
    def update_settings(self, settings: Dict) -> bool:
        """Update archive settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for key, value in settings.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO archive_metadata (setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, str(value), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Update instance variables
            if 'retention_days' in settings:
                self.retention_days = int(settings['retention_days'])
            if 'scraping_days' in settings:
                self.scraping_days = int(settings['scraping_days'])
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to update settings: {e}")
            return False
    
    def get_settings(self) -> Dict:
        """Get current archive settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT setting_key, setting_value FROM archive_metadata')
            results = cursor.fetchall()
            conn.close()
            
            settings = dict(results)
            settings.update({
                'retention_days': self.retention_days,
                'scraping_days': self.scraping_days
            })
            
            return settings
            
        except Exception as e:
            print(f"❌ Failed to get settings: {e}")
            return {
                'retention_days': self.retention_days,
                'scraping_days': self.scraping_days
            }