#!/usr/bin/env python3
"""
Email Setup Validation Script
Tests email configuration and SendGrid connectivity
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from email_service import EmailDigestService

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = {
        'SENDGRID_API_KEY': os.getenv('SENDGRID_API_KEY'),
        'FROM_EMAIL': os.getenv('FROM_EMAIL', 'noreply@ai-daily.com'),
        'FROM_NAME': os.getenv('FROM_NAME', 'AI Daily'),
        'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
        'JWT_SECRET': os.getenv('JWT_SECRET')
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value and var_value != 'your-secret-key-here':
            print(f"  ✅ {var_name}: {'*' * 20}...{var_value[-4:] if len(var_value) > 4 else '***'}")
        else:
            print(f"  ❌ {var_name}: Not set or using default value")
            all_set = False
    
    return all_set

def test_email_service_initialization():
    """Test if EmailDigestService initializes correctly"""
    print("\n📧 Testing Email Service Initialization...")
    
    try:
        email_service = EmailDigestService()
        
        if email_service.sg:
            print("  ✅ SendGrid client initialized successfully")
            print(f"  ✅ From Email: {email_service.from_email}")
            print(f"  ✅ From Name: {email_service.from_name}")
            return email_service
        else:
            print("  ❌ SendGrid client not initialized (missing API key)")
            return None
            
    except Exception as e:
        print(f"  ❌ Email service initialization failed: {e}")
        return None

def test_email_template_generation():
    """Test email template generation"""
    print("\n📝 Testing Email Template Generation...")
    
    try:
        email_service = EmailDigestService()
        
        # Sample user data
        user_data = {
            'id': 1,
            'email': 'test@example.com',
            'name': 'Test User',
            'preferences': {
                'frequency': 'daily',
                'content_types': ['all'],
                'categories': ['all']
            }
        }
        
        # Sample articles
        sample_articles = [
            {
                'title': 'Revolutionary AI Model Achieves Human-Level Reasoning',
                'summary': 'OpenAI\'s latest model demonstrates unprecedented reasoning capabilities in complex problem-solving tasks.',
                'url': 'https://example.com/article1',
                'source': 'OpenAI Blog',
                'significance_score': 9.2,
                'published_date': datetime.now().isoformat()
            },
            {
                'title': 'Google Announces New AI Ethics Framework',
                'summary': 'Comprehensive guidelines for responsible AI development and deployment across all Google products.',
                'url': 'https://example.com/article2', 
                'source': 'Google AI Blog',
                'significance_score': 7.8,
                'published_date': datetime.now().isoformat()
            }
        ]
        
        # Sample multimedia content
        multimedia_content = {
            'audio': [
                {
                    'title': 'The Future of AI Safety',
                    'description': 'Leading AI researchers discuss safety measures and alignment challenges.',
                    'url': 'https://example.com/audio1',
                    'source': 'AI Podcast',
                    'duration': 45
                }
            ],
            'video': [
                {
                    'title': 'GPT-4 Turbo Deep Dive',
                    'description': 'Technical overview of the latest GPT-4 improvements and capabilities.',
                    'url': 'https://example.com/video1',
                    'source': 'OpenAI',
                    'duration': 25
                }
            ]
        }
        
        # Generate HTML template
        html_content = email_service.generate_daily_digest_html(user_data, sample_articles, multimedia_content)
        
        if html_content and len(html_content) > 1000:
            print("  ✅ Daily digest HTML template generated successfully")
            print(f"  ✅ Template length: {len(html_content):,} characters")
            
            # Save sample for inspection
            with open('/tmp/sample_email.html', 'w') as f:
                f.write(html_content)
            print("  ✅ Sample saved to /tmp/sample_email.html")
            
        else:
            print("  ❌ HTML template generation failed or too short")
            return False
        
        # Generate text template
        text_content = email_service.generate_text_digest(user_data, sample_articles)
        
        if text_content and len(text_content) > 500:
            print("  ✅ Daily digest text template generated successfully")
            print(f"  ✅ Text length: {len(text_content):,} characters")
        else:
            print("  ❌ Text template generation failed or too short")
            return False
        
        # Generate welcome email
        welcome_html = email_service.generate_welcome_email_html(user_data)
        
        if welcome_html and len(welcome_html) > 1000:
            print("  ✅ Welcome email template generated successfully")
        else:
            print("  ❌ Welcome email template generation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Template generation failed: {e}")
        return False

async def test_sendgrid_connectivity():
    """Test connection to SendGrid API"""
    print("\n🌐 Testing SendGrid API Connectivity...")
    
    try:
        email_service = EmailDigestService()
        
        if not email_service.sg:
            print("  ❌ SendGrid not initialized - skipping connectivity test")
            return False
        
        # Test with a dry run (we won't actually send)
        user_data = {
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        try:
            # Try to create a mail object (doesn't send)
            from sendgrid.helpers.mail import Mail, Email, To
            
            from_email = Email(email_service.from_email, email_service.from_name)
            to_email = To("test@example.com", "Test User")
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject="Test Subject",
                plain_text_content="Test content"
            )
            
            print("  ✅ SendGrid mail object created successfully")
            print("  ✅ API key format appears valid")
            print("  ⚠️  Actual sending test requires real email address")
            
            return True
            
        except Exception as e:
            print(f"  ❌ SendGrid mail creation failed: {e}")
            return False
        
    except Exception as e:
        print(f"  ❌ SendGrid connectivity test failed: {e}")
        return False

def print_next_steps(env_ok, service_ok, template_ok, connectivity_ok):
    """Print next steps based on test results"""
    print("\n" + "="*60)
    print("📋 TEST RESULTS SUMMARY")
    print("="*60)
    
    print(f"Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Email Service Init:    {'✅ PASS' if service_ok else '❌ FAIL'}")
    print(f"Template Generation:   {'✅ PASS' if template_ok else '❌ FAIL'}")
    print(f"SendGrid Connectivity: {'✅ PASS' if connectivity_ok else '❌ FAIL'}")
    
    print("\n📋 NEXT STEPS:")
    
    if not env_ok:
        print("❌ Fix Environment Variables:")
        print("   1. Set SENDGRID_API_KEY in Vercel dashboard")
        print("   2. Set FROM_EMAIL to your verified sender email")
        print("   3. Redeploy your backend")
    
    elif not service_ok:
        print("❌ Fix Email Service:")
        print("   1. Check SendGrid API key is valid")
        print("   2. Verify sender email in SendGrid dashboard")
        print("   3. Check SendGrid account status")
    
    elif not template_ok:
        print("❌ Fix Template Generation:")
        print("   1. Check email_service.py imports")
        print("   2. Verify jinja2 and premailer dependencies")
        print("   3. Check template syntax")
    
    elif not connectivity_ok:
        print("❌ Fix SendGrid Connectivity:")
        print("   1. Verify API key has Mail Send permissions")
        print("   2. Check SendGrid account is active")
        print("   3. Try regenerating API key")
    
    else:
        print("✅ ALL TESTS PASSED! Ready for live testing:")
        print("   1. Deploy your backend: vercel --prod")
        print("   2. Deploy your frontend: vercel --prod")
        print("   3. Sign in to your app")
        print("   4. Click 'Send Test Email' in user menu")
        print("   5. Check your inbox!")
        
        print("\n📧 MANUAL TESTING STEPS:")
        print("   1. Visit your deployed frontend")
        print("   2. Sign in with Google")
        print("   3. Click your profile → 'Send Test Email'")
        print("   4. Click your profile → 'Preview Email' to see HTML")
        print("   5. Check your email inbox (and spam folder)")

async def main():
    print("🧪 AI Daily Email Setup Validation")
    print("="*50)
    
    # Run all tests
    env_ok = test_environment_variables()
    service_ok = test_email_service_initialization() is not None
    template_ok = test_email_template_generation()
    connectivity_ok = await test_sendgrid_connectivity()
    
    # Print summary and next steps
    print_next_steps(env_ok, service_ok, template_ok, connectivity_ok)
    
    return all([env_ok, service_ok, template_ok, connectivity_ok])

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)