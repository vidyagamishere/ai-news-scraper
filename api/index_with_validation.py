from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
import sys
import os
import random
import time
import re

# Add parent directory to path to import sources config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import updated sources config
try:
    from ai_sources_config_updated import AI_SOURCES, CONTENT_TYPES
    SOURCES_UPDATED = True
except ImportError:
    try:
        from ai_sources_config import AI_SOURCES, CONTENT_TYPES
        SOURCES_UPDATED = False
    except ImportError:
        # Fallback if import fails
        AI_SOURCES = []
        CONTENT_TYPES = {}
        SOURCES_UPDATED = False

try:
    from top_stories_config import TOP_STORIES, URL_VALIDATION_CONFIG
except ImportError:
    # Fallback top stories if import fails
    TOP_STORIES = []
    URL_VALIDATION_CONFIG = {}

# Import email service
try:
    from email_service import EmailDigestService
    email_service = EmailDigestService()
except ImportError as e:
    print(f"Email service import failed: {e}")
    email_service = None

# Import validation modules
try:
    from source_validator import validate_sources_sync
    VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Validation not available: {e}")
    VALIDATION_AVAILABLE = False

# Simple Enhanced Scraper - Inline Implementation
import pytz
import hashlib

try:
    import anthropic
    import feedparser
    ENHANCED_DEPS_AVAILABLE = True
except ImportError:
    ENHANCED_DEPS_AVAILABLE = False

IST = pytz.timezone('Asia/Kolkata') if ENHANCED_DEPS_AVAILABLE else None

