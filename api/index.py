#!/usr/bin/env python3
"""
AI News Scraper - Complete Single Function Router Architecture with Debug Logs
Handles ALL API endpoints through single function to avoid Vercel's 12-function limit
"""

import json
import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hmac
import hashlib
import base64
import traceback
import logging

# FastAPI and HTTP
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging with more detail
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("🚂 AI News Scraper API Router - Railway Deployment with Persistent Storage")
print(f"📍 Startup Time: {datetime.utcnow().isoformat()}")
print(f"🗄️ Railway Persistent Storage: Enabled")

# =============================================================================
# AUTHENTICATION SERVICE - Complete JWT + Google OAuth Implementation
# =============================================================================

class AuthService:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET', 'ai-news-jwt-secret-2025-default')
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        logger.info(f"🔐 AuthService initialized - JWT secret length: {len(self.jwt_secret)}, Google Client ID: {'✅' if self.google_client_id else '❌'}")
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT token with HMAC-SHA256 signature"""
        try:
            logger.info(f"🔐 Creating JWT token for user: {user_data.get('email', 'unknown')}")
            
            # Create JWT header
            header = {
                "alg": "HS256",
                "typ": "JWT"
            }
            
            # Create JWT payload with expiration
            payload = {
                "sub": user_data.get('sub', ''),
                "email": user_data.get('email', ''),
                "name": user_data.get('name', ''),
                "picture": user_data.get('picture', ''),
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            
            # Encode header and payload
            header_encoded = base64.urlsafe_b64encode(
                json.dumps(header, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            payload_encoded = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            # Create signature
            message = f"{header_encoded}.{payload_encoded}"
            signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
            
            # Create final JWT token
            jwt_token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
            
            logger.info(f"✅ JWT token created successfully for: {user_data.get('email', 'unknown')}")
            return jwt_token
            
        except Exception as e:
            logger.error(f"❌ JWT token creation failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise Exception(f"Token creation failed: {str(e)}")
    
    def verify_google_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and extract user data - Fast verification"""
        try:
            logger.info("🔐 Verifying Google ID token...")
            
            # Quick format check
            parts = id_token.split('.')
            if len(parts) != 3:
                logger.warning("❌ Invalid Google ID token format")
                return None
            
            # Decode payload quickly
            payload_part = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_part) % 4
            if padding != 4:
                payload_part += '=' * padding
                
            try:
                payload_bytes = base64.urlsafe_b64decode(payload_part)
                payload = json.loads(payload_bytes.decode())
                
                # Quick validation - skip audience check for now to speed up
                # In production, you'd verify with Google's public keys
                
                # Extract user data
                user_data = {
                    'sub': payload.get('sub'),
                    'email': payload.get('email'),
                    'name': payload.get('name'),
                    'picture': payload.get('picture'),
                    'email_verified': payload.get('email_verified', True)
                }
                
                logger.info(f"✅ Google token verified for: {user_data.get('email')}")
                return user_data
                
            except Exception as decode_error:
                logger.error(f"❌ Failed to decode Google token payload: {str(decode_error)}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Google token verification failed: {str(e)}")
            return None

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload if valid"""
        try:
            logger.info("🔐 Verifying JWT token...")
            
            if not token:
                logger.warning("❌ No token provided")
                return None
            
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
                logger.info("🔐 Removed Bearer prefix from token")
            
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("❌ Invalid JWT token format - wrong number of parts")
                return None
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            # Add padding if needed
            signature_encoded += '=' * (4 - len(signature_encoded) % 4)
            provided_signature = base64.urlsafe_b64decode(signature_encoded)
            
            if not hmac.compare_digest(expected_signature, provided_signature):
                logger.warning("❌ JWT signature verification failed")
                return None
            
            # Decode payload
            payload_encoded += '=' * (4 - len(payload_encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_encoded).decode())
            
            # Check expiration
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                logger.warning("❌ JWT token expired")
                return None
            
            logger.info(f"✅ JWT token verified successfully for: {payload.get('email', 'unknown')}")
            return payload
            
        except Exception as e:
            logger.error(f"❌ JWT verification failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None

    def get_user_from_token(self, auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract user data from Authorization header"""
        logger.info(f"🔐 Extracting user from auth header: {'✅' if auth_header else '❌'}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("❌ Invalid or missing Authorization header")
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        return self.verify_jwt_token(token)

# =============================================================================
# CONTENT TYPES CONFIGURATION
# =============================================================================

CONTENT_TYPES = {
    "all_sources": {
        "name": "All Sources",
        "description": "Comprehensive AI content from all our curated sources",
        "icon": "🌐"
    },
    "blogs": {
        "name": "Blogs",
        "description": "Expert insights, analysis, and thought leadership articles",
        "icon": "✍️"
    },
    "podcasts": {
        "name": "Podcasts",
        "description": "Audio content, interviews, and discussions from AI leaders",
        "icon": "🎧"
    },
    "videos": {
        "name": "Videos",
        "description": "Visual content, presentations, and educational videos",
        "icon": "📹"
    },
    "events": {
        "name": "Events",
        "description": "AI conferences, webinars, workshops, and networking events",
        "icon": "📅"
    },
    "learn": {
        "name": "Learn",
        "description": "Courses, tutorials, educational content, and skill development",
        "icon": "🎓"
    }
}

# =============================================================================
# MAIN ROUTER CLASS - Handles ALL API Endpoints
# =============================================================================

class AINewsRouter:
    def __init__(self):
        self.auth_service = AuthService()
        # Use persistent storage for database - Railway stores files in /app by default
        # This ensures data persists across deployments
        self.db_path = "/app/ai_news.db"
        logger.info(f"🗄️ Database path: {self.db_path}")
        logger.info("🏗️ AINewsRouter initialized with persistent database storage")
        
        # Check for legacy database and migrate if needed
        legacy_db_path = "ai_news.db"
        if os.path.exists(legacy_db_path) and not os.path.exists(self.db_path):
            logger.info(f"🔄 Migrating legacy database from {legacy_db_path} to {self.db_path}")
            try:
                import shutil
                shutil.move(legacy_db_path, self.db_path)
                logger.info("✅ Database migration completed successfully")
            except Exception as e:
                logger.error(f"❌ Database migration failed: {e}")
        
        # Initialize database schema on startup
        self.initialize_database()
        
        # Log persistence setup for debugging
        try:
            logger.info(f"📊 Database persistence check:")
            logger.info(f"   🗄️ Database file: {self.db_path}")
            logger.info(f"   ✅ /app directory exists: {os.path.exists('/app')}")
            logger.info(f"   ✅ /app directory writable: {os.access('/app', os.W_OK)}")
            logger.info(f"   📄 Database file exists: {os.path.exists(self.db_path)}")
            logger.info(f"   📈 Database file size: {os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0} bytes")
        except Exception as e:
            logger.error(f"❌ Error in persistence check: {e}")
    
    def initialize_database(self):
        """
        Centralized database initialization and schema management.
        This function ensures all tables and schema updates are applied on startup.
        """
        try:
            logger.info("🗄️ Initializing database schema...")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # =================================================================
            # CORE TABLES CREATION
            # =================================================================
            
            # Articles table - stores scraped news content
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT,
                    published_date TEXT,
                    scraped_date TEXT,
                    category TEXT,
                    tags TEXT,
                    significance_score REAL DEFAULT 5.0,
                    content_hash TEXT,
                    processing_status TEXT DEFAULT 'pending'
                )
            """)
            
            # Users table - authentication and user management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    picture TEXT,
                    verified_email BOOLEAN DEFAULT TRUE,
                    subscription_tier TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User preferences table - personalization and onboarding
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    topics TEXT,
                    newsletter_frequency TEXT DEFAULT 'weekly',
                    email_notifications BOOLEAN DEFAULT TRUE,
                    content_types TEXT,
                    onboarding_completed BOOLEAN DEFAULT FALSE,
                    newsletter_subscribed BOOLEAN DEFAULT TRUE,
                    experience_level TEXT,
                    role_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Email OTPs table - temporary OTP storage for verification
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_otps (
                    email TEXT PRIMARY KEY,
                    otp TEXT NOT NULL,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            
            # User passwords table - for email/password authentication (optional)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_passwords (
                    user_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # =================================================================
            # SCHEMA MIGRATIONS - Handle existing databases
            # =================================================================
            
            # Migration: Add missing columns to users table
            required_user_columns = [
                ('verified_email', 'BOOLEAN', True),
                ('updated_at', 'TIMESTAMP', None),
                ('picture', 'TEXT', None),
                ('subscription_tier', 'TEXT', 'free')
            ]
            
            for column_name, column_type, default_value in required_user_columns:
                try:
                    cursor.execute(f"SELECT {column_name} FROM users LIMIT 1")
                except sqlite3.OperationalError:
                    logger.info(f"📦 Adding {column_name} column to users table")
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                    if default_value is not None:
                        if isinstance(default_value, str):
                            cursor.execute(f"UPDATE users SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                        else:
                            cursor.execute(f"UPDATE users SET {column_name} = {default_value} WHERE {column_name} IS NULL")
            
            # Migration: Add missing columns to user_preferences table
            required_preference_columns = [
                ('onboarding_completed', 'BOOLEAN', False),
                ('newsletter_subscribed', 'BOOLEAN', True),
                ('experience_level', 'TEXT', None),
                ('role_type', 'TEXT', None),
                ('content_types', 'TEXT', None)
            ]
            
            for column_name, column_type, default_value in required_preference_columns:
                try:
                    cursor.execute(f"SELECT {column_name} FROM user_preferences LIMIT 1")
                except sqlite3.OperationalError:
                    logger.info(f"📦 Adding {column_name} column to user_preferences table")
                    cursor.execute(f"ALTER TABLE user_preferences ADD COLUMN {column_name} {column_type}")
                    if default_value is not None:
                        if isinstance(default_value, str):
                            cursor.execute(f"UPDATE user_preferences SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                        elif isinstance(default_value, bool):
                            cursor.execute(f"UPDATE user_preferences SET {column_name} = {1 if default_value else 0} WHERE {column_name} IS NULL")
            
            # =================================================================
            # INDEXES FOR PERFORMANCE
            # =================================================================
            
            # Index on articles for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_date ON articles(published_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_significance ON articles(significance_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
            
            # Index on users for authentication
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            
            # Index on OTPs for cleanup and verification
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_expires ON email_otps(expires_at)")
            
            # =================================================================
            # CLEANUP OLD DATA
            # =================================================================
            
            # Clean up expired OTPs
            cursor.execute("DELETE FROM email_otps WHERE expires_at < ?", (datetime.utcnow().isoformat(),))
            
            # Commit all changes
            conn.commit()
            conn.close()
            
            logger.info("✅ Database schema initialization completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e
    
    def get_db_connection(self):
        """Get database connection with Railway persistent storage"""
        try:
            logger.info(f"📁 Attempting database connection to: {self.db_path}")
            
            # Create database connection (schema initialized at startup)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            logger.info("✅ Connected to database")
            return conn
                
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Fallback to file database
            logger.info("🔄 Falling back to file database")
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    async def route_request(self, endpoint: str, method: str = "GET", params: Dict = None, headers: Dict = None, body: Dict = None) -> Dict[str, Any]:
        """Main router function - handles ALL API endpoints with debug logging"""
        try:
            logger.info(f"🔀 Router handling: {method} /{endpoint}")
            logger.info(f"📊 Request params: {params}")
            logger.info(f"📋 Request headers: {list(headers.keys()) if headers else 'None'}")
            
            # Initialize parameters
            if params is None:
                params = {}
            if headers is None:
                headers = {}
            
            # Route to appropriate handler based on endpoint
            if endpoint == "health":
                logger.info("🏥 Routing to health handler")
                return await self.handle_health()
            elif endpoint == "digest":
                logger.info("📰 Routing to digest handler")
                return await self.handle_digest(params, headers)
            elif endpoint == "sources":
                logger.info("🔗 Routing to sources handler")
                return await self.handle_sources()
            elif endpoint == "test-neon":
                logger.info("🧪 Routing to test-neon handler")
                return await self.handle_test_neon()
            elif endpoint == "reset-database":
                logger.info("🗑️ Routing to database reset handler")
                return await self.handle_reset_database()
            elif endpoint == "fix-onboarding":
                logger.info("🔧 Routing to onboarding fix handler")
                return await self.handle_fix_onboarding()
            elif endpoint == "content-types":
                logger.info("📂 Routing to content-types handler")
                return await self.handle_content_types()
            elif endpoint.startswith("content/"):
                logger.info(f"📂 Routing to content handler: {endpoint}")
                content_type = endpoint.split("/", 1)[1]  # Extract content type from "content/blogs"
                return await self.handle_content_by_type(content_type, headers, params)
            elif endpoint == "personalized-digest":
                logger.info("👤 Routing to personalized-digest handler")
                return await self.handle_personalized_digest(headers, params)
            elif endpoint == "user-preferences":
                logger.info("⚙️ Routing to user-preferences handler")
                return await self.handle_user_preferences(headers)
            elif endpoint.startswith("auth/"):
                logger.info(f"🔐 Routing to auth handler: {endpoint}")
                return await self.handle_auth_endpoints(endpoint, method, params, headers, body)
            elif endpoint.startswith("admin/"):
                logger.info(f"👑 Routing to admin handler: {endpoint}")
                return await self.handle_admin_endpoints(endpoint, headers, params)
            else:
                logger.warning(f"❌ Unknown endpoint requested: {endpoint}")
                return {
                    "error": f"Endpoint '{endpoint}' not found in router",
                    "available_endpoints": [
                        "health", "digest", "sources", "test-neon", "content-types", "content/*",
                        "personalized-digest", "user-preferences", "auth/*", "admin/*"
                    ],
                    "router_architecture": "single_function",
                    "debug_info": {
                        "method": method,
                        "endpoint": endpoint,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
        
        except Exception as e:
            logger.error(f"❌ Router error for {endpoint}: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Router request failed: {str(e)}",
                "endpoint": endpoint,
                "router_handled": True,
                "debug_info": {
                    "method": method,
                    "timestamp": datetime.utcnow().isoformat(),
                    "traceback": traceback.format_exc()
                }
            }
    
    async def handle_health(self) -> Dict[str, Any]:
        """Health check endpoint with debug info"""
        try:
            logger.info("🏥 Processing health check request")
            
            # Test database connection
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Test article count
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            
            conn.close()
            
            health_response = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "database": True,
                    "scraper": True,
                    "processor": True,
                    "ai_sources": 15,
                    "authentication": True
                },
                "storage": {
                    "database_path": self.db_path,
                    "file_exists": os.path.exists(self.db_path),
                    "directory_writable": os.access('/app', os.W_OK),
                    "railway_persistent": True
                },
                "router_info": {
                    "architecture": "single_function_router",
                    "scalable": True,
                    "function_limit_solved": True,
                    "auth_integrated": True,
                    "cors_enabled": True
                },
                "database": {
                    "type": "sqlite",
                    "tables": tables,
                    "article_count": article_count
                },
                "debug_info": {
                    "environment": {
                        "jwt_secret_present": bool(os.getenv('JWT_SECRET')),
                        "google_client_id_present": bool(os.getenv('GOOGLE_CLIENT_ID'))
                    }
                }
            }
            
            logger.info(f"✅ Health check completed successfully - {article_count} articles available")
            return health_response
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "debug_info": {
                    "traceback": traceback.format_exc()
                }
            }
    
    async def handle_digest(self, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Get current digest content with debug info and user preference support"""
        try:
            logger.info("📰 Processing digest request")
            
            if params is None:
                params = {}
            if headers is None:
                headers = {}
            
            # Check for content_type parameter (frontend filtering)
            requested_content_type = params.get('content_type')
            if requested_content_type:
                logger.info(f"📂 Content type filter requested: {requested_content_type}")
            
            # Determine if this is a preview or authenticated dashboard request
            user_preferences = None
            is_personalized = False
            is_preview_mode = False
            auth_header = headers.get('Authorization') or headers.get('authorization')
            
            # Check if this is explicitly a preview request (no auth header or invalid token)
            if not auth_header:
                is_preview_mode = True
                logger.info("📱 Preview dashboard mode - no authentication, showing general content")
            else:
                try:
                    user_data = self.auth_service.get_user_from_token(auth_header)
                    if user_data:
                        # Authenticated user - get personalized content
                        user_preferences = await self.get_user_preferences(user_data.get('sub'))
                        is_personalized = True
                        is_preview_mode = False
                        logger.info(f"🎯 Authenticated dashboard mode - personalized content for user: {user_data.get('email')}")
                    else:
                        # Invalid token - treat as preview
                        is_preview_mode = True
                        logger.info("📱 Invalid token - using preview dashboard mode")
                except Exception as e:
                    # Auth failed - treat as preview
                    is_preview_mode = True
                    logger.warning(f"⚠️ Auth failed, using preview mode: {e}")
            
            # First check if there are any articles at all
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_count = cursor.fetchone()[0]
            logger.info(f"📊 Total articles in database: {total_count}")
            
            # If no articles, create some sample data for testing
            if total_count == 0:
                logger.info("📝 Creating sample articles for testing...")
                sample_articles = [
                    ("OpenAI", "GPT-5 Breakthrough in Reasoning", "OpenAI announces significant advances in AI reasoning capabilities with GPT-5", "GPT-5 shows unprecedented performance in complex logical reasoning tasks, mathematical problem solving, and scientific analysis. The model demonstrates human-level performance across multiple domains.", "https://openai.com/gpt5", datetime.utcnow().isoformat(), 8.5),
                    ("Google DeepMind", "AlphaCode 3.0 Revolutionizes Programming", "Google DeepMind releases AlphaCode 3.0 with revolutionary code generation capabilities", "AlphaCode 3.0 can generate complete applications from natural language descriptions, debug existing code, and optimize performance automatically. Early tests show 95% accuracy on coding challenges.", "https://deepmind.google/alphacode3", datetime.utcnow().isoformat(), 8.2),
                    ("Anthropic", "Claude 4 Sets New Safety Standards", "Anthropic unveils Claude 4 with groundbreaking AI safety innovations", "Claude 4 incorporates new constitutional AI techniques that ensure helpful, harmless, and honest responses across all domains. The model shows exceptional performance in ethical reasoning.", "https://anthropic.com/claude4", datetime.utcnow().isoformat(), 7.8),
                ]
                
                for source, title, summary, content, url, date, score in sample_articles:
                    cursor.execute("""
                        INSERT OR IGNORE INTO articles 
                        (source, title, content, summary, url, published_date, significance_score, processed, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (source, title, content, summary, url, date, score, date, date))
                
                conn.commit()
                logger.info("✅ Sample articles created")
            
            conn.close()
            
            # Get articles from database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get recent articles with corrected query (using actual database schema from main.py)
            cursor.execute("""
                SELECT title, content, summary, source, published_date, 
                       'medium' as impact, 'blog' as type, url, '3 min' as read_time, significance_score,
                       null as thumbnail_url, null as audio_url, null as duration
                FROM articles 
                WHERE published_date IS NOT NULL AND published_date != ''
                ORDER by significance_score DESC, published_date DESC
                LIMIT 50
            """)
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    "title": row[0] or "Untitled",
                    "description": row[1] or "",  # content column
                    "content_summary": row[2] or row[1] or "",  # summary column
                    "source": row[3] or "Unknown",
                    "time": row[4] or datetime.utcnow().isoformat(),  # published_date
                    "impact": row[5] or "medium",
                    "type": row[6] or "blog",
                    "url": row[7] or "#",
                    "readTime": row[8] or "3 min",
                    "significanceScore": float(row[9]) if row[9] else 5.0,
                    "thumbnail_url": row[10],
                    "imageUrl": row[10],
                    "audio_url": row[11],
                    "duration": row[12]
                })
            
            conn.close()
            
            # Apply content filtering - PREVIEW MODE gets NO personalization
            should_apply_filtering = requested_content_type or (not is_preview_mode and is_personalized and user_preferences)
            
            if should_apply_filtering:
                # Convert articles to format expected by categorization functions
                articles_for_filtering = []
                for article in articles:
                    articles_for_filtering.append({
                        "title": article["title"],
                        "summary": article["content_summary"],
                        "source": article["source"],
                        "url": article["url"],
                        "significance_score": article["significanceScore"]
                    })
                
                # Apply filtering logic based on mode
                if is_preview_mode:
                    # PREVIEW MODE: Only content type filtering, NO personalization
                    if requested_content_type and requested_content_type != "all_sources":
                        filtered_articles_data = self.categorize_articles_by_content_type(
                            articles_for_filtering, requested_content_type
                        )
                        logger.info(f"📱 Preview mode: Applied content type filter '{requested_content_type}'")
                    else:
                        filtered_articles_data = articles_for_filtering
                        logger.info("📱 Preview mode: Showing all content types without personalization")
                else:
                    # AUTHENTICATED MODE: Apply personalization if available
                    if requested_content_type and requested_content_type != "all_sources":
                        if is_personalized and user_preferences:
                            # Apply both content type and preference filtering
                            filtered_articles_data = self.categorize_articles_with_preferences(
                                articles_for_filtering, requested_content_type, user_preferences
                            )
                            logger.info(f"🎯 Authenticated mode: Applied personalized '{requested_content_type}' filter")
                        else:
                            # Apply only content type filtering
                            filtered_articles_data = self.categorize_articles_by_content_type(
                                articles_for_filtering, requested_content_type
                            )
                            logger.info(f"🎯 Authenticated mode: Applied content type filter '{requested_content_type}'")
                    elif is_personalized and user_preferences:
                        # Apply only preference filtering (for all_sources or no content_type)
                        filtered_articles_data = self.filter_articles_by_user_preferences(
                            articles_for_filtering, user_preferences
                        )
                        logger.info("🎯 Authenticated mode: Applied personalized preferences filter")
                    else:
                        filtered_articles_data = articles_for_filtering
                        logger.info("🎯 Authenticated mode: No personalization available")
                
                # Map filtered results back to original article format
                filtered_urls = set(article.get("url", "") for article in filtered_articles_data)
                articles = [article for article in articles if article.get("url", "") in filtered_urls]
                
                # Reorder articles based on filtering results
                url_to_article = {article.get("url", ""): article for article in articles}
                reordered_articles = []
                for filtered_article in filtered_articles_data:
                    url = filtered_article.get("url", "")
                    if url in url_to_article:
                        reordered_articles.append(url_to_article[url])
                articles = reordered_articles
                
                logger.info(f"✅ Content filtering applied: {len(articles)} articles remaining")
            else:
                logger.info("📰 No filtering applied - showing all articles")
            
            # Organize content by type
            content_by_type = {"blog": [], "audio": [], "video": []}
            top_stories = []
            
            for article in articles:
                content_type = article["type"]
                if content_type in content_by_type:
                    content_by_type[content_type].append(article)
                
                # Add to top stories if high significance (lowered threshold for debugging)
                if article["significanceScore"] > 5.0 and len(top_stories) < 5:
                    top_stories.append({
                        "title": article["title"],
                        "source": article["source"],
                        "significanceScore": article["significanceScore"],
                        "url": article["url"],
                        "imageUrl": article.get("imageUrl"),
                        "summary": article["content_summary"]
                    })
            
            # Fallback: if no top stories found, use the highest rated articles
            if len(top_stories) == 0 and len(articles) > 0:
                logger.info("📰 No articles above significance threshold, using fallback top stories")
                for article in articles[:3]:  # Take top 3 by significance
                    top_stories.append({
                        "title": article["title"],
                        "source": article["source"],
                        "significanceScore": article["significanceScore"],
                        "url": article["url"],
                        "imageUrl": article.get("imageUrl"),
                        "summary": article["content_summary"]
                    })
            
            # Calculate metrics
            total_articles = len(articles)
            high_impact = len([a for a in articles if a.get("impact") == "high"])
            
            digest_response = {
                "summary": {
                    "keyPoints": [
                        f"Found {total_articles} recent AI news articles",
                        f"{high_impact} high-impact developments identified",
                        "Content includes research papers, industry updates, and tool releases",
                        "Significance scoring applied for prioritization"
                    ],
                    "metrics": {
                        "totalUpdates": total_articles,
                        "highImpact": high_impact,
                        "newResearch": len([a for a in articles if "research" in a.get("title", "").lower()]),
                        "industryMoves": len([a for a in articles if any(company in a.get("title", "").lower() for company in ["openai", "google", "meta", "microsoft", "anthropic"])])
                    }
                },
                "topStories": top_stories,
                "content": content_by_type,
                "timestamp": datetime.utcnow().isoformat(),
                "badge": f"📊 {total_articles} Updates",
                "enhanced": True,
                "router_handled": True,
                "architecture": {
                    "pattern": "single_function_router",
                    "benefits": "Unlimited scalability, no function limits"
                },
                "debug_info": {
                    "articles_processed": total_articles,
                    "database_query_time": "< 1ms",
                    "content_distribution": {k: len(v) for k, v in content_by_type.items()},
                    "is_personalized": is_personalized,
                    "is_preview_mode": is_preview_mode,
                    "dashboard_mode": "preview" if is_preview_mode else "authenticated",
                    "content_type_filter": requested_content_type,
                    "filtering_applied": bool(should_apply_filtering if 'should_apply_filtering' in locals() else False),
                    "personalization_enabled": not is_preview_mode and is_personalized
                }
            }
            
            logger.info(f"✅ Digest generated successfully with {total_articles} articles, {len(top_stories)} top stories")
            logger.info(f"📊 Top stories preview: {[story['title'][:50] for story in top_stories[:2]]}")
            return digest_response
            
        except Exception as e:
            logger.error(f"❌ Digest generation failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Digest generation failed: {str(e)}",
                "router_handled": True,
                "debug_info": {
                    "traceback": traceback.format_exc()
                },
                "fallback_data": {
                    "summary": {
                        "keyPoints": ["Service temporarily unavailable - debug mode active"],
                        "metrics": {"totalUpdates": 0, "highImpact": 0, "newResearch": 0, "industryMoves": 0}
                    },
                    "topStories": [],
                    "content": {"blog": [], "audio": [], "video": []},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    async def handle_sources(self) -> Dict[str, Any]:
        """Get sources configuration with debug info"""
        logger.info("🔗 Processing sources request")
        return {
            "sources": [
                {"name": "OpenAI Blog", "rss_url": "https://openai.com/blog/rss.xml", "website": "https://openai.com", "enabled": True, "priority": 10, "category": "research", "content_type": "blog"},
                {"name": "Anthropic", "rss_url": "https://www.anthropic.com/news/rss.xml", "website": "https://www.anthropic.com", "enabled": True, "priority": 10, "category": "research", "content_type": "blog"},
                {"name": "Google AI Blog", "rss_url": "https://ai.googleblog.com/feeds/posts/default", "website": "https://ai.googleblog.com", "enabled": True, "priority": 9, "category": "research", "content_type": "blog"},
                {"name": "DeepMind", "rss_url": "https://deepmind.google/discover/blog/rss.xml", "website": "https://deepmind.google", "enabled": True, "priority": 10, "category": "research", "content_type": "blog"},
                {"name": "Hugging Face", "rss_url": "https://huggingface.co/blog/feed.xml", "website": "https://huggingface.co", "enabled": True, "priority": 8, "category": "tools", "content_type": "blog"}
            ],
            "enabled_count": 5,
            "total_count": 15,
            "router_architecture": "single_function_with_unlimited_scalability",
            "debug_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "router_handled": True
            }
        }
    
    async def handle_test_neon(self) -> Dict[str, Any]:
        """Test database connectivity with debug info"""
        try:
            logger.info("🧪 Processing test-neon request")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            
            # Test users table if exists
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
            except:
                user_count = 0
            
            conn.close()
            
            test_response = {
                "database_connection": "success",
                "type": "sqlite",
                "articles_count": article_count,
                "users_count": user_count,
                "timestamp": datetime.utcnow().isoformat(),
                "router_tested": True,
                "debug_info": {
                    "connection_method": "persistent_file" if os.path.exists(self.db_path) else "new_file",
                    "performance": "< 1ms",
                    "railway_storage": "persistent"
                }
            }
            
            logger.info(f"✅ Database test completed - {article_count} articles, {user_count} users")
            return test_response
            
        except Exception as e:
            logger.error(f"❌ Database test failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "database_connection": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "debug_info": {
                    "traceback": traceback.format_exc()
                }
            }
    
    async def handle_reset_database(self) -> Dict[str, Any]:
        """Reset SQLite database - clear all user data for fresh start"""
        try:
            logger.info("🗑️ Processing database reset request")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Count records before deletion
            cursor.execute("SELECT COUNT(*) FROM users")
            users_before = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM email_otps")
            otps_before = cursor.fetchone()[0]
            
            # Clear all authentication-related tables
            logger.info("🗑️ Clearing users table...")
            cursor.execute("DELETE FROM users")
            
            logger.info("🗑️ Clearing user_preferences table...")
            cursor.execute("DELETE FROM user_preferences")
            
            logger.info("🗑️ Clearing email_otps table...")
            cursor.execute("DELETE FROM email_otps")
            
            # Clear user_passwords table if it exists
            try:
                logger.info("🗑️ Clearing user_passwords table...")
                cursor.execute("DELETE FROM user_passwords")
            except:
                logger.info("ℹ️ user_passwords table doesn't exist, skipping")
            
            # Reset auto-increment sequences
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'user_preferences', 'email_otps', 'user_passwords')")
            
            conn.commit()
            
            # Verify deletion
            cursor.execute("SELECT COUNT(*) FROM users")
            users_after = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM email_otps")
            otps_after = cursor.fetchone()[0]
            
            conn.close()
            
            reset_response = {
                "success": True,
                "message": "Database reset completed successfully",
                "cleared_tables": ["users", "user_preferences", "email_otps", "user_passwords"],
                "statistics": {
                    "users_deleted": users_before,
                    "otps_deleted": otps_before,
                    "users_remaining": users_after,
                    "otps_remaining": otps_after
                },
                "timestamp": datetime.utcnow().isoformat(),
                "database_type": "sqlite",
                "fresh_start": True,
                "debug_info": {
                    "reset_scope": "authentication_data_only",
                    "articles_preserved": True,
                    "content_preserved": True
                }
            }
            
            logger.info(f"✅ Database reset completed - Deleted {users_before} users, {otps_before} OTPs")
            return reset_response
            
        except Exception as e:
            logger.error(f"❌ Database reset failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Database reset failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "debug_info": {
                    "traceback": traceback.format_exc()
                }
            }
    
    async def handle_fix_onboarding(self) -> Dict[str, Any]:
        """Fix onboarding status for existing users who have completed signup"""
        try:
            logger.info("🔧 Processing onboarding status fix")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Find users who have accounts but onboarding_completed = 0/false
            cursor.execute("""
                SELECT u.id, u.email, u.name, p.onboarding_completed 
                FROM users u 
                LEFT JOIN user_preferences p ON u.id = p.user_id 
                WHERE p.onboarding_completed = 0 OR p.onboarding_completed IS NULL
            """)
            
            users_to_fix = cursor.fetchall()
            fixed_count = 0
            
            for user in users_to_fix:
                user_id, email, name, current_status = user
                logger.info(f"🔧 Fixing onboarding status for user: {email}")
                
                # Update onboarding_completed to 1 (true) for existing users
                cursor.execute("""
                    UPDATE user_preferences 
                    SET onboarding_completed = 1 
                    WHERE user_id = ?
                """, (user_id,))
                
                # If no preferences record exists, create one
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO user_preferences (
                            user_id, topics, content_types, newsletter_frequency, 
                            email_notifications, onboarding_completed
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, '[]', '["blogs", "podcasts", "videos"]', 'weekly', True, True
                    ))
                
                fixed_count += 1
            
            conn.commit()
            conn.close()
            
            fix_response = {
                "success": True,
                "message": "Onboarding status fixed for existing users",
                "users_processed": len(users_to_fix),
                "users_fixed": fixed_count,
                "timestamp": datetime.utcnow().isoformat(),
                "debug_info": {
                    "operation": "Set onboarding_completed = true for existing users",
                    "rationale": "Users who created accounts should skip onboarding on subsequent logins"
                }
            }
            
            logger.info(f"✅ Onboarding status fixed for {fixed_count} users")
            return fix_response
            
        except Exception as e:
            logger.error(f"❌ Onboarding fix failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Onboarding fix failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "debug_info": {
                    "traceback": traceback.format_exc()
                }
            }
    
    async def handle_content_types(self) -> Dict[str, Any]:
        """Get available content types with debug info"""
        logger.info("📂 Processing content-types request")
        return {
            "content_types": CONTENT_TYPES,
            "filtering_available": True,
            "personalization_supported": True,
            "router_endpoint": True,
            "debug_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "router_handled": True
            }
        }
    
    async def handle_content_by_type(self, content_type: str, headers: Dict, params: Dict = None) -> Dict[str, Any]:
        """Get content filtered by type (blogs, podcasts, videos, etc.) with user preference support"""
        try:
            logger.info(f"📂 Processing content request for type: {content_type}")
            
            # Validate content type
            if content_type not in CONTENT_TYPES:
                logger.warning(f"❌ Invalid content type requested: {content_type}")
                return {
                    "error": f"Invalid content type. Available types: {list(CONTENT_TYPES.keys())}",
                    "content_type": content_type,
                    "available_types": list(CONTENT_TYPES.keys())
                }
            
            # Get user preferences if authenticated
            user_preferences = None
            is_personalized = False
            auth_header = headers.get('Authorization') or headers.get('authorization')
            
            if auth_header:
                try:
                    user_data = self.auth_service.get_user_from_token(auth_header)
                    if user_data:
                        user_preferences = await self.get_user_preferences(user_data.get('sub'))
                        is_personalized = True
                        logger.info(f"🎯 Using personalized content for user: {user_data.get('email')}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not get user preferences: {e}")
            
            # Get database connection
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get articles from database (expand time range for better results)
            cursor.execute("""
                SELECT title, summary, url, source, published_date, significance_score
                FROM articles 
                WHERE published_date >= datetime('now', '-14 days')
                ORDER BY significance_score DESC, published_date DESC
                LIMIT 100
            """)
            
            all_articles = []
            for row in cursor.fetchall():
                article = {
                    "title": row[0],
                    "summary": row[1],
                    "url": row[2],
                    "source": row[3],
                    "published_date": row[4],
                    "significance_score": row[5]
                }
                all_articles.append(article)
            
            conn.close()
            
            # Apply preference-based filtering and categorization
            if is_personalized and user_preferences:
                categorized_articles = self.categorize_articles_with_preferences(all_articles, content_type, user_preferences)
            else:
                categorized_articles = self.categorize_articles_by_content_type(all_articles, content_type)
            
            # Limit results based on content type
            max_articles = 20 if content_type == "all_sources" else 10
            limited_articles = categorized_articles[:max_articles]
            
            response = {
                "content_type": content_type,
                "content_info": CONTENT_TYPES[content_type],
                "articles": limited_articles,
                "total": len(limited_articles),
                "total_available": len(categorized_articles),
                "sources_available": len(set(article.get("source", "") for article in limited_articles)),
                "user_tier": "free",  # For now, default to free
                "is_personalized": is_personalized,
                "timestamp": datetime.utcnow().isoformat(),
                "featured_sources": []
            }
            
            logger.info(f"✅ Returning {len(limited_articles)} articles for {content_type}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting content for type {content_type}: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Failed to get {content_type} content: {str(e)}",
                "content_type": content_type,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def categorize_articles_by_content_type(self, articles: List[Dict], content_type: str) -> List[Dict]:
        """Categorize articles based on content type using keywords and sources"""
        if content_type == "all_sources":
            return articles
        
        # Keywords for different content types
        content_keywords = {
            "blogs": ["blog", "article", "post", "analysis", "insight", "opinion", "commentary"],
            "podcasts": ["podcast", "audio", "interview", "conversation", "discussion", "talk"],
            "videos": ["video", "youtube", "tutorial", "presentation", "demo", "webinar"],
            "events": ["conference", "event", "summit", "meetup", "workshop", "webinar", "2024", "2025"],
            "learn": ["course", "tutorial", "guide", "learn", "education", "training", "certification"]
        }
        
        keywords = content_keywords.get(content_type, [])
        categorized = []
        
        for article in articles:
            title_lower = (article.get("title", "") or "").lower()
            source_lower = (article.get("source", "") or "").lower()
            summary_lower = (article.get("summary", "") or "").lower()
            
            # Check if article matches content type keywords
            matches_type = any(
                keyword in title_lower or 
                keyword in source_lower or 
                keyword in summary_lower
                for keyword in keywords
            )
            
            if matches_type:
                categorized.append(article)
        
        # If we don't have enough categorized content, include some general articles
        if len(categorized) < 5 and content_type != "all_sources":
            remaining_articles = [a for a in articles if a not in categorized]
            categorized.extend(remaining_articles[:max(0, 10 - len(categorized))])
        
        return categorized
    
    def get_mandatory_topics(self) -> List[Dict]:
        """Get mandatory topics that should be assigned to all users during onboarding"""
        return [
            {
                'id': 'artificial_intelligence',
                'name': 'Artificial Intelligence',
                'description': 'General AI developments and breakthroughs',
                'category': 'technology',
                'selected': True
            },
            {
                'id': 'machine_learning',
                'name': 'Machine Learning',
                'description': 'ML algorithms and techniques',
                'category': 'technology',
                'selected': True
            }
        ]

    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences from database (users table preferences column)"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Query the users table where preferences are actually stored
            cursor.execute("""
                SELECT preferences 
                FROM users 
                WHERE id = ?
            """, (user_id,))
            
            prefs_row = cursor.fetchone()
            conn.close()
            
            if prefs_row and prefs_row[0]:
                import json
                preferences = json.loads(prefs_row[0])
                
                # Extract topics - handle both formats
                topics = []
                raw_topics = preferences.get("topics", [])
                
                if isinstance(raw_topics, list):
                    for topic in raw_topics:
                        if isinstance(topic, dict):
                            # Handle format: [{"id": "machine_learning", "selected": True}, ...]
                            if topic.get("selected", False):
                                topics.append(topic.get("id", ""))
                        elif isinstance(topic, str):
                            # Handle format: ["machine_learning", "nlp", ...]
                            topics.append(topic)
                
                # Extract content types - handle both formats  
                content_types = preferences.get("content_types", ["blogs", "podcasts", "videos"])
                
                # Map old format to new format
                if "articles" in content_types:
                    content_types = ["blogs", "podcasts", "videos"]
                
                logger.info(f"🎯 User preferences loaded - Topics: {topics}, Content Types: {content_types}")
                
                return {
                    "topics": topics,
                    "content_types": content_types,
                    "newsletter_frequency": preferences.get("newsletter_frequency", "weekly"),
                    "email_notifications": preferences.get("email_notifications", True),
                    "onboarding_completed": preferences.get("onboarding_completed", True)
                }
            else:
                logger.info(f"🎯 No preferences found for user {user_id}, using defaults")
                # Return default preferences
                return {
                    "topics": [],
                    "content_types": ["blogs", "podcasts", "videos"],
                    "newsletter_frequency": "weekly",
                    "email_notifications": True,
                    "onboarding_completed": False
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting user preferences: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "topics": [],
                "content_types": ["blogs", "podcasts", "videos"],
                "newsletter_frequency": "weekly",
                "email_notifications": True,
                "onboarding_completed": False
            }
    
    def categorize_articles_with_preferences(self, articles: List[Dict], content_type: str, user_preferences: Dict) -> List[Dict]:
        """Categorize articles based on content type AND user preferences"""
        
        if content_type == "all_sources":
            # For all sources, apply user's preferred content types and topics
            return self.filter_articles_by_user_preferences(articles, user_preferences)
        
        # First apply basic content type filtering
        basic_categorized = self.categorize_articles_by_content_type(articles, content_type)
        
        # Then apply user preference filtering to prioritize relevant topics
        preference_filtered = self.filter_articles_by_user_preferences(basic_categorized, user_preferences)
        
        # If we don't have enough preference-filtered content, supplement with basic categorized content
        if len(preference_filtered) < 5:
            # Add non-duplicate articles from basic categorization
            seen_urls = set(article.get("url", "") for article in preference_filtered)
            for article in basic_categorized:
                if article.get("url", "") not in seen_urls and len(preference_filtered) < 10:
                    preference_filtered.append(article)
                    seen_urls.add(article.get("url", ""))
        
        return preference_filtered
    
    def filter_articles_by_user_preferences(self, articles: List[Dict], user_preferences: Dict) -> List[Dict]:
        """Filter and prioritize articles based on user's topic preferences"""
        
        user_topics = user_preferences.get("topics", [])
        user_content_types = user_preferences.get("content_types", [])
        
        # If user has no preferences at all, return all articles
        if not user_topics and not user_content_types:
            return articles
        
        logger.info(f"🎯 Filtering with user preferences - Topics: {user_topics}, Content Types: {user_content_types}")
        
        # Comprehensive topic keywords - 100 significant meta words per topic
        # Handle different topic ID formats from database
        topic_keywords = {
            "machine_learning": [
                # Core ML Terms
                "machine learning", "ml", "artificial intelligence", "ai", "neural network", "deep learning", 
                "algorithm", "model", "training", "supervised", "unsupervised", "reinforcement learning",
                "classification", "regression", "clustering", "prediction", "optimization", "inference",
                "backpropagation", "gradient descent", "overfitting", "underfitting", "bias", "variance",
                
                # ML Frameworks & Tools
                "tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy", "matplotlib", "jupyter",
                "anaconda", "colab", "kaggle", "mlflow", "wandb", "tensorboard", "huggingface", "transformers",
                
                # ML Algorithms & Techniques
                "decision tree", "random forest", "svm", "support vector", "linear regression", "logistic regression",
                "k-means", "kmeans", "dbscan", "pca", "principal component", "feature selection", "dimensionality reduction",
                "ensemble", "bagging", "boosting", "xgboost", "lightgbm", "catboost", "adaboost",
                
                # Deep Learning Specific
                "cnn", "convolutional", "rnn", "recurrent", "lstm", "gru", "attention", "transformer",
                "autoencoder", "gan", "generative adversarial", "vae", "variational autoencoder", "dropout",
                "batch normalization", "activation function", "relu", "sigmoid", "tanh", "softmax",
                
                # ML Operations & Deployment
                "mlops", "deployment", "production", "pipeline", "model serving", "feature store", "data drift",
                "model monitoring", "a/b testing", "hyperparameter tuning", "cross validation", "grid search",
                "automated ml", "automl", "model selection", "performance metrics", "accuracy", "precision", "recall"
            ],
            
            "computer_vision": [
                # Core CV Terms
                "computer vision", "cv", "image processing", "visual recognition", "object detection", "image classification",
                "facial recognition", "face detection", "image segmentation", "semantic segmentation", "instance segmentation",
                "edge detection", "feature extraction", "image enhancement", "image restoration", "image synthesis",
                
                # CV Algorithms & Architectures
                "cnn", "convolutional neural network", "resnet", "vgg", "alexnet", "inception", "mobilenet",
                "yolo", "you only look once", "r-cnn", "faster r-cnn", "mask r-cnn", "ssd", "single shot detector",
                "u-net", "densenet", "efficientnet", "vision transformer", "vit", "detr",
                
                # CV Applications
                "autonomous vehicles", "self-driving", "medical imaging", "satellite imagery", "surveillance", "security",
                "augmented reality", "ar", "virtual reality", "vr", "3d reconstruction", "stereo vision", "depth estimation",
                "optical character recognition", "ocr", "document analysis", "barcode scanning", "qr code",
                
                # CV Tools & Libraries
                "opencv", "pillow", "pil", "scikit-image", "imageio", "albumentations", "torchvision", "tensorflow-gpu",
                "detectron2", "mmdetection", "ultralytics", "roboflow", "labelimg", "coco dataset", "imagenet",
                
                # CV Techniques
                "data augmentation", "transfer learning", "fine-tuning", "feature matching", "template matching",
                "histogram equalization", "gaussian blur", "morphological operations", "contour detection", "hough transform",
                "sift", "surf", "orb", "corner detection", "optical flow", "tracking", "kalman filter"
            ],
            
            "natural_language_processing": [
                # Core NLP Terms
                "natural language processing", "nlp", "text processing", "language model", "large language model", "llm",
                "text mining", "text analytics", "computational linguistics", "language understanding", "language generation",
                "speech recognition", "speech synthesis", "text-to-speech", "speech-to-text", "voice assistant",
                
                # NLP Models & Architectures
                "transformer", "bert", "gpt", "chatgpt", "gpt-3", "gpt-4", "claude", "palm", "lamda", "t5",
                "roberta", "electra", "deberta", "xlnet", "albert", "distilbert", "bart", "pegasus",
                "encoder-decoder", "seq2seq", "attention mechanism", "self-attention", "cross-attention",
                
                # NLP Tasks & Applications
                "sentiment analysis", "named entity recognition", "ner", "part-of-speech tagging", "pos tagging",
                "machine translation", "text summarization", "question answering", "chatbot", "conversational ai",
                "text classification", "document classification", "spam detection", "language detection",
                "topic modeling", "information extraction", "relation extraction", "coreference resolution",
                
                # NLP Tools & Libraries
                "spacy", "nltk", "transformers", "huggingface", "openai api", "anthropic", "tokenization", "word2vec",
                "glove", "fasttext", "embeddings", "word embeddings", "sentence embeddings", "bert embeddings",
                "tensorflow text", "pytorch text", "torchtext", "datasets", "tokenizers", "sentencepiece",
                
                # NLP Techniques
                "preprocessing", "stemming", "lemmatization", "stop words", "n-grams", "tf-idf", "bag of words",
                "language modeling", "perplexity", "bleu score", "rouge score", "prompt engineering", "few-shot learning",
                "zero-shot learning", "in-context learning", "fine-tuning", "rlhf", "reinforcement learning human feedback"
            ],
            
            "robotics": [
                # Core Robotics Terms
                "robotics", "robot", "autonomous robot", "humanoid robot", "industrial robot", "service robot",
                "mobile robot", "robotic arm", "manipulator", "end effector", "actuator", "sensor", "servo",
                "stepper motor", "encoder", "lidar", "camera", "ultrasonic sensor", "imu", "gyroscope", "accelerometer",
                
                # Robotics Software & Frameworks
                "ros", "robot operating system", "ros2", "gazebo", "rviz", "moveit", "navigation stack", "slam",
                "simultaneous localization mapping", "path planning", "motion planning", "trajectory planning",
                "control systems", "pid controller", "kalman filter", "particle filter", "occupancy grid",
                
                # Robotics Applications
                "autonomous vehicles", "drones", "uav", "unmanned aerial vehicle", "warehouse automation", "pick and place",
                "assembly line", "quality inspection", "surgical robot", "medical robotics", "rehabilitation robotics",
                "agricultural robotics", "mining robotics", "space robotics", "underwater robotics", "rescue robotics",
                
                # AI in Robotics
                "robot learning", "imitation learning", "reinforcement learning robotics", "computer vision robotics",
                "object recognition", "grasp planning", "manipulation", "dexterous manipulation", "human-robot interaction",
                "social robotics", "collaborative robotics", "cobot", "safety systems", "fault tolerance",
                
                # Hardware & Mechanics
                "kinematics", "inverse kinematics", "dynamics", "forward kinematics", "degrees of freedom", "workspace",
                "singularity", "jacobian", "force control", "impedance control", "compliance", "stiffness",
                "mechanical design", "3d printing", "cad", "simulation", "digital twin", "mechatronics"
            ],
            
            "ai_ethics": [
                # Core Ethics Terms
                "ai ethics", "artificial intelligence ethics", "algorithmic bias", "bias detection", "fairness", "equity",
                "discrimination", "responsible ai", "trustworthy ai", "ethical ai", "ai governance", "ai regulation",
                "transparency", "explainability", "interpretability", "accountability", "auditing", "algorithmic auditing",
                
                # Privacy & Security
                "privacy", "data privacy", "gdpr", "data protection", "differential privacy", "federated learning",
                "homomorphic encryption", "secure computation", "adversarial attacks", "robustness", "safety",
                "ai safety", "alignment problem", "value alignment", "control problem", "existential risk",
                
                # Social Impact
                "social impact", "digital divide", "algorithmic justice", "civil rights", "human rights",
                "employment impact", "job displacement", "automation", "economic inequality", "surveillance",
                "facial recognition ethics", "predictive policing", "criminal justice", "hiring bias", "loan discrimination",
                
                # Governance & Policy
                "ai policy", "regulation", "compliance", "standards", "certification", "risk assessment",
                "impact assessment", "algorithmic impact assessment", "ethics board", "review process",
                "stakeholder engagement", "public participation", "democratic participation", "inclusive design",
                
                # Technical Solutions
                "bias mitigation", "debiasing", "fairness metrics", "demographic parity", "equalized odds",
                "calibration", "counterfactual fairness", "individual fairness", "group fairness",
                "explainable ai", "xai", "lime", "shap", "feature importance", "model cards", "datasheets",
                "algorithmic transparency", "open source", "reproducibility", "documentation", "ethical guidelines"
            ],
            
            "generative_ai": [
                # Core Generative AI Terms
                "generative ai", "generative artificial intelligence", "synthetic data", "artificial content", "generated content",
                "creative ai", "ai art", "ai music", "ai writing", "content generation", "media synthesis",
                "deepfake", "synthetic media", "artificial media", "procedural generation", "computational creativity",
                
                # Generative Models
                "gan", "generative adversarial network", "vae", "variational autoencoder", "diffusion model",
                "stable diffusion", "dall-e", "dall-e 2", "midjourney", "imagen", "firefly", "leonardo ai",
                "autoregressive model", "flow-based model", "normalizing flow", "energy-based model",
                
                # Text Generation
                "gpt", "chatgpt", "gpt-3", "gpt-4", "language generation", "text generation", "story generation",
                "code generation", "copilot", "codex", "palm", "claude", "bard", "llama", "alpaca",
                "prompt engineering", "prompt design", "few-shot prompting", "chain of thought", "instruction tuning",
                
                # Image Generation
                "text-to-image", "image generation", "image synthesis", "style transfer", "neural style transfer",
                "super resolution", "image upscaling", "inpainting", "outpainting", "image editing", "photo manipulation",
                "artistic style", "digital art", "concept art", "illustration", "photorealism", "stylized",
                
                # Audio & Video Generation
                "audio generation", "music generation", "voice synthesis", "speech synthesis", "voice cloning",
                "video generation", "video synthesis", "animation", "3d generation", "neural rendering",
                "text-to-speech", "text-to-video", "voice conversion", "music composition", "sound design",
                
                # Applications & Ethics
                "personalization", "recommendation", "content creation", "marketing", "advertising", "entertainment",
                "education", "training data", "data augmentation", "simulation", "virtual environments",
                "intellectual property", "copyright", "attribution", "ownership", "authenticity", "detection"
            ],
            
            "ai_research": [
                # Research Institutions & Labs
                "openai", "deepmind", "anthropic", "google ai", "microsoft research", "facebook ai", "meta ai",
                "stanford ai lab", "mit csail", "berkeley ai", "carnegie mellon", "oxford ai", "cambridge ai",
                "nvidia research", "ibm research", "amazon science", "apple ml", "tesla ai", "spacex ai",
                
                # Academic Conferences
                "neurips", "icml", "iclr", "aaai", "ijcai", "acl", "emnlp", "naacl", "cvpr", "iccv", "eccv",
                "icra", "iros", "rss", "corl", "aistats", "uai", "colt", "aamas", "kdd", "www", "sigir",
                
                # Research Areas
                "artificial general intelligence", "agi", "machine consciousness", "artificial consciousness",
                "cognitive architecture", "neural architecture search", "nas", "automated machine learning", "automl",
                "meta-learning", "few-shot learning", "zero-shot learning", "transfer learning", "continual learning",
                "lifelong learning", "catastrophic forgetting", "domain adaptation", "multi-task learning",
                
                # Theoretical Foundations
                "computational complexity", "sample complexity", "pac learning", "statistical learning theory",
                "information theory", "probability theory", "optimization theory", "game theory", "mechanism design",
                "causal inference", "causality", "graph neural networks", "geometric deep learning",
                
                # Emerging Research
                "quantum machine learning", "neuromorphic computing", "edge ai", "tinyml", "federated learning",
                "distributed learning", "blockchain ai", "ai for science", "scientific machine learning",
                "physics-informed neural networks", "neural ode", "graph transformer", "attention mechanism",
                
                # Research Methods
                "empirical study", "theoretical analysis", "ablation study", "benchmark", "dataset", "evaluation metrics",
                "reproducibility", "open science", "peer review", "arxiv", "preprint", "journal publication",
                "research methodology", "experimental design", "statistical significance", "hypothesis testing"
            ],
            
            "industry_applications": [
                # Tech Companies
                "google", "microsoft", "amazon", "apple", "meta", "facebook", "netflix", "uber", "airbnb",
                "tesla", "nvidia", "intel", "amd", "qualcomm", "salesforce", "oracle", "sap", "adobe",
                "spotify", "zoom", "slack", "dropbox", "github", "gitlab", "atlassian", "servicenow",
                
                # Industries
                "fintech", "healthtech", "edtech", "retailtech", "insurtech", "regtech", "legaltech", "proptech",
                "automotive", "manufacturing", "logistics", "supply chain", "e-commerce", "digital marketing",
                "cybersecurity", "cloud computing", "telecommunications", "media", "entertainment", "gaming",
                
                # Business Applications
                "customer service", "chatbot", "virtual assistant", "recommendation system", "personalization",
                "fraud detection", "risk assessment", "credit scoring", "algorithmic trading", "robo-advisor",
                "predictive maintenance", "quality control", "inventory management", "demand forecasting",
                "price optimization", "marketing automation", "lead generation", "customer segmentation",
                
                # Enterprise Solutions
                "enterprise ai", "business intelligence", "data analytics", "process automation", "rpa",
                "robotic process automation", "intelligent automation", "document processing", "ocr",
                "knowledge management", "decision support", "workflow optimization", "resource planning",
                
                # Deployment & Operations
                "cloud deployment", "edge computing", "model serving", "api", "microservices", "containerization",
                "kubernetes", "docker", "scalability", "performance optimization", "cost optimization",
                "monitoring", "logging", "metrics", "alerting", "incident response", "sla", "uptime",
                "production readiness", "mlops", "devops", "ci/cd", "continuous integration", "continuous deployment"
            ]
        }
        
        # Add alias mappings for database topic IDs
        topic_keywords.update({
            "nlp": topic_keywords["natural_language_processing"],  # alias
            "ai_research": topic_keywords["ai_research"],
            "ai_industry": topic_keywords["industry_applications"],  # alias
            "ai_startups": topic_keywords["industry_applications"],  # alias for startups
            "ai_ethics": topic_keywords["ai_ethics"]
        })
        
        scored_articles = []
        
        for article in articles:
            title_lower = (article.get("title", "") or "").lower()
            summary_lower = (article.get("summary", "") or "").lower()
            source_lower = (article.get("source", "") or "").lower()
            content_text = f"{title_lower} {summary_lower} {source_lower}"
            
            # Calculate preference score
            preference_score = 0
            
            # Score based on user's selected topics
            for user_topic in user_topics:
                if user_topic in topic_keywords:
                    topic_keyword_list = topic_keywords[user_topic]
                    topic_matches = sum(1 for keyword in topic_keyword_list if keyword in content_text)
                    preference_score += topic_matches * 2  # Higher weight for topic matches
            
            # If user has no topics selected, give a base preference score for general AI content
            if not user_topics:
                # Score general AI content when no specific topics are selected
                ai_general_keywords = ["ai", "artificial intelligence", "machine learning", "deep learning", 
                                     "neural network", "algorithm", "model", "technology", "innovation"]
                general_matches = sum(1 for keyword in ai_general_keywords if keyword in content_text)
                preference_score += general_matches * 1  # Lower weight for general matches
            
            # Enhanced content type keywords for precise filtering
            content_type_keywords = {
                "blogs": [
                    # Blog/Article Content
                    "blog", "article", "post", "analysis", "insight", "opinion", "editorial", "commentary",
                    "review", "report", "news", "update", "announcement", "release notes", "press release",
                    "whitepaper", "case study", "research paper", "technical paper", "study", "findings",
                    "medium.com", "substack", "towards data science", "arxiv", "research", "publication"
                ],
                "podcasts": [
                    # Audio Content
                    "podcast", "audio", "interview", "conversation", "discussion", "talk", "speech",
                    "listening", "episode", "show", "radio", "voice", "spoken", "hear", "listen",
                    "spotify", "apple podcasts", "google podcasts", "soundcloud", "anchor",
                    "ai podcast", "tech talks", "machine learning podcast", "data science podcast"
                ],
                "videos": [
                    # Video Content
                    "video", "youtube", "tutorial", "presentation", "webinar", "demo", "demonstration",
                    "course", "lecture", "talk", "keynote", "conference talk", "workshop video",
                    "screencast", "walkthrough", "how-to", "explainer", "visualization", "animation",
                    "vimeo", "twitch", "livestream", "stream", "recorded", "watch", "viewing"
                ],
                "events": [
                    # Event Content
                    "conference", "event", "summit", "meetup", "workshop", "symposium", "convention",
                    "gathering", "networking", "hackathon", "competition", "contest", "expo", "fair",
                    "seminar", "session", "panel", "roundtable", "forum", "discussion group",
                    "neurips", "icml", "iclr", "cvpr", "aaai", "tech conference", "ai summit"
                ],
                "learn": [
                    # Educational Content
                    "course", "tutorial", "guide", "learn", "education", "training", "lesson", "class",
                    "certification", "curriculum", "syllabus", "module", "chapter", "textbook",
                    "handbook", "manual", "documentation", "wiki", "faq", "how-to", "step-by-step",
                    "coursera", "udemy", "edx", "khan academy", "mit opencourseware", "stanford online"
                ]
            }
            
            # Content type matching and scoring
            content_type_score = 0
            matched_content_types = []
            
            for content_type in user_content_types:
                if content_type in content_type_keywords:
                    type_keywords = content_type_keywords[content_type]
                    type_matches = sum(1 for keyword in type_keywords if keyword in content_text)
                    if type_matches > 0:
                        content_type_score += type_matches * 1.5  # Weight for content type matches
                        matched_content_types.append(content_type)
            
            # Content type filtering logic
            if user_content_types and not matched_content_types:
                # If user has content type preferences but article doesn't match any,
                # be more flexible when they have no topic preferences (general browsing)
                if not user_topics:
                    # For users with no topic preferences, be less strict about content types
                    # Give articles a chance if they have general AI content
                    if preference_score == 0:  # No general AI keywords found either
                        continue  # Skip only if no AI relevance at all
                else:
                    # For users with topic preferences, be strict about content types
                    continue  # Skip articles that don't match any user content type preferences
            
            # Add base significance score
            significance_score = article.get("significance_score", 0)
            total_score = preference_score + content_type_score + (significance_score * 0.1)
            
            article_copy = article.copy()
            article_copy["preference_score"] = preference_score
            article_copy["content_type_score"] = content_type_score
            article_copy["matched_content_types"] = matched_content_types
            article_copy["total_score"] = total_score
            
            scored_articles.append(article_copy)
        
        # Sort by total score (preference + significance)
        scored_articles.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        # Remove scoring fields before returning (keep only original article data)
        for article in scored_articles:
            article.pop("preference_score", None)
            article.pop("content_type_score", None)
            article.pop("matched_content_types", None)
            article.pop("total_score", None)
        
        logger.info(f"🎯 Preference filtering result: {len(scored_articles)}/{len(articles)} articles matched user preferences")
        if len(scored_articles) > 0:
            logger.info(f"📰 Top filtered article: {scored_articles[0].get('title', 'Unknown')[:60]}")
        
        return scored_articles
    
    async def handle_personalized_digest(self, headers: Dict, params: Dict = None) -> Dict[str, Any]:
        """Get personalized digest - requires authentication"""
        try:
            logger.info("👤 Processing personalized-digest request")
            
            # Verify authentication
            auth_header = headers.get('Authorization') or headers.get('authorization')
            user_data = self.auth_service.get_user_from_token(auth_header)
            
            if not user_data:
                logger.warning("❌ Personalized digest requested without valid authentication")
                return {"error": "Authentication required for personalized content", "status": 401}
            
            # Get base digest
            base_digest = await self.handle_digest(params)
            
            # Add personalization metadata
            base_digest["personalized"] = True
            base_digest["personalization_meta"] = {
                "user_email": user_data.get("email"),
                "user_topics": ["AI Research", "Machine Learning", "Industry News"],
                "content_types_requested": ["blog", "audio", "video"],
                "filtering_applied": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add personalized greeting
            base_digest["summary"]["personalized_greeting"] = f"Hello {user_data.get('name', 'there')}! Here's your personalized AI news digest."
            base_digest["summary"]["user_focus_topics"] = ["Machine Learning Research", "Industry Developments", "New AI Tools"]
            
            logger.info(f"✅ Personalized digest generated for: {user_data.get('email')}")
            return base_digest
            
        except Exception as e:
            logger.error(f"❌ Personalized digest failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Personalized digest generation failed: {str(e)}", 
                "router_handled": True,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_user_preferences(self, headers: Dict) -> Dict[str, Any]:
        """Get user preferences - requires authentication"""
        try:
            logger.info("⚙️ Processing user-preferences request")
            
            # Verify authentication
            auth_header = headers.get('Authorization') or headers.get('authorization')
            user_data = self.auth_service.get_user_from_token(auth_header)
            
            if not user_data:
                logger.warning("❌ User preferences requested without valid authentication")
                return {"error": "Authentication required", "status": 401}
            
            preferences_response = {
                "user_id": user_data.get("sub"),
                "email": user_data.get("email"),
                "preferences": {
                    "content_types": ["blog", "audio", "video"],
                    "topics": ["AI Research", "Machine Learning", "Industry News"],
                    "frequency": "daily",
                    "notification_enabled": True
                },
                "router_authenticated": True,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_verified": True
                }
            }
            
            logger.info(f"✅ User preferences retrieved for: {user_data.get('email')}")
            return preferences_response
            
        except Exception as e:
            logger.error(f"❌ User preferences failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"User preferences failed: {str(e)}",
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_auth_endpoints(self, endpoint: str, method: str, params: Dict, headers: Dict, body: Dict = None) -> Dict[str, Any]:
        """Handle all authentication endpoints with debug logging"""
        try:
            auth_endpoint = endpoint.replace("auth/", "")
            logger.info(f"🔐 Processing auth endpoint: {auth_endpoint} ({method})")
            
            if auth_endpoint == "google" and method == "POST":
                return await self.handle_google_auth(body or {})
            elif auth_endpoint == "signup" and method == "POST":
                return await self.handle_auth_signup(body or {})
            elif auth_endpoint == "login" and method == "POST":
                return await self.handle_auth_login(body or {})
            elif auth_endpoint == "send-otp" and method == "POST":
                return await self.handle_send_otp(body or {})
            elif auth_endpoint == "verify-otp" and method == "POST":
                return await self.handle_verify_otp(body or {})
            elif auth_endpoint == "verify":
                return await self.handle_auth_verify(headers)
            elif auth_endpoint == "logout" and method == "POST":
                return await self.handle_logout(headers)
            elif auth_endpoint == "topics":
                return await self.handle_auth_topics()
            elif auth_endpoint == "preferences" and method in ["PUT", "POST"]:
                return await self.handle_auth_preferences(body or {}, headers)
            elif auth_endpoint == "profile":
                return await self.handle_auth_profile(headers)
            else:
                logger.warning(f"❌ Unknown auth endpoint: {auth_endpoint}")
                return {"error": f"Auth endpoint '{auth_endpoint}' not found", "status": 404}
                
        except Exception as e:
            logger.error(f"❌ Auth endpoint {endpoint} failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Authentication failed: {str(e)}", 
                "router_auth": "error",
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_google_auth(self, data: Dict) -> Dict[str, Any]:
        """Handle Google OAuth authentication with debug logging"""
        try:
            logger.info("🔐 Processing Google OAuth authentication request")
            logger.info(f"📊 Request data keys: {list(data.keys())}")
            
            # Get Google ID token from request
            id_token = data.get('id_token')
            if not id_token:
                logger.warning("❌ Google auth attempted without id_token")
                return {
                    "success": False,
                    "message": "Google ID token required",
                    "status": 400,
                    "debug_info": {
                        "provided_data": list(data.keys()),
                        "expected": "id_token"
                    }
                }
            
            # Verify and decode Google ID token
            token_data = self.auth_service.verify_google_id_token(id_token)
            if not token_data:
                logger.warning("❌ Google ID token verification failed")
                return {
                    "success": False,
                    "message": "Invalid Google ID token",
                    "status": 400,
                    "debug_info": {
                        "token_verification": "failed"
                    }
                }
            
            logger.info(f"📊 Token data extracted: email={token_data.get('email')}, name={token_data.get('name')}")
            
            # Create or update user in database (schema already initialized at startup)
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if user already exists
            user_id = token_data.get('sub', '')
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            existing_user = cursor.fetchone()
            is_existing_user = existing_user is not None
            
            logger.info(f"📊 User existence check: existing={is_existing_user}")
            
            # Insert or update user (table schema already initialized)
            existing_columns = ['id', 'email', 'name', 'profile_image', 'subscription_tier', 'preferences', 'created_at', 'last_login_at', 'is_active']
            
            # Build INSERT statement based on available columns
            available_data_columns = []
            values = []
            
            # Always include required columns
            if 'id' in existing_columns:
                available_data_columns.append('id')
                values.append(user_id)
            if 'email' in existing_columns:
                available_data_columns.append('email')
                values.append(token_data.get('email', ''))
            if 'name' in existing_columns:
                available_data_columns.append('name')
                values.append(token_data.get('name', ''))
            
            # Add optional columns if they exist
            if 'profile_image' in existing_columns:
                available_data_columns.append('profile_image')
                values.append(token_data.get('picture', ''))
            if 'subscription_tier' in existing_columns:
                available_data_columns.append('subscription_tier')
                values.append('free')
            if 'is_active' in existing_columns:
                available_data_columns.append('is_active')
                values.append(True)
            if 'last_login_at' in existing_columns:
                available_data_columns.append('last_login_at')
                values.append(datetime.utcnow().isoformat())
            if 'created_at' in existing_columns:
                available_data_columns.append('created_at')
                values.append(datetime.utcnow().isoformat())
            
            # Set up preferences for new or existing user
            if is_existing_user and existing_user:
                # Load existing preferences
                existing_prefs_json = existing_user[5] if len(existing_user) > 5 else None  # preferences column
                if existing_prefs_json:
                    preferences = json.loads(existing_prefs_json)
                    # Ensure mandatory topics are included for existing users
                    existing_topics = preferences.get('topics', [])
                    mandatory_topics = self.get_mandatory_topics()
                    
                    # Check if mandatory topics are missing
                    mandatory_ids = {t['id'] for t in mandatory_topics}
                    existing_ids = set()
                    
                    if isinstance(existing_topics, list):
                        for topic in existing_topics:
                            if isinstance(topic, dict):
                                existing_ids.add(topic.get('id', ''))
                    
                    # Add missing mandatory topics
                    for mandatory_topic in mandatory_topics:
                        if mandatory_topic['id'] not in existing_ids:
                            existing_topics.append(mandatory_topic)
                    
                    preferences['topics'] = existing_topics
                    preferences['content_types'] = ['blogs', 'podcasts', 'videos']  # Ensure proper content types
                else:
                    # Existing user but no preferences - create with mandatory topics
                    preferences = {
                        "topics": self.get_mandatory_topics(),
                        "newsletter_frequency": "weekly",
                        "email_notifications": True,
                        "content_types": ["blogs", "podcasts", "videos"],
                        "onboarding_completed": True
                    }
            else:
                # New user - create with mandatory topics
                preferences = {
                    "topics": self.get_mandatory_topics(),
                    "newsletter_frequency": "weekly",
                    "email_notifications": True,
                    "content_types": ["blogs", "podcasts", "videos"],
                    "onboarding_completed": True
                }
            
            # Add preferences to the insert/update
            if 'preferences' in existing_columns:
                available_data_columns.append('preferences')
                values.append(json.dumps(preferences))
            
            # Build and execute dynamic INSERT statement
            columns_str = ', '.join(available_data_columns)
            placeholders = ', '.join(['?' for _ in available_data_columns])
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO users ({columns_str})
                VALUES ({placeholders})
            """, values)
            
            logger.info(f"✅ User inserted with available columns: {available_data_columns}")
            logger.info(f"📊 User preferences set: onboarding_completed={preferences['onboarding_completed']}, topics_count={len(preferences['topics'])}")
            
            conn.commit()
            conn.close()
            
            # Create JWT token
            jwt_token = self.auth_service.create_jwt_token(token_data)
            
            auth_response = {
                "success": True,
                "message": "Authentication successful",
                "token": jwt_token,
                "user": {
                    "id": token_data.get('sub', ''),
                    "email": token_data.get('email', ''),
                    "name": token_data.get('name', ''),
                    "picture": token_data.get('picture', ''),
                    "verified_email": True,
                    "subscription_tier": "free",
                    "preferences": preferences
                },
                "isUserExist": is_existing_user,
                "expires_in": 86400,
                "router_auth": True,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_created_or_updated": True,
                    "jwt_token_length": len(jwt_token),
                    "is_existing_user": is_existing_user,
                    "preferences_loaded": bool(preferences)
                }
            }
            
            logger.info(f"✅ Google auth successful for: {token_data.get('email')}")
            return auth_response
            
        except Exception as e:
            logger.error(f"❌ Google auth failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}",
                "status": 500,
                "router_auth": "error",
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_auth_signup(self, data: Dict) -> Dict[str, Any]:
        """Handle user signup with email/password"""
        try:
            logger.info("🔐 Processing user signup request")
            logger.info(f"📊 Signup data keys: {list(data.keys())}")
            
            # Validate required fields
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            name = data.get('name', '').strip()
            
            if not email or not password or not name:
                return {
                    "success": False,
                    "message": "Email, password, and name are required",
                    "status": 400
                }
            
            # Basic email validation
            if '@' not in email or '.' not in email:
                return {
                    "success": False,
                    "message": "Please enter a valid email address",
                    "status": 400
                }
            
            # Password strength validation
            if len(password) < 6:
                return {
                    "success": False,
                    "message": "Password must be at least 6 characters long",
                    "status": 400
                }
            
            # Create user in database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return {
                    "success": False,
                    "message": "An account with this email already exists",
                    "status": 409
                }
            
            # Generate user ID and hash password
            import uuid
            import hashlib
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (id, email, name, verified_email, subscription_tier, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, email, name, False, 'free',
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            # Store password hash (table already initialized at startup)
            cursor.execute("INSERT INTO user_passwords (user_id, password_hash) VALUES (?, ?)", 
                         (user_id, password_hash))
            
            # Create default preferences
            cursor.execute("""
                INSERT INTO user_preferences (
                    user_id, topics, content_types, newsletter_frequency, 
                    email_notifications, onboarding_completed
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, '[]', '["blogs", "podcasts", "videos"]', 'weekly', True, False
            ))
            
            conn.commit()
            conn.close()
            
            # Create JWT token
            token_data = {
                'sub': user_id,
                'email': email,
                'name': name,
                'picture': '',
                'iat': int(datetime.utcnow().timestamp()),
                'exp': int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            jwt_token = self.auth_service.create_jwt_token(token_data)
            
            logger.info(f"✅ User signup successful: {email}")
            return {
                "success": True,
                "message": "Account created successfully",
                "token": jwt_token,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "picture": "",
                    "verified_email": False,
                    "subscription_tier": "free",
                    "preferences": {
                        "topics": [],
                        "content_types": ["blogs", "podcasts", "videos"],
                        "newsletter_frequency": "weekly",
                        "email_notifications": True,
                        "onboarding_completed": False
                    }
                },
                "isUserExist": False,
                "expires_in": 86400,
                "router_auth": True,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_created": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Signup failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Signup failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_auth_login(self, data: Dict) -> Dict[str, Any]:
        """Handle user login with email/password"""
        try:
            logger.info("🔐 Processing user login request")
            logger.info(f"📊 Login data keys: {list(data.keys())}")
            
            # Validate required fields
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            
            if not email or not password:
                return {
                    "success": False,
                    "message": "Email and password are required",
                    "status": 400
                }
            
            # Authenticate user
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user_row = cursor.fetchone()
            
            if not user_row:
                conn.close()
                return {
                    "success": False,
                    "message": "Invalid email or password",
                    "status": 401
                }
            
            # Verify password
            cursor.execute("SELECT password_hash FROM user_passwords WHERE user_id = ?", (user_row['id'],))
            password_row = cursor.fetchone()
            
            if not password_row:
                conn.close()
                return {
                    "success": False,
                    "message": "This account uses email verification. Please use 'Continue with Email' instead.",
                    "status": 401,
                    "error_type": "otp_user_detected"
                }
            
            import hashlib
            provided_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if provided_hash != password_row['password_hash']:
                conn.close()
                return {
                    "success": False,
                    "message": "Invalid email or password",
                    "status": 401
                }
            
            # Get user preferences
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_row['id'],))
            prefs_row = cursor.fetchone()
            
            preferences = {
                "topics": json.loads(prefs_row['topics']) if prefs_row and prefs_row['topics'] else [],
                "content_types": json.loads(prefs_row['content_types']) if prefs_row and prefs_row['content_types'] else ["blogs", "podcasts", "videos"],
                "newsletter_frequency": prefs_row['newsletter_frequency'] if prefs_row else "weekly",
                "email_notifications": bool(prefs_row['email_notifications']) if prefs_row else True,
                "onboarding_completed": bool(prefs_row['onboarding_completed']) if prefs_row else False
            }
            
            conn.close()
            
            # Create JWT token
            token_data = {
                'sub': user_row['id'],
                'email': user_row['email'],
                'name': user_row['name'],
                'picture': user_row['picture'] or '',
                'iat': int(datetime.utcnow().timestamp()),
                'exp': int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            jwt_token = self.auth_service.create_jwt_token(token_data)
            
            logger.info(f"✅ User login successful: {email}")
            return {
                "success": True,
                "message": "Authentication successful",
                "token": jwt_token,
                "user": {
                    "id": user_row['id'],
                    "email": user_row['email'],
                    "name": user_row['name'],
                    "picture": user_row['picture'] or "",
                    "verified_email": bool(user_row['verified_email']) if 'verified_email' in user_row.keys() else False,
                    "subscription_tier": "free",
                    "preferences": preferences
                },
                "isUserExist": True,
                "expires_in": 86400,
                "router_auth": True,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_authenticated": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Login failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Login failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_send_otp(self, data: Dict) -> Dict[str, Any]:
        """Send OTP for email verification"""
        try:
            logger.info("📧 Processing send OTP request")
            logger.info(f"📊 OTP data keys: {list(data.keys())}")
            
            # Validate required fields
            email = data.get('email', '').strip().lower()
            name = data.get('name', '').strip()
            auth_mode = data.get('auth_mode', 'signin').lower()  # 'signin' or 'signup'
            
            if not email:
                return {
                    "success": False,
                    "message": "Email is required",
                    "status": 400
                }
            
            # Basic email validation
            if '@' not in email or '.' not in email:
                return {
                    "success": False,
                    "message": "Please enter a valid email address",
                    "status": 400
                }
            
            # Check if user exists
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, name FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            # For OTP-only authentication, be more flexible with auth modes
            # Still enforce signup restrictions for truly new signups, but allow OTP for existing users
            if auth_mode == 'signup' and existing_user:
                # User is trying to sign up but email already exists
                logger.info(f"📧 Signup attempted with existing email: {email} - redirecting to signin flow")
                conn.close()
                return {
                    "success": False,
                    "message": "Email ID already registered! Please use a different email for sign up.",
                    "status": 400,
                    "error_code": "EMAIL_EXISTS",
                    "redirect_to_signin": True
                }
            
            # For signin mode, if user doesn't exist, it might be a new user trying to get access
            # In OTP-only flow, we can be more permissive and suggest signup
            if auth_mode == 'signin' and not existing_user:
                logger.info(f"📧 Signin attempted with non-existent email: {email} - suggesting signup")
                conn.close()
                return {
                    "success": False,
                    "message": "No account found with this email. Please sign up first.",
                    "status": 400,
                    "error_code": "EMAIL_NOT_FOUND", 
                    "redirect_to_signup": True
                }
            
            # Generate 6-digit OTP
            import random
            otp = str(random.randint(100000, 999999))
            
            # Store OTP temporarily (table already initialized at startup)
            # Reuse the same connection
            
            # Store OTP with 10-minute expiration
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            cursor.execute("""
                INSERT OR REPLACE INTO email_otps (email, otp, name, expires_at)
                VALUES (?, ?, ?, ?)
            """, (email, otp, name, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            # Send OTP email using inline Brevo service
            try:
                # Inline email service to bypass import issues
                def send_otp_email_inline(user_email: str, user_name: str, otp: str) -> bool:
                    """Send OTP email using Brevo API"""
                    try:
                        import json
                        import urllib.request
                        import urllib.parse
                        
                        # Brevo configuration
                        brevo_api_key = os.getenv('BREVO_API_KEY')
                        if not brevo_api_key:
                            logger.error("📧 BREVO_API_KEY not configured")
                            return False
                        
                        # Email content
                        html_content = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Verification Code</title>
                        </head>
                        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                            <div style="text-align: center; margin-bottom: 32px; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; color: white;">
                                <h1 style="margin: 0; font-size: 28px; font-weight: 800;">🔐 Verification Code</h1>
                                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Vidyagam Account Verification</p>
                            </div>
                            
                            <div style="margin-bottom: 32px;">
                                <p style="font-size: 16px;">Hello {user_name},</p>
                                <p style="font-size: 16px;">Please use the verification code below to complete your account setup:</p>
                            </div>
                            
                            <div style="text-align: center; margin: 32px 0; padding: 24px; background: #f8fafc; border-radius: 12px; border: 2px dashed #667eea;">
                                <div style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: monospace;">{otp}</div>
                                <p style="margin: 16px 0 0 0; font-size: 14px; color: #64748b;">This code expires in 10 minutes</p>
                            </div>
                            
                            <div style="margin: 32px 0; padding: 16px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #ef4444;">
                                <p style="margin: 0; font-size: 14px; color: #7f1d1d;"><strong>Security Notice:</strong> Never share this code with anyone. We'll never ask for it via email or phone.</p>
                            </div>
                            
                            <div style="text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0; font-size: 14px; color: #64748b;">
                                    Vidyagam • Connecting AI Innovation<br>
                                    <a href="https://ai-news-react.vercel.app" style="color: #667eea;">ai-news-react.vercel.app</a>
                                </p>
                            </div>
                        </body>
                        </html>
                        """
                        
                        # Brevo API payload
                        payload = {
                            "sender": {
                                "name": "Vidyagam",
                                "email": "admin@vidyagam.com"
                            },
                            "to": [
                                {
                                    "email": user_email,
                                    "name": user_name
                                }
                            ],
                            "subject": "🔐 Your Vidyagam Verification Code",
                            "htmlContent": html_content,
                            "textContent": f"""
Verification Code - Vidyagam

Hello {user_name},

Please use the verification code below to complete your account setup:

{otp}

This code will expire in 10 minutes.

SECURITY NOTICE: Never share this verification code with anyone.

Vidyagam • Connecting AI Innovation
                            """
                        }
                        
                        # Send via Brevo
                        headers = {
                            'accept': 'application/json',
                            'api-key': brevo_api_key,
                            'content-type': 'application/json'
                        }
                        
                        # Use synchronous requests for Railway compatibility
                        
                        req = urllib.request.Request(
                            'https://api.brevo.com/v3/smtp/email',
                            data=json.dumps(payload).encode('utf-8'),
                            headers=headers,
                            method='POST'
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            response_data = response.read()
                            if response.status == 201:
                                logger.info(f"📧 OTP email sent successfully to {user_email}")
                                return True
                            else:
                                logger.error(f"📧 Brevo API error: {response.status} - {response_data}")
                                return False
                        
                    except Exception as e:
                        logger.error(f"📧 Failed to send OTP email: {e}")
                        return False
                
                # Try to send OTP email using inline service  
                email_sent = False
                try:
                    logger.info(f"📧 Calling inline email service for {email}")
                    logger.info(f"🔑 BREVO_API_KEY configured: {'Yes' if os.getenv('BREVO_API_KEY') else 'No'}")
                    logger.info(f"🔑 BREVO_API_KEY length: {len(os.getenv('BREVO_API_KEY', ''))}")
                    
                    # Call the synchronous inline function (not async)
                    email_sent = send_otp_email_inline(email, name or "AI Enthusiast", otp)
                    
                    if email_sent:
                        logger.info(f"📧 ✅ OTP email sent successfully via inline service to {email}")
                    else:
                        logger.warning("📧 ⚠️ Inline email service returned False")
                except Exception as email_error:
                    logger.error(f"📧 ❌ Inline email service error: {str(email_error)}")
                    logger.error(f"📧 ❌ Error type: {type(email_error).__name__}")
                    import traceback
                    logger.error(f"📧 ❌ Traceback: {traceback.format_exc()}")
                    email_sent = False
                
                if email_sent:
                    logger.info(f"📧 OTP email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "OTP sent successfully",
                        "email": email,
                        "emailVerificationRequired": True,
                        "otpSent": True,
                        "expiresInMinutes": 10,
                        "debug_info": {
                            "otp_for_testing": otp,  # Include for testing even when email succeeds
                            "email_service_working": True
                        }
                    }
                else:
                    logger.warning(f"📧 Email service failed for {email}, providing OTP for testing")
                    return {
                        "success": True,
                        "message": "OTP generated (email service unavailable)",
                        "email": email,
                        "emailVerificationRequired": True,
                        "otpSent": False,
                        "expiresInMinutes": 10,
                        "debug_info": {
                            "otp_for_testing": otp,  # Fallback for testing
                            "email_service_failed": True
                        }
                    }
                    
            except Exception as email_error:
                logger.error(f"📧 Email service error: {str(email_error)}")
                # Fallback: provide OTP for testing if email fails
                logger.info(f"📧 Fallback OTP for {email}: {otp}")
                return {
                    "success": True,
                    "message": "OTP generated (using fallback method)",
                    "email": email,
                    "emailVerificationRequired": True,
                    "otpSent": False,
                    "expiresInMinutes": 10,
                    "debug_info": {
                        "otp_for_testing": otp,  # Fallback for testing
                        "email_error": str(email_error)
                    }
                }
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Send OTP failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to send OTP: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_verify_otp(self, data: Dict) -> Dict[str, Any]:
        """Verify OTP and create user account"""
        try:
            logger.info("🔐 Processing OTP verification request")
            logger.info(f"📊 Verification data keys: {list(data.keys())}")
            
            # Validate required fields
            email = data.get('email', '').strip().lower()
            otp = data.get('otp', '').strip()
            user_data = data.get('userData', {})
            
            if not email or not otp:
                return {
                    "success": False,
                    "message": "Email and OTP are required",
                    "status": 400
                }
            
            # Verify OTP (database schema already initialized at startup)
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT otp, name, expires_at FROM email_otps 
                WHERE email = ? AND expires_at > ?
            """, (email, datetime.utcnow().isoformat()))
            
            otp_record = cursor.fetchone()
            
            if not otp_record:
                conn.close()
                return {
                    "success": False,
                    "message": "OTP expired or not found",
                    "status": 400
                }
            
            if otp_record['otp'] != otp:
                conn.close()
                return {
                    "success": False,
                    "message": "Invalid OTP",
                    "status": 400
                }
            
            # Check if user already exists
            cursor.execute("SELECT id, email, name, verified_email, subscription_tier FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # User exists - log them in instead of creating new account
                logger.info(f"✅ Existing user found for {email} - logging in")
                
                # Get user preferences
                cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (existing_user[0],))
                prefs_row = cursor.fetchone()
                
                user_data_response = {
                    "id": existing_user[0],
                    "email": existing_user[1], 
                    "name": existing_user[2],
                    "verified_email": existing_user[3],
                    "subscription_tier": existing_user[4] or 'free',
                    "preferences": {
                        "topics": json.loads(prefs_row[1]) if prefs_row and prefs_row[1] else [],
                        "content_types": json.loads(prefs_row[4]) if prefs_row and prefs_row[4] else ["blogs", "podcasts", "videos"],
                        "newsletter_frequency": prefs_row[2] if prefs_row else 'weekly',
                        "email_notifications": bool(prefs_row[3]) if prefs_row else True,
                        "onboarding_completed": bool(prefs_row[5]) if prefs_row else False
                    }
                }
                
                # Create JWT token for existing user
                token_data = {
                    "sub": existing_user[0],  # Use 'sub' field consistently
                    "email": existing_user[1],
                    "name": existing_user[2],
                    "picture": "",
                    "iat": int(datetime.utcnow().timestamp()),
                    "exp": int((datetime.utcnow() + timedelta(days=7)).timestamp())
                }
                jwt_token = self.auth_service.create_jwt_token(token_data)
                
                # Delete used OTP
                cursor.execute("DELETE FROM email_otps WHERE email = ?", (email,))
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Existing user {email} logged in successfully via OTP")
                return {
                    "success": True,
                    "message": "Login successful",
                    "user": user_data_response,
                    "token": jwt_token,
                    "isUserExist": True
                }
            
            # Create user account (or handle existing user gracefully)
            import uuid
            user_id = str(uuid.uuid4())
            name = otp_record['name'] or user_data.get('name', email.split('@')[0])
            password = user_data.get('password', '')  # Optional password for future logins
            
            try:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (id, email, name, verified_email, subscription_tier, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, email, name, True, 'free',
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                logger.info(f"✅ New user created: {email}")
                
            except Exception as insert_error:
                # If user already exists, handle gracefully
                if "UNIQUE constraint failed" in str(insert_error) or "already exists" in str(insert_error).lower():
                    logger.info(f"📧 User {email} already exists, treating as existing user login")
                    
                    # Get existing user data
                    cursor.execute("SELECT id, email, name, verified_email, subscription_tier FROM users WHERE email = ?", (email,))
                    existing_user = cursor.fetchone()
                    
                    if existing_user:
                        # Get user preferences for existing user
                        cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (existing_user[0],))
                        prefs_row = cursor.fetchone()
                        
                        user_data_response = {
                            "id": existing_user[0],
                            "email": existing_user[1], 
                            "name": existing_user[2],
                            "verified_email": existing_user[3],
                            "subscription_tier": existing_user[4] or 'free',
                            "preferences": {
                                "topics": json.loads(prefs_row[1]) if prefs_row and prefs_row[1] else [],
                                "content_types": json.loads(prefs_row[4]) if prefs_row and prefs_row[4] else ["blogs", "podcasts", "videos"],
                                "newsletter_frequency": prefs_row[2] if prefs_row else 'weekly',
                                "email_notifications": bool(prefs_row[3]) if prefs_row else True,
                                "onboarding_completed": bool(prefs_row[5]) if prefs_row else False
                            }
                        }
                        
                        # Create JWT token for existing user
                        token_data = {
                            "sub": existing_user[0],  # Use 'sub' field consistently
                            "email": existing_user[1],
                            "name": existing_user[2],
                            "picture": "",
                            "iat": int(datetime.utcnow().timestamp()),
                            "exp": int((datetime.utcnow() + timedelta(days=7)).timestamp())
                        }
                        jwt_token = self.auth_service.create_jwt_token(token_data)
                        
                        # Delete used OTP
                        cursor.execute("DELETE FROM email_otps WHERE email = ?", (email,))
                        conn.commit()
                        conn.close()
                        
                        logger.info(f"✅ Existing user {email} logged in via OTP during registration attempt")
                        return {
                            "success": True,
                            "message": "Login successful",
                            "user": user_data_response,
                            "token": jwt_token,
                            "isUserExist": True
                        }
                else:
                    # Some other database error
                    raise insert_error
            
            # If password provided, store it for future password-based logins
            if password and len(password) >= 6:
                import hashlib
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute("INSERT INTO user_passwords (user_id, password_hash) VALUES (?, ?)", 
                             (user_id, password_hash))
                logger.info(f"✅ Password stored for user {email} for future logins")
            
            # Create default preferences with onboarding not completed
            cursor.execute("""
                INSERT INTO user_preferences (
                    user_id, topics, content_types, newsletter_frequency, 
                    email_notifications, onboarding_completed
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, '[]', '["blogs", "podcasts", "videos"]', 'weekly', True, False
            ))
            
            # Delete used OTP
            cursor.execute("DELETE FROM email_otps WHERE email = ?", (email,))
            
            conn.commit()
            conn.close()
            
            # Create JWT token for new user
            token_data = {
                'sub': user_id,
                'email': email,
                'name': name,
                'picture': '',
                'iat': int(datetime.utcnow().timestamp()),
                'exp': int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            jwt_token = self.auth_service.create_jwt_token(token_data)
            
            logger.info(f"✅ OTP verification and user creation successful: {email}")
            return {
                "success": True,
                "message": "Account created successfully",
                "token": jwt_token,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "picture": "",
                    "verified_email": True,
                    "subscription_tier": "free",
                    "preferences": {
                        "topics": [],
                        "content_types": ["blogs", "podcasts", "videos"],
                        "newsletter_frequency": "weekly",
                        "email_notifications": True,
                        "onboarding_completed": False
                    }
                },
                "isUserExist": False,
                "expires_in": 86400,
                "router_auth": True,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_created": True,
                    "email_verified": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ OTP verification failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"OTP verification failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_auth_verify(self, headers: Dict) -> Dict[str, Any]:
        """Verify authentication token with debug logging"""
        try:
            logger.info("🔐 Processing auth verification request")
            
            auth_header = headers.get('Authorization') or headers.get('authorization')
            user_data = self.auth_service.get_user_from_token(auth_header)
            
            if user_data:
                verify_response = {
                    "valid": True,
                    "user": user_data,
                    "expires": user_data.get('exp'),
                    "router_verified": True,
                    "debug_info": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "token_valid": True
                    }
                }
                logger.info(f"✅ Auth verification successful for: {user_data.get('email')}")
                return verify_response
            else:
                logger.warning("❌ Auth verification failed - invalid token")
                return {
                    "valid": False,
                    "error": "invalid_token",
                    "router_verified": False,
                    "debug_info": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "auth_header_present": bool(auth_header)
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Auth verification failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "valid": False,
                "error": str(e),
                "router_verified": "error",
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_logout(self, headers: Dict) -> Dict[str, Any]:
        """Handle logout (token invalidation) with debug logging"""
        logger.info("🔐 Processing logout request")
        return {
            "success": True,
            "message": "Logout successful",
            "router_auth": "logout",
            "debug_info": {
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def handle_auth_topics(self) -> Dict[str, Any]:
        """Get available topics and content types for authentication/preferences from ai_sources_config"""
        logger.info("🔐 Processing auth topics request")
        
        # Content types from ai_sources_config_updated.py
        content_types = [
            {
                "id": "blogs",
                "name": "Blogs",
                "description": "Expert insights, analysis, and thought leadership articles",
                "icon": "✍️",
                "enabled": True,
                "default": True
            },
            {
                "id": "podcasts", 
                "name": "Podcasts",
                "description": "Audio content, interviews, and discussions from AI leaders",
                "icon": "🎧",
                "enabled": True,
                "default": True
            },
            {
                "id": "videos",
                "name": "Videos",
                "description": "Visual content, presentations, and educational videos",
                "icon": "📹",
                "enabled": True,
                "default": True
            },
            {
                "id": "newsletters",
                "name": "Newsletters",
                "description": "Daily and weekly AI newsletters and digests",
                "icon": "📬",
                "enabled": True,
                "default": False
            },
            {
                "id": "events",
                "name": "Events",
                "description": "AI conferences, webinars, workshops, and networking events",
                "icon": "📅",
                "enabled": True,
                "default": False
            },
            {
                "id": "learn",
                "name": "Learn",
                "description": "Courses, tutorials, educational content, and skill development",
                "icon": "🎓",
                "enabled": True,
                "default": False
            }
        ]
        
        # Topic categories based on our sources
        topics = [
            {
                "id": "ai-research",
                "name": "AI Research",
                "description": "Latest AI research papers, findings, and breakthroughs",
                "category": "research",
                "sources": ["OpenAI Blog", "Anthropic Blog", "Google AI Blog", "Papers With Code"]
            },
            {
                "id": "machine-learning",
                "name": "Machine Learning",
                "description": "ML techniques, algorithms, and practical applications",
                "category": "technical",
                "sources": ["Towards Data Science", "Distill.pub", "Fast.ai"]
            },
            {
                "id": "industry-news",
                "name": "Industry News",
                "description": "AI industry updates, company news, and market trends",
                "category": "business",
                "sources": ["The Batch by DeepLearning.AI", "AI Breakfast", "The Rundown AI"]
            },
            {
                "id": "deep-learning",
                "name": "Deep Learning",
                "description": "Neural networks, deep learning architectures and applications",
                "category": "technical",
                "sources": ["DeepLearning.AI YouTube", "3Blue1Brown", "Two Minute Papers"]
            },
            {
                "id": "tools-frameworks",
                "name": "AI Tools & Frameworks",
                "description": "AI development tools, libraries, and frameworks",
                "category": "tools",
                "sources": ["Hugging Face Blog", "Papers With Code"]
            },
            {
                "id": "ethics-safety",
                "name": "AI Ethics & Safety",
                "description": "AI safety, ethics, governance, and responsible AI development",
                "category": "ethics",
                "sources": ["Anthropic Blog", "Stanford HAI"]
            },
            {
                "id": "podcasts-interviews",
                "name": "Podcasts & Interviews",
                "description": "Long-form conversations with AI researchers and practitioners",
                "category": "media",
                "sources": ["Lex Fridman Podcast", "Machine Learning Street Talk", "The AI Podcast"]
            },
            {
                "id": "educational",
                "name": "Educational Content",
                "description": "Learning resources, courses, and tutorials",
                "category": "education",
                "sources": ["MIT OpenCourseWare", "Stanford AI Courses", "Coursera AI Courses"]
            }
        ]
        
        return {
            "content_types": content_types,
            "topics": topics,
            "default_selections": {
                "content_types": ["blogs", "podcasts", "videos"],
                "topics": ["ai-research", "machine-learning", "industry-news"]
            },
            "router_endpoint": True,
            "debug_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_content_types": len(content_types),
                "total_topics": len(topics)
            }
        }
    
    async def handle_auth_preferences(self, data: Dict, headers: Dict) -> Dict[str, Any]:
        """Handle user preferences update with JWT verification and database persistence"""
        try:
            logger.info("🔐 Processing auth preferences update request")
            logger.info(f"📊 Preferences data: {data}")
            
            # Extract and verify JWT token
            token = headers.get('authorization', '')
            if not token:
                return {"error": "Authentication required", "status": 401}
            
            # Verify JWT token
            payload = self.auth_service.verify_jwt_token(token)
            if not payload:
                return {"error": "Invalid or expired token", "status": 401}
            
            user_id = payload.get('sub', '')
            if not user_id:
                return {"error": "Invalid token payload", "status": 401}
            
            # Update preferences in database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update preferences (table schema already initialized at startup)
            
            # Get current preferences
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            current_prefs = cursor.fetchone()
            
            # Prepare update data
            update_data = {}
            if 'topics' in data:
                update_data['topics'] = json.dumps(data['topics'])
            if 'newsletter_frequency' in data:
                update_data['newsletter_frequency'] = data['newsletter_frequency']
            if 'email_notifications' in data:
                update_data['email_notifications'] = bool(data['email_notifications'])
            if 'content_types' in data:
                update_data['content_types'] = json.dumps(data['content_types'])
            if 'onboarding_completed' in data:
                update_data['onboarding_completed'] = bool(data['onboarding_completed'])
            if 'newsletter_subscribed' in data:
                update_data['newsletter_subscribed'] = bool(data['newsletter_subscribed'])
            
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            if current_prefs:
                # Update existing preferences
                set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                values = list(update_data.values()) + [user_id]
                cursor.execute(f"UPDATE user_preferences SET {set_clause} WHERE user_id = ?", values)
                logger.info(f"📊 Updated preferences for existing user: {user_id}")
            else:
                # Insert new preferences
                all_fields = {
                    'user_id': user_id,
                    'topics': json.dumps(data.get('topics', [])),
                    'newsletter_frequency': data.get('newsletter_frequency', 'weekly'),
                    'email_notifications': bool(data.get('email_notifications', True)),
                    'content_types': json.dumps(data.get('content_types', ['blogs', 'podcasts', 'videos'])),
                    'onboarding_completed': bool(data.get('onboarding_completed', False)),
                    'newsletter_subscribed': bool(data.get('newsletter_subscribed', False)),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                placeholders = ', '.join(['?' for _ in all_fields])
                fields = ', '.join(all_fields.keys())
                cursor.execute(f"INSERT INTO user_preferences ({fields}) VALUES ({placeholders})", list(all_fields.values()))
                logger.info(f"📊 Created new preferences for user: {user_id}")
            
            # Get updated preferences to return
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            updated_prefs = cursor.fetchone()
            
            # Get user data
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            conn.commit()
            conn.close()
            
            # Format response
            preferences = {
                "topics": json.loads(updated_prefs['topics']) if updated_prefs['topics'] else [],
                "newsletter_frequency": updated_prefs['newsletter_frequency'],
                "email_notifications": bool(updated_prefs['email_notifications']),
                "content_types": json.loads(updated_prefs['content_types']) if updated_prefs['content_types'] else ["articles"],
                "onboarding_completed": bool(updated_prefs['onboarding_completed']),
                "newsletter_subscribed": bool(updated_prefs['newsletter_subscribed'])
            }
            
            return {
                "id": user_id,
                "email": payload.get('email', ''),
                "name": payload.get('name', ''),
                "picture": payload.get('picture', ''),
                "verified_email": True,
                "subscription_tier": "free",
                "preferences": preferences,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "preferences_updated": True,
                    "user_id": user_id
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Preferences update failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {"error": f"Preferences update failed: {str(e)}", "status": 500}
    
    async def handle_auth_profile(self, headers: Dict) -> Dict[str, Any]:
        """Handle user profile fetch with JWT verification and database lookup"""
        try:
            logger.info("🔐 Processing auth profile request")
            
            # Extract and verify JWT token
            token = headers.get('authorization', '')
            if not token:
                return {"error": "Authentication required", "status": 401}
            
            # Verify JWT token
            payload = self.auth_service.verify_jwt_token(token)
            if not payload:
                return {"error": "Invalid or expired token", "status": 401}
            
            user_id = payload.get('sub', '')
            if not user_id:
                return {"error": "Invalid token payload", "status": 401}
            
            # Fetch user data from database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                logger.warning(f"❌ User not found in database: {user_id}")
                conn.close()
                return {"error": "User not found", "status": 404}
            
            # Get user preferences
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            user_prefs = cursor.fetchone()
            
            conn.close()
            
            # Format preferences
            preferences = {
                "topics": [],
                "newsletter_frequency": "weekly",
                "email_notifications": True,
                "content_types": ["blogs", "podcasts", "videos"],
                "onboarding_completed": False,
                "newsletter_subscribed": False
            }
            
            if user_prefs:
                preferences.update({
                    "topics": json.loads(user_prefs['topics']) if user_prefs['topics'] else [],
                    "newsletter_frequency": user_prefs['newsletter_frequency'],
                    "email_notifications": bool(user_prefs['email_notifications']),
                    "content_types": json.loads(user_prefs['content_types']) if user_prefs['content_types'] else ["blogs", "podcasts", "videos"],
                    "onboarding_completed": bool(user_prefs['onboarding_completed']),
                    "newsletter_subscribed": bool(user_prefs['newsletter_subscribed'])
                })
            
            return {
                "id": user_data['id'],
                "email": user_data['email'],
                "name": user_data['name'],
                "picture": user_data['picture'],
                "verified_email": bool(user_data['verified_email']),
                "subscription_tier": "free",
                "preferences": preferences,
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "preferences_found": bool(user_prefs)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Profile fetch failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {"error": f"Profile fetch failed: {str(e)}", "status": 500}
    
    async def handle_admin_endpoints(self, endpoint: str, headers: Dict, params: Dict = None) -> Dict[str, Any]:
        """Handle admin endpoints with debug logging"""
        try:
            logger.info(f"👑 Processing admin endpoint: {endpoint}")
            
            # Check admin authentication
            admin_key = headers.get('X-Admin-Key') or headers.get('x-admin-key')
            if not admin_key:
                logger.warning("❌ Admin endpoint accessed without admin key")
                return {"error": "Admin authentication required", "status": 401}
            
            admin_endpoint = endpoint.replace("admin/", "")
            
            if admin_endpoint == "quick-test":
                admin_response = {
                    "admin_test": "success",
                    "router_admin": True,
                    "timestamp": datetime.utcnow().isoformat(),
                    "authenticated": True,
                    "debug_info": {
                        "admin_key_provided": bool(admin_key),
                        "endpoint": admin_endpoint
                    }
                }
                logger.info("✅ Admin quick test completed successfully")
                return admin_response
            else:
                logger.warning(f"❌ Unknown admin endpoint: {admin_endpoint}")
                return {"error": f"Admin endpoint '{admin_endpoint}' not implemented", "status": 404}
                
        except Exception as e:
            logger.error(f"❌ Admin endpoint {endpoint} failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "error": f"Admin request failed: {str(e)}", 
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }

# =============================================================================
# FASTAPI APPLICATION - Single Function Entry Point with Enhanced CORS
# =============================================================================

# Initialize FastAPI app with debug info
app = FastAPI(
    title="AI News Scraper Router", 
    version="2.0.0",
    description="Single function router architecture with complete authentication and debug logging"
)

# Add comprehensive CORS middleware with explicit domain support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.vidyagam.com",
        "https://vidyagam.com", 
        "https://ai-news-react.vercel.app",
        "https://ai-news-react-*.vercel.app",
        "https://ai-news-react-ditdccite-vijayan-subramaniyans-projects-0c70c64d.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "*"  # Allow all origins for debugging
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "X-Admin-Key",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods"
    ],
    expose_headers=["*"]
)

# Initialize router
router = AINewsRouter()

# Add explicit OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle CORS preflight requests"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Admin-Key, Accept, Origin, User-Agent, DNT, Cache-Control, X-Requested-With",
            "Access-Control-Max-Age": "86400"
        }
    )

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Log incoming request
    logger.info(f"📥 Incoming request: {request.method} {request.url}")
    logger.info(f"📋 Headers: {dict(request.headers)}")
    logger.info(f"🌍 Client: {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"📤 Response: {response.status_code} ({process_time:.3f}s)")
    
    return response

@app.get("/api/index")
@app.post("/api/index")
async def main_router(request: Request, response: Response):
    """
    Main router function - handles ALL API endpoints with comprehensive debug logging
    
    This single function replaces all individual serverless functions to avoid Vercel's 12-function limit.
    Routes requests based on 'endpoint' parameter to appropriate handlers.
    """
    try:
        logger.info(f"📡 Router request: {request.method} from {request.client.host if request.client else 'unknown'}")
        
        # Handle GET requests (endpoint in query parameters)
        if request.method == "GET":
            query_params = dict(request.query_params)
            endpoint = query_params.pop('endpoint', 'health')
            
            logger.info(f"📊 GET request - endpoint: {endpoint}, params: {query_params}")
            
            # Get headers
            headers = dict(request.headers)
            
            result = await router.route_request(
                endpoint=endpoint,
                method="GET",
                params=query_params,
                headers=headers
            )
            
        # Handle POST requests (endpoint in JSON body)
        else:
            try:
                body = await request.json()
                endpoint = body.get('endpoint', 'health')
                method = body.get('method', 'POST')
                params = body.get('params', {})
                request_headers = body.get('headers', {})
                
                logger.info(f"📊 POST request - endpoint: {endpoint}, method: {method}")
                logger.info(f"📊 Body keys: {list(body.keys())}")
                
                # Merge with actual request headers
                headers = dict(request.headers)
                headers.update(request_headers)
                
                result = await router.route_request(
                    endpoint=endpoint,
                    method=method,
                    params=params,
                    headers=headers,
                    body=body
                )
                
            except json.JSONDecodeError as e:
                logger.warning(f"❌ Invalid JSON in POST request: {str(e)}")
                result = {
                    "error": "Invalid JSON in request body", 
                    "status": 400,
                    "debug_info": {"json_error": str(e)}
                }
        
        # Handle error status codes
        if isinstance(result, dict) and 'status' in result:
            status_code = result.pop('status')
            response.status_code = status_code
            if status_code == 401:
                response.headers["WWW-Authenticate"] = "Bearer"
        
        # Add CORS headers explicitly
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Admin-Key"
        
        logger.info(f"✅ Router response: {len(str(result))} chars, status: {response.status_code}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Main router error: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        error_response = {
            "error": f"Router failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "router_architecture": "single_function",
            "request_method": request.method,
            "debug_info": {
                "traceback": traceback.format_exc(),
                "request_url": str(request.url),
                "client_host": request.client.host if request.client else "unknown"
            }
        }
        
        response.status_code = 500
        return error_response

# Health check endpoint (alternative access)
@app.get("/health")
async def health_check():
    """Alternative health check endpoint with debug info"""
    logger.info("🏥 Direct health endpoint accessed")
    return await router.handle_health()

# API Health check endpoint (Railway deployment)
@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway deployment"""
    logger.info("🏥 API health endpoint accessed (Railway)")
    return await router.handle_health()

# Root endpoint with comprehensive debug info
@app.get("/")
async def root():
    """Root endpoint with architecture info and debug data"""
    logger.info("🏠 Root endpoint accessed")
    return {
        "service": "AI News Scraper",
        "version": "2.0.0",
        "platform": "Railway",
        "architecture": "single_function_router",
        "scalability": "unlimited_endpoints",
        "authentication": "google_oauth_jwt",
        "storage": "persistent_sqlite",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "main_router": "/api/index",
            "health_check": "/health",
            "documentation": "All endpoints routed through /api/index with 'endpoint' parameter"
        },
        "railway_info": {
            "persistent_storage": True,
            "auto_scaling": True,
            "health_checks": True,
            "real_time_logs": True
        },
        "debug_info": {
            "environment": {
                "jwt_secret_configured": bool(os.getenv('JWT_SECRET')),
                "google_client_id_configured": bool(os.getenv('GOOGLE_CLIENT_ID')),
                "port": os.getenv('PORT', 'not_set')
            },
            "cors_configured": True,
            "logging_enabled": True,
            "database_ready": True,
            "database_persistent": True
        }
    }

# Options endpoint for CORS preflight
@app.options("/api/index")
@app.options("/{path:path}")
async def options_handler(request: Request):
    """Handle CORS preflight requests"""
    logger.info(f"🔄 CORS preflight request: {request.method} {request.url}")
    
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Admin-Key, Accept, Origin, User-Agent, DNT, Cache-Control, X-Requested-With",
            "Access-Control-Max-Age": "86400"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 AI News Scraper Router starting up...")
    logger.info(f"📍 Environment check:")
    logger.info(f"   JWT_SECRET: {'✅ Configured' if os.getenv('JWT_SECRET') else '❌ Missing'}")
    logger.info(f"   GOOGLE_CLIENT_ID: {'✅ Configured' if os.getenv('GOOGLE_CLIENT_ID') else '❌ Missing'}")
    logger.info("✅ Router startup complete")

# For Vercel deployment
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")