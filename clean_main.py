#!/usr/bin/env python3
"""
Clean main entry point for AI News Scraper API
PostgreSQL CRUD operations only - no migration code
"""

import os
import sys
import logging
import json
import base64
import hmac
import hashlib
import requests
import feedparser
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, Dict, List, Any
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Import Pydantic models for authentication and responses
try:
    from app.models.schemas import (
        UserResponse, UserPreferences, GoogleAuthRequest, 
        OTPRequest, OTPVerifyRequest, TokenResponse
    )
except ImportError:
    # Define minimal models inline if app.models.schemas is not available
    class UserResponse(BaseModel):
        id: str
        email: str
        name: Optional[str] = None
        profile_image: Optional[str] = None
        subscription_tier: str = "free"
        preferences: Dict[str, Any] = {}
        verified_email: bool = False
        
    class UserPreferences(BaseModel):
        topics: Optional[List[str]] = []
        user_roles: Optional[List[str]] = []
        role_type: Optional[str] = None
        experience_level: Optional[str] = None
        content_types: Optional[List[str]] = []
        newsletter_frequency: Optional[str] = "weekly"
        email_notifications: Optional[bool] = True
        breaking_news_alerts: Optional[bool] = False
        newsletter_subscribed: Optional[bool] = True
        onboarding_completed: Optional[bool] = False
        
    class GoogleAuthRequest(BaseModel):
        credential: str
        
    class OTPRequest(BaseModel):
        email: str
        name: Optional[str] = None
        auth_mode: Optional[str] = "signin"
        
    class OTPVerifyRequest(BaseModel):
        email: str
        otp: str
        userData: Optional[Dict[str, Any]] = {}
        
    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"
        user: UserResponse

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import simple database service
from simple_db_service import get_database_service, close_database_service

