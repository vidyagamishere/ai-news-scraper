#!/usr/bin/env python3
"""
Test script for authentication endpoints
Run this after deployment to verify the subscription system works
"""

import requests
import json
import sys

def test_api_health(base_url):
    """Test API health endpoint"""
    print("Testing API health...")
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy")
            print(f"   Components: {data.get('components', {})}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False

def test_endpoints_structure(base_url):
    """Test that auth endpoints exist (will return 401/400, but should not 404)"""
    endpoints = [
        ("/auth/google", "POST"),
        ("/auth/profile", "GET"),
        ("/subscription/preferences", "GET"),
        ("/subscription/preferences", "POST"),
        ("/admin/subscribers", "GET"),
        ("/admin/subscribers/stats", "GET"),
    ]
    
    print("\nTesting endpoint availability...")
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}")
            else:
                response = requests.post(f"{base_url}{endpoint}", json={})
            
            if response.status_code == 404:
                print(f"❌ {method} {endpoint} - Not Found (404)")
            elif response.status_code in [401, 422, 400]:
                print(f"✅ {method} {endpoint} - Available (returns {response.status_code} as expected)")
            else:
                print(f"⚠️  {method} {endpoint} - Unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")

def test_cors_headers(base_url):
    """Test CORS headers are set correctly"""
    print("\nTesting CORS headers...")
    try:
        response = requests.options(f"{base_url}/auth/profile")
        headers = response.headers
        
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        for header, expected_value in cors_headers.items():
            actual_value = headers.get(header, '')
            if expected_value in actual_value or actual_value == expected_value:
                print(f"✅ {header}: {actual_value}")
            else:
                print(f"❌ {header}: Expected '{expected_value}', got '{actual_value}'")
                
    except Exception as e:
        print(f"❌ CORS test error: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_auth.py <base_url>")
        print("Example: python test_auth.py https://ai-news-scraper.vercel.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    print(f"Testing AI News Scraper API at: {base_url}")
    print("=" * 50)
    
    # Run tests
    health_ok = test_api_health(base_url)
    test_endpoints_structure(base_url)
    test_cors_headers(base_url)
    
    print("\n" + "=" * 50)
    if health_ok:
        print("✅ Basic deployment test completed successfully!")
        print("🔧 Next steps:")
        print("   1. Set up Google OAuth Client ID in environment variables")
        print("   2. Test Google authentication from the frontend")
        print("   3. Verify JWT token generation and validation")
    else:
        print("❌ Deployment has issues. Check logs and environment variables.")

if __name__ == "__main__":
    main()