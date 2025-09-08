"""
Flask app with integrated source validation for admin panel
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing modules
try:
    from ai_sources_config_updated import AI_SOURCES, CONTENT_TYPES
except ImportError:
    try:
        from ai_sources_config import AI_SOURCES, CONTENT_TYPES
    except ImportError:
        AI_SOURCES = []
        CONTENT_TYPES = {}

# Import validation modules
try:
    from admin_validation_endpoints import admin_validation
    VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Validation endpoints not available: {e}")
    VALIDATION_AVAILABLE = False
    admin_validation = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configure admin API key (should be set via environment variable)
app.config['ADMIN_API_KEY'] = os.getenv('ADMIN_API_KEY', 'your-secure-admin-key-here')

# Register validation blueprint if available
if VALIDATION_AVAILABLE and admin_validation:
    app.register_blueprint(admin_validation)
    logger.info("✅ Admin validation endpoints registered")
else:
    logger.warning("⚠️ Admin validation endpoints not available")

# Existing API endpoints (from your current backend)
@app.route('/', methods=['GET'])
def home():
    """Home endpoint with admin links"""
    return jsonify({
        'status': 'AI News Scraper API',
        'version': '2.0.0',
        'features': [
            'RSS feed scraping',
            'AI-powered summaries',
            'Multi-content type support',
            'Admin validation panel' if VALIDATION_AVAILABLE else 'Basic scraping'
        ],
        'endpoints': {
            'health': '/api/health',
            'digest': '/api/digest', 
            'sources': '/api/sources',
            'content_types': '/api/content-types',
            'admin_validation': '/api/admin/validate-sources' if VALIDATION_AVAILABLE else None
        },
        'admin_panel': '/admin-validation' if VALIDATION_AVAILABLE else None
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check with validation status"""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'api': True,
            'database': True,
            'scraper': True,
            'validation': VALIDATION_AVAILABLE
        },
        'sources_info': {
            'total_sources': len(AI_SOURCES),
            'enabled_sources': len([s for s in AI_SOURCES if s.get('enabled', True)]),
            'content_types': list(CONTENT_TYPES.keys())
        }
    }
    
    if VALIDATION_AVAILABLE:
        health_data['admin_features'] = {
            'source_validation': True,
            'health_monitoring': True,
            'real_time_testing': True
        }
    
    return jsonify(health_data)