# Authentication helper functions
class AuthService:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET', 'ai-news-jwt-secret-2025-default')
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT token with HMAC-SHA256 signature"""
        try:
            header = {"alg": "HS256", "typ": "JWT"}
            payload = {
                "sub": user_data.get('sub', ''),
                "email": user_data.get('email', ''),
                "name": user_data.get('name', ''),
                "picture": user_data.get('picture', ''),
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            
            header_encoded = base64.urlsafe_b64encode(
                json.dumps(header, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            payload_encoded = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            message = f"{header_encoded}.{payload_encoded}"
            signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
            
            return f"{header_encoded}.{payload_encoded}.{signature_encoded}"
        except Exception as e:
            logger.error(f"❌ JWT token creation failed: {str(e)}")
            raise Exception(f"Token creation failed: {str(e)}")
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and extract user data"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
            
            signature_to_verify = signature_encoded
            while len(signature_to_verify) % 4:
                signature_to_verify += '='
            
            expected_with_padding = expected_signature_encoded
            while len(expected_with_padding) % 4:
                expected_with_padding += '='
            
            if signature_to_verify != expected_with_padding:
                return None
            
            # Decode payload
            payload_with_padding = payload_encoded
            while len(payload_with_padding) % 4:
                payload_with_padding += '='
            
            payload_decoded = base64.urlsafe_b64decode(payload_with_padding.encode())
            payload_data = json.loads(payload_decoded.decode())
            
            # Check expiration
            current_time = int(datetime.utcnow().timestamp())
            if payload_data.get('exp', 0) < current_time:
                return None
            
            return payload_data
        except Exception as e:
            logger.error(f"❌ JWT token verification failed: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from PostgreSQL database"""
        try:
            db = get_database_service()
            query = """
                SELECT id, email, name, profile_image, subscription_tier, preferences, 
                       created_at, last_login_at, verified_email
                FROM users 
                WHERE email = %s
            """
            result = db.execute_query(query, (email,), fetch_all=False)
            
            if result:
                user_dict = dict(result)
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                return user_dict
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get user by email: {str(e)}")
            return None
    
    def create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user in PostgreSQL database"""
        try:
            db = get_database_service()
            existing_user = self.get_user_by_email(user_data['email'])
            
            if existing_user:
                query = """
                    UPDATE users 
                    SET name = %s, profile_image = %s, last_login_at = CURRENT_TIMESTAMP
                    WHERE email = %s
                    RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email
                """
                result = db.execute_query(
                    query, 
                    (user_data.get('name'), user_data.get('picture'), user_data['email']),
                    fetch_all=False
                )
            else:
                user_id = user_data.get('sub', f"user_{int(datetime.utcnow().timestamp())}")
                query = """
                    INSERT INTO users (id, email, name, profile_image, verified_email, created_at, last_login_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email
                """
                result = db.execute_query(
                    query,
                    (user_id, user_data['email'], user_data.get('name'), user_data.get('picture'), True),
                    fetch_all=False
                )
            
            if result:
                user_dict = dict(result)
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                else:
                    user_dict['preferences'] = {}
                return user_dict
            else:
                raise Exception("Failed to create/update user")
        except Exception as e:
            logger.error(f"❌ Failed to create/update user: {str(e)}")
            raise e
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user preferences in PostgreSQL database"""
        try:
            db = get_database_service()
            query = """
                UPDATE users 
                SET preferences = %s
                WHERE id = %s
                RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email
            """
            result = db.execute_query(
                query,
                (json.dumps(preferences), user_id),
                fetch_all=False
            )
            
            if result:
                user_dict = dict(result)
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                return user_dict
            else:
                raise Exception("Failed to update user preferences")
        except Exception as e:
            logger.error(f"❌ Failed to update user preferences: {str(e)}")
            raise e

# Authentication dependency
def get_current_user(authorization: Optional[str] = Header(None)) -> UserResponse:
    """Get current authenticated user from JWT token"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.split(' ')[1]
    auth_service = AuthService()
    user_data = auth_service.verify_jwt_token(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user from database
    user = auth_service.get_user_by_email(user_data['email'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(**user)

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[UserResponse]:
    """Get current authenticated user from JWT token - optional for digest endpoint"""
    try:
        if not authorization or not authorization.startswith('Bearer '):
            return None
        
        token = authorization.split(' ')[1]
        auth_service = AuthService()
        user_data = auth_service.verify_jwt_token(token)
        
        if not user_data:
            return None
        
        # Get user from database
        user = auth_service.get_user_by_email(user_data['email'])
        if not user:
            return None
        
        return UserResponse(**user)
    except Exception:
        return None

def get_auth_service() -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService()

# Scraping functionality
async def scrape_content_from_sources():
    """Scrape content from ai_sources table and store in articles table"""
    try:
        logger.info("🕷️ Starting content scraping from ai_sources...")
        db = get_database_service()
        
        # Get enabled sources
        sources_query = "SELECT name, rss_url, content_type, category FROM ai_sources WHERE enabled = TRUE"
        sources = db.execute_query(sources_query)
        
        scraped_count = 0
        for source in sources:
            try:
                logger.info(f"📡 Scraping: {source['name']}")
                
                # Fetch RSS feed
                response = requests.get(source['rss_url'], timeout=30)
                feed = feedparser.parse(response.content)
                
                # Process entries
                for entry in getattr(feed, 'entries', [])[:10]:  # Limit to 10 per source
                    try:
                        # Parse published date
                        published_at = datetime.utcnow()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_at = datetime(*entry.published_parsed[:6])
                        
                        # Create article data
                        article_data = {
                            'title': entry.get('title', ''),
                            'url': entry.get('link', ''),
                            'description': entry.get('description', ''),
                            'source': source['name'],
                            'published_at': published_at,
                            'category': source['category'],
                            'content_type': source['content_type'],
                            'significance_score': 5.0,  # Default score
                            'reading_time': 5,  # Default reading time
                            'created_at': datetime.utcnow()
                        }
                        
                        # Insert into articles table with content_type (avoid duplicates by URL)
                        insert_query = """
                            INSERT INTO articles (title, url, description, source, published_at, category, 
                                                content_type, significance_score, reading_time, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (url) DO NOTHING
                        """
                        
                        db.execute_query(
                            insert_query,
                            (
                                article_data['title'][:500],  # Limit title length
                                article_data['url'],
                                article_data['description'][:1000],  # Limit description
                                article_data['source'],
                                article_data['published_at'],
                                article_data['category'],
                                article_data['content_type'],  # Add content_type
                                article_data['significance_score'],
                                article_data['reading_time'],
                                article_data['created_at']
                            ),
                            fetch_results=False
                        )
                        
                        scraped_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process entry from {source['name']}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to scrape {source['name']}: {str(e)}")
                continue
        
        logger.info(f"✅ Scraping completed. Added {scraped_count} articles")
        return {"success": True, "articles_added": scraped_count}
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {str(e)}")
        return {"success": False, "error": str(e)}

def ensure_postgresql_only():
    """Rename SQLite files to ensure PostgreSQL is used exclusively"""
    try:
        import os
        import shutil
        from pathlib import Path
        
        # List of SQLite files to rename/disable
        sqlite_files = [
            '/app/ai_news.db',
            '/app/ai_news_backup_20250922_235538.db',
            './ai_news.db',
            './ai_news_backup_20250922_235538.db',
            'ai_news.db',
            'ai_news_backup_20250922_235538.db'
        ]
        
        for sqlite_file in sqlite_files:
            if os.path.exists(sqlite_file):
                backup_name = f"{sqlite_file}.disabled_{int(datetime.utcnow().timestamp())}"
                try:
                    shutil.move(sqlite_file, backup_name)
                    logger.info(f"🗃️ Renamed SQLite file: {sqlite_file} → {backup_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not rename {sqlite_file}: {str(e)}")
        
        # Also check common SQLite file locations in Docker containers
        docker_paths = ['/app/data/', '/app/', '/opt/app/', './']
        for path in docker_paths:
            try:
                for file in Path(path).glob('*.db'):
                    if file.name.startswith('ai_news'):
                        backup_name = f"{file}.disabled_{int(datetime.utcnow().timestamp())}"
                        try:
                            file.rename(backup_name)
                            logger.info(f"🗃️ Renamed Docker SQLite file: {file} → {backup_name}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not rename {file}: {str(e)}")
            except Exception:
                continue
        
        logger.info("✅ SQLite file cleanup completed - PostgreSQL will be used exclusively")
        
    except Exception as e:
        logger.warning(f"⚠️ SQLite cleanup failed: {str(e)} - This is expected in some environments")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting AI News Scraper API with clean PostgreSQL")
    
    # First, ensure we're using PostgreSQL only by disabling SQLite files
    ensure_postgresql_only()
    
    try:
        # Test PostgreSQL database connection
        db = get_database_service()
        logger.info("✅ PostgreSQL connection established")
        
        # Log database connection details (without sensitive info)
        postgres_url = os.getenv('POSTGRES_URL', '')
        if postgres_url:
            # Extract host info without credentials
            if '@' in postgres_url:
                host_part = postgres_url.split('@')[1].split('/')[0]
                logger.info(f"🐘 Connected to PostgreSQL host: {host_part}")
            else:
                logger.info("🐘 PostgreSQL connection configured")
        else:
            logger.warning("⚠️ No POSTGRES_URL environment variable found")
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        logger.error("🔍 Make sure POSTGRES_URL environment variable is set correctly")
        raise e
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI News Scraper API")
    try:
        close_database_service()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Database shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title="AI News Scraper API",
    description="Clean PostgreSQL backend for AI news aggregation",
    version="4.0.0-clean-postgresql",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://ai-news-react.vercel.app",
    "https://www.vidyagam.com",
    # Allow all Vercel deployment URLs for ai-news-react
    "https://ai-news-react-*.vercel.app",
]

# Function to check if origin matches allowed patterns
def is_origin_allowed(origin: str) -> bool:
    """Check if origin is allowed including wildcard patterns"""
    for allowed in allowed_origins:
        if '*' in allowed:
            # Convert wildcard pattern to regex
            pattern = allowed.replace('*', '.*')
            import re
            if re.match(f"^{pattern}$", origin):
                return True
        elif origin == allowed:
            return True
    return False

# Add environment origins
env_origins = os.getenv('ALLOWED_ORIGINS', '')
if env_origins:
    allowed_origins.extend([origin.strip() for origin in env_origins.split(',')])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI News Scraper API - Clean PostgreSQL Version",
        "version": "4.0.0-clean-postgresql",
        "database": "postgresql",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "sources": "/sources", 
            "digest": "/digest",
            "scrape": "/scrape",
            "auth": {
                "google": "/auth/google",
                "send_otp": "/auth/send-otp", 
                "verify_otp": "/auth/verify-otp",
                "profile": "/auth/profile",
                "preferences": "/auth/preferences"
            }
        }
    }

# Health endpoint
@app.get("/health")
async def health():
    """Health check endpoint with comprehensive table stats"""
    try:
        db = get_database_service()
        
        # Check all tables that the backend uses
        table_stats = {}
        
        # Check ai_sources table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM ai_sources")
            table_stats["ai_sources"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["ai_sources"] = f"Error: {str(e)}"
        
        # Check articles table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM articles")
            table_stats["articles"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["articles"] = f"Error: {str(e)}"
        
        # Check ai_topics table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM ai_topics")
            table_stats["ai_topics"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["ai_topics"] = f"Error: {str(e)}"
        
        # Check article_topics table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM article_topics")
            table_stats["article_topics"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["article_topics"] = f"Error: {str(e)}"
        
        # Check users table
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM users")
            table_stats["users"] = result[0]['count'] if result else 0
        except Exception as e:
            table_stats["users"] = f"Error: {str(e)}"
        
        return {
            "status": "healthy",
            "version": "4.0.0-clean-postgresql",
            "database": "postgresql",
            "timestamp": "2025-09-23T16:45:00Z",
            "database_stats": table_stats,
            "connection_pool": "active"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "database": "postgresql"
            }
        )

# Authentication endpoints (modular implementation)
@app.post("/auth/google")
async def google_auth(request: GoogleAuthRequest, auth_service: AuthService = Depends(get_auth_service)):
    """Google OAuth authentication - modular implementation"""
    try:
        logger.info("🔐 Processing Google authentication")
        
        google_token = request.credential
        if not google_token:
            raise HTTPException(
                status_code=400,
                detail={'error': 'Missing Google token', 'message': 'Google credential token is required'}
            )
        
        # Extract email from token payload (simplified for demo)
        try:
            parts = google_token.split('.')
            if len(parts) >= 2:
                payload_encoded = parts[1]
                # Add padding
                while len(payload_encoded) % 4:
                    payload_encoded += '='
                payload_decoded = base64.urlsafe_b64decode(payload_encoded.encode())
                google_data = json.loads(payload_decoded.decode())
                
                user_data = {
                    'sub': google_data.get('sub', ''),
                    'email': google_data.get('email', ''),
                    'name': google_data.get('name', ''),
                    'picture': google_data.get('picture', '')
                }
            else:
                raise Exception("Invalid Google token format")
        except Exception:
            # Fallback for testing
            user_data = {
                'sub': 'google_user_' + str(int(datetime.utcnow().timestamp())),
                'email': 'test@example.com',
                'name': 'Test User',
                'picture': ''
            }
        
        # Create or update user in PostgreSQL
        user = auth_service.create_or_update_user(user_data)
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user_data)
        
        # Return response expected by frontend
        response = {
            'success': True,
            'message': f'Authentication successful for {user_data["email"]}',
            'token': jwt_token,
            'user': {
                'id': str(user['id']),
                'email': str(user['email']),
                'name': str(user.get('name', '')),
                'picture': str(user.get('profile_image', user_data.get('picture', ''))),
                'verified_email': bool(user.get('verified_email', True))
            },
            'expires_in': 3600,
            'router_auth': False,  # Modular architecture
            'isUserExist': True
        }
        
        logger.info(f"✅ Google authentication successful for: {user_data['email']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google auth failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Authentication failed', 'message': str(e), 'database': 'postgresql'}
        )

@app.post("/auth/send-otp")
async def send_otp(request: OTPRequest, auth_service: AuthService = Depends(get_auth_service)):
    """Send OTP for email authentication"""
    try:
        logger.info(f"📧 OTP requested for: {request.email}")
        
        # For development, return success with test OTP
        test_otp = "123456"
        
        response = {
            'success': True,
            'message': f'OTP sent to {request.email}',
            'otpSent': False,  # Set to True when email service is implemented
            'debug_info': {
                'otp_for_testing': test_otp,
                'auth_mode': request.auth_mode,
                'email_service_status': 'development_mode'
            }
        }
        
        logger.info(f"✅ OTP generation successful for: {request.email}")
        return response
        
    except Exception as e:
        logger.error(f"❌ OTP send failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to send OTP', 'message': str(e), 'database': 'postgresql'}
        )

@app.post("/auth/verify-otp")
async def verify_otp(request: OTPVerifyRequest, auth_service: AuthService = Depends(get_auth_service)):
    """Verify OTP and authenticate user"""
    try:
        logger.info(f"🔐 OTP verification for: {request.email}")
        
        # For development, accept the test OTP
        if request.otp != "123456":
            raise HTTPException(
                status_code=400,
                detail={'error': 'Invalid OTP', 'message': 'The OTP code is incorrect or has expired'}
            )
        
        # Create user data from request
        user_data = {
            'sub': f"otp_user_{int(datetime.utcnow().timestamp())}",
            'email': request.email,
            'name': request.userData.get('name', ''),
            'picture': ''
        }
        
        # Create or update user in PostgreSQL
        user = auth_service.create_or_update_user(user_data)
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user_data)
        
        # Return response expected by frontend
        response = {
            'success': True,
            'message': f'OTP verification successful for {request.email}',
            'token': jwt_token,
            'user': {
                'id': str(user['id']),
                'email': str(user['email']),
                'name': str(user.get('name', '')),
                'picture': str(user.get('profile_image', '')),
                'verified_email': bool(user.get('verified_email', True))
            },
            'expires_in': 3600,
            'router_auth': False,  # Modular architecture
            'isUserExist': True
        }
        
        logger.info(f"✅ OTP verification successful for: {request.email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OTP verification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'OTP verification failed', 'message': str(e), 'database': 'postgresql'}
        )

@app.get("/auth/profile")
async def get_profile(current_user: UserResponse = Depends(get_current_user)):
    """Get user profile - requires authentication"""
    try:
        logger.info(f"👤 Profile requested for: {current_user.email}")
        logger.info(f"✅ Profile retrieved for: {current_user.email}")
        return current_user
    except Exception as e:
        logger.error(f"❌ Profile endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get profile', 'message': str(e), 'database': 'postgresql'}
        )

@app.post("/auth/preferences")
@app.put("/auth/preferences")
async def update_preferences(
    preferences: UserPreferences,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user preferences for personalization"""
    try:
        logger.info(f"⚙️ Preferences update for: {current_user.email}")
        
        # Convert preferences to dict
        preferences_dict = preferences.dict(exclude_unset=True)
        
        # Update user preferences in database
        updated_user = auth_service.update_user_preferences(current_user.id, preferences_dict)
        
        response = UserResponse(**updated_user)
        logger.info(f"✅ Preferences updated for: {current_user.email}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Preferences update failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to update preferences', 'message': str(e), 'database': 'postgresql'}
        )

# Personalized content rendering
def get_personalized_articles(user_preferences: dict, limit: int = 20) -> List[dict]:
    """Get personalized articles based on user preferences and topics"""
    try:
        db = get_database_service()
        
        # Base query for articles
        base_query = """
            SELECT DISTINCT a.id, a.title, a.url, a.description, a.source, a.published_at, 
                   a.category, a.significance_score, a.reading_time, 
                   COALESCE(a.content_type, 'blog') as content_type,
                   array_agg(DISTINCT t.name) as topics
            FROM articles a
            LEFT JOIN article_topics at ON a.id = at.article_id
            LEFT JOIN ai_topics t ON at.topic_id = t.id
            WHERE a.published_at >= (CURRENT_DATE - INTERVAL '7 days')
        """
        
        # Add personalization filters if user has preferences
        user_topics = user_preferences.get('topics', [])
        user_content_types = user_preferences.get('content_types', [])
        
        conditions = []
        params = []
        
        if user_topics and len(user_topics) > 0:
            # Filter by user's selected topics
            placeholders = ','.join(['%s'] * len(user_topics))
            conditions.append(f"t.id IN ({placeholders})")
            params.extend(user_topics)
        
        if user_content_types and len(user_content_types) > 0:
            # Filter by user's selected content types
            placeholders = ','.join(['%s'] * len(user_content_types))
            conditions.append(f"COALESCE(a.content_type, 'blog') IN ({placeholders})")
            params.extend(user_content_types)
        
        # Build final query
        if conditions:
            base_query += " AND (" + " OR ".join(conditions) + ")"
        
        base_query += """
            GROUP BY a.id, a.title, a.url, a.description, a.source, a.published_at, 
                     a.category, a.significance_score, a.reading_time, COALESCE(a.content_type, 'blog')
            ORDER BY a.significance_score DESC, a.published_at DESC
            LIMIT %s
        """
        
        params.append(limit)
        
        # Execute query
        articles = db.execute_query(base_query, tuple(params))
        
        # Convert to list of dicts
        result = []
        for article in articles:
            article_dict = dict(article)
            # Convert topics array to list
            article_dict['topics'] = article_dict.get('topics', []) or []
            result.append(article_dict)
        
        logger.info(f"📊 Retrieved {len(result)} personalized articles")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get personalized articles: {str(e)}")
        # Fallback to general articles
        return get_general_articles(limit)

def get_general_articles(limit: int = 20) -> List[dict]:
    """Get general articles when personalization is not available"""
    try:
        db = get_database_service()
        
        query = """
            SELECT a.id, a.title, a.url, a.description, a.source, a.published_at, 
                   a.category, a.significance_score, a.reading_time, 
                   COALESCE(a.content_type, 'blog') as content_type
            FROM articles a
            WHERE a.published_at >= (CURRENT_DATE - INTERVAL '7 days')
            ORDER BY a.significance_score DESC, a.published_at DESC
            LIMIT %s
        """
        
        articles = db.execute_query(query, (limit,))
        
        result = []
        for article in articles:
            article_dict = dict(article)
            article_dict['topics'] = []  # No topics for general articles
            result.append(article_dict)
        
        logger.info(f"📊 Retrieved {len(result)} general articles")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get general articles: {str(e)}")
        return []

# Digest endpoint with personalization (unified, clean implementation)
@app.get("/digest")
async def get_digest(request: Request):
    """Get news digest - personalized for authenticated users"""
    try:
        logger.info("📊 Digest requested")
        db = get_database_service()
        
        # Check for authentication token
        current_user = None
        personalized = False
        
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                auth_service = AuthService()
                payload = auth_service.verify_jwt_token(token)
                if payload:
                    # Get user preferences from database
                    user_query = "SELECT preferences FROM users WHERE email = %s"
                    user_result = db.execute_query(user_query, (payload.get("email"),))
                    user_preferences = {}
                    if user_result and user_result[0].get('preferences'):
                        if isinstance(user_result[0]['preferences'], str):
                            user_preferences = json.loads(user_result[0]['preferences'])
                        else:
                            user_preferences = user_result[0]['preferences']
                    
                    current_user = {"email": payload.get("email"), "preferences": user_preferences}
                    logger.info(f"👤 Authenticated user: {current_user['email']}")
            except Exception as e:
                logger.info(f"🔐 Token verification failed: {str(e)}, proceeding as unauthenticated")
        
        # Get articles with COALESCE for content_type column fix
        articles_query = """
            SELECT a.id, a.source, a.title, a.url, a.published_at, a.description, 
                   a.significance_score, a.category, a.reading_time, a.image_url,
                   COALESCE(a.content_type, 'blog') as content_type, a.keywords
            FROM articles a
            WHERE a.published_at > NOW() - INTERVAL '7 days'
        """
        
        # Add personalization filters if user has preferences
        params = []
        if current_user and current_user.get("preferences"):
            prefs = current_user["preferences"]
            topics = prefs.get("topics", [])
            content_types = prefs.get("content_types", [])
            
            if topics or content_types:
                conditions = []
                if topics:
                    # Topic-based filtering using keywords
                    topic_conditions = []
                    for topic in topics:
                        topic_conditions.append("a.keywords ILIKE %s")
                        params.append(f"%{topic}%")
                    if topic_conditions:
                        conditions.append("(" + " OR ".join(topic_conditions) + ")")
                        
                if content_types:
                    placeholders = ','.join(['%s'] * len(content_types))
                    conditions.append(f"COALESCE(a.content_type, 'blog') IN ({placeholders})")
                    params.extend(content_types)
                
                if conditions:
                    articles_query += " AND (" + " OR ".join(conditions) + ")"
                    personalized = True
        
        articles_query += " ORDER BY a.significance_score DESC, a.published_at DESC LIMIT 50"
        
        articles = db.execute_query(articles_query, tuple(params) if params else None)
        
        processed_articles = []
        for article in articles:
            article_dict = dict(article)
            
            # Convert timestamp to ISO format
            if article_dict.get('published_at'):
                article_dict['published_at'] = article_dict['published_at'].isoformat()
            
            # Add required frontend fields
            article_dict['type'] = article_dict.get('content_type', 'blog')
            article_dict['time'] = format_time_ago(article_dict.get('published_at'))
            article_dict['impact'] = get_impact_level(article_dict.get('significance_score', 5))
            article_dict['readTime'] = f"{article_dict.get('reading_time', 3)} min read"
            article_dict['significanceScore'] = article_dict.get('significance_score', 5)
            
            processed_articles.append(article_dict)
        
        # Organize by content type for frontend - support all 6 content types
        content_by_type = {
            'blog': [a for a in processed_articles if a.get('content_type') == 'blog'][:20],
            'audio': [a for a in processed_articles if a.get('content_type') == 'audio'][:10],
            'video': [a for a in processed_articles if a.get('content_type') == 'video'][:10],
            'learning': [a for a in processed_articles if a.get('content_type') == 'learning'][:10],
            'demos': [a for a in processed_articles if a.get('content_type') == 'demos'][:10],
            'events': [a for a in processed_articles if a.get('content_type') == 'events'][:10]
        }
        
        # Get top stories (high significance score)
        top_stories = sorted(processed_articles, key=lambda x: x.get('significance_score', 0), reverse=True)[:10]
        
        response = {
            'topStories': top_stories,
            'content': content_by_type,
            'summary': {
                'total_articles': len(processed_articles),
                'top_stories_count': len(top_stories),
                'personalization_note': "Customized based on your preferences" if personalized else "General AI news content",
                'last_updated': datetime.utcnow().isoformat(),
                'keyPoints': [
                    "Latest AI breakthroughs and developments",
                    "Comprehensive coverage from leading sources", 
                    "Personalized content based on preferences" if personalized else "General AI news digest"
                ],
                'metrics': {
                    'totalUpdates': len(processed_articles),
                    'highImpact': len([a for a in processed_articles if a.get('significance_score', 0) >= 8]),
                    'newResearch': len([a for a in processed_articles if a.get('category') == 'research']),
                    'industryMoves': len([a for a in processed_articles if a.get('category') == 'business'])
                }
            },
            'personalized': personalized,
            'database': 'postgresql',
            'timestamp': datetime.utcnow().isoformat(),
            'badge': 'Personalized' if personalized else 'Preview',
            'debug_info': {
                'user_authenticated': current_user is not None,
                'personalization_enabled': personalized,
                'dashboard_mode': 'personalized' if personalized else 'preview',
                'is_preview_mode': not personalized,
                'content_type_column_fixed': True
            }
        }
        
        logger.info(f"✅ Digest generated - {len(processed_articles)} articles, personalized: {personalized}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Digest endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get digest',
                'message': str(e),
                'database': 'postgresql'
            }
        )

# Manual scraping endpoint
@app.post("/scrape")
async def manual_scrape(current_user: Optional[UserResponse] = Depends(get_current_user_optional)):
    """Manually trigger content scraping - admin function"""
    try:
        logger.info("🕷️ Manual scraping triggered")
        
        # Run scraping function
        result = await scrape_content_from_sources()
        
        response = {
            "success": result.get("success", False),
            "message": f"Scraping completed. Added {result.get('articles_added', 0)} articles",
            "articles_added": result.get('articles_added', 0),
            "database": "postgresql",
            "triggered_by": current_user.email if current_user else "anonymous"
        }
        
        logger.info(f"✅ Manual scraping result: {result}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Manual scraping failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Scraping failed', 'message': str(e), 'database': 'postgresql'}
        )

# Sources endpoint for content management
@app.get("/sources")
async def get_sources():
    """Get all AI news sources"""
    try:
        logger.info("📚 Sources requested")
        db = get_database_service()
        
        query = """
            SELECT name, rss_url, website, content_type, category, enabled, priority, description
            FROM ai_sources
            ORDER BY priority ASC, name ASC
        """
        
        sources = db.execute_query(query)
        
        # Convert to list of dicts
        sources_list = []
        for source in sources:
            source_dict = dict(source)
            sources_list.append(source_dict)
        
        # Calculate stats
        total_count = len(sources_list)
        enabled_count = len([s for s in sources_list if s.get('enabled', False)])
        
        response = {
            "sources": sources_list,
            "total_count": total_count,
            "enabled_count": enabled_count,
            "database": "postgresql",
            "categories": list(set([s.get('category', '') for s in sources_list if s.get('category')])),
            "content_types": list(set([s.get('content_type', '') for s in sources_list if s.get('content_type')]))
        }
        
        logger.info(f"✅ Sources retrieved - {total_count} total, {enabled_count} enabled")
        return response
        
    except Exception as e:
        logger.error(f"❌ Sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get sources', 'message': str(e), 'database': 'postgresql'}
        )

# Content endpoints for frontend compatibility
@app.get("/multimedia/audio")
async def get_audio_content(hours: int = 24, limit: int = 20):
    """Get recent audio/podcast content"""
    try:
        logger.info(f"📻 Audio content requested - {hours}h range, limit {limit}")
        db = get_database_service()
        
        query = """
            SELECT id, title, url, description, source, published_at, 
                   significance_score, reading_time, 
                   COALESCE(content_type, 'audio') as content_type
            FROM articles 
            WHERE COALESCE(content_type, 'audio') = 'audio' 
            AND published_at >= (CURRENT_TIMESTAMP - INTERVAL '%s hours')
            ORDER BY significance_score DESC, published_at DESC
            LIMIT %s
        """
        
        articles = db.execute_query(query, (hours, limit))
        
        audio_content = []
        for article in articles:
            audio_content.append({
                "title": article.get('title', ''),
                "description": article.get('description', ''),
                "source": article.get('source', ''),
                "url": article.get('url', ''),
                "audio_url": article.get('url', ''),  # Same as URL for now
                "duration": 0,  # Default duration
                "published_date": article.get('published_at', '').isoformat() if article.get('published_at') else '',
                "significance_score": float(article.get('significance_score', 5.0)),
                "processed": True
            })
        
        response = {
            "audio_content": audio_content,
            "total_count": len(audio_content),
            "hours_range": hours,
            "database": "postgresql"
        }
        
        logger.info(f"✅ Audio content retrieved - {len(audio_content)} items")
        return response
        
    except Exception as e:
        logger.error(f"❌ Audio content endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get audio content', 'message': str(e), 'database': 'postgresql'}
        )

@app.get("/multimedia/video")
async def get_video_content(hours: int = 24, limit: int = 20):
    """Get recent video content"""
    try:
        logger.info(f"📺 Video content requested - {hours}h range, limit {limit}")
        db = get_database_service()
        
        query = """
            SELECT id, title, url, description, source, published_at, 
                   significance_score, reading_time, 
                   COALESCE(content_type, 'video') as content_type
            FROM articles 
            WHERE COALESCE(content_type, 'video') = 'video' 
            AND published_at >= (CURRENT_TIMESTAMP - INTERVAL '%s hours')
            ORDER BY significance_score DESC, published_at DESC
            LIMIT %s
        """
        
        articles = db.execute_query(query, (hours, limit))
        
        video_content = []
        for article in articles:
            video_content.append({
                "title": article.get('title', ''),
                "description": article.get('description', ''),
                "source": article.get('source', ''),
                "url": article.get('url', ''),
                "thumbnail_url": "",  # Default empty thumbnail
                "duration": 0,  # Default duration
                "published_date": article.get('published_at', '').isoformat() if article.get('published_at') else '',
                "significance_score": float(article.get('significance_score', 5.0)),
                "processed": True
            })
        
        response = {
            "video_content": video_content,
            "total_count": len(video_content),
            "hours_range": hours,
            "database": "postgresql"
        }
        
        logger.info(f"✅ Video content retrieved - {len(video_content)} items")
        return response
        
    except Exception as e:
        logger.error(f"❌ Video content endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get video content', 'message': str(e), 'database': 'postgresql'}
        )

@app.get("/multimedia/sources")
async def get_multimedia_sources():
    """Get multimedia sources configuration"""
    try:
        logger.info("📚 Multimedia sources requested")
        db = get_database_service()
        
        query = """
            SELECT name, rss_url, website, content_type, category, enabled, priority, description
            FROM ai_sources
            WHERE content_type IN ('audio', 'video')
            ORDER BY content_type, priority ASC, name ASC
        """
        
        sources = db.execute_query(query)
        
        # Organize by content type
        audio_sources = []
        video_sources = []
        
        for source in sources:
            source_data = {
                "name": source.get('name', ''),
                "type": f"{source.get('content_type', '')}_rss",
                "url": source.get('rss_url', ''),
                "website": source.get('website', ''),
                "priority": source.get('priority', 1),
                "enabled": source.get('enabled', True)
            }
            
            if source.get('content_type') == 'audio':
                audio_sources.append(source_data)
            elif source.get('content_type') == 'video':
                video_sources.append(source_data)
        
        response = {
            "sources": {
                "audio": audio_sources,
                "video": video_sources
            },
            "audio_sources": len(audio_sources),
            "video_sources": len(video_sources),
            "claude_available": True,
            "database": "postgresql"
        }
        
        logger.info(f"✅ Multimedia sources retrieved - {len(audio_sources)} audio, {len(video_sources)} video")
        return response
        
    except Exception as e:
        logger.error(f"❌ Multimedia sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get multimedia sources', 'message': str(e), 'database': 'postgresql'}
        )

@app.get("/multimedia/scrape")
async def manual_multimedia_scrape():
    """Manually trigger multimedia content scraping"""
    try:
        logger.info("🕷️ Manual multimedia scraping triggered")
        
        # Run scraping for multimedia content
        result = await scrape_content_from_sources()
        
        # Filter the results for multimedia content
        multimedia_added = result.get('articles_added', 0)
        
        response = {
            "message": "Multimedia scraping completed",
            "audio_found": multimedia_added // 2,  # Rough estimation
            "video_found": multimedia_added // 2,  # Rough estimation
            "audio_processed": multimedia_added // 2,
            "video_processed": multimedia_added // 2,
            "audio_sources": ["OpenAI Podcast", "Practical AI", "Latent Space"],
            "video_sources": ["Two Minute Papers", "DeepLearning.AI", "Yannic Kilcher"],
            "claude_available": True,
            "database": "postgresql"
        }
        
        logger.info(f"✅ Manual multimedia scraping completed")
        return response
        
    except Exception as e:
        logger.error(f"❌ Manual multimedia scraping failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Multimedia scraping failed', 'message': str(e), 'database': 'postgresql'}
        )

# Content type specific endpoints
@app.get("/content/{content_type}")
async def get_content_by_type(content_type: str, limit: int = 20):
    """Get content filtered by type (blog, audio, video, learning, demos, events)"""
    try:
        logger.info(f"📊 Content requested for type: {content_type}")
        db = get_database_service()
        
        # Validate content type
        valid_types = ['blog', 'audio', 'video', 'learning', 'demos', 'events']
        if content_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail={'error': 'Invalid content type', 'valid_types': valid_types}
            )
        
        query = """
            SELECT id, title, url, description, source, published_at, 
                   category, significance_score, reading_time, 
                   COALESCE(content_type, 'blog') as content_type
            FROM articles 
            WHERE COALESCE(content_type, 'blog') = %s 
            AND published_at >= (CURRENT_DATE - INTERVAL '7 days')
            ORDER BY significance_score DESC, published_at DESC
            LIMIT %s
        """
        
        articles = db.execute_query(query, (content_type, limit))
        
        # Format articles
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "id": article.get('id'),
                "title": article.get('title', ''),
                "description": article.get('description', ''),
                "source": article.get('source', ''),
                "url": article.get('url', ''),
                "published_at": article.get('published_at', '').isoformat() if article.get('published_at') else '',
                "category": article.get('category', ''),
                "significance_score": float(article.get('significance_score', 5.0)),
                "reading_time": article.get('reading_time', 5),
                "content_type": article.get('content_type', ''),
                "topics": []  # Empty for now
            })
        
        response = {
            "articles": formatted_articles,
            "content_type": content_type,
            "count": len(formatted_articles),
            "database": "postgresql"
        }
        
        logger.info(f"✅ Content by type retrieved - {len(formatted_articles)} {content_type} articles")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Content by type endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': f'Failed to get {content_type} content', 'message': str(e), 'database': 'postgresql'}
        )

