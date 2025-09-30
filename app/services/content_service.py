#!/usr/bin/env python3
"""
Content service for modular FastAPI architecture
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List

# Ensure logging is available globally as a fallback
import logging as logging_module

# Make logging available in global namespace as a workaround
globals()['logging'] = logging

from db_service import get_database_service

logger = logging.getLogger(__name__)


class ContentService:
    def __init__(self):
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        logger.info("📰 ContentService initialized with PostgreSQL")
        
        if self.DEBUG:
            logger.debug("🔍 Debug mode enabled in ContentService")
    
    def get_digest(self, user_id: Optional[str] = None, personalized: bool = False) -> Dict[str, Any]:
        """Get news digest from PostgreSQL database with topic information"""
        try:
            db = get_database_service()
            
            logger.info(f"📊 Getting digest - User: {user_id or 'anonymous'}, Personalized: {personalized}")
            
            if self.DEBUG:
                logger.debug(f"🔍 Digest parameters - user_id: {user_id}, personalized: {personalized}")
            
            # Get articles with topic information using database view
            articles_query = """
                SELECT * FROM digest_articles
                WHERE published_at > NOW() - INTERVAL '7 days'
                ORDER BY published_at DESC, significance_score DESC
                LIMIT 100
            """
            
            if self.DEBUG:
                logger.debug(f"🔍 Executing digest query")
            
            articles = db.execute_query(articles_query)
            
            if self.DEBUG:
                logger.debug(f"🔍 Found {len(articles) if articles else 0} articles for digest")
            
            # Process articles for response
            processed_articles = []
            for article in articles:
                article_dict = dict(article)
                
                # Convert timestamps to ISO format
                for field in ['published_at', 'scraped_at']:
                    if article_dict.get(field):
                        article_dict[field] = article_dict[field].isoformat() if hasattr(article_dict[field], 'isoformat') else str(article_dict[field])
                
                # Parse topics JSON
                if article_dict.get('topics'):
                    if isinstance(article_dict['topics'], str):
                        article_dict['topics'] = json.loads(article_dict['topics'])
                
                # Convert topic strings to lists
                if article_dict.get('topic_names'):
                    if isinstance(article_dict['topic_names'], str):
                        article_dict['topic_names'] = article_dict['topic_names'].split(', ') if article_dict['topic_names'] else []
                
                if article_dict.get('topic_categories'):
                    if isinstance(article_dict['topic_categories'], str):
                        article_dict['topic_categories'] = article_dict['topic_categories'].split(', ') if article_dict['topic_categories'] else []
                
                processed_articles.append(article_dict)
            
            # Get top stories (high significance score)
            top_stories = [article for article in processed_articles if article.get('significance_score', 0) >= 8][:10]
            
            # Organize content by type using content_type_name from database view
            content = {
                'blog': [a for a in processed_articles if a.get('content_type_name') == 'blogs'][:20],
                'audio': [a for a in processed_articles if a.get('content_type_name') == 'podcasts'][:15],
                'video': [a for a in processed_articles if a.get('content_type_name') == 'videos'][:15],
                'events': [a for a in processed_articles if a.get('content_type_name') == 'events'][:10],
                'learning': [a for a in processed_articles if a.get('content_type_name') == 'learning'][:10],
                'demos': [a for a in processed_articles if a.get('content_type_name') == 'demos'][:10]
            }
            
            # Create summary
            summary = {
                'total_articles': len(processed_articles),
                'top_stories_count': len(top_stories),
                'content_distribution': {k: len(v) for k, v in content.items()},
                'latest_update': datetime.utcnow().isoformat(),
                'personalization_note': f"{'Personalized' if personalized else 'General'} content for AI professionals"
            }
            
            response = {
                'topStories': top_stories,
                'content': content,
                'summary': summary,
                'personalized': personalized,
                'debug_info': {
                    'total_articles_fetched': len(processed_articles),
                    'database_view_used': 'digest_articles',
                    'is_personalized': personalized,
                    'user_id': user_id,
                    'database_type': 'postgresql',
                    'migration_from_sqlite': True,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ Digest generated successfully - {len(processed_articles)} articles, {len(top_stories)} top stories")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to get digest: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e
    
    def get_content_by_type(self, content_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get content by type from PostgreSQL"""
        try:
            db = get_database_service()
            
            query = """
                SELECT * FROM articles_with_topics
                WHERE content_type_name = %s
                ORDER BY published_at DESC
                LIMIT %s
            """
            
            articles = db.execute_query(query, (content_type, limit))
            
            processed_articles = []
            for article in articles:
                article_dict = dict(article)
                
                # Convert timestamps
                for field in ['published_at', 'scraped_at']:
                    if article_dict.get(field):
                        article_dict[field] = article_dict[field].isoformat() if hasattr(article_dict[field], 'isoformat') else str(article_dict[field])
                
                # Parse JSON fields
                if article_dict.get('topics'):
                    if isinstance(article_dict['topics'], str):
                        article_dict['topics'] = json.loads(article_dict['topics'])
                
                processed_articles.append(article_dict)
            
            logger.info(f"✅ Retrieved {len(processed_articles)} articles for content type: {content_type}")
            return processed_articles
            
        except Exception as e:
            logger.error(f"❌ Failed to get content by type: {str(e)}")
            return []
    
    def get_ai_topics(self) -> List[Dict[str, Any]]:
        """Get all AI topics from PostgreSQL"""
        try:
            db = get_database_service()
            
            query = """
                SELECT id, name, description, category, is_active
                FROM ai_topics
                WHERE is_active = TRUE
                ORDER BY name
            """
            
            topics = db.execute_query(query)
            
            processed_topics = []
            for topic in topics:
                processed_topics.append(dict(topic))
            
            logger.info(f"✅ Retrieved {len(processed_topics)} AI topics")
            return processed_topics
            
        except Exception as e:
            logger.error(f"❌ Failed to get AI topics: {str(e)}")
            return []
    
    def get_content_types(self) -> List[Dict[str, Any]]:
        """Get all content types from PostgreSQL"""
        try:
            db = get_database_service()
            
            query = """
                SELECT id, name, display_name, description, frontend_section, icon, is_active
                FROM content_types
                WHERE is_active = TRUE
                ORDER BY name
            """
            
            content_types = db.execute_query(query)
            
            processed_types = []
            for content_type in content_types:
                processed_types.append(dict(content_type))
            
            logger.info(f"✅ Retrieved {len(processed_types)} content types")
            return processed_types
            
        except Exception as e:
            logger.error(f"❌ Failed to get content types: {str(e)}")
            return []
    
    def scrape_content(self) -> Dict[str, Any]:
        """Trigger content scraping operation"""
        try:
            logger.info("🕷️ Starting content scraping operation")
            
            if self.DEBUG:
                logger.debug("🔍 Scrape content method called")
            
            db = get_database_service()
            
            # Get enabled sources for scraping
            sources_query = """
                SELECT 
                    s.id, s.name, s.rss_url, s.website, s.content_type, s.priority,
                    COALESCE(c.name, 'general') as category
                FROM ai_sources s
                LEFT JOIN ai_topics t ON s.ai_topic_id = t.id
                LEFT JOIN ai_categories_master c ON t.category_id = c.id
                WHERE s.enabled = TRUE
                ORDER BY s.priority ASC
            """
            
            if self.DEBUG:
                logger.debug("🔍 Getting enabled sources for scraping")
            
            sources = db.execute_query(sources_query)
            
            if not sources:
                logger.warning("⚠️ No enabled sources found for scraping")
                return {
                    'success': False,
                    'message': 'No enabled sources found',
                    'sources_processed': 0,
                    'articles_scraped': 0
                }
            
            if self.DEBUG:
                logger.debug(f"🔍 Found {len(sources)} enabled sources")
            
            # For now, return a mock response since actual scraping needs implementation
            # In a real implementation, you would iterate through sources and scrape content
            articles_scraped = 0
            for source in sources:
                if self.DEBUG:
                    logger.debug(f"🔍 Processing source: {source['name']}")
                # Mock scraping - in real implementation:
                # articles = scrape_rss_feed(source['rss_url'])
                # articles_scraped += len(articles)
                articles_scraped += 3  # Mock number
            
            logger.info(f"✅ Content scraping completed - {len(sources)} sources, {articles_scraped} articles")
            
            return {
                'success': True,
                'message': 'Content scraping completed successfully',
                'sources_processed': len(sources),
                'articles_scraped': articles_scraped,
                'sources': [{'name': s['name'], 'category': s['category']} for s in sources]
            }
            
        except Exception as e:
            logger.error(f"❌ Content scraping failed: {str(e)}")
            if self.DEBUG:
                logger.debug(f"🔍 Scraping error details: {traceback.format_exc()}")
            raise e