@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get configured sources"""
    enabled_sources = [source for source in AI_SOURCES if source.get('enabled', True)]
    
    return jsonify({
        'sources': enabled_sources,
        'enabled_count': len(enabled_sources),
        'total_count': len(AI_SOURCES),
        'content_types': CONTENT_TYPES
    })

@app.route('/api/content-types', methods=['GET'])
def get_content_types():
    """Get available content types"""
    return jsonify({
        'content_types': CONTENT_TYPES
    })

@app.route('/api/digest', methods=['GET'])
def get_digest():
    """Basic digest endpoint - enhanced with validation status"""
    # This would typically call your existing digest logic
    # For now, return a basic structure
    
    refresh = request.args.get('refresh', False)
    
    # Mock digest response
    digest_data = {
        'summary': {
            'keyPoints': [
                '• Configuration updated with free AI resources',
                '• Admin validation panel available' if VALIDATION_AVAILABLE else '• Basic scraping active',
                f'• {len(AI_SOURCES)} sources configured',
                f'• {len([s for s in AI_SOURCES if s.get("priority", 5) <= 2])} high-priority sources'
            ],
            'metrics': {
                'totalUpdates': len(AI_SOURCES),
                'highImpact': len([s for s in AI_SOURCES if s.get('priority') == 1]),
                'newResearch': len([s for s in AI_SOURCES if s.get('content_type') == 'blogs']),
                'industryMoves': len([s for s in AI_SOURCES if s.get('category') == 'company']),
                'sourcesConfigured': len(AI_SOURCES),
                'validationEnabled': VALIDATION_AVAILABLE
            }
        },
        'content': {
            'blog': [],
            'audio': [],
            'video': []
        },
        'topStories': [],
        'timestamp': datetime.now().isoformat(),
        'badge': 'Configuration Updated',
        'admin_features': VALIDATION_AVAILABLE
    }
    
    return jsonify(digest_data)

@app.route('/api/content/<content_type>', methods=['GET'])
def get_content_by_type(content_type):
    """Get content filtered by type"""
    # Filter sources by content type
    filtered_sources = [
        source for source in AI_SOURCES 
        if source.get('content_type') == content_type or content_type == 'all_sources'
    ]
    
    # Mock content response
    content_info = CONTENT_TYPES.get(content_type, {
        'name': content_type.title(),
        'description': f'{content_type} content from AI sources',
        'icon': '📄'
    })
    
    # Generate sample articles for demonstration
    sample_articles = []
    if filtered_sources:
        for i, source in enumerate(filtered_sources[:5]):  # Show top 5 sources
            sample_articles.append({
                'title': f'Latest from {source["name"]}',
                'description': f'Recent content from {source["name"]} - configured and ready for scraping',
                'source': source['name'],
                'url': source.get('website', source.get('rss_url', '')),
                'published_date': datetime.now().isoformat(),
                'priority': source.get('priority', 3),
                'status': 'configured'
            })
    
    return jsonify({
        'content_type': content_type,
        'content_info': content_info,
        'articles': sample_articles,
        'total': len(sample_articles),
        'sources_available': len(filtered_sources),
        'user_tier': 'admin',
        'featured_sources': [
            {'name': source['name'], 'website': source.get('website', '')} 
            for source in filtered_sources[:5]
        ]
    })

# Serve admin validation HTML
@app.route('/admin-validation')
def serve_admin_panel():
    """Serve the admin validation HTML page"""
    if not VALIDATION_AVAILABLE:
        return jsonify({
            'error': 'Admin validation not available',
            'message': 'Validation modules not loaded'
        }), 404
    
    try:
        admin_html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'admin_validation.html'
        )
        
        if os.path.exists(admin_html_path):
            with open(admin_html_path, 'r') as f:
                return f.read(), 200, {'Content-Type': 'text/html'}
        else:
            return jsonify({
                'error': 'Admin panel not found',
                'message': 'admin_validation.html not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'error': 'Failed to load admin panel',
            'message': str(e)
        }), 500

# Test endpoint for validation
@app.route('/api/test-validation', methods=['GET'])
def test_validation():
    """Test if validation is working"""
    if not VALIDATION_AVAILABLE:
        return jsonify({
            'validation_available': False,
            'message': 'Validation modules not loaded'
        })
    
    return jsonify({
        'validation_available': True,
        'admin_endpoints': [
            '/api/admin/validate-sources',
            '/api/admin/validate-single-source',
            '/api/admin/health-check',
            '/api/admin/validate-priority-sources',
            '/api/admin/validate-newsletters',
            '/api/admin/quick-test'
        ],
        'total_sources': len(AI_SOURCES),
        'free_sources': len([s for s in AI_SOURCES if s.get('priority', 5) <= 2]),
        'content_types': list(CONTENT_TYPES.keys())
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/', 
            '/api/health', 
            '/api/sources',
            '/api/content-types',
            '/api/digest',
            '/api/content/<type>',
            '/admin-validation' if VALIDATION_AVAILABLE else None,
            '/api/test-validation'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# Development server
if __name__ == '__main__':
    print("🚀 Starting AI News Scraper with Admin Validation...")
    print(f"📊 Total sources configured: {len(AI_SOURCES)}")
    print(f"🔧 Validation available: {VALIDATION_AVAILABLE}")
    print(f"🎯 Free sources (Priority 1-2): {len([s for s in AI_SOURCES if s.get('priority', 5) <= 2])}")
    
    if VALIDATION_AVAILABLE:
        print("🎉 Admin panel available at: http://localhost:5000/admin-validation")
    else:
        print("⚠️ Admin validation not available - check imports")
    
    # Run in debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)