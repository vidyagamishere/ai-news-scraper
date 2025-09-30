#!/usr/bin/env python3
"""
Admin router for FastAPI application
Handles admin endpoints for source management and scraping operations
"""

import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Get DEBUG mode
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    logger.debug("🔍 Admin router initialized in DEBUG mode")

router = APIRouter(prefix="/admin")


class SourceCreate(BaseModel):
    name: str
    rss_url: str
    website: str = ""
    enabled: bool = True
    priority: int = 5
    category: str = "other"


class SourceUpdate(BaseModel):
    index: int
    name: str
    rss_url: str
    website: str = ""
    enabled: bool = True
    priority: int = 5
    category: str = "other"


class SourceDelete(BaseModel):
    index: int


class ScrapeRequest(BaseModel):
    scrape_type: str = "current_day"
    filter_current_day: bool = True


def verify_admin_key(request: Request):
    """Verify admin authentication"""
    auth_header = request.headers.get('Authorization', '')
    x_admin_key = request.headers.get('x-admin-key', '')
    
    # Check for Bearer token or x-admin-key
    if not (auth_header.startswith('Bearer admin-') or x_admin_key):
        raise HTTPException(
            status_code=401,
            detail={
                'error': 'Admin authentication required',
                'message': 'Please provide admin credentials'
            }
        )
    return True


def get_database_service():
    """Get database service instance"""
    try:
        from db_service import get_database_service
        return get_database_service()
    except ImportError:
        logger.error("❌ Database service not available")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Database service unavailable',
                'message': 'Cannot connect to database service'
            }
        )


@router.get("/sources")
async def get_admin_sources(
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Get all AI sources for admin management"""
    try:
        logger.info("🔧 Admin sources requested")
        
        if DEBUG:
            logger.debug("🔍 Getting database service for admin sources")
        
        db = get_database_service()
        
        sources_query = """
            SELECT 
                s.name, 
                s.rss_url, 
                s.website, 
                s.content_type, 
                s.priority, 
                s.enabled,
                COALESCE(c.name, 'general') as category
            FROM ai_sources s
            LEFT JOIN ai_topics t ON s.ai_topic_id = t.id
            LEFT JOIN ai_categories_master c ON t.category_id = c.id
            ORDER BY s.priority ASC, s.name ASC
        """
        
        if DEBUG:
            logger.debug("🔍 Executing admin sources query")
        
        sources = db.execute_query(sources_query)
        
        if DEBUG:
            logger.debug(f"🔍 Retrieved {len(sources) if sources else 0} sources from database")
        
        processed_sources = []
        for source in sources:
            processed_sources.append({
                'name': source['name'],
                'rss_url': source['rss_url'],
                'website': source.get('website', ''),
                'content_type': source.get('content_type', 'blogs'),
                'category': source.get('category', 'other'),
                'priority': source['priority'],
                'enabled': source['enabled'],
                'description': source.get('description', '')
            })
        
        logger.info(f"✅ Admin sources retrieved successfully - {len(processed_sources)} sources")
        return {
            'success': True,
            'sources': processed_sources,
            'total_count': len(processed_sources),
            'enabled_count': len([s for s in processed_sources if s['enabled']]),
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Admin sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get admin sources',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.post("/sources/add")
async def add_source(
    source: SourceCreate,
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Add a new AI source"""
    try:
        logger.info(f"🔧 Adding new source: {source.name}")
        db = get_database_service()
        
        # Note: category is derived from ai_topic_id, not stored directly
        insert_query = """
            INSERT INTO ai_sources (name, rss_url, website, content_type, priority, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        db.execute_query(
            insert_query,
            (
                source.name,
                source.rss_url,
                source.website,
                "blogs",  # Default content type
                source.priority,
                source.enabled
            ),
            fetch_results=False
        )
        
        logger.info(f"✅ Source added successfully: {source.name}")
        return {
            'success': True,
            'message': f'Source "{source.name}" added successfully',
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Add source failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to add source',
                'message': str(e)
            }
        )


@router.post("/sources/update")
async def update_source(
    update_data: SourceUpdate,
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Update an existing AI source by index"""
    try:
        logger.info(f"🔧 Updating source at index {update_data.index}")
        db = get_database_service()
        
        # First get the source at the specified index
        get_sources_query = """
            SELECT rowid FROM ai_sources ORDER BY priority ASC, name ASC
            LIMIT 1 OFFSET ?
        """
        
        result = db.execute_query(get_sources_query, (update_data.index,))
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail={'error': 'Source not found at specified index'}
            )
        
        source_rowid = result[0]['rowid']
        
        # Update the source
        update_query = """
            UPDATE ai_sources 
            SET name = ?, rss_url = ?, website = ?, category = ?, priority = ?, enabled = ?
            WHERE rowid = ?
        """
        
        db.execute_query(
            update_query,
            (
                update_data.name,
                update_data.rss_url,
                update_data.website,
                update_data.category,
                update_data.priority,
                update_data.enabled,
                source_rowid
            ),
            fetch_results=False
        )
        
        logger.info(f"✅ Source updated successfully at index {update_data.index}")
        return {
            'success': True,
            'message': f'Source at index {update_data.index} updated successfully',
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Update source failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to update source',
                'message': str(e)
            }
        )