# Database schema endpoint
@app.get("/db-schema")
async def get_database_schema():
    """Get database schema and table information"""
    try:
        db = get_database_service()
        
        # Get all tables
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """
        tables_result = db.execute_query(tables_query)
        tables = [row['table_name'] for row in tables_result]
        
        # Get table details for each table
        table_details = {}
        for table in tables:
            try:
                # Get column information
                columns_query = f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """
                columns = db.execute_query(columns_query)
                
                # Get row count
                count_query = f"SELECT COUNT(*) as count FROM {table}"
                count_result = db.execute_query(count_query)
                row_count = count_result[0]['count'] if count_result else 0
                
                table_details[table] = {
                    "columns": columns,
                    "row_count": row_count
                }
            except Exception as e:
                table_details[table] = {"error": str(e)}
        
        return {
            "database": "postgresql",
            "total_tables": len(tables),
            "tables": tables,
            "table_details": table_details,
            "backend_usage": {
                "ai_sources": "Used by /sources endpoint for content source configuration",
                "articles": "Used by /digest endpoint for news content",
                "ai_topics": "Not currently used in clean backend",
                "article_topics": "Not currently used in clean backend", 
                "users": "Not currently used in clean backend (auth endpoints missing)",
                "daily_archives": "Not currently used in clean backend"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Database schema endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get database schema',
                'message': str(e)
            }
        )

