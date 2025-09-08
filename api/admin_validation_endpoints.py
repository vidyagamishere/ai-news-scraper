"""
Admin Validation API Endpoints
Flask endpoints for source validation in admin panel
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import time
import logging
from typing import Dict, List

# Import our validation modules
from source_validator import validate_sources_sync, SourceHealthChecker
from ai_sources_config_updated import AI_SOURCES, CONTENT_TYPES

# Create blueprint for admin validation
admin_validation = Blueprint('admin_validation', __name__, url_prefix='/api/admin')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Add your admin authentication logic here
        # For now, we'll use a simple API key approach
        api_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
        
        # You can set this in your environment variables
        expected_key = current_app.config.get('ADMIN_API_KEY', 'your-secure-admin-key-here')
        
        if not api_key or api_key != expected_key:
            return jsonify({
                'error': 'Admin authentication required',
                'message': 'Please provide valid admin API key'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

@admin_validation.route('/validate-sources', methods=['POST'])
@admin_required
def validate_sources_endpoint():
    """Validate RSS sources from request or use default sources"""
    try:
        data = request.get_json() or {}
        
        # Get sources to validate
        sources_to_validate = data.get('sources', AI_SOURCES)
        
        # Get validation options
        timeout = data.get('timeout', 10)
        max_concurrent = data.get('max_concurrent', 5)
        content_type_filter = data.get('content_type')
        priority_filter = data.get('priority')
        
        # Filter sources if requested
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
        
        logger.info(f"Validating {len(sources_to_validate)} sources...")
        
        # Run validation
        results = validate_sources_sync(
            sources_to_validate,
            timeout=timeout,
            max_concurrent=max_concurrent
        )
        
        # Add metadata
        results['metadata'] = {
            'total_configured_sources': len(AI_SOURCES),
            'sources_tested': len(sources_to_validate),
            'filters_applied': {
                'content_type': content_type_filter,
                'priority': priority_filter
            }
        }
        
        logger.info(f"Validation complete. Success rate: {results['summary']['success_rate']}%")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'error': 'Validation failed',
            'message': str(e)
        }), 500

@admin_validation.route('/validate-single-source', methods=['POST'])
@admin_required
def validate_single_source_endpoint():
    """Validate a single RSS source"""
    try:
        data = request.get_json()
        if not data or 'rss_url' not in data:
            return jsonify({
                'error': 'Missing RSS URL',
                'message': 'Please provide rss_url in request body'
            }), 400
        
        # Create source object
        source = {
            'name': data.get('name', 'Test Source'),
            'rss_url': data['rss_url'],
            'website': data.get('website', ''),
            'priority': data.get('priority', 3),
            'content_type': data.get('content_type', 'blogs'),
            'category': data.get('category', 'test')
        }
        
        # Validate single source
        results = validate_sources_sync([source])
        
        if results['results']:
            return jsonify({
                'source_validation': results['results'][0],
                'timestamp': results['timestamp']
            })
        else:
            return jsonify({
                'error': 'Validation failed',
                'message': 'No results returned'
            }), 500
            
    except Exception as e:
        logger.error(f"Single source validation error: {str(e)}")
        return jsonify({
            'error': 'Single source validation failed',
            'message': str(e)
        }), 500

@admin_validation.route('/health-check', methods=['GET', 'POST'])
@admin_required
def health_check_endpoint():
    """Run comprehensive health check on all sources"""
    try:
        # Get parameters
        if request.method == 'POST':
            data = request.get_json() or {}
            sources_to_check = data.get('sources', AI_SOURCES)
        else:
            sources_to_check = AI_SOURCES
        
        logger.info(f"Running health check on {len(sources_to_check)} sources...")
        
        # Create health checker
        health_checker = SourceHealthChecker(sources_to_check)
        
        # Run health check (this will use async internally)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(health_checker.run_health_check())
        finally:
            loop.close()
        
        logger.info(f"Health check complete. Overall score: {results['health_report']['overall_health_score']}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'error': 'Health check failed',
            'message': str(e)
        }), 500

@admin_validation.route('/sources-by-type', methods=['GET'])
@admin_required
def get_sources_by_type():
    """Get sources organized by content type"""
    try:
        sources_by_type = {}
        
        for source in AI_SOURCES:
            content_type = source.get('content_type', 'blogs')
            if content_type not in sources_by_type:
                sources_by_type[content_type] = []
            sources_by_type[content_type].append(source)
        
        # Add counts and metadata
        type_summary = {}
        for content_type, sources in sources_by_type.items():
            type_info = CONTENT_TYPES.get(content_type, {})
            type_summary[content_type] = {
                'name': type_info.get('name', content_type.title()),
                'description': type_info.get('description', ''),
                'icon': type_info.get('icon', '📄'),
                'source_count': len(sources),
                'priority_breakdown': {}
            }
            
            # Priority breakdown
            for source in sources:
                priority = source.get('priority', 5)
                p_key = f'Priority {priority}'
                type_summary[content_type]['priority_breakdown'][p_key] = \
                    type_summary[content_type]['priority_breakdown'].get(p_key, 0) + 1
        
        return jsonify({
            'sources_by_type': sources_by_type,
            'type_summary': type_summary,
            'total_sources': len(AI_SOURCES),
            'content_types': list(CONTENT_TYPES.keys())
        })
        
    except Exception as e:
        logger.error(f"Sources by type error: {str(e)}")
        return jsonify({
            'error': 'Failed to organize sources',
            'message': str(e)
        }), 500

@admin_validation.route('/validate-priority-sources', methods=['POST'])
@admin_required
def validate_priority_sources():
    """Validate only high-priority sources (1-2)"""
    try:
        data = request.get_json() or {}
        max_priority = data.get('max_priority', 2)
        
        priority_sources = [
            source for source in AI_SOURCES 
            if source.get('priority', 5) <= max_priority
        ]
        
        logger.info(f"Validating {len(priority_sources)} priority sources (priority <= {max_priority})...")
        
        results = validate_sources_sync(priority_sources, timeout=15, max_concurrent=3)
        
        # Add priority analysis
        results['priority_analysis'] = {
            'max_priority_tested': max_priority,
            'priority_sources_count': len(priority_sources),
            'total_sources_count': len(AI_SOURCES),
            'percentage_of_total': round(len(priority_sources) / len(AI_SOURCES) * 100, 1)
        }
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Priority validation error: {str(e)}")
        return jsonify({
            'error': 'Priority source validation failed',
            'message': str(e)
        }), 500

@admin_validation.route('/validate-newsletters', methods=['GET', 'POST'])
@admin_required
def validate_newsletters():
    """Validate newsletter sources specifically"""
    try:
        newsletter_sources = [
            source for source in AI_SOURCES 
            if source.get('content_type') == 'newsletters'
        ]
        
        if not newsletter_sources:
            return jsonify({
                'error': 'No newsletter sources found',
                'message': 'No sources with content_type="newsletters" configured'
            }), 404
        
        logger.info(f"Validating {len(newsletter_sources)} newsletter sources...")
        
        results = validate_sources_sync(newsletter_sources, timeout=12)
        
        # Add newsletter-specific analysis
        newsletter_analysis = {
            'newsletter_sources_count': len(newsletter_sources),
            'free_newsletters': len([s for s in newsletter_sources if s.get('priority', 5) <= 2]),
            'working_newsletters': len([r for r in results['results'] if r['status'] in ['success', 'warning']]),
            'newsletters_with_recent_content': len([r for r in results['results'] if r.get('entries_count', 0) > 0])
        }
        
        results['newsletter_analysis'] = newsletter_analysis
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Newsletter validation error: {str(e)}")
        return jsonify({
            'error': 'Newsletter validation failed', 
            'message': str(e)
        }), 500

@admin_validation.route('/quick-test', methods=['GET'])
@admin_required
def quick_test():
    """Quick test of top 10 sources"""
    try:
        # Get top 10 highest priority sources
        top_sources = sorted(AI_SOURCES, key=lambda x: x.get('priority', 5))[:10]
        
        logger.info("Running quick test on top 10 sources...")
        
        results = validate_sources_sync(top_sources, timeout=8, max_concurrent=5)
        
        results['test_type'] = 'quick'
        results['sources_tested'] = 10
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Quick test error: {str(e)}")
        return jsonify({
            'error': 'Quick test failed',
            'message': str(e)
        }), 500

@admin_validation.route('/validation-status', methods=['GET'])
@admin_required
def get_validation_status():
    """Get current validation system status"""
    try:
        status = {
            'system_status': 'operational',
            'total_configured_sources': len(AI_SOURCES),
            'content_types': list(CONTENT_TYPES.keys()),
            'content_type_counts': {},
            'priority_distribution': {},
            'validation_endpoints': [
                '/api/admin/validate-sources',
                '/api/admin/validate-single-source', 
                '/api/admin/health-check',
                '/api/admin/validate-priority-sources',
                '/api/admin/validate-newsletters',
                '/api/admin/quick-test'
            ],
            'timestamp': time.time()
        }
        
        # Content type counts
        for source in AI_SOURCES:
            ct = source.get('content_type', 'unknown')
            status['content_type_counts'][ct] = status['content_type_counts'].get(ct, 0) + 1
        
        # Priority distribution
        for source in AI_SOURCES:
            p = source.get('priority', 5)
            status['priority_distribution'][f'Priority {p}'] = status['priority_distribution'].get(f'Priority {p}', 0) + 1
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'error': 'Status check failed',
            'message': str(e),
            'system_status': 'error'
        }), 500

# Error handlers
@admin_validation.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested admin validation endpoint does not exist'
    }), 404

@admin_validation.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred during validation'
    }), 500

# Export the blueprint
__all__ = ['admin_validation']