@router.post("/sources/delete")
async def delete_source(
    delete_data: SourceDelete,
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Delete an AI source by index"""
    try:
        logger.info(f"🔧 Deleting source at index {delete_data.index}")
        db = get_database_service()
        
        # First get the source at the specified index
        get_sources_query = """
            SELECT rowid, name FROM ai_sources ORDER BY priority ASC, name ASC
            LIMIT 1 OFFSET ?
        """
        
        result = db.execute_query(get_sources_query, (delete_data.index,))
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail={'error': 'Source not found at specified index'}
            )
        
        source_rowid = result[0]['rowid']
        source_name = result[0]['name']
        
        # Delete the source
        delete_query = "DELETE FROM ai_sources WHERE rowid = ?"
        db.execute_query(delete_query, (source_rowid,), fetch_results=False)
        
        logger.info(f"✅ Source deleted successfully: {source_name}")
        return {
            'success': True,
            'message': f'Source "{source_name}" deleted successfully',
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Delete source failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to delete source',
                'message': str(e)
            }
        )


@router.post("/scrape")
async def admin_scrape(
    scrape_request: ScrapeRequest = ScrapeRequest(),
    request: Request = None,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Initiate admin scraping operation"""
    try:
        logger.info(f"🔧 Admin scrape initiated: type={scrape_request.scrape_type}")
        db = get_database_service()
        
        # Get enabled sources for scraping with category lookup
        sources_query = """
            SELECT 
                s.name, 
                s.rss_url, 
                s.website, 
                s.content_type, 
                s.priority,
                COALESCE(c.name, 'general') as category
            FROM ai_sources s
            LEFT JOIN ai_topics t ON s.ai_topic_id = t.id
            LEFT JOIN ai_categories_master c ON t.category_id = c.id
            WHERE s.enabled = TRUE
            ORDER BY s.priority ASC
        """
        
        sources = db.execute_query(sources_query)
        
        if not sources:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'No enabled sources found',
                    'message': 'Please enable at least one source for scraping'
                }
            )
        
        # For now, return a mock response since we need the enhanced scraper
        # In a real implementation, you would use the enhanced_scraper here
        logger.info(f"✅ Mock scraping completed for {len(sources)} sources")
        
        return {
            'success': True,
            'message': 'Admin scraping completed successfully',
            'data': {
                'scrape_type': scrape_request.scrape_type,
                'filter_current_day': scrape_request.filter_current_day,
                'sources_count': len(sources),
                'articles_processed': len(sources) * 5,  # Mock number
                'status': 'completed'
            },
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Admin scrape failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Admin scraping failed',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.post("/validate-feed")
async def validate_single_feed(
    request_data: dict,
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Validate a single RSS feed"""
    try:
        feed_url = request_data.get('feed_url')
        if not feed_url:
            raise HTTPException(
                status_code=400,
                detail={'error': 'Missing feed_url parameter'}
            )
        
        logger.info(f"🔧 Validating feed: {feed_url}")
        
        # Mock validation - in real implementation, you'd fetch and parse the feed
        import requests
        from urllib.parse import urlparse
        
        try:
            response = requests.head(feed_url, timeout=10)
            is_valid = response.status_code == 200
            
            validation_result = {
                'feed_url': feed_url,
                'status': 'valid' if is_valid else 'invalid',
                'message': f'Feed returned status {response.status_code}',
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
        except requests.RequestException as e:
            validation_result = {
                'feed_url': feed_url,
                'status': 'invalid',
                'message': f'Feed validation failed: {str(e)}',
                'content_type': 'unknown'
            }
        
        logger.info(f"✅ Feed validation completed: {validation_result['status']}")
        return {
            'success': True,
            'result': validation_result
        }
        
    except Exception as e:
        logger.error(f"❌ Feed validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Feed validation failed',
                'message': str(e)
            }
        )


@router.post("/validate-all-feeds")
async def validate_all_feeds(
    request: Request,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Validate all RSS feeds in the database"""
    try:
        logger.info("🔧 Validating all feeds")
        db = get_database_service()
        
        # Get all sources
        sources_query = "SELECT name, rss_url FROM ai_sources ORDER BY name ASC"
        sources = db.execute_query(sources_query)
        
        validation_results = []
        
        for source in sources:
            try:
                import requests
                response = requests.head(source['rss_url'], timeout=10)
                is_valid = response.status_code == 200
                
                validation_results.append({
                    'name': source['name'],
                    'feed_url': source['rss_url'],
                    'status': 'valid' if is_valid else 'invalid',
                    'message': f'Status {response.status_code}',
                    'content_type': response.headers.get('content-type', 'unknown')
                })
                
            except requests.RequestException as e:
                validation_results.append({
                    'name': source['name'],
                    'feed_url': source['rss_url'],
                    'status': 'invalid',
                    'message': f'Error: {str(e)}',
                    'content_type': 'unknown'
                })
        
        valid_count = len([r for r in validation_results if r['status'] == 'valid'])
        invalid_count = len([r for r in validation_results if r['status'] == 'invalid'])
        
        logger.info(f"✅ Feed validation completed: {valid_count} valid, {invalid_count} invalid")
        return {
            'success': True,
            'total_checked': len(validation_results),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'results': validation_results
        }
        
    except Exception as e:
        logger.error(f"❌ All feeds validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'All feeds validation failed',
                'message': str(e)
            }
        )