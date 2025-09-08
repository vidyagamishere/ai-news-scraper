"""
Source Validator Module for Admin Panel
Real-time RSS feed validation and testing
"""

import asyncio
import aiohttp
import feedparser
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceValidator:
    """Real-time RSS feed validator for admin panel"""
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 5):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.session = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; AINewsBot/1.0; Admin Validator)'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def validate_single_source(self, source: Dict) -> Dict:
        """Validate a single RSS source"""
        start_time = time.time()
        
        try:
            # Extract source info
            name = source.get('name', 'Unknown')
            rss_url = source.get('rss_url', '')
            website = source.get('website', '')
            priority = source.get('priority', 5)
            content_type = source.get('content_type', 'blogs')
            
            if not rss_url:
                return {
                    'name': name,
                    'status': 'error',
                    'message': 'No RSS URL provided',
                    'response_time': 0,
                    'entries_count': 0,
                    'last_updated': None,
                    'content_type': content_type,
                    'priority': priority,
                    'url': rss_url
                }
            
            # Test RSS feed
            async with self.session.get(rss_url) as response:
                response_time = time.time() - start_time
                
                if response.status != 200:
                    return {
                        'name': name,
                        'status': 'error', 
                        'message': f'HTTP {response.status}: {response.reason}',
                        'response_time': response_time,
                        'entries_count': 0,
                        'last_updated': None,
                        'content_type': content_type,
                        'priority': priority,
                        'url': rss_url
                    }
                
                content = await response.read()
                
                # Parse feed
                feed = feedparser.parse(content)
                
                # Check for feed errors
                if feed.bozo:
                    status = 'warning'
                    message = f'Feed has parsing issues: {str(feed.bozo_exception)[:100]}'
                else:
                    status = 'success'
                    message = 'RSS feed is working correctly'
                
                # Get feed metadata
                entries_count = len(feed.entries) if hasattr(feed, 'entries') else 0
                feed_title = getattr(feed.feed, 'title', name)
                feed_description = getattr(feed.feed, 'description', '')[:200]
                
                # Get latest entry date
                last_updated = None
                if feed.entries:
                    try:
                        latest_entry = feed.entries[0]
                        if hasattr(latest_entry, 'published_parsed') and latest_entry.published_parsed:
                            last_updated = datetime(*latest_entry.published_parsed[:6]).isoformat()
                        elif hasattr(latest_entry, 'updated_parsed') and latest_entry.updated_parsed:
                            last_updated = datetime(*latest_entry.updated_parsed[:6]).isoformat()
                    except:
                        pass
                
                # Additional checks
                issues = []
                if entries_count == 0:
                    issues.append('No entries found')
                elif entries_count < 5:
                    issues.append(f'Only {entries_count} entries')
                
                if last_updated:
                    last_update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00').replace('+00:00', ''))
                    days_old = (datetime.now() - last_update_date).days
                    if days_old > 30:
                        issues.append(f'Last update {days_old} days ago')
                
                if issues and status == 'success':
                    status = 'warning'
                    message += f' (Issues: {", ".join(issues)})'
                
                return {
                    'name': name,
                    'status': status,
                    'message': message,
                    'response_time': round(response_time, 2),
                    'entries_count': entries_count,
                    'last_updated': last_updated,
                    'feed_title': feed_title,
                    'feed_description': feed_description[:100] + '...' if len(feed_description) > 100 else feed_description,
                    'content_type': content_type,
                    'priority': priority,
                    'url': rss_url,
                    'website': website,
                    'issues': issues,
                    'sample_titles': [entry.title for entry in feed.entries[:3]] if feed.entries else []
                }
                
        except asyncio.TimeoutError:
            return {
                'name': name,
                'status': 'error',
                'message': f'Timeout after {self.timeout}s',
                'response_time': self.timeout,
                'entries_count': 0,
                'last_updated': None,
                'content_type': content_type,
                'priority': priority,
                'url': rss_url
            }
        except Exception as e:
            return {
                'name': name,
                'status': 'error',
                'message': f'Error: {str(e)[:100]}',
                'response_time': time.time() - start_time,
                'entries_count': 0,
                'last_updated': None,
                'content_type': content_type,
                'priority': priority,
                'url': rss_url
            }
    
    async def validate_sources_batch(self, sources: List[Dict]) -> Dict:
        """Validate multiple sources concurrently"""
        if not sources:
            return {'results': [], 'summary': {}}
        
        start_time = time.time()
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def validate_with_semaphore(source):
            async with semaphore:
                return await self.validate_single_source(source)
        
        # Run validations concurrently
        results = await asyncio.gather(*[
            validate_with_semaphore(source) for source in sources
        ])
        
        total_time = time.time() - start_time
        
        # Generate summary
        summary = self._generate_summary(results, total_time)
        
        return {
            'results': results,
            'summary': summary,
            'total_time': round(total_time, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_summary(self, results: List[Dict], total_time: float) -> Dict:
        """Generate validation summary statistics"""
        total = len(results)
        success = len([r for r in results if r['status'] == 'success'])
        warning = len([r for r in results if r['status'] == 'warning'])
        error = len([r for r in results if r['status'] == 'error'])
        
        # Response time stats
        response_times = [r['response_time'] for r in results if r['response_time'] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Entry count stats
        total_entries = sum(r['entries_count'] for r in results)
        sources_with_entries = len([r for r in results if r['entries_count'] > 0])
        
        # Content type breakdown
        content_types = {}
        for result in results:
            ct = result.get('content_type', 'unknown')
            content_types[ct] = content_types.get(ct, 0) + 1
        
        # Priority breakdown
        priority_breakdown = {}
        for result in results:
            p = result.get('priority', 5)
            priority_breakdown[f'Priority {p}'] = priority_breakdown.get(f'Priority {p}', 0) + 1
        
        return {
            'total_sources': total,
            'successful': success,
            'warnings': warning,
            'errors': error,
            'success_rate': round((success + warning) / total * 100, 1) if total > 0 else 0,
            'avg_response_time': round(avg_response_time, 2),
            'total_entries': total_entries,
            'sources_with_entries': sources_with_entries,
            'content_type_breakdown': content_types,
            'priority_breakdown': priority_breakdown,
            'validation_time': round(total_time, 2)
        }
    
    def filter_results(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Filter validation results based on criteria"""
        filtered = results
        
        if filters.get('status'):
            filtered = [r for r in filtered if r['status'] == filters['status']]
        
        if filters.get('content_type'):
            filtered = [r for r in filtered if r.get('content_type') == filters['content_type']]
        
        if filters.get('priority'):
            filtered = [r for r in filtered if r.get('priority') == int(filters['priority'])]
        
        if filters.get('min_entries'):
            min_entries = int(filters['min_entries'])
            filtered = [r for r in filtered if r.get('entries_count', 0) >= min_entries]
        
        if filters.get('max_response_time'):
            max_time = float(filters['max_response_time'])
            filtered = [r for r in filtered if r.get('response_time', 0) <= max_time]
        
        return filtered

# Async context manager for easy usage
async def validate_sources(sources: List[Dict], **kwargs) -> Dict:
    """Convenience function to validate sources"""
    async with SourceValidator(**kwargs) as validator:
        return await validator.validate_sources_batch(sources)

# Sync wrapper for Flask compatibility
def validate_sources_sync(sources: List[Dict], **kwargs) -> Dict:
    """Synchronous wrapper for Flask endpoints"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(validate_sources(sources, **kwargs))
    finally:
        loop.close()

# Source health checker
class SourceHealthChecker:
    """Continuous health monitoring for sources"""
    
    def __init__(self, sources: List[Dict]):
        self.sources = sources
        self.health_history = {}
    
    async def run_health_check(self) -> Dict:
        """Run a comprehensive health check"""
        async with SourceValidator(timeout=15, max_concurrent=3) as validator:
            results = await validator.validate_sources_batch(self.sources)
        
        # Update health history
        timestamp = datetime.now().isoformat()
        for result in results['results']:
            source_name = result['name']
            if source_name not in self.health_history:
                self.health_history[source_name] = []
            
            self.health_history[source_name].append({
                'timestamp': timestamp,
                'status': result['status'],
                'response_time': result['response_time'],
                'entries_count': result['entries_count']
            })
            
            # Keep only last 24 hours of history
            cutoff = datetime.now() - timedelta(hours=24)
            self.health_history[source_name] = [
                h for h in self.health_history[source_name]
                if datetime.fromisoformat(h['timestamp']) > cutoff
            ]
        
        # Generate health report
        health_report = self._generate_health_report(results)
        
        return {
            **results,
            'health_report': health_report,
            'history': self.health_history
        }
    
    def _generate_health_report(self, results: Dict) -> Dict:
        """Generate comprehensive health report"""
        # Identify problematic sources
        problematic_sources = [
            r for r in results['results'] 
            if r['status'] == 'error' or r.get('entries_count', 0) == 0
        ]
        
        # Identify slow sources
        slow_sources = [
            r for r in results['results']
            if r.get('response_time', 0) > 5.0
        ]
        
        # Identify stale sources (no recent updates)
        stale_sources = []
        for result in results['results']:
            if result.get('last_updated'):
                try:
                    last_update = datetime.fromisoformat(result['last_updated'].replace('Z', ''))
                    days_old = (datetime.now() - last_update).days
                    if days_old > 7:  # More than a week old
                        stale_sources.append({**result, 'days_old': days_old})
                except:
                    pass
        
        return {
            'problematic_sources': len(problematic_sources),
            'slow_sources': len(slow_sources),
            'stale_sources': len(stale_sources),
            'problematic_details': problematic_sources[:5],  # Top 5
            'slow_details': slow_sources[:5],
            'stale_details': stale_sources[:5],
            'overall_health_score': self._calculate_health_score(results['results'])
        }
    
    def _calculate_health_score(self, results: List[Dict]) -> float:
        """Calculate overall health score (0-100)"""
        if not results:
            return 0
        
        total = len(results)
        success = len([r for r in results if r['status'] == 'success'])
        warning = len([r for r in results if r['status'] == 'warning'])
        
        # Base score from success rate
        base_score = (success + warning * 0.5) / total * 100
        
        # Penalty for slow responses
        slow_count = len([r for r in results if r.get('response_time', 0) > 5.0])
        slow_penalty = (slow_count / total) * 10
        
        # Penalty for empty feeds
        empty_count = len([r for r in results if r.get('entries_count', 0) == 0])
        empty_penalty = (empty_count / total) * 15
        
        final_score = max(0, base_score - slow_penalty - empty_penalty)
        return round(final_score, 1)

# Export main functions
__all__ = [
    'SourceValidator',
    'validate_sources',
    'validate_sources_sync', 
    'SourceHealthChecker'
]