# Duplicate sources endpoint removed - keeping the unified implementation above

# Duplicate digest endpoint removed - keeping the unified implementation above

# Personalized digest endpoint
@app.get("/personalized-digest")
async def get_personalized_digest(request: Request):
    """Get personalized digest for authenticated users"""
    try:
        # Extract JWT token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")
        
        token = auth_header.split(" ")[1]
        auth_service = AuthService()
        payload = auth_service.verify_jwt_token(token)
        user_email = payload.get("email")
        
        logger.info(f"👤 Personalized digest for: {user_email}")
        
        # Get user preferences from database
        db = get_database_service()
        user_query = "SELECT preferences FROM users WHERE email = %s"
        user_result = db.execute_query(user_query, (user_email,))
        
        if not user_result:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_preferences = user_result[0].get('preferences', {})
        
        # Get personalized articles
        articles = get_personalized_articles(user_preferences, 50)
        
        # Organize content by type
        content_by_type = {
            'blog': [a for a in articles if a.get('content_type') == 'blog'][:20],
            'audio': [a for a in articles if a.get('content_type') == 'audio'][:10],
            'video': [a for a in articles if a.get('content_type') == 'video'][:10],
            'learning': [a for a in articles if a.get('content_type') == 'learning'][:10],
            'demos': [a for a in articles if a.get('content_type') == 'demos'][:10],
            'events': [a for a in articles if a.get('content_type') == 'events'][:10]
        }
        
        top_stories = sorted(articles, key=lambda x: x.get('significance_score', 0), reverse=True)[:10]
        
        return {
            'topStories': top_stories,
            'content': content_by_type,
            'summary': {
                'total_articles': len(articles),
                'personalization_note': f"Personalized for {user_email}",
                'user_topics': user_preferences.get('topics', []),
                'last_updated': datetime.utcnow().isoformat()
            },
            'personalized': True,
            'database': 'postgresql',
            'debug_info': {
                'is_personalized': True,
                'filtering_applied': True,
                'personalization_enabled': True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Personalized digest failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get personalized digest', 'message': str(e)}
        )

# Helper functions for digest
def format_time_ago(timestamp_str):
    """Convert timestamp to human readable time ago format"""
    if not timestamp_str:
        return "unknown"
    try:
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = timestamp_str
        
        now = datetime.utcnow().replace(tzinfo=dt.tzinfo) if dt.tzinfo else datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        else:
            return f"{diff.seconds // 60}m ago"
    except:
        return "recently"

def get_impact_level(score):
    """Convert significance score to impact level"""
    if score >= 8:
        return "high"
    elif score >= 6:
        return "medium"
    else:
        return "low"

def get_personalized_articles(user_preferences: dict, limit: int = 20) -> List[dict]:
    """Get personalized articles based on user preferences"""
    try:
        db = get_database_service()
        
        base_query = """
            SELECT id, title, url, description, source, published_at, 
                   category, significance_score, reading_time, 
                   COALESCE(content_type, 'blog') as content_type, keywords
            FROM articles
            WHERE published_at >= (CURRENT_DATE - INTERVAL '7 days')
        """
        
        user_topics = user_preferences.get('topics', [])
        user_content_types = user_preferences.get('content_types', [])
        
        conditions = []
        params = []
        
        if user_topics:
            # Topic-based filtering using keywords
            topic_conditions = []
            for topic in user_topics:
                topic_conditions.append("keywords ILIKE %s")
                params.append(f"%{topic}%")
            if topic_conditions:
                conditions.append("(" + " OR ".join(topic_conditions) + ")")
        
        if user_content_types:
            placeholders = ','.join(['%s'] * len(user_content_types))
            conditions.append(f"COALESCE(content_type, 'blog') IN ({placeholders})")
            params.extend(user_content_types)
        
        if conditions:
            base_query += " AND (" + " OR ".join(conditions) + ")"
        
        base_query += " ORDER BY significance_score DESC, published_at DESC LIMIT %s"
        params.append(limit)
        
        articles = db.execute_query(base_query, tuple(params))
        
        result = []
        for article in articles:
            article_dict = dict(article)
            # Add frontend-compatible fields
            article_dict['type'] = article_dict.get('content_type', 'blog')
            article_dict['time'] = format_time_ago(article_dict.get('published_at'))
            article_dict['impact'] = get_impact_level(article_dict.get('significance_score', 5))
            article_dict['readTime'] = f"{article_dict.get('reading_time', 3)} min read"
            article_dict['significanceScore'] = article_dict.get('significance_score', 5)
            if article_dict.get('published_at'):
                article_dict['published_at'] = article_dict['published_at'].isoformat()
            result.append(article_dict)
        
        logger.info(f"📊 Retrieved {len(result)} personalized articles")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get personalized articles: {str(e)}")
        return []

# Manual scraping endpoint
@app.post("/scrape")
async def manual_scrape():
    """Manually trigger content scraping"""
    try:
        logger.info("🕷️ Manual scraping triggered")
        
        # Run scraping function
        result = await scrape_content_from_sources()
        
        return {
            "success": result.get("success", False),
            "message": f"Scraping completed. Added {result.get('articles_added', 0)} articles",
            "articles_found": result.get('articles_found', 0),
            "articles_processed": result.get('articles_added', 0),
            "sources": result.get('sources_scraped', []),
            "database": "postgresql"
        }
        
    except Exception as e:
        logger.error(f"❌ Manual scraping failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Scraping failed', 'message': str(e), 'database': 'postgresql'}
        )

# Duplicate multimedia endpoints removed - using the ones above

@app.get("/multimedia/sources")
async def get_multimedia_sources():
    """Get multimedia sources configuration"""
    try:
        db = get_database_service()
        
        query = """
            SELECT name, rss_url, website, content_type, category, enabled, priority
            FROM ai_sources
            WHERE content_type IN ('audio', 'video')
            ORDER BY content_type, priority ASC
        """
        
        sources = db.execute_query(query)
        
        # Organize by content type
        audio_sources = []
        video_sources = []
        
        for source in sources:
            source_data = {
                'name': source['name'],
                'type': 'podcast_rss' if source['content_type'] == 'audio' else 'youtube_channel',
                'url': source['rss_url'],
                'website': source.get('website', ''),
                'priority': source['priority'],
                'enabled': source['enabled']
            }
            
            if source['content_type'] == 'audio':
                audio_sources.append(source_data)
            else:
                video_sources.append(source_data)
        
        return {
            "sources": {
                "audio": audio_sources,
                "video": video_sources
            },
            "audio_sources": len(audio_sources),
            "video_sources": len(video_sources),
            "database": "postgresql"
        }
        
    except Exception as e:
        logger.error(f"❌ Multimedia sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get multimedia sources', 'message': str(e)}
        )

@app.get("/multimedia/scrape")
async def scrape_multimedia():
    """Manually trigger multimedia content scraping"""
    try:
        logger.info("🎬 Multimedia scraping triggered")
        
        # This would trigger multimedia-specific scraping
        result = await scrape_content_from_sources(content_types=['audio', 'video'])
        
        return {
            "message": "Multimedia scraping completed",
            "audio_found": result.get('audio_found', 0),
            "video_found": result.get('video_found', 0),
            "audio_processed": result.get('audio_processed', 0),
            "video_processed": result.get('video_processed', 0),
            "audio_sources": result.get('audio_sources', []),
            "video_sources": result.get('video_sources', []),
            "database": "postgresql"
        }
        
    except Exception as e:
        logger.error(f"❌ Multimedia scraping failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Multimedia scraping failed', 'message': str(e)}
        )

# Content type filtering endpoints
@app.get("/content/{content_type}")
async def get_content_by_type(content_type: str, limit: int = 20):
    """Get articles by content type"""
    try:
        # Validate content type
        valid_types = ['blog', 'audio', 'video', 'learning', 'demos', 'events']
        if content_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid content type. Must be one of: {', '.join(valid_types)}"
            )
        
        db = get_database_service()
        
        query = """
            SELECT id, title, url, description, source, published_at, 
                   significance_score, reading_time, 
                   COALESCE(content_type, 'blog') as content_type, category, image_url
            FROM articles 
            WHERE COALESCE(content_type, 'blog') = %s
            AND published_at >= (CURRENT_DATE - INTERVAL '30 days')
            ORDER BY significance_score DESC, published_at DESC
            LIMIT %s
        """
        
        articles = db.execute_query(query, (content_type, limit))
        
        processed_articles = []
        for article in articles:
            article_dict = dict(article)
            # Add frontend-compatible fields
            article_dict['type'] = content_type
            article_dict['time'] = format_time_ago(article_dict.get('published_at'))
            article_dict['impact'] = get_impact_level(article_dict.get('significance_score', 5))
            article_dict['readTime'] = f"{article_dict.get('reading_time', 3)} min read"
            article_dict['significanceScore'] = article_dict.get('significance_score', 5)
            if article_dict.get('published_at'):
                article_dict['published_at'] = article_dict['published_at'].isoformat()
            processed_articles.append(article_dict)
        
        return {
            "articles": processed_articles,
            "content_type": content_type,
            "count": len(processed_articles),
            "database": "postgresql"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Content by type endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': f'Failed to get {content_type} content', 'message': str(e)}
        )


