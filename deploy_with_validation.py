#!/usr/bin/env python3
"""
Deployment script for AI News Scraper with Admin Validation
Tests local functionality before deployment
"""

import sys
import os
import subprocess
import time
import requests
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask',
        'flask-cors', 
        'requests',
        'feedparser',
        'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """Install missing packages"""
    if not packages:
        return True
    
    print(f"📦 Installing missing packages: {', '.join(packages)}")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install'
        ] + packages)
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install packages")
        return False

def test_local_validation():
    """Test the validation functionality locally"""
    print("🧪 Testing validation functionality locally...")
    
    # Test imports
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from api.source_validator import validate_sources_sync
        from ai_sources_config_updated import AI_SOURCES
        
        # Test with a few sources
        test_sources = AI_SOURCES[:3] if AI_SOURCES else []
        
        if test_sources:
            print(f"Testing {len(test_sources)} sources...")
            results = validate_sources_sync(test_sources, timeout=5)
            
            if results:
                summary = results.get('summary', {})
                print(f"✅ Validation test successful!")
                print(f"   Success rate: {summary.get('success_rate', 0)}%")
                print(f"   Total entries: {summary.get('total_entries', 0)}")
                return True
            else:
                print("❌ Validation returned no results")
                return False
        else:
            print("⚠️ No sources to test")
            return True
            
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def start_test_server():
    """Start the Flask test server"""
    print("🚀 Starting test server...")
    
    try:
        # Change to the API directory
        api_dir = os.path.join(os.path.dirname(__file__), 'api')
        
        # Start the Flask app with validation
        app_file = os.path.join(api_dir, 'app_with_validation.py')
        
        if os.path.exists(app_file):
            print(f"Starting server from: {app_file}")
            process = subprocess.Popen([
                sys.executable, app_file
            ], cwd=api_dir)
            return process
        else:
            print(f"❌ App file not found: {app_file}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start test server: {e}")
        return None

def test_api_endpoints():
    """Test API endpoints"""
    base_url = "http://localhost:5000"
    
    print("🔍 Testing API endpoints...")
    
    # Wait for server to start
    time.sleep(3)
    
    endpoints_to_test = [
        ("/", "Home endpoint"),
        ("/api/health", "Health check"),
        ("/api/sources", "Sources list"),
        ("/api/content-types", "Content types"),
        ("/api/test-validation", "Validation test")
    ]
    
    results = []
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                results.append(True)
            else:
                print(f"❌ {description}: HTTP {response.status_code}")
                results.append(False)
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {str(e)}")
            results.append(False)
    
    return all(results)

def update_vercel_config():
    """Update Vercel configuration with validation support"""
    print("📝 Updating Vercel configuration...")
    
    vercel_json = {
        "version": 2,
        "builds": [
            {
                "src": "api/app_with_validation.py",
                "use": "@vercel/python"
            }
        ],
        "routes": [
            {
                "src": "/admin-validation",
                "dest": "/api/app_with_validation.py"
            },
            {
                "src": "/api/(.*)",
                "dest": "/api/app_with_validation.py"
            },
            {
                "src": "/(.*)",
                "dest": "/api/app_with_validation.py"
            }
        ],
        "env": {
            "ADMIN_API_KEY": "@admin_api_key"
        },
        "functions": {
            "api/app_with_validation.py": {
                "maxDuration": 30
            }
        }
    }
    
    try:
        import json
        with open('vercel_validation.json', 'w') as f:
            json.dump(vercel_json, f, indent=2)
        
        print("✅ Created vercel_validation.json")
        return True
    except Exception as e:
        print(f"❌ Failed to create Vercel config: {e}")
        return False

def create_requirements_txt():
    """Create requirements.txt with validation dependencies"""
    print("📋 Creating requirements.txt...")
    
    requirements = [
        "flask>=2.0.0",
        "flask-cors>=3.0.0", 
        "requests>=2.25.0",
        "feedparser>=6.0.0",
        "aiohttp>=3.8.0",
        "python-dateutil>=2.8.0",
        "pytz>=2021.1"
    ]
    
    try:
        with open('requirements_validation.txt', 'w') as f:
            f.write('\n'.join(requirements))
        
        print("✅ Created requirements_validation.txt")
        return True
    except Exception as e:
        print(f"❌ Failed to create requirements: {e}")
        return False

def main():
    """Main deployment preparation"""
    print("🎯 AI News Scraper - Admin Validation Deployment")
    print("=" * 50)
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"📍 Working directory: {current_dir}")
    
    # Step 1: Check dependencies
    print("\n1️⃣ Checking dependencies...")
    missing_deps = check_dependencies()
    
    if missing_deps:
        print(f"⚠️ Missing packages: {missing_deps}")
        if input("Install missing packages? (y/n): ").lower() == 'y':
            if not install_dependencies(missing_deps):
                print("❌ Deployment preparation failed")
                return False
        else:
            print("⚠️ Continuing without installing packages")
    else:
        print("✅ All dependencies available")
    
    # Step 2: Test validation functionality
    print("\n2️⃣ Testing validation functionality...")
    if not test_local_validation():
        print("⚠️ Validation test failed, but continuing...")
    
    # Step 3: Create configuration files
    print("\n3️⃣ Creating deployment configuration...")
    update_vercel_config()
    create_requirements_txt()
    
    # Step 4: Test server locally (optional)
    if input("\n4️⃣ Test server locally? (y/n): ").lower() == 'y':
        print("Starting test server...")
        server_process = start_test_server()
        
        if server_process:
            try:
                # Test endpoints
                if test_api_endpoints():
                    print("✅ All endpoint tests passed!")
                else:
                    print("⚠️ Some endpoint tests failed")
                
                print(f"\n🎉 Test server running at http://localhost:5000")
                print(f"🎛️ Admin panel: http://localhost:5000/admin-validation")
                print("\nPress Enter to stop the server...")
                input()
                
            finally:
                server_process.terminate()
                print("🛑 Test server stopped")
        else:
            print("❌ Failed to start test server")
    
    # Step 5: Deployment instructions
    print("\n" + "=" * 50)
    print("🚀 DEPLOYMENT INSTRUCTIONS")
    print("=" * 50)
    print("""
To deploy with admin validation:

1. Update your main API file:
   cp api/app_with_validation.py api/index.py

2. Update sources configuration:
   cp ai_sources_config_updated.py ai_sources_config.py

3. Update requirements:
   cp requirements_validation.txt requirements.txt

4. Update Vercel config:
   cp vercel_validation.json vercel.json

5. Set admin API key in Vercel:
   vercel env add ADMIN_API_KEY

6. Deploy to Vercel:
   vercel --prod

7. Access admin panel:
   https://your-domain.vercel.app/admin-validation

🔑 IMPORTANT: Set a secure ADMIN_API_KEY in your Vercel environment!
""")

    print("✅ Deployment preparation complete!")
    return True

if __name__ == "__main__":
    main()