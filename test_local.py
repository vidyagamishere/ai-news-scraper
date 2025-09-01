#!/usr/bin/env python3
"""
Local test script for AI News Scraper API
Tests the Vercel handler function locally
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from index import handler
import json

def test_endpoint(method, path, body=None):
    """Test an API endpoint locally"""
    request = {
        'httpMethod': method,
        'path': path,
        'body': json.dumps(body) if body else None
    }
    
    context = {}
    response = handler(request, context)
    
    print(f"\n{'='*50}")
    print(f"Testing: {method} {path}")
    print(f"Status: {response['statusCode']}")
    print(f"Headers: {json.dumps(response.get('headers', {}), indent=2)}")
    
    if response.get('body'):
        try:
            body_data = json.loads(response['body'])
            print(f"Body: {json.dumps(body_data, indent=2)}")
        except:
            print(f"Body (raw): {response['body'][:200]}...")
    
    return response

def main():
    """Run comprehensive API tests"""
    print("AI News Scraper API - Local Testing")
    print("Testing all endpoints...")
    
    # System endpoints
    test_endpoint('GET', '/')
    test_endpoint('GET', '/health')
    test_endpoint('GET', '/docs')
    test_endpoint('GET', '/openapi.json')
    
    # Content endpoints
    test_endpoint('GET', '/api/digest')
    test_endpoint('GET', '/api/content-types')
    test_endpoint('GET', '/api/content/blogs')
    test_endpoint('GET', '/api/scrape')
    test_endpoint('GET', '/api/sources')
    
    # Multimedia endpoints
    test_endpoint('GET', '/api/multimedia/audio')
    test_endpoint('GET', '/api/multimedia/video')
    test_endpoint('GET', '/api/multimedia/scrape')
    test_endpoint('GET', '/api/multimedia/sources')
    
    # Auth endpoints
    test_endpoint('POST', '/auth/google', {'token': 'test-token'})
    test_endpoint('POST', '/auth/register', {'email': 'test@example.com', 'password': 'test123'})
    test_endpoint('POST', '/auth/signup', {'name': 'Test User', 'email': 'test@example.com', 'password': 'test123'})
    test_endpoint('POST', '/auth/login', {'email': 'test@example.com', 'password': 'test123'})
    test_endpoint('GET', '/auth/profile')
    test_endpoint('PUT', '/auth/preferences', {'content_types': ['blogs', 'events'], 'frequency': 'weekly'})
    
    # Content-specific endpoints
    test_endpoint('GET', '/api/content/events')
    test_endpoint('GET', '/api/content/learn')
    test_endpoint('GET', '/api/user-preferences')
    test_endpoint('GET', '/topics')
    
    # Auto-update endpoints
    test_endpoint('GET', '/api/auto-update/status')
    test_endpoint('POST', '/api/auto-update/trigger')
    
    # Subscription endpoints
    test_endpoint('GET', '/subscription/preferences')
    test_endpoint('POST', '/subscription/preferences', {'frequency': 'daily'})
    test_endpoint('POST', '/subscription/upgrade')
    
    # Admin endpoints
    test_endpoint('GET', '/admin/subscribers')
    test_endpoint('GET', '/admin/subscribers/stats')
    test_endpoint('POST', '/admin/subscribers/1/activate')
    
    # Test 404
    test_endpoint('GET', '/nonexistent')
    
    print(f"\n{'='*50}")
    print("Local testing completed!")

if __name__ == '__main__':
    main()