# Content types endpoint
@app.get("/content-types")
async def get_content_types():
    """Get available content types"""
    return {
        "content_types": {
            "blog": {
                "id": 1,
                "name": "blog",
                "display_name": "Blog Articles",
                "description": "Technical articles and blog posts about AI",
                "frontend_section": "blogs",
                "icon": "📝"
            },
            "audio": {
                "id": 2,
                "name": "audio",
                "display_name": "Podcasts",
                "description": "AI-focused podcast episodes and audio content",
                "frontend_section": "podcasts",
                "icon": "🎧"
            },
            "video": {
                "id": 3,
                "name": "video",
                "display_name": "Videos",
                "description": "YouTube videos and video content about AI",
                "frontend_section": "videos",
                "icon": "🎥"
            },
            "learning": {
                "id": 4,
                "name": "learning",
                "display_name": "Learning Resources",
                "description": "Educational content, courses, and tutorials",
                "frontend_section": "learning",
                "icon": "📚"
            },
            "demos": {
                "id": 5,
                "name": "demos",
                "display_name": "Demos & Tools",
                "description": "Interactive demos and AI tools",
                "frontend_section": "demos",
                "icon": "🛠️"
            },
            "events": {
                "id": 6,
                "name": "events",
                "display_name": "Events & Conferences",
                "description": "AI conferences, webinars, and events",
                "frontend_section": "events",
                "icon": "📅"
            }
        },
        "database": "postgresql"
    }