class SimpleEnhancedScraper:
    def __init__(self):
        self.claude_client = None
        if ENHANCED_DEPS_AVAILABLE:
            try:
                claude_key = os.getenv('ANTHROPIC_API_KEY')
                if claude_key:
                    self.claude_client = anthropic.Anthropic(api_key=claude_key)
                    print("✅ Claude API initialized")
            except Exception as e:
                print(f"Claude API initialization failed: {e}")
    
    def scrape_sources(self, sources=None, priority_only=False, content_type=None):
        """Scrape articles from configured sources"""
        try:
            if sources is None:
                sources = AI_SOURCES
            
            # Filter sources based on parameters
            if priority_only:
                sources = [s for s in sources if s.get('priority', 5) <= 2]
            
            if content_type and content_type != 'all_sources':
                sources = [s for s in sources if s.get('content_type') == content_type]
            
            # Filter enabled sources
            enabled_sources = [s for s in sources if s.get('enabled', True)]
            
            print(f"📡 Scraping {len(enabled_sources)} sources...")
            
            articles = []
            processed_sources = []
            errors = []
            
            for source in enabled_sources[:20]:  # Limit to 20 sources for performance
                try:
                    source_articles = self.scrape_single_source(source)
                    articles.extend(source_articles)
                    processed_sources.append(source['name'])
                    
                    # Add small delay to be respectful
                    time.sleep(0.1)
                    
                except Exception as e:
                    error_msg = f"{source['name']}: {str(e)[:100]}"
                    errors.append(error_msg)
                    print(f"❌ Error scraping {source['name']}: {e}")
            
            # Sort articles by significance score or date
            articles.sort(key=lambda x: x.get('significanceScore', 0), reverse=True)
            
            return {
                'articles': articles[:50],  # Limit to 50 articles
                'sources_processed': processed_sources,
                'total_sources': len(enabled_sources),
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return {
                'articles': [],
                'sources_processed': [],
                'total_sources': 0,
                'errors': [str(e)],
                'timestamp': datetime.now().isoformat()
            }
    
    def scrape_single_source(self, source):
        """Scrape a single RSS source"""
        articles = []
        
        try:
            if not ENHANCED_DEPS_AVAILABLE:
                # Return mock data if feedparser not available
                return [{
                    'title': f'Sample from {source["name"]}',
                    'description': 'Sample article for testing',
                    'source': source['name'],
                    'url': source.get('website', ''),
                    'time': '1h ago',
                    'significanceScore': 7.5,
                    'type': source.get('content_type', 'blog')
                }]
            
            # Parse RSS feed
            feed = feedparser.parse(source['rss_url'])
            
            if feed.bozo:
                print(f"⚠️ Feed parsing issue for {source['name']}: {feed.bozo_exception}")
            
            # Process entries
            for entry in feed.entries[:5]:  # Limit to 5 entries per source
                try:
                    # Extract article data
                    title = getattr(entry, 'title', 'Untitled')
                    description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
                    link = getattr(entry, 'link', source.get('website', ''))
                    
                    # Clean HTML from description
                    import re
                    description = re.sub(r'<[^>]+>', '', description)[:200]
                    
                    # Calculate significance score
                    significance = self.calculate_significance(title, description)
                    
                    # Get published date
                    pub_date = getattr(entry, 'published', '')
                    time_str = self.format_time_ago(pub_date) if pub_date else 'Recently'
                    
                    article = {
                        'title': title[:150],
                        'description': description,
                        'source': source['name'],
                        'url': link,
                        'time': time_str,
                        'significanceScore': significance,
                        'type': source.get('content_type', 'blog'),
                        'priority': source.get('priority', 3),
                        'category': source.get('category', 'general')
                    }
                    
                    articles.append(article)
                    
                except Exception as e:
                    print(f"❌ Error processing entry from {source['name']}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error scraping {source['name']}: {e}")
            
        return articles
    
    def calculate_significance(self, title, description):
        """Calculate article significance score"""
        score = 5.0  # Base score
        
        # High impact keywords
        high_impact_keywords = [
            'breakthrough', 'announces', 'launches', 'releases', 'new model',
            'GPT', 'ChatGPT', 'Claude', 'research', 'study', 'paper',
            'AI safety', 'AGI', 'artificial general intelligence',
            'machine learning', 'deep learning', 'neural network'
        ]
        
        text = f"{title} {description}".lower()
        
        for keyword in high_impact_keywords:
            if keyword.lower() in text:
                score += 1.0
        
        # Company mentions boost score
        companies = ['openai', 'anthropic', 'google', 'microsoft', 'meta', 'nvidia']
        for company in companies:
            if company in text:
                score += 0.5
        
        return min(score, 10.0)  # Cap at 10.0
    
    def format_time_ago(self, pub_date_str):
        """Format publication date as time ago"""
        try:
            if not pub_date_str:
                return 'Recently'
            
            # Simple time formatting
            if 'T' in pub_date_str:
                # ISO format
                pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            else:
                # Try parsing common formats
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(pub_date_str)
            
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            diff = now - pub_date
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600}h ago"
            else:
                return f"{diff.seconds // 60}m ago"
                
        except Exception:
            return 'Recently'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse URL and query parameters
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Add CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key')
        self.end_headers()
        
        response_data = {}
        
        try:
            # Route handling
            if path == '/' or path == '/api':
                response_data = {
                    'status': 'AI News Scraper API with Admin Validation',
                    'version': '2.0.0',
                    'features': [
                        'Enhanced RSS scraping',
                        'Free AI sources (45+ sources)',
                        'Admin validation panel',
                        'Real-time source testing'
                    ],
                    'sources_info': {
                        'total_sources': len(AI_SOURCES),
                        'free_sources': len([s for s in AI_SOURCES if s.get('priority', 5) <= 2]),
                        'content_types': list(CONTENT_TYPES.keys())
                    },
                    'admin_panel': '/admin-validation' if VALIDATION_AVAILABLE else None,
                    'validation_available': VALIDATION_AVAILABLE,
                    'sources_updated': SOURCES_UPDATED
                }
            
            elif path == '/api/health':
                response_data = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'components': {
                        'api': True,
                        'database': True,
                        'scraper': True,
                        'validation': VALIDATION_AVAILABLE,
                        'enhanced_scraping': ENHANCED_DEPS_AVAILABLE
                    },
                    'sources_info': {
                        'total_sources': len(AI_SOURCES),
                        'enabled_sources': len([s for s in AI_SOURCES if s.get('enabled', True)]),
                        'free_sources': len([s for s in AI_SOURCES if s.get('priority', 5) <= 2]),
                        'content_types': list(CONTENT_TYPES.keys())
                    },
                    'admin_features': {
                        'validation': VALIDATION_AVAILABLE,
                        'sources_updated': SOURCES_UPDATED
                    }
                }
            
            elif path == '/api/sources':
                enabled_sources = [source for source in AI_SOURCES if source.get('enabled', True)]
                response_data = {
                    'sources': enabled_sources,
                    'enabled_count': len(enabled_sources),
                    'total_count': len(AI_SOURCES),
                    'content_types': CONTENT_TYPES,
                    'free_sources_count': len([s for s in enabled_sources if s.get('priority', 5) <= 2])
                }
            
            elif path == '/api/content-types':
                response_data = {
                    'content_types': CONTENT_TYPES,
                    'available_types': list(CONTENT_TYPES.keys()),
                    'sources_by_type': {}
                }
                
                # Add source counts by type
                for content_type in CONTENT_TYPES.keys():
                    count = len([s for s in AI_SOURCES if s.get('content_type') == content_type])
                    response_data['sources_by_type'][content_type] = count
            
            elif path == '/api/digest':
                # Enhanced digest with real scraping
                refresh = query_params.get('refresh', ['false'])[0].lower() == 'true'
                
                scraper = SimpleEnhancedScraper()
                scraping_result = scraper.scrape_sources(priority_only=True)  # Focus on free sources
                
                articles = scraping_result['articles']
                
                # Organize by content type
                content_by_type = {
                    'blog': [a for a in articles if a.get('type') in ['blog', 'blogs']],
                    'audio': [a for a in articles if a.get('type') == 'podcasts'],
                    'video': [a for a in articles if a.get('type') == 'videos']
                }
                
                # Create top stories from highest scored articles
                top_stories = []
                for article in articles[:10]:
                    top_stories.append({
                        'title': article['title'],
                        'source': article['source'],
                        'significanceScore': article.get('significanceScore', 7.0),
                        'url': article['url'],
                        'summary': article.get('description', '')[:150]
                    })
                
                response_data = {
                    'summary': {
                        'keyPoints': [
                            f"• Latest updates from {len(scraping_result['sources_processed'])} free AI sources",
                            f"• {len(articles)} articles processed and ranked",
                            f"• Admin validation available" if VALIDATION_AVAILABLE else "• Basic scraping active",
                            f"• {len([s for s in AI_SOURCES if s.get('priority', 5) <= 2])} high-priority free sources configured"
                        ],
                        'metrics': {
                            'totalUpdates': len(articles),
                            'highImpact': len([a for a in articles if a.get('significanceScore', 0) > 8]),
                            'newResearch': len(content_by_type['blog']),
                            'industryMoves': len([a for a in articles if 'announces' in a.get('title', '').lower()]),
                            'sourcesScraped': len(scraping_result['sources_processed']),
                            'validationEnabled': VALIDATION_AVAILABLE,
                            'sourcesUpdated': SOURCES_UPDATED
                        }
                    },
                    'content': content_by_type,
                    'topStories': top_stories,
                    'timestamp': scraping_result['timestamp'],
                    'badge': f"Free Sources: {len(scraping_result['sources_processed'])} active",
                    'enhanced': ENHANCED_DEPS_AVAILABLE,
                    'admin_features': VALIDATION_AVAILABLE,
                    'scraping_errors': scraping_result.get('errors', [])[:5]  # Show first 5 errors
                }
            
            elif path.startswith('/api/content/'):
                content_type = path.split('/')[-1]
                
                scraper = SimpleEnhancedScraper()
                scraping_result = scraper.scrape_sources(content_type=content_type)
                
                articles = scraping_result['articles']
                
                content_info = CONTENT_TYPES.get(content_type, {
                    'name': content_type.title(),
                    'description': f'{content_type} content from AI sources',
                    'icon': '📄'
                })
                
                # Get featured sources for this content type
                featured_sources = []
                for source in AI_SOURCES:
                    if (source.get('content_type') == content_type or content_type == 'all_sources') and source.get('enabled', True):
                        featured_sources.append({
                            'name': source['name'],
                            'website': source.get('website', '')
                        })
                        if len(featured_sources) >= 5:
                            break
                
                response_data = {
                    'content_type': content_type,
                    'content_info': content_info,
                    'articles': articles,
                    'total': len(articles),
                    'sources_available': len(featured_sources),
                    'user_tier': 'free',
                    'featured_sources': featured_sources,
                    'scraping_info': {
                        'sources_processed': scraping_result['sources_processed'],
                        'timestamp': scraping_result['timestamp']
                    }
                }
            
            elif path == '/admin-validation':
                # Serve admin panel HTML
                try:
                    admin_html_path = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'admin_validation.html'
                    )
                    
                    if os.path.exists(admin_html_path):
                        with open(admin_html_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(html_content.encode('utf-8'))
                        return
                    else:
                        response_data = {'error': 'Admin panel not found', 'path': admin_html_path}
                except Exception as e:
                    response_data = {'error': f'Failed to load admin panel: {str(e)}'}
            
            # Admin validation endpoints
            elif path.startswith('/api/admin/') and VALIDATION_AVAILABLE:
                admin_key = self.headers.get('X-Admin-Key') or query_params.get('admin_key', [''])[0]
                expected_key = os.getenv('ADMIN_API_KEY', 'your-secure-admin-key-here')
                
                if not admin_key or admin_key != expected_key:
                    response_data = {
                        'error': 'Admin authentication required',
                        'message': 'Please provide valid admin API key'
                    }
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data, indent=2).encode())
                    return
                
                # Handle admin endpoints
                if path == '/api/admin/quick-test':
                    # Quick test of top 5 sources
                    top_sources = sorted(AI_SOURCES, key=lambda x: x.get('priority', 5))[:5]
                    results = validate_sources_sync(top_sources, timeout=8, max_concurrent=3)
                    response_data = {**results, 'test_type': 'quick', 'sources_tested': 5}
                
                elif path == '/api/admin/validate-priority-sources':
                    priority_sources = [s for s in AI_SOURCES if s.get('priority', 5) <= 2]
                    results = validate_sources_sync(priority_sources, timeout=10, max_concurrent=3)
                    response_data = {
                        **results,
                        'priority_analysis': {
                            'max_priority_tested': 2,
                            'priority_sources_count': len(priority_sources),
                            'total_sources_count': len(AI_SOURCES)
                        }
                    }
                
                elif path == '/api/admin/validation-status':
                    response_data = {
                        'system_status': 'operational',
                        'total_configured_sources': len(AI_SOURCES),
                        'free_sources': len([s for s in AI_SOURCES if s.get('priority', 5) <= 2]),
                        'content_types': list(CONTENT_TYPES.keys()),
                        'validation_available': VALIDATION_AVAILABLE,
                        'enhanced_scraping': ENHANCED_DEPS_AVAILABLE,
                        'sources_updated': SOURCES_UPDATED,
                        'timestamp': time.time()
                    }
                
                else:
                    response_data = {
                        'error': 'Admin endpoint not found',
                        'available_endpoints': [
                            '/api/admin/quick-test',
                            '/api/admin/validate-priority-sources', 
                            '/api/admin/validation-status'
                        ]
                    }
            
            else:
                response_data = {
                    'error': 'Endpoint not found',
                    'available_endpoints': [
                        '/',
                        '/api/health',
                        '/api/sources',
                        '/api/content-types', 
                        '/api/digest',
                        '/api/content/<type>',
                        '/admin-validation'
                    ]
                }
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            response_data = {
                'error': 'Internal server error',
                'message': str(e)[:200],
                'path': path
            }
        
        # Send JSON response
        try:
            json_response = json.dumps(response_data, indent=2, default=str)
            self.wfile.write(json_response.encode())
        except Exception as e:
            error_response = json.dumps({'error': f'JSON encoding failed: {str(e)}'})
            self.wfile.write(error_response.encode())
    
    def do_POST(self):
        # Handle POST requests for admin validation
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key')
        self.end_headers()
        
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
            
            try:
                request_data = json.loads(post_data)
            except json.JSONDecodeError:
                request_data = {}
            
            # Admin authentication check
            if path.startswith('/api/admin/'):
                admin_key = self.headers.get('X-Admin-Key')
                expected_key = os.getenv('ADMIN_API_KEY', 'your-secure-admin-key-here')
                
                if not admin_key or admin_key != expected_key:
                    response_data = {
                        'error': 'Admin authentication required',
                        'message': 'Please provide valid admin API key in X-Admin-Key header'
                    }
                    self.wfile.write(json.dumps(response_data).encode())
                    return
                
                if not VALIDATION_AVAILABLE:
                    response_data = {
                        'error': 'Validation not available',
                        'message': 'Validation modules not loaded'
                    }
                    self.wfile.write(json.dumps(response_data).encode())
                    return
                
                # Handle POST admin endpoints
                if path == '/api/admin/validate-sources':
                    timeout = request_data.get('timeout', 10)
                    max_concurrent = request_data.get('max_concurrent', 5)
                    content_type_filter = request_data.get('content_type')
                    priority_filter = request_data.get('priority')
                    
                    # Filter sources
                    sources_to_validate = AI_SOURCES.copy()
                    
                    if content_type_filter:
                        sources_to_validate = [
                            s for s in sources_to_validate 
                            if s.get('content_type') == content_type_filter
                        ]
                    
                    if priority_filter is not None:
                        sources_to_validate = [
                            s for s in sources_to_validate 
                            if s.get('priority') == int(priority_filter)
                        ]
                    
                    # Run validation
                    results = validate_sources_sync(
                        sources_to_validate,
                        timeout=timeout,
                        max_concurrent=max_concurrent
                    )
                    
                    response_data = {
                        **results,
                        'metadata': {
                            'total_configured_sources': len(AI_SOURCES),
                            'sources_tested': len(sources_to_validate),
                            'filters_applied': {
                                'content_type': content_type_filter,
                                'priority': priority_filter
                            }
                        }
                    }
                
                elif path == '/api/admin/validate-single-source':
                    if 'rss_url' not in request_data:
                        response_data = {
                            'error': 'Missing RSS URL',
                            'message': 'Please provide rss_url in request body'
                        }
                    else:
                        source = {
                            'name': request_data.get('name', 'Test Source'),
                            'rss_url': request_data['rss_url'],
                            'website': request_data.get('website', ''),
                            'priority': request_data.get('priority', 3),
                            'content_type': request_data.get('content_type', 'blogs'),
                            'category': request_data.get('category', 'test')
                        }
                        
                        results = validate_sources_sync([source])
                        
                        if results['results']:
                            response_data = {
                                'source_validation': results['results'][0],
                                'timestamp': results['timestamp']
                            }
                        else:
                            response_data = {
                                'error': 'Validation failed',
                                'message': 'No results returned'
                            }
                
                else:
                    response_data = {
                        'error': 'POST endpoint not found',
                        'available_post_endpoints': [
                            '/api/admin/validate-sources',
                            '/api/admin/validate-single-source'
                        ]
                    }
            else:
                response_data = {
                    'error': 'POST endpoint not found',
                    'message': 'This endpoint only supports GET requests'
                }
                
        except Exception as e:
            response_data = {
                'error': 'POST request failed',
                'message': str(e)[:200]
            }
        
        # Send response
        try:
            json_response = json.dumps(response_data, indent=2, default=str)
            self.wfile.write(json_response.encode())
        except Exception as e:
            error_response = json.dumps({'error': f'JSON encoding failed: {str(e)}'})
            self.wfile.write(error_response.encode())
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key')
        self.end_headers()

# Export the handler for Vercel
def handler_function(request):
    """Vercel handler wrapper"""
    return handler(request)