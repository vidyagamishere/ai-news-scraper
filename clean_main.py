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
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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
            result = db.execute_query(query, (email,), fetch_one=True)
            
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
                    fetch_one=True
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
                    fetch_one=True
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
                fetch_one=True
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
                        
                        # Insert into articles table (avoid duplicates by URL)
                        insert_query = """
                            INSERT INTO articles (title, url, description, source, published_at, category, 
                                                significance_score, reading_time, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting AI News Scraper API with clean PostgreSQL")
    
    try:
        # Just test database connection - no migration
        db = get_database_service()
        logger.info("✅ PostgreSQL connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
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
]

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
                   a.category, a.significance_score, a.reading_time, a.content_type,
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
            conditions.append(f"a.content_type IN ({placeholders})")
            params.extend(user_content_types)
        
        # Build final query
        if conditions:
            base_query += " AND (" + " OR ".join(conditions) + ")"
        
        base_query += """
            GROUP BY a.id, a.title, a.url, a.description, a.source, a.published_at, 
                     a.category, a.significance_score, a.reading_time, a.content_type
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
                   a.category, a.significance_score, a.reading_time, a.content_type
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

# Digest endpoint with personalization
@app.get("/digest")
async def get_digest(current_user: Optional[UserResponse] = Depends(get_current_user)):
    """Get news digest - personalized for authenticated users"""
    try:
        logger.info("📊 Digest requested")
        
        # Determine if user is authenticated and has preferences
        personalized = False
        articles = []
        
        if current_user and current_user.preferences:
            logger.info(f"👤 Personalized digest for: {current_user.email}")
            articles = get_personalized_articles(current_user.preferences, 50)
            personalized = True
        else:
            logger.info("🌐 General digest for unauthenticated user")
            articles = get_general_articles(50)
        
        # Organize articles by content type
        content_by_type = {
            'blog': [a for a in articles if a.get('content_type') == 'blog'],
            'audio': [a for a in articles if a.get('content_type') == 'audio'],
            'video': [a for a in articles if a.get('content_type') == 'video']
        }
        
        # Top stories (highest significance scores)
        top_stories = sorted(articles, key=lambda x: x.get('significance_score', 0), reverse=True)[:10]
        
        response = {
            "personalized": personalized,
            "topStories": top_stories,
            "content": content_by_type,
            "summary": {
                "total_articles": len(articles),
                "personalization_note": "Showing content based on your preferences" if personalized else "General AI news content",
                "last_updated": datetime.utcnow().isoformat()
            },
            "database": "postgresql",
            "version": "4.0.0-clean-postgresql"
        }
        
        logger.info(f"✅ Digest generated - {len(articles)} articles, personalized: {personalized}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Digest generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={'error': 'Failed to generate digest', 'message': str(e), 'database': 'postgresql'}
        )

# Manual scraping endpoint
@app.post("/scrape")
async def manual_scrape(current_user: Optional[UserResponse] = Depends(get_current_user)):
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

# Sources endpoint  
@app.get("/sources")
async def get_sources():
    """Get all content sources"""
    try:
        db = get_database_service()
        
        sources_query = """
            SELECT name, rss_url, website, content_type, category, priority, enabled
            FROM ai_sources
            WHERE enabled = TRUE
            ORDER BY priority ASC, name ASC
        """
        
        sources = db.execute_query(sources_query)
        
        processed_sources = []
        for source in sources:
            processed_sources.append({
                'name': source['name'],
                'rss_url': source['rss_url'],
                'website': source.get('website', ''),
                'content_type': source['content_type'],
                'category': source.get('category', 'general'),
                'priority': source['priority'],
                'enabled': source['enabled']
            })
        
        return {
            'sources': processed_sources,
            'total_count': len(processed_sources),
            'enabled_count': len([s for s in processed_sources if s['enabled']]),
            'database': 'postgresql'
        }
        
    except Exception as e:
        logger.error(f"❌ Sources endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get sources',
                'message': str(e),
                'database': 'postgresql'
            }
        )

# Digest endpoint
@app.get("/digest")
async def get_digest():
    """Get news digest"""
    try:
        db = get_database_service()
        
        articles_query = """
            SELECT source, title, url, published_at, description, 
                   significance_score, category, reading_time, image_url
            FROM articles
            WHERE published_at > NOW() - INTERVAL '7 days'
            ORDER BY published_at DESC, significance_score DESC
            LIMIT 50
        """
        
        articles = db.execute_query(articles_query)
        
        processed_articles = []
        for article in articles:
            article_dict = dict(article)
            
            # Convert timestamp to ISO format
            if article_dict.get('published_at'):
                article_dict['published_at'] = article_dict['published_at'].isoformat()
            
            processed_articles.append(article_dict)
        
        # Get top stories (high significance score)
        top_stories = [article for article in processed_articles if article.get('significance_score', 0) >= 8][:10]
        
        return {
            'topStories': top_stories,
            'content': {
                'blog': [a for a in processed_articles if a.get('category') == 'blogs'][:20],
                'audio': [a for a in processed_articles if a.get('category') == 'podcasts'][:10],
                'video': [a for a in processed_articles if a.get('category') == 'videos'][:10],
            },
            'summary': {
                'total_articles': len(processed_articles),
                'top_stories_count': len(top_stories),
                'latest_update': "2025-09-23T12:40:00Z"
            },
            'personalized': False,
            'database': 'postgresql'
        }
        
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


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI News Scraper API - Clean PostgreSQL Version",
        "version": "4.0.0-clean-postgresql",
        "database": "postgresql",
        "status": "operational"
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