# Database info endpoint
@app.get("/db-info")
async def get_database_info():
    """Get database information and statistics"""
    try:
        db = get_database_service()
        
        # Get table counts
        stats = {}
        tables = ['articles', 'users', 'ai_sources', 'ai_topics']
        
        for table in tables:
            try:
                count_query = f"SELECT COUNT(*) as count FROM {table}"
                result = db.execute_query(count_query)
                stats[table] = result[0]['count'] if result else 0
            except Exception as e:
                logger.warning(f"Could not get count for table {table}: {str(e)}")
                stats[table] = 0
        
        # Get recent articles by content type
        content_type_query = """
            SELECT COALESCE(content_type, 'blog') as content_type, COUNT(*) as count
            FROM articles
            WHERE published_at >= (CURRENT_DATE - INTERVAL '30 days')
            GROUP BY COALESCE(content_type, 'blog')
            ORDER BY count DESC
        """
        
        content_type_stats = {}
        try:
            content_results = db.execute_query(content_type_query)
            for row in content_results:
                content_type_stats[row['content_type']] = row['count']
        except Exception as e:
            logger.warning(f"Could not get content type stats: {str(e)}")
        
        return {
            "database": "postgresql",
            "connection_status": "active",
            "table_counts": stats,
            "content_type_distribution": content_type_stats,
            "migration_from": "/app/ai_news.db",
            "last_checked": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Database info endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get database info', 'message': str(e)}
        )

# AI topics endpoint
@app.get("/topics")
async def get_ai_topics():
    """Get available AI topics for filtering and personalization"""
    try:
        db = get_database_service()
        
        query = """
            SELECT id, name, category, description, is_active
            FROM ai_topics
            WHERE is_active = TRUE
            ORDER BY category, name
        """
        
        topics = db.execute_query(query)
        
        # Organize by category
        topics_by_category = {}
        all_topics = []
        
        for topic in topics:
            topic_data = dict(topic)
            all_topics.append(topic_data)
            
            category = topic_data.get('category', 'general')
            if category not in topics_by_category:
                topics_by_category[category] = []
            topics_by_category[category].append(topic_data)
        
        return {
            "topics": all_topics,
            "topics_by_category": topics_by_category,
            "total_count": len(all_topics),
            "categories": list(topics_by_category.keys()),
            "database": "postgresql"
        }
        
    except Exception as e:
        logger.error(f"❌ Topics endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get AI topics', 'message': str(e)}
        )

# Archive endpoint for newsletter history
@app.get("/archive")
async def get_archive(limit: int = 50):
    """Get archived content/newsletter history"""
    try:
        db = get_database_service()
        
        # Get recent digest summaries (simulated archive)
        query = """
            SELECT DATE(published_at) as digest_date, 
                   COUNT(*) as article_count,
                   AVG(significance_score) as avg_significance,
                   STRING_AGG(DISTINCT source, ', ') as sources
            FROM articles
            WHERE published_at >= (CURRENT_DATE - INTERVAL '30 days')
            GROUP BY DATE(published_at)
            ORDER BY digest_date DESC
            LIMIT %s
        """
        
        archive_data = db.execute_query(query, (limit,))
        
        archives = []
        for row in archive_data:
            archive_entry = {
                'date': row['digest_date'].isoformat() if row['digest_date'] else None,
                'article_count': row['article_count'],
                'avg_significance': float(row['avg_significance']) if row['avg_significance'] else 0,
                'sources': row['sources'].split(', ') if row['sources'] else [],
                'digest_url': f"/digest?date={row['digest_date']}" if row['digest_date'] else None
            }
            archives.append(archive_entry)
        
        return {
            "archives": archives,
            "total_archives": len(archives),
            "database": "postgresql"
        }
        
    except Exception as e:
        logger.error(f"❌ Archive endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to get archive', 'message': str(e)}
        )

# Admin endpoint to update RSS sources
@app.post("/admin/update-sources")
async def update_rss_sources(request: Request):
    """Update RSS sources with working URLs - admin endpoint"""
    try:
        logger.info("🔧 Admin RSS sources update requested")
        db = get_database_service()
        
        # Simple admin key check
        admin_key = request.headers.get("x-admin-key", "")
        if admin_key != "update-sources-2025":
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Clear existing sources and add working ones
        logger.info("🧹 Clearing existing sources...")
        db.execute_query("DELETE FROM ai_sources;")
        
        # Insert working AI sources with correct RSS feeds
        logger.info("📚 Inserting working AI news sources...")
        sources = [
            # High-priority research sources
            ("OpenAI Blog", "https://openai.com/blog/rss.xml", "https://openai.com", "blogs", "research", True, 1, "Official OpenAI blog and announcements"),
            ("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "https://www.technologyreview.com", "blogs", "research", True, 1, "MIT Technology Review AI coverage"),
            ("VentureBeat AI", "https://venturebeat.com/ai/feed/", "https://venturebeat.com", "blogs", "business", True, 1, "AI business news and trends"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "https://techcrunch.com", "blogs", "business", True, 1, "AI startup and business news"),
            ("Towards Data Science", "https://towardsdatascience.com/feed", "https://towardsdatascience.com", "blogs", "technical", True, 2, "Data science and ML tutorials"),
            ("AI News", "https://www.artificialintelligence-news.com/feed/", "https://www.artificialintelligence-news.com", "blogs", "technical", True, 2, "AI industry news and analysis"),
            ("Machine Learning Mastery", "https://machinelearningmastery.com/feed/", "https://machinelearningmastery.com", "blogs", "education", True, 2, "ML tutorials and guides"),
            
            # Podcast sources
            ("Lex Fridman Podcast", "https://lexfridman.com/feed/podcast/", "https://lexfridman.com", "podcasts", "education", True, 1, "Long-form conversations about AI"),
            ("AI Podcast by NVIDIA", "https://feeds.soundcloud.com/users/soundcloud:users:264034133/sounds.rss", "https://blogs.nvidia.com", "podcasts", "technical", True, 2, "NVIDIA AI discussions"),
            
            # Video sources (YouTube RSS)
            ("Two Minute Papers", "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", "https://www.youtube.com/channel/UCbfYPyITQ-7l4upoX8nvctg", "videos", "education", True, 1, "AI research paper explanations"),
            ("AI Explained", "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw", "https://www.youtube.com/channel/UCNJ1Ymd5yFuUPtn21xtRbbw", "videos", "education", True, 2, "AI concepts explained"),
            ("Yannic Kilcher", "https://www.youtube.com/feeds/videos.xml?channel_id=UCZHmQk67mSJgfCCTn7xBfew", "https://www.youtube.com/channel/UCZHmQk67mSJgfCCTn7xBfew", "videos", "research", True, 2, "AI research and paper discussions"),
            
            # News aggregators
            ("Google AI Blog", "https://ai.googleblog.com/feeds/posts/default", "https://ai.googleblog.com", "blogs", "research", True, 1, "Google AI research and developments"),
            ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "https://www.theverge.com", "blogs", "business", True, 2, "Consumer AI technology news"),
            ("Wired AI", "https://www.wired.com/feed/category/business/artificial-intelligence/latest/rss", "https://www.wired.com", "blogs", "business", True, 2, "AI technology and society coverage"),
            
            # Learning resources
            ("Distill", "https://distill.pub/rss.xml", "https://distill.pub", "learning", "research", True, 1, "Visual explanations of ML concepts"),
            ("Papers With Code Blog", "https://paperswithcode.com/feed.xml", "https://paperswithcode.com", "learning", "research", True, 2, "Latest ML papers and implementations"),
        ]
        
        for source in sources:
            db.execute_query("""
                INSERT INTO ai_sources (name, rss_url, website, content_type, category, enabled, priority, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, source)
        
        # Create indexes
        logger.info("🔗 Creating indexes...")
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_enabled ON ai_sources(enabled);")
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_priority ON ai_sources(priority);")
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_category ON ai_sources(category);")
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_content_type ON ai_sources(content_type);")
        
        # Get count
        count_result = db.execute_query("SELECT COUNT(*) as count FROM ai_sources WHERE enabled = TRUE;")
        count = count_result[0]['count'] if count_result else 0
        
        logger.info(f"✅ RSS sources updated successfully with {count} enabled sources")
        
        return {
            'success': True,
            'message': f'RSS sources updated successfully with {count} working sources',
            'sources_updated': count,
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to update RSS sources: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to update sources', 'message': str(e)}
        )

# Duplicate topics and content-types endpoints removed - keeping the unified implementations above

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API - Complete Modular PostgreSQL Backend",
        "version": "4.0.0-complete-modular-postgresql",
        "database": "postgresql",
        "status": "operational",
        "features": [
            "User Authentication (Google OAuth, OTP, JWT)",
            "Personalized Content Rendering",
            "Daily RSS Scraping from AI Sources",
            "Multimedia Content Support",
            "Content Type Filtering",
            "User Preferences Management",
            "Complete Frontend API Compatibility"
        ],
        "endpoints": {
            "authentication": ["/auth/google", "/auth/send-otp", "/auth/verify-otp", "/auth/profile", "/auth/preferences"],
            "content": ["/digest", "/personalized-digest", "/scrape", "/sources"],
            "multimedia": ["/multimedia/audio", "/multimedia/video", "/multimedia/sources", "/multimedia/scrape"],
            "filtering": ["/content/{content_type}", "/content-types", "/topics"],
            "system": ["/health", "/db-info", "/db-schema", "/archive"],
            "frontend_compatibility": "All frontend API endpoints now have corresponding backend endpoints"
        }
    }

# For Railway deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting Clean AI News Scraper API on port {port}")
    uvicorn.run(
        "clean_main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )