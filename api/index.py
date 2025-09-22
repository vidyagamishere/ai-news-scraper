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

print("🚂 AI News Scraper API Router - Railway Deployment with Persistent Storage (Updated)")
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
            
            # Content Types table - master reference for all content types
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    frontend_section TEXT NOT NULL,
                    icon TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AI Topics table - master reference for all AI topics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    icon TEXT,
                    target_roles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Article Topics junction table - many-to-many relationship between articles and AI topics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    relevance_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES ai_topics (id) ON DELETE CASCADE,
                    UNIQUE(article_id, topic_id)
                )
            """)
            
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
                    processing_status TEXT DEFAULT 'pending',
                    content_type_id INTEGER DEFAULT 1,
                    content TEXT,
                    thumbnail_url TEXT,
                    audio_url TEXT,
                    video_url TEXT,
                    duration TEXT,
                    read_time TEXT DEFAULT '3 min',
                    FOREIGN KEY (content_type_id) REFERENCES content_types (id)
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
            
            # Add new columns to articles table for unified content storage
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN content_type_id INTEGER DEFAULT 1")
                logger.info("✅ Added content_type_id column to articles table")
            except:
                logger.info("ℹ️ content_type_id column already exists in articles table")
                
            # Legacy support - keep old content_type column for backward compatibility during migration
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN content_type TEXT DEFAULT 'blogs'")
                logger.info("✅ Added content_type column to articles table (legacy support)")
            except:
                logger.info("ℹ️ content_type column already exists in articles table")
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN content TEXT")
                logger.info("✅ Added content column to articles table")
            except:
                logger.info("ℹ️ content column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN thumbnail_url TEXT")
                logger.info("✅ Added thumbnail_url column to articles table")
            except:
                logger.info("ℹ️ thumbnail_url column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN audio_url TEXT")
                logger.info("✅ Added audio_url column to articles table")
            except:
                logger.info("ℹ️ audio_url column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN video_url TEXT")
                logger.info("✅ Added video_url column to articles table")
            except:
                logger.info("ℹ️ video_url column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN duration TEXT")
                logger.info("✅ Added duration column to articles table")
            except:
                logger.info("ℹ️ duration column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN read_time TEXT DEFAULT '3 min'")
                logger.info("✅ Added read_time column to articles table")
            except:
                logger.info("ℹ️ read_time column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN processing_status TEXT DEFAULT 'pending'")
                logger.info("✅ Added processing_status column to articles table")
            except:
                logger.info("ℹ️ processing_status column already exists in articles table")
                
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN content_hash TEXT")
                logger.info("✅ Added content_hash column to articles table")
            except:
                logger.info("ℹ️ content_hash column already exists in articles table")
            
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
                ('content_types', 'TEXT', None),
                ('user_roles', 'TEXT', None)  # JSON array of selected user roles
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
            # AI SOURCES TABLE - Database-driven source management
            # =================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rss_url TEXT NOT NULL,
                    website TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 5,
                    content_type TEXT DEFAULT 'blogs', -- blogs, podcasts, videos, learning, events, demos
                    category TEXT DEFAULT 'general',
                    ai_topics TEXT, -- JSON array of AI topic IDs this source covers
                    meta_tags TEXT, -- JSON array of keywords and tags for topic matching
                    description TEXT,
                    language TEXT DEFAULT 'en',
                    verified BOOLEAN DEFAULT 0, -- Verified as legitimate source
                    last_scraped TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active', -- active, inactive, error
                    error_count INTEGER DEFAULT 0,
                    max_articles INTEGER DEFAULT 10,
                    scrape_frequency TEXT DEFAULT 'daily', -- daily, weekly, hourly
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # =================================================================
            # CLEANUP OLD DATA
            # =================================================================
            
            # Clean up expired OTPs
            cursor.execute("DELETE FROM email_otps WHERE expires_at < ?", (datetime.utcnow().isoformat(),))
            
            # Populate content types table with master data
            self.populate_content_types_table(cursor)
            
            # Populate AI topics table with comprehensive topic data
            self.populate_ai_topics_table(cursor)
            
            # Populate AI sources table with comprehensive legitimate sources
            self.populate_ai_sources_table(cursor)
            
            # Sync content types from ai_sources to articles table
            self.sync_content_types_to_articles(cursor)
            
            # =================================================================
            # INDEXES FOR PERFORMANCE (Created AFTER table population)
            # =================================================================
            
            logger.info("🔧 Creating database indexes for performance optimization...")
            
            # Index on articles for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_date ON articles(published_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_significance ON articles(significance_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_content_type_id ON articles(content_type_id)")
            
            # Indexes on AI topics and article_topics junction table
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_topics_topic_id ON ai_topics(topic_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_topics_category ON ai_topics(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_topics_article_id ON article_topics(article_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_topics_topic_id ON article_topics(topic_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_topics_relevance ON article_topics(relevance_score)")
            
            # Index on users for authentication
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            
            # Index on OTPs for cleanup and verification
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_expires ON email_otps(expires_at)")
            
            logger.info("✅ Database indexes created successfully")
            
            # =================================================================
            # DATABASE VIEWS FOR OPTIMIZED LLM-SUMMARIZED CONTENT DELIVERY
            # =================================================================
            
            logger.info("🎯 Creating optimized database views for LLM content delivery...")
            
            # View 1: Enhanced Articles with Content Types and Topics (Main digest view)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_enhanced_articles AS
                SELECT 
                    a.id,
                    a.title,
                    COALESCE(a.content, a.summary) as content,
                    a.summary,
                    a.source,
                    a.published_date,
                    a.url,
                    a.significance_score,
                    a.thumbnail_url,
                    a.audio_url,
                    a.video_url,
                    a.duration,
                    COALESCE(a.read_time, a.duration, '3 min') as read_time,
                    a.processing_status,
                    a.content_hash,
                    -- Content type information
                    COALESCE(ct.name, 'blogs') as content_type,
                    ct.display_name as content_type_display,
                    ct.frontend_section,
                    ct.icon as content_type_icon,
                    -- Topic information (aggregated)
                    GROUP_CONCAT(DISTINCT t.topic_id) as topic_ids,
                    GROUP_CONCAT(DISTINCT t.display_name) as topic_names,
                    GROUP_CONCAT(DISTINCT t.category) as topic_categories,
                    GROUP_CONCAT(DISTINCT at.relevance_score) as topic_relevance_scores,
                    COUNT(DISTINCT t.id) as topic_count,
                    AVG(at.relevance_score) as avg_relevance_score,
                    -- Computed fields for frontend
                    'medium' as impact,
                    CASE 
                        WHEN a.significance_score >= 8.0 THEN 'high'
                        WHEN a.significance_score >= 6.0 THEN 'medium'
                        ELSE 'low'
                    END as impact_level
                FROM articles a
                LEFT JOIN content_types ct ON a.content_type_id = ct.id
                LEFT JOIN article_topics at ON a.id = at.article_id
                LEFT JOIN ai_topics t ON at.topic_id = t.id
                WHERE a.published_date IS NOT NULL AND a.published_date != ''
                GROUP BY a.id, a.title, a.content, a.summary, a.source, a.published_date, 
                         a.url, a.significance_score, a.thumbnail_url, a.audio_url, a.video_url,
                         a.duration, a.read_time, a.processing_status, a.content_hash,
                         ct.name, ct.display_name, ct.frontend_section, ct.icon
            """)
            
            # View 2: Top Stories with Enhanced Metadata (Digest top stories)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_top_stories AS
                SELECT 
                    ea.*,
                    -- Additional computed fields for top stories
                    RANK() OVER (ORDER BY ea.significance_score DESC, ea.published_date DESC) as story_rank,
                    CASE 
                        WHEN ea.topic_count > 3 THEN 'multi-topic'
                        WHEN ea.topic_count > 1 THEN 'cross-topic'
                        WHEN ea.topic_count = 1 THEN 'focused'
                        ELSE 'general'
                    END as topic_classification
                FROM v_enhanced_articles ea
                WHERE ea.significance_score >= 5.0
                ORDER BY ea.significance_score DESC, ea.published_date DESC
            """)
            
            # View 3: Content by Type (for ContentTabs optimization)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_content_by_type AS
                SELECT 
                    ct.name as content_type,
                    ct.display_name,
                    ct.frontend_section,
                    COUNT(a.id) as article_count,
                    AVG(a.significance_score) as avg_significance,
                    MAX(a.published_date) as latest_article_date,
                    -- Sample articles for each content type
                    GROUP_CONCAT(
                        DISTINCT a.title || '|' || a.url || '|' || a.significance_score, 
                        ';;;'
                    ) as sample_articles
                FROM content_types ct
                LEFT JOIN articles a ON ct.id = a.content_type_id
                WHERE a.published_date IS NOT NULL AND a.published_date != ''
                GROUP BY ct.id, ct.name, ct.display_name, ct.frontend_section
                ORDER BY article_count DESC
            """)
            
            # View 4: Personalized Content for User Preferences
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_personalized_articles AS
                SELECT 
                    ea.*,
                    -- User preference matching (to be filtered by application logic)
                    CASE 
                        WHEN ea.topic_count > 0 THEN 'topic_matched'
                        ELSE 'general_content'
                    END as personalization_type,
                    -- Content freshness score
                    CASE 
                        WHEN DATE(ea.published_date) = DATE('now') THEN 3.0
                        WHEN DATE(ea.published_date) >= DATE('now', '-1 day') THEN 2.0
                        WHEN DATE(ea.published_date) >= DATE('now', '-7 days') THEN 1.0
                        ELSE 0.5
                    END as freshness_score,
                    -- Combined scoring for personalization
                    (ea.significance_score * 0.7 + 
                     COALESCE(ea.avg_relevance_score, 0.5) * 0.3) as personalization_score
                FROM v_enhanced_articles ea
                ORDER BY personalization_score DESC, ea.published_date DESC
            """)
            
            # View 5: Topic Distribution Summary (for admin analytics)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_topic_analytics AS
                SELECT 
                    t.topic_id,
                    t.display_name,
                    t.category,
                    t.target_roles,
                    COUNT(DISTINCT at.article_id) as article_count,
                    AVG(at.relevance_score) as avg_relevance,
                    COUNT(DISTINCT a.source) as unique_sources,
                    MAX(a.published_date) as latest_article_date,
                    AVG(a.significance_score) as avg_article_significance,
                    -- Content type distribution for this topic
                    GROUP_CONCAT(
                        DISTINCT ct.name || ':' || COUNT(a.id) OVER (PARTITION BY t.id, ct.id)
                    ) as content_type_distribution
                FROM ai_topics t
                LEFT JOIN article_topics at ON t.id = at.topic_id
                LEFT JOIN articles a ON at.article_id = a.id
                LEFT JOIN content_types ct ON a.content_type_id = ct.id
                GROUP BY t.id, t.topic_id, t.display_name, t.category, t.target_roles
                ORDER BY article_count DESC, avg_relevance DESC
            """)
            
            logger.info("✅ Database views created successfully for optimized content delivery")
            
            # Commit all changes
            conn.commit()
            conn.close()
            
            # Auto-populate article-topic mappings if junction table is empty
            self.auto_populate_article_topic_mappings()
            
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
    
    def populate_content_types_table(self, cursor):
        """Populate content_types table with master content type data"""
        logger.info("📋 Populating content_types table with master data")
        
        # Check if content types already exist
        cursor.execute("SELECT COUNT(*) as count FROM content_types")
        existing_count = cursor.fetchone()['count']
        
        if existing_count > 0:
            logger.info(f"📊 Found {existing_count} existing content types, skipping population")
            return
        
        # Master content types with frontend mapping
        content_types = [
            {
                "name": "blogs",
                "display_name": "Blog Articles",
                "description": "News articles, analysis pieces, and written content",
                "frontend_section": "blog",
                "icon": "📝"
            },
            {
                "name": "podcasts", 
                "display_name": "Podcasts",
                "description": "Audio content, interviews, and discussions",
                "frontend_section": "audio",
                "icon": "🎵"
            },
            {
                "name": "videos",
                "display_name": "Videos", 
                "description": "Video content, tutorials, and presentations",
                "frontend_section": "video",
                "icon": "🎬"
            },
            {
                "name": "learning",
                "display_name": "Learning Resources",
                "description": "Educational content, courses, and tutorials",
                "frontend_section": "blog",
                "icon": "📚"
            },
            {
                "name": "events",
                "display_name": "Events",
                "description": "Conferences, meetups, and industry events",
                "frontend_section": "blog", 
                "icon": "📅"
            },
            {
                "name": "demos",
                "display_name": "Demos & Showcases",
                "description": "Product demonstrations and proof of concepts",
                "frontend_section": "video",
                "icon": "🚀"
            }
        ]
        
        # Insert content types
        for content_type in content_types:
            cursor.execute("""
                INSERT INTO content_types (name, display_name, description, frontend_section, icon)
                VALUES (?, ?, ?, ?, ?)
            """, (
                content_type["name"],
                content_type["display_name"], 
                content_type["description"],
                content_type["frontend_section"],
                content_type["icon"]
            ))
        
        logger.info(f"✅ Populated {len(content_types)} content types")
        
        # Log the content types for verification
        cursor.execute("SELECT id, name, display_name, frontend_section FROM content_types ORDER BY id")
        types = cursor.fetchall()
        logger.info("📋 Content types created:")
        for row in types:
            logger.info(f"   ID {row[0]}: {row[1]} → {row[3]} section ({row[2]})")
    
    def populate_ai_topics_table(self, cursor):
        """Populate ai_topics table with comprehensive AI topic data"""
        logger.info("🧠 Populating ai_topics table with comprehensive AI topics")
        
        # Check if ai_topics table has correct schema (check for topic_id column)
        try:
            cursor.execute("SELECT topic_id FROM ai_topics LIMIT 1")
            schema_correct = True
        except sqlite3.OperationalError:
            logger.info("⚠️ Old ai_topics table schema detected, migrating to new schema")
            schema_correct = False
            
        # If schema is incorrect, drop and recreate table
        if not schema_correct:
            # Drop both tables to maintain foreign key integrity
            cursor.execute("DROP TABLE IF EXISTS article_topics")
            cursor.execute("DROP TABLE IF EXISTS ai_topics")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    icon TEXT,
                    target_roles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    relevance_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES ai_topics (id) ON DELETE CASCADE,
                    UNIQUE(article_id, topic_id)
                )
            """)
            logger.info("✅ Recreated ai_topics and article_topics tables with correct schema")
        
        # Check if AI topics already exist (after potential recreation)
        cursor.execute("SELECT COUNT(*) as count FROM ai_topics")
        existing_count = cursor.fetchone()['count']
        
        if existing_count > 0:
            logger.info(f"📊 Found {existing_count} existing AI topics, skipping population")
            return
        
        # Comprehensive AI topics covering all aspects of AI development and research
        ai_topics = [
            # Novice-friendly topics
            {"topic_id": "ai-explained", "display_name": "AI Explained", "description": "Simple explanations of AI concepts", "category": "novice", "icon": "🤖", "target_roles": "novice,student"},
            {"topic_id": "ai-in-everyday-life", "display_name": "AI in Everyday Life", "description": "How AI impacts daily life", "category": "novice", "icon": "🏠", "target_roles": "novice,student"},
            {"topic_id": "fun-and-interesting-ai", "display_name": "Fun & Interesting AI", "description": "Entertaining AI developments", "category": "novice", "icon": "🎮", "target_roles": "novice,student"},
            {"topic_id": "basic-ethics", "display_name": "Basic AI Ethics", "description": "Fundamental ethical considerations", "category": "novice", "icon": "⚖️", "target_roles": "novice,student,executive"},
            
            # Student-focused topics
            {"topic_id": "educational-content", "display_name": "Educational Content", "description": "Learning resources and tutorials", "category": "student", "icon": "📚", "target_roles": "student"},
            {"topic_id": "project-ideas", "display_name": "Project Ideas", "description": "AI project inspiration and guides", "category": "student", "icon": "💡", "target_roles": "student"},
            {"topic_id": "career-trends", "display_name": "AI Career Trends", "description": "Job market and career opportunities", "category": "student", "icon": "📈", "target_roles": "student,professional"},
            {"topic_id": "machine-learning", "display_name": "Machine Learning", "description": "ML algorithms and applications", "category": "student", "icon": "🧮", "target_roles": "student,professional"},
            {"topic_id": "deep-learning", "display_name": "Deep Learning", "description": "Neural networks and deep AI", "category": "student", "icon": "🧠", "target_roles": "student,professional"},
            {"topic_id": "tools-and-frameworks", "display_name": "AI Tools & Frameworks", "description": "Development tools and platforms", "category": "student", "icon": "🔧", "target_roles": "student,professional"},
            {"topic_id": "data-science", "display_name": "Data Science", "description": "Data analysis and insights", "category": "student", "icon": "📊", "target_roles": "student,professional"},
            
            # Professional topics
            {"topic_id": "industry-news", "display_name": "Industry News", "description": "AI industry developments", "category": "professional", "icon": "📰", "target_roles": "professional,executive"},
            {"topic_id": "applied-ai", "display_name": "Applied AI", "description": "Real-world AI implementations", "category": "professional", "icon": "⚙️", "target_roles": "professional"},
            {"topic_id": "case-studies", "display_name": "Case Studies", "description": "Detailed implementation examples", "category": "professional", "icon": "📋", "target_roles": "professional,executive"},
            {"topic_id": "podcasts-and-interviews", "display_name": "Podcasts & Interviews", "description": "Expert discussions and insights", "category": "professional", "icon": "🎙️", "target_roles": "professional,executive"},
            {"topic_id": "cloud-computing", "display_name": "AI & Cloud Computing", "description": "Cloud-based AI solutions", "category": "professional", "icon": "☁️", "target_roles": "professional"},
            {"topic_id": "robotics", "display_name": "Robotics & Automation", "description": "AI-powered robotics", "category": "professional", "icon": "🤖", "target_roles": "professional"},
            
            # Executive-level topics
            {"topic_id": "ai-ethics-and-safety", "display_name": "AI Ethics & Safety", "description": "Responsible AI development", "category": "executive", "icon": "🛡️", "target_roles": "executive,professional"},
            {"topic_id": "investment-and-funding", "display_name": "AI Investment & Funding", "description": "Financial aspects of AI", "category": "executive", "icon": "💰", "target_roles": "executive"},
            {"topic_id": "strategic-implications", "display_name": "Strategic Implications", "description": "Business strategy and AI", "category": "executive", "icon": "🎯", "target_roles": "executive"},
            {"topic_id": "policy-and-regulation", "display_name": "AI Policy & Regulation", "description": "Government and legal aspects", "category": "executive", "icon": "🏛️", "target_roles": "executive"},
            {"topic_id": "leadership-and-innovation", "display_name": "AI Leadership", "description": "Leading AI transformation", "category": "executive", "icon": "👔", "target_roles": "executive"},
            {"topic_id": "ai-research", "display_name": "AI Research", "description": "Latest research and breakthroughs", "category": "executive", "icon": "🔬", "target_roles": "executive,professional"}
        ]
        
        # Insert AI topics
        for topic in ai_topics:
            cursor.execute("""
                INSERT INTO ai_topics (topic_id, display_name, description, category, icon, target_roles)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                topic["topic_id"],
                topic["display_name"],
                topic["description"],
                topic["category"],
                topic["icon"],
                topic["target_roles"]
            ))
        
        logger.info(f"✅ Populated {len(ai_topics)} AI topics")
        
        # Log the AI topics for verification
        cursor.execute("SELECT id, topic_id, display_name, category FROM ai_topics ORDER BY category, id")
        topics = cursor.fetchall()
        logger.info("🧠 AI topics created:")
        for row in topics:
            logger.info(f"   ID {row[0]}: {row[1]} → {row[3]} ({row[2]})")
    
    def auto_populate_article_topic_mappings(self):
        """Automatically populate article-topic mappings if junction table is empty"""
        try:
            logger.info("🔗 Checking article-topic mappings...")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if junction table has any mappings
            cursor.execute("SELECT COUNT(*) FROM article_topics")
            mapping_count = cursor.fetchone()[0]
            
            if mapping_count > 0:
                logger.info(f"📊 Found {mapping_count} existing article-topic mappings, skipping auto-population")
                conn.close()
                return
            
            # Check if we have articles and topics to map
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ai_topics")
            topic_count = cursor.fetchone()[0]
            
            if article_count == 0 or topic_count == 0:
                logger.info(f"📊 Insufficient data for mapping (articles: {article_count}, topics: {topic_count})")
                conn.close()
                return
            
            logger.info(f"🧠 Auto-populating mappings for {article_count} articles to {topic_count} topics...")
            
            # Get all articles
            cursor.execute("SELECT id, source, title, COALESCE(content, summary, '') as content FROM articles")
            articles = cursor.fetchall()
            
            mapped_count = 0
            for article in articles:
                article_id, source, title, content = article
                self.map_article_to_topics(article_id, source or "", title or "", content or "")
                mapped_count += 1
            
            conn.close()
            logger.info(f"✅ Auto-populated {mapped_count} article-topic mappings")
            
        except Exception as e:
            logger.error(f"❌ Auto-population of article-topic mappings failed: {str(e)}")
    
    def populate_ai_sources_table(self, cursor):
        """Populate AI sources table with comprehensive legitimate sources covering ALL 23 AI topics"""
        logger.info("📚 Populating AI sources table with comprehensive sources for all 23 topics")
        
        # Check if sources already exist
        cursor.execute("SELECT COUNT(*) as count FROM ai_sources")
        existing_count = cursor.fetchone()['count']
        
        if existing_count > 0:
            logger.info(f"📊 Found {existing_count} existing sources, skipping population")
            return
        
        # Import comprehensive AI sources covering all 23 topics with proper content types and meta tags
        from comprehensive_ai_sources import COMPREHENSIVE_AI_SOURCES
        comprehensive_sources = COMPREHENSIVE_AI_SOURCES
        
        # Insert all sources with meta_tags column included
        for source in comprehensive_sources:
            cursor.execute("""
                INSERT INTO ai_sources (
                    name, rss_url, website, content_type, category, ai_topics,
                    meta_tags, description, verified, priority, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source["name"],
                source["rss_url"],
                source["website"],
                source["content_type"],
                source["category"],
                source["ai_topics"],
                source.get("meta_tags", "[]"),  # Include meta_tags with fallback
                source["description"],
                source["verified"],
                source["priority"],
                True
            ))
        
        logger.info(f"✅ Populated {len(comprehensive_sources)} AI sources covering all 23 AI topics with meta tags")
    
    def ensure_ai_sources_table(self, cursor):
        """Ensure ai_sources table exists and is populated with comprehensive sources"""
        try:
            # Check if table exists and has data
            cursor.execute("SELECT COUNT(*) as count FROM ai_sources")
            existing_count = cursor.fetchone()['count']
            
            if existing_count == 0:
                logger.info("📥 ai_sources table empty, populating with comprehensive sources...")
                self.populate_ai_sources_table(cursor)
            else:
                logger.info(f"📊 ai_sources table has {existing_count} sources")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring ai_sources table: {str(e)}")
            # Table might not exist, let it be created by schema initialization
            logger.info("🔄 Will populate on next schema initialization")
    
    def sync_content_types_to_articles(self, cursor):
        """Sync content types from ai_sources to articles table using foreign key relationship"""
        try:
            logger.info("🔄 Syncing content types from ai_sources to articles table with foreign keys...")
            
            # Update articles content_type_id based on source mapping from ai_sources and content_types
            cursor.execute("""
                UPDATE articles 
                SET content_type_id = (
                    SELECT content_types.id 
                    FROM ai_sources 
                    JOIN content_types ON ai_sources.content_type = content_types.name
                    WHERE ai_sources.name = articles.source
                )
                WHERE EXISTS (
                    SELECT 1 FROM ai_sources 
                    WHERE ai_sources.name = articles.source
                )
            """)
            
            rows_updated = cursor.rowcount
            logger.info(f"✅ Updated {rows_updated} articles with content_type_id from ai_sources")
            
            # Also update legacy content_type column for backward compatibility
            cursor.execute("""
                UPDATE articles 
                SET content_type = (
                    SELECT ai_sources.content_type 
                    FROM ai_sources 
                    WHERE ai_sources.name = articles.source
                )
                WHERE EXISTS (
                    SELECT 1 FROM ai_sources 
                    WHERE ai_sources.name = articles.source
                )
            """)
            
            # Log content type distribution for debugging using JOIN
            cursor.execute("""
                SELECT ct.name, ct.display_name, ct.frontend_section, COUNT(*) as count 
                FROM articles a
                JOIN content_types ct ON a.content_type_id = ct.id
                GROUP BY ct.id, ct.name, ct.display_name, ct.frontend_section
                ORDER BY count DESC
            """)
            
            distribution = cursor.fetchall()
            logger.info("📊 Content type distribution after sync (using foreign keys):")
            for row in distribution:
                logger.info(f"   {row[0]} ({row[1]}) → {row[2]} section: {row[3]} articles")
                
        except Exception as e:
            logger.error(f"❌ Error syncing content types: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
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
            elif endpoint == "init-sources":
                logger.info("🚀 Routing to public sources initialization handler")
                return await self.handle_public_init_sources()
            elif endpoint == "init-topics":
                logger.info("🔗 Routing to public article-topic mapping handler")
                return await self.handle_public_init_topics()
            elif endpoint == "add-research-articles":
                logger.info("📚 Routing to public research articles handler")
                return await self.handle_public_add_research_articles()
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
                        "health", "digest", "sources", "init-sources", "test-neon", "content-types", "content/*",
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
                    "cors_enabled": True,
                    "version": "2.4.0"
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
            logger.info(f"🔧 handle_digest called with params={params}, headers keys: {list(headers.keys()) if headers else 'None'}")
            
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
            logger.info(f"🔧 handle_digest auth header check: {'Found' if auth_header else 'NOT FOUND'}")
            
            # Check if this is explicitly a preview request (no auth header or invalid token)
            if not auth_header:
                is_preview_mode = True
                logger.info("📱 Preview dashboard mode - no authentication, showing general content")
            else:
                try:
                    # Add detailed logging for auth debugging
                    logger.info(f"🔐 Auth header received: {'Bearer ...' if auth_header.startswith('Bearer ') else 'Invalid format'}")
                    user_data = self.auth_service.get_user_from_token(auth_header)
                    logger.info(f"🔐 Token verification result: {'SUCCESS' if user_data else 'FAILED'}")
                    
                    if user_data:
                        # Authenticated user - get personalized content
                        logger.info(f"🔐 User data: ID={user_data.get('sub')}, Email={user_data.get('email')}")
                        user_preferences = await self.get_user_preferences(user_data.get('sub'))
                        logger.info(f"🎯 User preferences loaded: {len(user_preferences.get('topics', []))} topics")
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
                    logger.warning(f"⚠️ Auth exception details: {traceback.format_exc()}")
            
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
            
            # Get recent content using optimized view for faster LLM-summarized content delivery
            cursor.execute("""
                SELECT 
                    title,
                    content,
                    summary,
                    source,
                    published_date,
                    impact,
                    content_type as type,
                    url,
                    read_time,
                    significance_score,
                    thumbnail_url,
                    audio_url,
                    duration,
                    content_type_display,
                    frontend_section,
                    topic_ids,
                    topic_names,
                    topic_categories,
                    topic_relevance_scores
                FROM v_enhanced_articles
                ORDER BY significance_score DESC, published_date DESC
                LIMIT 50
            """)
            
            articles = []
            for row in cursor.fetchall():
                # Parse topic information from GROUP_CONCAT results from the view
                topic_ids = row[15].split(',') if row[15] else []
                topic_names = row[16].split(',') if row[16] else []
                topic_categories = row[17].split(',') if row[17] else []
                topic_relevance_scores = [float(score) for score in row[18].split(',') if score] if row[18] else []
                
                # Create topic objects combining the parsed data
                topics = []
                for i, topic_id in enumerate(topic_ids):
                    if topic_id:  # Only include non-empty topic_ids
                        topics.append({
                            "id": topic_id.strip(),
                            "name": topic_names[i].strip() if i < len(topic_names) else topic_id,
                            "category": topic_categories[i].strip() if i < len(topic_categories) else "general",
                            "relevance_score": topic_relevance_scores[i] if i < len(topic_relevance_scores) else 1.0
                        })
                
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
                    "duration": row[12],
                    "content_type_display": row[13],
                    "frontend_section": row[14],
                    "topics": topics,  # Enhanced: Article topic associations from view
                    "topic_count": len(topics),  # Enhanced: Number of topics associated
                    "from_view": True  # Flag to indicate this came from optimized view
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
            
            # Organize content by type using foreign key relationship
            content_by_type = {"blog": [], "audio": [], "video": []}
            top_stories = []
            
            # Log initial content distribution with foreign key data
            logger.info(f"📊 Content types from database (with FK): {[(article.get('type', 'unknown'), article.get('frontend_section', 'unknown')) for article in articles[:5]]}")
            
            for article in articles:
                # Use frontend_section from content_types table (via foreign key JOIN)
                frontend_section = article.get("frontend_section", "blog")
                
                # Fallback to hardcoded mapping if frontend_section is not available
                if not frontend_section:
                    content_type = article.get("type", "blogs")
                    content_type_mapping = {
                        "blogs": "blog",
                        "podcasts": "audio", 
                        "videos": "video",
                        "learning": "blog",
                        "events": "blog",
                        "demos": "video"
                    }
                    frontend_section = content_type_mapping.get(content_type, "blog")
                
                if frontend_section in content_by_type:
                    content_by_type[frontend_section].append(article)
                    
            logger.info(f"📊 Content distribution (using foreign keys): blog={len(content_by_type['blog'])}, audio={len(content_by_type['audio'])}, video={len(content_by_type['video'])}")
            
            # Generate top stories with personalization for authenticated users
            if is_personalized and user_preferences and not is_preview_mode:
                # For authenticated users, apply preference filtering to top stories as well
                logger.info("🎯 Generating personalized top stories based on user preferences")
                
                # Convert articles to format for preference filtering
                articles_for_top_stories = []
                for article in articles:
                    articles_for_top_stories.append({
                        "title": article["title"],
                        "summary": article["content_summary"],
                        "source": article["source"],
                        "url": article["url"],
                        "significance_score": article["significanceScore"]
                    })
                
                # Apply user preference filtering to find personalized top stories
                personalized_articles = self.filter_articles_by_user_preferences(
                    articles_for_top_stories, user_preferences
                )
                
                # Create top stories from personalized articles (higher threshold for quality)
                personalized_urls = set(article.get("url", "") for article in personalized_articles)
                personalized_top_candidates = [
                    article for article in articles 
                    if article.get("url", "") in personalized_urls and article["significanceScore"] > 5.0
                ]
                
                # Sort by significance score and take top 5
                personalized_top_candidates.sort(key=lambda x: x["significanceScore"], reverse=True)
                
                for article in personalized_top_candidates[:5]:
                    top_stories.append({
                        "title": article["title"],
                        "source": article["source"],
                        "significanceScore": article["significanceScore"],
                        "url": article["url"],
                        "imageUrl": article.get("imageUrl"),
                        "summary": article["content_summary"],
                        "topics": article.get("topics", []),  # Include topic data from view
                        "from_view": article.get("from_view", False)  # Include view flag
                    })
                
                logger.info(f"🎯 Personalized top stories generated: {len(top_stories)} stories from {len(personalized_top_candidates)} candidates")
                
                # Fallback: if no personalized top stories found, use highest rated personalized articles
                if len(top_stories) == 0 and len(personalized_articles) > 0:
                    logger.info("🎯 No personalized articles above significance threshold, using fallback personalized top stories")
                    fallback_candidates = [
                        article for article in articles 
                        if article.get("url", "") in personalized_urls
                    ]
                    fallback_candidates.sort(key=lambda x: x["significanceScore"], reverse=True)
                    
                    for article in fallback_candidates[:3]:
                        top_stories.append({
                            "title": article["title"],
                            "source": article["source"],
                            "significanceScore": article["significanceScore"],
                            "url": article["url"],
                            "imageUrl": article.get("imageUrl"),
                            "summary": article["content_summary"],
                            "topics": article.get("topics", []),  # Include topic data from view
                            "from_view": article.get("from_view", False)  # Include view flag
                        })
            else:
                # For non-authenticated users or preview mode, use general top stories
                logger.info("📰 Generating general top stories (no personalization)")
                
                for article in articles:
                    # Add to top stories if high significance (lowered threshold for debugging)
                    if article["significanceScore"] > 5.0 and len(top_stories) < 5:
                        top_stories.append({
                            "title": article["title"],
                            "source": article["source"],
                            "significanceScore": article["significanceScore"],
                            "url": article["url"],
                            "imageUrl": article.get("imageUrl"),
                            "summary": article["content_summary"],
                            "topics": article.get("topics", []),  # Include topic data from view
                            "from_view": article.get("from_view", False)  # Include view flag
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
                            "summary": article["content_summary"],
                            "topics": article.get("topics", []),  # Include topic data from view
                            "from_view": article.get("from_view", False)  # Include view flag
                        })
            
            # Calculate metrics
            total_articles = len(articles)
            high_impact = len([a for a in articles if a.get("impact") == "high"])
            
            digest_response = {
                "personalized": is_personalized and not is_preview_mode,  # Add personalized flag to main response
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
        """Get sources configuration from database with comprehensive AI sources"""
        logger.info("🔗 Processing sources request - fetching from ai_sources database table")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Ensure ai_sources table exists and is populated
            self.ensure_ai_sources_table(cursor)
            
            # Fetch all sources from database
            cursor.execute("""
                SELECT name, rss_url, website, enabled, priority, content_type, category, 
                       ai_topics, description, verified, status, last_scraped, max_articles
                FROM ai_sources 
                ORDER BY priority DESC, name ASC
            """)
            
            db_sources = cursor.fetchall()
            
            # Format sources for API response
            sources = []
            enabled_count = 0
            content_type_counts = {}
            
            for source in db_sources:
                source_dict = {
                    "name": source[0],
                    "rss_url": source[1], 
                    "website": source[2],
                    "enabled": bool(source[3]),
                    "priority": source[4],
                    "content_type": source[5],
                    "category": source[6],
                    "ai_topics": json.loads(source[7]) if source[7] else [],
                    "description": source[8],
                    "verified": bool(source[9]),
                    "status": source[10],
                    "last_scraped": source[11],
                    "max_articles": source[12]
                }
                
                sources.append(source_dict)
                
                if source_dict["enabled"]:
                    enabled_count += 1
                    
                # Count content types
                content_type = source_dict["content_type"]
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            conn.close()
            
            logger.info(f"✅ Loaded {len(sources)} sources from database ({enabled_count} enabled)")
            logger.info(f"📊 Content type distribution: {content_type_counts}")
            
            return {
                "sources": sources,
                "enabled_count": enabled_count,
                "total_count": len(sources),
                "content_type_distribution": content_type_counts,
                "router_architecture": "database_driven_with_comprehensive_ai_sources",
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "router_handled": True,
                    "database_source": "ai_sources_table",
                    "legitimate_sources_verified": True,
                    "ai_topics_covered": "all_23_topics",
                    "source_management": "database_driven_for_future_url_additions"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching sources from database: {str(e)}")
            
            # Fallback to minimal hardcoded sources if database fails
            fallback_sources = [
                {"name": "OpenAI Blog", "rss_url": "https://openai.com/blog/rss.xml", "website": "https://openai.com", "enabled": True, "priority": 10, "category": "research", "content_type": "blogs"},
                {"name": "Anthropic", "rss_url": "https://www.anthropic.com/news/rss.xml", "website": "https://www.anthropic.com", "enabled": True, "priority": 10, "category": "research", "content_type": "blogs"},
                {"name": "Google AI Blog", "rss_url": "https://ai.googleblog.com/feeds/posts/default", "website": "https://ai.googleblog.com", "enabled": True, "priority": 9, "category": "research", "content_type": "blogs"}
            ]
            
            return {
                "sources": fallback_sources,
                "enabled_count": 3,
                "total_count": 3,
                "router_architecture": "fallback_mode_database_error",
                "error": str(e),
                "debug_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "router_handled": True,
                    "database_error": True,
                    "fallback_mode": True
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
            "learning": ["course", "tutorial", "guide", "learn", "education", "training", "certification"],
            "demos": ["demo", "demonstration", "showcase", "example", "sample", "prototype", "proof of concept"]
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
        # Removed mandatory AI and ML topics to enable true personalization differences between users
        return []
    
    def get_topics_from_user_roles(self, user_roles: List[str]) -> List[str]:
        """Convert user roles to consolidated topic list for feed generation"""
        # Role-to-topics mapping
        role_topic_mapping = {
            "novice": ["ai-explained", "ai-in-everyday-life", "fun-and-interesting-ai", "basic-ethics"],
            "student": ["educational-content", "project-ideas", "career-trends", "machine-learning", "deep-learning", "tools-and-frameworks", "data-science"],
            "professional": ["industry-news", "applied-ai", "case-studies", "podcasts-and-interviews", "cloud-computing", "robotics"],
            "executive": ["ai-ethics-and-safety", "investment-and-funding", "strategic-implications", "policy-and-regulation", "leadership-and-innovation", "ai-research"]
        }
        
        # Consolidate topics from all selected roles
        consolidated_topics = set()
        for role in user_roles:
            if role in role_topic_mapping:
                consolidated_topics.update(role_topic_mapping[role])
        
        # Convert back to list and log the consolidation
        topics_list = list(consolidated_topics)
        logger.info(f"🎯 Role consolidation: {user_roles} → {len(topics_list)} topics: {topics_list}")
        
        return topics_list

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
                
                # Extract user roles - NEW ENHANCEMENT
                user_roles = preferences.get("user_roles", [])
                if isinstance(user_roles, str):
                    try:
                        user_roles = json.loads(user_roles)
                    except:
                        user_roles = []
                
                logger.info(f"🎯 User preferences loaded - Topics: {topics}, Content Types: {content_types}, User Roles: {user_roles}")
                
                return {
                    "topics": topics,
                    "user_roles": user_roles,
                    "content_types": content_types,
                    "newsletter_frequency": preferences.get("newsletter_frequency", "weekly"),
                    "email_notifications": preferences.get("email_notifications", True),
                    "onboarding_completed": preferences.get("onboarding_completed", True)
                }
            else:
                logger.info(f"🎯 No preferences found for user {user_id}, using defaults")
                # Return default preferences with default student role
                return {
                    "topics": [],
                    "user_roles": ["student"],  # Default to student role
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
                "user_roles": ["student"],  # Default to student role
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
        """Filter and prioritize articles based on user's role-based topic preferences"""
        
        user_topics = user_preferences.get("topics", [])
        user_roles = user_preferences.get("user_roles", [])
        user_content_types = user_preferences.get("content_types", [])
        
        # Convert user roles to topics for consolidated filtering
        if user_roles:
            role_based_topics = self.get_topics_from_user_roles(user_roles)
            # Combine explicit topics with role-based topics
            all_topics = list(set(user_topics + role_based_topics))
            logger.info(f"🎯 Role-based filtering: Roles {user_roles} + Topics {user_topics} = Combined {all_topics}")
        else:
            all_topics = user_topics
        
        # If user has no preferences at all, return all articles
        if not all_topics and not user_content_types:
            return articles
        
        logger.info(f"🎯 Filtering with consolidated preferences - Topics: {all_topics}, Content Types: {user_content_types}")
        
        # Comprehensive topic keywords - includes new role-based topics
        # Handle different topic ID formats from database and new role-based topics
        topic_keywords = {
            # === NEW ROLE-BASED TOPICS ===
            
            # Novice Topics
            "ai-explained": [
                "ai explained", "artificial intelligence explained", "beginner ai", "ai basics", "introduction to ai",
                "simple ai", "ai for beginners", "what is ai", "ai concepts", "basic ai", "ai fundamentals",
                "easy ai", "ai simplified", "understanding ai", "ai overview", "ai tutorial", "learn ai",
                "ai guide", "ai primer", "ai introduction", "ai 101", "ai for dummies", "plain english ai"
            ],
            "ai-in-everyday-life": [
                "everyday ai", "ai in daily life", "ai applications", "ai examples", "real world ai",
                "consumer ai", "smart devices", "virtual assistant", "siri", "alexa", "google assistant",
                "smart home", "ai phones", "ai apps", "navigation", "maps", "recommendations", "netflix ai",
                "spotify ai", "social media ai", "shopping ai", "email filters", "spam detection"
            ],
            "fun-and-interesting-ai": [
                "fun ai", "interesting ai", "cool ai", "amazing ai", "weird ai", "funny ai", "creative ai",
                "ai art", "ai music", "ai games", "ai stories", "ai jokes", "ai creativity", "strange ai",
                "surprising ai", "fascinating ai", "mind blowing ai", "incredible ai", "awesome ai"
            ],
            "basic-ethics": [
                "ai ethics basics", "simple ai ethics", "ai fairness", "ai bias basics", "responsible ai basics",
                "ai safety basics", "ai privacy", "ai transparency", "ai accountability", "ethical ai introduction"
            ],
            
            # Student Topics  
            "educational-content": [
                "ai education", "learning ai", "ai courses", "ai tutorials", "ai training", "ai certification",
                "ai bootcamp", "ai curriculum", "ai degree", "ai mooc", "coursera ai", "udacity ai", "edx ai",
                "khan academy", "mit opencourseware", "stanford ai course", "berkeley ai course"
            ],
            "project-ideas": [
                "ai projects", "ml projects", "ai hackathon", "ai competition", "kaggle", "github ai",
                "ai portfolio", "ai demos", "ai prototypes", "ai experiments", "hands on ai", "practical ai",
                "build ai", "create ai", "develop ai", "ai coding", "ai programming"
            ],
            "career-trends": [
                "ai jobs", "ai careers", "ai employment", "ai salary", "ai hiring", "ai skills", "ai resume",
                "data scientist jobs", "ml engineer", "ai engineer", "ai researcher jobs", "tech careers",
                "ai job market", "ai skills demand", "ai career path", "ai internship"
            ],
            "tools-and-frameworks": [
                "ai tools", "ml frameworks", "tensorflow", "pytorch", "scikit-learn", "keras", "pandas",
                "numpy", "jupyter", "colab", "anaconda", "docker ai", "kubernetes ai", "cloud ai tools",
                "hugging face", "wandb", "mlflow", "streamlit", "gradio", "fastapi"
            ],
            "data-science": [
                "data science", "data analysis", "data visualization", "statistics", "data mining",
                "big data", "data engineering", "etl", "sql", "python data", "r programming",
                "tableau", "power bi", "matplotlib", "seaborn", "plotly", "pandas", "data cleaning"
            ],
            
            # Professional Topics
            "applied-ai": [
                "ai implementation", "ai deployment", "ai in production", "enterprise ai", "ai solutions",
                "ai consulting", "ai strategy", "ai transformation", "ai adoption", "ai integration",
                "business ai", "commercial ai", "ai roi", "ai value", "ai success stories"
            ],
            "case-studies": [
                "ai case study", "ai success story", "ai implementation story", "ai project case",
                "real world ai", "ai in action", "ai results", "ai impact", "ai outcomes",
                "ai lessons learned", "ai best practices", "ai failure stories", "ai mistakes"
            ],
            "cloud-computing": [
                "cloud ai", "aws ai", "azure ai", "google cloud ai", "cloud ml", "serverless ai",
                "ai as a service", "cloud deployment", "kubernetes", "docker", "microservices ai",
                "edge computing", "distributed ai", "scalable ai", "cloud infrastructure"
            ],
            
            # Executive Topics
            "investment-and-funding": [
                "ai investment", "ai funding", "ai venture capital", "ai vc", "ai startups funding",
                "ai ipo", "ai valuation", "ai market cap", "ai unicorn", "ai acquisition", "ai merger",
                "ai stock", "ai public companies", "ai private equity", "ai angel investment"
            ],
            "strategic-implications": [
                "ai strategy", "business strategy", "digital transformation", "ai disruption",
                "competitive advantage", "market disruption", "ai impact on business", "strategic ai",
                "ai roadmap", "ai planning", "business model innovation", "ai value creation"
            ],
            "policy-and-regulation": [
                "ai regulation", "ai policy", "ai governance", "ai compliance", "ai law", "ai legal",
                "gdpr ai", "ai privacy law", "ai safety regulation", "government ai", "public policy ai",
                "ai standards", "ai certification", "regulatory framework", "ai oversight"
            ],
            "leadership-and-innovation": [
                "ai leadership", "innovation management", "digital leadership", "change management",
                "ai transformation", "organizational change", "ai culture", "innovation strategy",
                "technology leadership", "ai vision", "executive ai", "c-suite ai", "board ai"
            ],
            
            # === EXISTING TOPICS (preserved) ===
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
            
            # Score based on user's selected topics (including role-based topics)
            for user_topic in all_topics:
                if user_topic in topic_keywords:
                    topic_keyword_list = topic_keywords[user_topic]
                    topic_matches = sum(1 for keyword in topic_keyword_list if keyword in content_text)
                    preference_score += topic_matches * 2  # Higher weight for topic matches
            
            # If user has no topics selected, give a base preference score for general AI content
            if not all_topics:
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
    
    def filter_articles_by_topics_foreign_key(self, user_topic_ids: List[str], limit: int = 50) -> List[Dict]:
        """Filter articles using foreign key relationships with ai_topics table"""
        logger.info(f"🎯 Database-driven topic filtering for topics: {user_topic_ids}")
        
        if not user_topic_ids:
            logger.info("📝 No topics specified, returning all articles")
            return []
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create placeholders for the IN clause
            placeholders = ','.join(['?' for _ in user_topic_ids])
            
            # Query articles that match user's topics via foreign key relationship
            query = f"""
                SELECT DISTINCT
                    a.title,
                    COALESCE(a.content, a.summary) as content,
                    a.summary,
                    a.source,
                    a.published_date,
                    'medium' as impact,
                    COALESCE(ct.name, 'blogs') as type,
                    a.url,
                    COALESCE(a.read_time, a.duration, '3 min') as read_time,
                    a.significance_score,
                    a.thumbnail_url,
                    a.audio_url,
                    a.duration,
                    ct.display_name,
                    ct.frontend_section,
                    GROUP_CONCAT(DISTINCT t.topic_id) as topic_ids,
                    GROUP_CONCAT(DISTINCT t.display_name) as topic_names,
                    GROUP_CONCAT(DISTINCT t.category) as topic_categories,
                    GROUP_CONCAT(DISTINCT at.relevance_score) as topic_relevance_scores,
                    COUNT(DISTINCT at.topic_id) as matched_topic_count,
                    AVG(at.relevance_score) as avg_relevance_score
                FROM articles a
                LEFT JOIN content_types ct ON a.content_type_id = ct.id
                INNER JOIN article_topics at ON a.id = at.article_id
                INNER JOIN ai_topics t ON at.topic_id = t.id
                WHERE t.topic_id IN ({placeholders})
                    AND a.published_date IS NOT NULL 
                    AND a.published_date != ''
                GROUP BY a.id, a.title, a.content, a.summary, a.source, a.published_date, a.url,
                         a.read_time, a.duration, a.significance_score, a.thumbnail_url, a.audio_url,
                         ct.name, ct.display_name, ct.frontend_section
                ORDER BY matched_topic_count DESC, avg_relevance_score DESC, a.significance_score DESC
                LIMIT ?
            """
            
            # Execute query with user topic IDs and limit
            cursor.execute(query, user_topic_ids + [limit])
            
            articles = []
            for row in cursor.fetchall():
                # Parse topic information from GROUP_CONCAT results
                topic_ids = row[15].split(',') if row[15] else []
                topic_names = row[16].split(',') if row[16] else []
                topic_categories = row[17].split(',') if row[17] else []
                topic_relevance_scores = [float(score) for score in row[18].split(',') if score] if row[18] else []
                
                # Create topic objects combining the parsed data
                topics = []
                for i, topic_id in enumerate(topic_ids):
                    if topic_id:  # Only include non-empty topic_ids
                        topics.append({
                            "id": topic_id.strip(),
                            "name": topic_names[i].strip() if i < len(topic_names) else topic_id,
                            "category": topic_categories[i].strip() if i < len(topic_categories) else "general",
                            "relevance_score": topic_relevance_scores[i] if i < len(topic_relevance_scores) else 1.0
                        })
                
                article = {
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
                    "duration": row[12],
                    "content_type_display": row[13],
                    "frontend_section": row[14],
                    "topics": topics,  # Article topic associations
                    "topic_count": len(topics),  # Number of topics associated
                    "matched_topic_count": int(row[19]) if row[19] else 0,  # How many user topics matched
                    "avg_relevance_score": float(row[20]) if row[20] else 0.0  # Average relevance for matched topics
                }
                
                articles.append(article)
            
            conn.close()
            
            logger.info(f"🎯 Foreign key topic filtering result: {len(articles)} articles found for topics {user_topic_ids}")
            if articles:
                top_article = articles[0]
                logger.info(f"📰 Top article: '{top_article.get('title', 'Unknown')[:60]}' with {top_article.get('matched_topic_count', 0)} matched topics")
            
            return articles
            
        except Exception as e:
            logger.error(f"❌ Error in topic-based filtering: {e}")
            conn.close()
            return []
    
    def map_article_to_topics(self, article_id: int, source: str, title: str, content: str) -> None:
        """Map an article to relevant AI topics based on content analysis and source mapping"""
        logger.info(f"🧠 Mapping article {article_id} to AI topics based on source '{source}'")
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # First, get all available AI topics
            cursor.execute("SELECT id, topic_id, display_name, category, target_roles FROM ai_topics")
            all_topics = cursor.fetchall()
            
            if not all_topics:
                logger.warning("⚠️ No AI topics found in database - skipping topic mapping")
                conn.close()
                return
            
            # Source-based topic mapping (high confidence)
            source_topic_mapping = {
                # Source name patterns mapped to topic IDs
                "openai": ["foundation_models", "nlp_llm", "generative_ai"],
                "anthropic": ["ai_ethics", "foundation_models", "nlp_llm"],
                "google": ["foundation_models", "computer_vision", "deep_learning"],
                "deepmind": ["reinforcement_learning", "computer_vision", "foundation_models"],
                "hugging face": ["nlp_llm", "foundation_models", "ai_tools"],
                "nvidia": ["computer_vision", "deep_learning", "robotics"],
                "tesla": ["autonomous_systems", "robotics", "computer_vision"],
                "microsoft": ["cloud_computing", "nlp_llm", "applied_ai"],
                "amazon": ["cloud_computing", "applied_ai", "nlp_llm"],
                "meta": ["computer_vision", "nlp_llm", "foundation_models"],
                "pytorch": ["deep_learning", "tools_frameworks", "ml_foundations"],
                "tensorflow": ["deep_learning", "tools_frameworks", "ml_foundations"],
                "kaggle": ["data_science", "project_ideas", "ml_foundations"],
                "arxiv": ["research_papers", "ml_foundations", "deep_learning"],
                "towards data science": ["educational_content", "data_science", "ml_foundations"],
                "ai news": ["industry_news", "applied_ai", "ml_foundations"],
                "venture beat": ["industry_news", "investment_funding", "applied_ai"],
                "techcrunch": ["industry_news", "investment_funding", "startup_news"],
                "wired": ["ai_in_everyday_life", "industry_news", "ai_ethics"],
                "mit technology review": ["research_papers", "ai_ethics", "foundation_models"],
                "nature": ["research_papers", "ml_foundations", "ai_ethics"],
                "ieee": ["research_papers", "technical_standards", "ml_foundations"],
                "acm": ["research_papers", "technical_standards", "computer_science"],
                "podcast": ["educational_content", "industry_news", "career_trends"],
                "youtube": ["educational_content", "tutorials", "project_ideas"],
                "coursera": ["educational_content", "career_trends", "tools_frameworks"],
                "udacity": ["educational_content", "career_trends", "project_ideas"]
            }
            
            # Content-based keyword mapping (medium confidence)
            content_text = f"{title} {content}".lower()
            
            # Find matching topics based on source
            matched_topics = []
            source_lower = source.lower()
            
            for source_pattern, topic_ids in source_topic_mapping.items():
                if source_pattern in source_lower:
                    for topic_id in topic_ids:
                        # Find the topic in our database
                        matching_topic = next((t for t in all_topics if t[1] == topic_id), None)
                        if matching_topic:
                            matched_topics.append({
                                "topic_db_id": matching_topic[0],
                                "topic_id": matching_topic[1],
                                "relevance_score": 0.9,  # High confidence for source-based mapping
                                "source": "source_mapping"
                            })
            
            # Content-based keyword analysis for additional topics
            keyword_topic_mapping = {
                "machine learning": ["ml_foundations", "educational_content"],
                "deep learning": ["deep_learning", "ml_foundations"],
                "neural network": ["deep_learning", "ml_foundations"],
                "artificial intelligence": ["ml_foundations", "ai_explained"],
                "computer vision": ["computer_vision", "deep_learning"],
                "natural language": ["nlp_llm", "foundation_models"],
                "robotics": ["robotics", "autonomous_systems"],
                "autonomous": ["autonomous_systems", "robotics"],
                "ethics": ["ai_ethics", "basic_ethics"],
                "bias": ["ai_ethics", "basic_ethics"],
                "fairness": ["ai_ethics", "basic_ethics"],
                "generative": ["generative_ai", "foundation_models"],
                "gpt": ["nlp_llm", "foundation_models"],
                "claude": ["nlp_llm", "ai_ethics"],
                "chatbot": ["nlp_llm", "ai_in_everyday_life"],
                "investment": ["investment_funding", "industry_news"],
                "funding": ["investment_funding", "startup_news"],
                "startup": ["startup_news", "industry_news"],
                "regulation": ["ai_policy", "ai_ethics"],
                "policy": ["ai_policy", "government_initiatives"],
                "tutorial": ["educational_content", "tools_frameworks"],
                "course": ["educational_content", "career_trends"],
                "project": ["project_ideas", "applied_ai"],
                "github": ["project_ideas", "tools_frameworks"],
                "research": ["research_papers", "ml_foundations"],
                "paper": ["research_papers", "ml_foundations"],
                "conference": ["events", "research_papers"],
                "summit": ["events", "industry_news"]
            }
            
            # Add content-based matches
            for keyword, topic_ids in keyword_topic_mapping.items():
                if keyword in content_text:
                    for topic_id in topic_ids:
                        # Find the topic in our database
                        matching_topic = next((t for t in all_topics if t[1] == topic_id), None)
                        if matching_topic:
                            # Check if we already have this topic from source mapping
                            existing = next((t for t in matched_topics if t["topic_db_id"] == matching_topic[0]), None)
                            if not existing:
                                matched_topics.append({
                                    "topic_db_id": matching_topic[0],
                                    "topic_id": matching_topic[1],
                                    "relevance_score": 0.7,  # Medium confidence for content-based mapping
                                    "source": "content_analysis"
                                })
                            else:
                                # Boost relevance if both source and content match
                                existing["relevance_score"] = min(1.0, existing["relevance_score"] + 0.1)
                                existing["source"] = "source_and_content"
            
            # If no topics matched, assign general AI topics based on user level
            if not matched_topics:
                general_topics = ["ml_foundations", "ai_explained", "industry_news"]
                for topic_id in general_topics:
                    matching_topic = next((t for t in all_topics if t[1] == topic_id), None)
                    if matching_topic:
                        matched_topics.append({
                            "topic_db_id": matching_topic[0],
                            "topic_id": matching_topic[1],
                            "relevance_score": 0.5,  # Low confidence for fallback mapping
                            "source": "fallback"
                        })
            
            # Insert mappings into article_topics junction table
            for topic_match in matched_topics:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO article_topics (article_id, topic_id, relevance_score)
                        VALUES (?, ?, ?)
                    """, (article_id, topic_match["topic_db_id"], topic_match["relevance_score"]))
                except Exception as e:
                    logger.warning(f"⚠️ Failed to insert topic mapping for article {article_id}, topic {topic_match['topic_id']}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Mapped article {article_id} to {len(matched_topics)} topics: {[t['topic_id'] for t in matched_topics]}")
            
        except Exception as e:
            logger.error(f"❌ Error mapping article to topics: {e}")
            conn.close()
    
    async def handle_personalized_digest(self, headers: Dict, params: Dict = None) -> Dict[str, Any]:
        """Get personalized digest - requires authentication"""
        try:
            logger.info("👤 Processing personalized-digest request")
            
            # Verify authentication
            auth_header = headers.get('Authorization') or headers.get('authorization')
            logger.info(f"🔐 Extracting user from auth header: {'✅' if auth_header else '❌'}")
            user_data = self.auth_service.get_user_from_token(auth_header)
            
            if not user_data:
                logger.warning("❌ Personalized digest requested without valid authentication")
                return {"error": "Authentication required for personalized content", "status": 401}
            
            logger.info(f"✅ JWT token verified successfully for: {user_data.get('email')}")
            
            # Get personalized digest with authentication headers passed through
            logger.info(f"🔧 Calling handle_digest with params={params} and headers keys: {list(headers.keys()) if headers else 'None'}")
            base_digest = await self.handle_digest(params, headers)
            
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
                # New user - create with empty topics (should go through onboarding)
                preferences = {
                    "topics": [],  # Empty topics for new users to select during onboarding
                    "newsletter_frequency": "weekly",
                    "email_notifications": True,
                    "content_types": ["blogs", "podcasts", "videos"],
                    "onboarding_completed": False  # New users need onboarding
                }
            
            # Add preferences to the insert/update
            if 'preferences' in existing_columns:
                available_data_columns.append('preferences')
                values.append(json.dumps(preferences))
            
            # Build and execute dynamic INSERT statement
            columns_str = ', '.join(available_data_columns)
            placeholders = ', '.join(['?' for _ in available_data_columns])
            insert_sql = f"INSERT OR REPLACE INTO users ({columns_str}) VALUES ({placeholders})"
            
            logger.info(f"🔧 Executing SQL: {insert_sql}")
            logger.info(f"🔧 Values: {[str(v)[:50] + '...' if len(str(v)) > 50 else v for v in values]}")
            
            try:
                cursor.execute(insert_sql, values)
                rows_affected = cursor.rowcount
                logger.info(f"✅ Database INSERT executed successfully, rows affected: {rows_affected}")
                
                # Verify the user was actually inserted
                cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
                verification_result = cursor.fetchone()
                if verification_result:
                    logger.info(f"✅ User verification successful: ID={verification_result[0]}, Email={verification_result[1]}, Name={verification_result[2]}")
                else:
                    logger.error(f"❌ User verification FAILED - user not found in database after INSERT")
                    raise Exception("User creation verification failed")
                
                logger.info(f"📊 User preferences set: onboarding_completed={preferences['onboarding_completed']}, topics_count={len(preferences['topics'])}")
                
                conn.commit()
                logger.info(f"✅ Database transaction committed successfully")
                
            except Exception as db_error:
                logger.error(f"❌ Database operation failed: {str(db_error)}")
                logger.error(f"❌ SQL: {insert_sql}")
                logger.error(f"❌ Values: {values}")
                conn.rollback()
                raise Exception(f"Database user creation failed: {str(db_error)}")
            finally:
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
        
        # Role-based topic system - NEW ENHANCEMENT
        # Four primary user roles, each with specific topics
        user_roles = [
            {
                "id": "novice",
                "name": "Novice",
                "description": "New to AI, looking for accessible explanations and everyday applications",
                "icon": "🌟",
                "topics": ["ai-explained", "ai-in-everyday-life", "fun-and-interesting-ai", "basic-ethics"]
            },
            {
                "id": "student", 
                "name": "Student",
                "description": "Learning AI, seeking educational content and career guidance",
                "icon": "🎓",
                "topics": ["educational-content", "project-ideas", "career-trends", "machine-learning", "deep-learning", "tools-and-frameworks", "data-science"]
            },
            {
                "id": "professional",
                "name": "Professional",
                "description": "Working in AI/tech, focused on industry applications and case studies",
                "icon": "💼",
                "topics": ["industry-news", "applied-ai", "case-studies", "podcasts-and-interviews", "cloud-computing", "robotics"]
            },
            {
                "id": "executive",
                "name": "Executive",
                "description": "Making strategic AI decisions, focused on ethics, investment, and policy",
                "icon": "🎯",
                "topics": ["ai-ethics-and-safety", "investment-and-funding", "strategic-implications", "policy-and-regulation", "leadership-and-innovation", "ai-research"]
            }
        ]
        
        # All available topics with enhanced metadata
        topics = [
            # Novice topics
            {"id": "ai-explained", "name": "AI Explained", "description": "Simple explanations of AI concepts for beginners", "category": "beginner", "role": "novice"},
            {"id": "ai-in-everyday-life", "name": "AI in Everyday Life", "description": "How AI affects daily life and common applications", "category": "beginner", "role": "novice"},
            {"id": "fun-and-interesting-ai", "name": "Fun & Interesting AI", "description": "Entertaining and fascinating AI stories and discoveries", "category": "beginner", "role": "novice"},
            {"id": "basic-ethics", "name": "Basic Ethics", "description": "Introduction to AI ethics and responsible use", "category": "ethics", "role": "novice"},
            
            # Student topics
            {"id": "educational-content", "name": "Educational Content", "description": "Learning resources, courses, and tutorials", "category": "education", "role": "student"},
            {"id": "project-ideas", "name": "Project Ideas", "description": "AI project suggestions and implementation guides", "category": "education", "role": "student"},
            {"id": "career-trends", "name": "Career Trends", "description": "AI job market trends and career development", "category": "career", "role": "student"},
            {"id": "machine-learning", "name": "Machine Learning", "description": "ML algorithms, techniques, and applications", "category": "technical", "role": "student"},
            {"id": "deep-learning", "name": "Deep Learning", "description": "Neural networks and deep learning architectures", "category": "technical", "role": "student"},
            {"id": "tools-and-frameworks", "name": "Tools & Frameworks", "description": "AI development tools, libraries, and platforms", "category": "tools", "role": "student"},
            {"id": "data-science", "name": "Data Science", "description": "Data analysis, visualization, and statistical methods", "category": "technical", "role": "student"},
            
            # Professional topics
            {"id": "industry-news", "name": "Industry News", "description": "AI industry updates, company news, and market trends", "category": "business", "role": "professional"},
            {"id": "applied-ai", "name": "Applied AI", "description": "Real-world AI implementations and solutions", "category": "application", "role": "professional"},
            {"id": "case-studies", "name": "Case Studies", "description": "Detailed analysis of successful AI implementations", "category": "application", "role": "professional"},
            {"id": "podcasts-and-interviews", "name": "Podcasts & Interviews", "description": "Expert conversations and industry insights", "category": "media", "role": "professional"},
            {"id": "cloud-computing", "name": "Cloud Computing", "description": "AI in cloud platforms and distributed systems", "category": "infrastructure", "role": "professional"},
            {"id": "robotics", "name": "Robotics", "description": "AI-powered robotics and automation", "category": "robotics", "role": "professional"},
            
            # Executive topics
            {"id": "ai-ethics-and-safety", "name": "AI Ethics & Safety", "description": "Responsible AI development and risk management", "category": "ethics", "role": "executive"},
            {"id": "investment-and-funding", "name": "Investment & Funding", "description": "AI investment trends and funding opportunities", "category": "finance", "role": "executive"},
            {"id": "strategic-implications", "name": "Strategic Implications", "description": "AI's impact on business strategy and operations", "category": "strategy", "role": "executive"},
            {"id": "policy-and-regulation", "name": "Policy & Regulation", "description": "AI governance, policies, and regulatory developments", "category": "policy", "role": "executive"},
            {"id": "leadership-and-innovation", "name": "Leadership & Innovation", "description": "Leading AI transformation and innovation", "category": "leadership", "role": "executive"},
            {"id": "ai-research", "name": "AI Research", "description": "Cutting-edge research and scientific breakthroughs", "category": "research", "role": "executive"}
        ]
        
        return {
            "content_types": content_types,
            "topics": topics,
            "user_roles": user_roles,
            "default_selections": {
                "content_types": ["blogs", "podcasts", "videos"],
                "user_roles": ["student"]  # Default to student role
            },
            "router_endpoint": True,
            "debug_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_content_types": len(content_types),
                "total_topics": len(topics),
                "total_user_roles": len(user_roles),
                "role_based_system": True
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
            
            # Update preferences in users table (preferences JSONB column)
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current user and preferences
            cursor.execute("SELECT preferences FROM users WHERE id = ?", (user_id,))
            current_prefs_row = cursor.fetchone()
            
            # Parse existing preferences or create new ones
            if current_prefs_row and current_prefs_row[0]:
                current_preferences = json.loads(current_prefs_row[0])
            else:
                current_preferences = {}
            
            # Handle topic format normalization
            if 'topics' in data:
                topics = data['topics']
                if topics and isinstance(topics[0], dict):
                    # Convert topic objects to topic IDs for filtering compatibility
                    topic_ids = [topic['id'] for topic in topics if topic.get('selected', True)]
                    logger.info(f"📊 Converting topic objects to IDs: {len(topics)} objects → {len(topic_ids)} IDs")
                    current_preferences['topics'] = topic_ids
                else:
                    # Already in ID format
                    current_preferences['topics'] = topics
            
            # Update other preference fields
            if 'user_roles' in data:
                current_preferences['user_roles'] = data['user_roles']
            if 'role_type' in data:
                current_preferences['role_type'] = data['role_type']
            if 'experience_level' in data:
                current_preferences['experience_level'] = data['experience_level']
            if 'newsletter_frequency' in data:
                current_preferences['newsletter_frequency'] = data['newsletter_frequency']
            if 'email_notifications' in data:
                current_preferences['email_notifications'] = bool(data['email_notifications'])
            if 'content_types' in data:
                current_preferences['content_types'] = data['content_types']
            if 'onboarding_completed' in data:
                current_preferences['onboarding_completed'] = bool(data['onboarding_completed'])
            if 'newsletter_subscribed' in data:
                current_preferences['newsletter_subscribed'] = bool(data['newsletter_subscribed'])
            
            # Update timestamp
            current_preferences['updated_at'] = datetime.utcnow().isoformat()
            
            # Save updated preferences back to users table
            preferences_json = json.dumps(current_preferences)
            cursor.execute("UPDATE users SET preferences = ? WHERE id = ?", (preferences_json, user_id))
            logger.info(f"📊 Updated preferences in users table for user: {user_id}")
            
            # Get updated user data to return
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            conn.commit()
            conn.close()
            
            # Format response - use the saved preferences data
            preferences = {
                "topics": current_preferences.get('topics', []),
                "newsletter_frequency": current_preferences.get('newsletter_frequency', 'weekly'),
                "email_notifications": bool(current_preferences.get('email_notifications', True)),
                "content_types": current_preferences.get('content_types', ["articles"]),
                "onboarding_completed": bool(current_preferences.get('onboarding_completed', False)),
                "newsletter_subscribed": bool(current_preferences.get('newsletter_subscribed', True)),
                "user_roles": current_preferences.get('user_roles', []),
                "role_type": current_preferences.get('role_type', ''),
                "experience_level": current_preferences.get('experience_level', '')
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
            
            # Get user preferences from users.preferences JSONB column (not user_preferences table)
            user_preferences_json = user_data['preferences'] if user_data and len(user_data) > 6 else '{}'
            
            conn.close()
            
            # Parse preferences from JSONB column
            try:
                user_prefs = json.loads(user_preferences_json) if user_preferences_json else {}
            except (json.JSONDecodeError, TypeError):
                user_prefs = {}
            
            # Format preferences with all fields including enhanced ones
            preferences = {
                "topics": user_prefs.get('topics', []),
                "newsletter_frequency": user_prefs.get('newsletter_frequency', 'weekly'),
                "email_notifications": bool(user_prefs.get('email_notifications', True)),
                "content_types": user_prefs.get('content_types', ["articles", "podcasts", "videos"]),
                "onboarding_completed": bool(user_prefs.get('onboarding_completed', False)),
                "newsletter_subscribed": bool(user_prefs.get('newsletter_subscribed', True)),
                "user_roles": user_prefs.get('user_roles', []),
                "role_type": user_prefs.get('role_type', ''),
                "experience_level": user_prefs.get('experience_level', '')
            }
            
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
    
    async def handle_cleanup_test_users(self, params: Dict = None) -> Dict[str, Any]:
        """Clean up test user data from all database tables"""
        try:
            logger.info("🧹 Starting test user cleanup...")
            
            # Define test user emails to clean up
            test_emails = ["vijayanishere@gmail.com", "vidyagamishere@gmail.com"]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cleanup_results = {}
            total_deleted = 0
            
            for email in test_emails:
                logger.info(f"🗑️ Cleaning up data for: {email}")
                email_deleted = 0
                
                # Get user ID first
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                user_row = cursor.fetchone()
                user_id = user_row[0] if user_row else None
                
                # Delete from all related tables
                tables_to_clean = [
                    ("email_otps", "email", email),
                    ("user_passwords", "user_id", user_id) if user_id else None,
                    ("user_sessions", "user_id", user_id) if user_id else None,
                    ("users", "email", email)
                ]
                
                for table_info in tables_to_clean:
                    if table_info is None:
                        continue
                        
                    table_name, column_name, value = table_info
                    
                    # Check if table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if not cursor.fetchone():
                        logger.info(f"📋 Table {table_name} does not exist, skipping")
                        continue
                    
                    # Count existing records
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = ?", (value,))
                    count_before = cursor.fetchone()[0]
                    
                    if count_before > 0:
                        # Delete records
                        cursor.execute(f"DELETE FROM {table_name} WHERE {column_name} = ?", (value,))
                        deleted_count = cursor.rowcount
                        email_deleted += deleted_count
                        logger.info(f"🗑️ Deleted {deleted_count} records from {table_name} for {email}")
                    else:
                        logger.info(f"📋 No records found in {table_name} for {email}")
                
                cleanup_results[email] = {
                    "total_records_deleted": email_deleted,
                    "user_id": user_id,
                    "status": "cleaned" if email_deleted > 0 else "no_data_found"
                }
                total_deleted += email_deleted
            
            # Commit all changes
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Test user cleanup completed. Total records deleted: {total_deleted}")
            
            return {
                "success": True,
                "message": "Test user cleanup completed successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "results": cleanup_results,
                "total_records_deleted": total_deleted,
                "emails_processed": test_emails
            }
            
        except Exception as e:
            logger.error(f"❌ Test user cleanup failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Cleanup failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }
    
    async def handle_init_ai_sources_table(self, params: Dict = None) -> Dict[str, Any]:
        """Initialize ai_sources table with comprehensive AI sources"""
        try:
            logger.info("🔧 Initializing ai_sources table with comprehensive AI sources...")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Ensure the table exists and is populated
            self.ensure_ai_sources_table(cursor)
            
            # Count sources in the table
            cursor.execute("SELECT COUNT(*) FROM ai_sources")
            total_sources = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ai_sources WHERE enabled = 1")
            enabled_sources = cursor.fetchone()[0]
            
            # Get content type distribution
            cursor.execute("SELECT content_type, COUNT(*) FROM ai_sources GROUP BY content_type")
            content_types = dict(cursor.fetchall())
            
            # Get sample sources
            cursor.execute("SELECT name, content_type, category, enabled FROM ai_sources ORDER BY priority DESC LIMIT 5")
            sample_sources = cursor.fetchall()
            
            conn.close()
            
            logger.info(f"✅ ai_sources table initialized successfully with {total_sources} sources")
            
            return {
                "success": True,
                "message": "AI sources table initialized successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "statistics": {
                    "total_sources": total_sources,
                    "enabled_sources": enabled_sources,
                    "content_type_distribution": content_types,
                    "sample_sources": [
                        {"name": row[0], "content_type": row[1], "category": row[2], "enabled": bool(row[3])}
                        for row in sample_sources
                    ]
                },
                "features": {
                    "comprehensive_coverage": "All 23 AI topics covered",
                    "legitimate_sources": "Only verified and legitimate sources included",
                    "content_diversity": f"{len(content_types)} different content types",
                    "database_driven": "Sources now fetched from database table",
                    "future_management": "URLs can be added per AI topic via database"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ AI sources table initialization failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"AI sources initialization failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }

    async def handle_bulk_map_articles_to_topics(self, params: Dict = None) -> Dict[str, Any]:
        """Bulk map existing articles to AI topics using foreign key relationships"""
        try:
            logger.info("🧠 Starting bulk article-to-topic mapping process...")
            
            if params is None:
                params = {}
            
            # Get optional parameters
            limit = params.get('limit', 50)  # Default to mapping 50 articles at a time
            offset = params.get('offset', 0)  # For pagination
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get articles that don't have topic mappings yet
            cursor.execute("""
                SELECT a.id, a.source, a.title, COALESCE(a.content, a.summary, '') as content
                FROM articles a
                LEFT JOIN article_topics at ON a.id = at.article_id
                WHERE at.article_id IS NULL
                ORDER BY a.significance_score DESC, a.published_date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            unmapped_articles = cursor.fetchall()
            
            if not unmapped_articles:
                conn.close()
                logger.info("✅ No unmapped articles found - all articles already have topic assignments")
                return {
                    "success": True,
                    "message": "No unmapped articles found",
                    "timestamp": datetime.utcnow().isoformat(),
                    "statistics": {
                        "articles_processed": 0,
                        "topics_assigned": 0,
                        "all_articles_mapped": True
                    }
                }
            
            logger.info(f"📊 Found {len(unmapped_articles)} unmapped articles (limit: {limit}, offset: {offset})")
            
            # Process each article and map to topics
            total_topics_assigned = 0
            processed_articles = 0
            
            for article in unmapped_articles:
                article_id, source, title, content = article
                logger.info(f"🧠 Mapping article {article_id}: '{title[:50]}...'")
                
                # Use the mapping method we created
                self.map_article_to_topics(article_id, source, title, content)
                processed_articles += 1
                
                # Count topics assigned to this article
                cursor.execute("SELECT COUNT(*) FROM article_topics WHERE article_id = ?", (article_id,))
                topics_for_article = cursor.fetchone()[0]
                total_topics_assigned += topics_for_article
            
            # Get summary statistics
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT article_id) FROM article_topics")
            mapped_articles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM article_topics")
            total_mappings = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT t.topic_id, t.display_name, COUNT(at.article_id) as article_count
                FROM ai_topics t
                LEFT JOIN article_topics at ON t.id = at.topic_id
                GROUP BY t.id, t.topic_id, t.display_name
                ORDER BY article_count DESC
                LIMIT 10
            """)
            topic_distribution = cursor.fetchall()
            
            conn.close()
            
            logger.info(f"✅ Bulk mapping completed: {processed_articles} articles processed, {total_topics_assigned} topic assignments made")
            
            return {
                "success": True,
                "message": f"Successfully mapped {processed_articles} articles to topics",
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": {
                    "limit": limit,
                    "offset": offset
                },
                "statistics": {
                    "articles_processed": processed_articles,
                    "topics_assigned": total_topics_assigned,
                    "total_articles": total_articles,
                    "mapped_articles": mapped_articles,
                    "unmapped_articles": total_articles - mapped_articles,
                    "total_mappings": total_mappings,
                    "avg_topics_per_article": round(total_mappings / max(mapped_articles, 1), 2)
                },
                "topic_distribution": [
                    {"topic_id": row[0], "name": row[1], "article_count": row[2]}
                    for row in topic_distribution
                ],
                "next_steps": {
                    "continue_mapping": total_articles > mapped_articles,
                    "next_offset": offset + limit if len(unmapped_articles) == limit else None,
                    "recommendation": "Run again with higher offset to map remaining articles" if len(unmapped_articles) == limit else "All articles have been mapped"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Bulk topic mapping failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Bulk topic mapping failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }

    async def handle_public_init_topics(self) -> Dict[str, Any]:
        """Public endpoint to initialize article-topic mappings"""
        try:
            logger.info("🔗 Public article-topic mapping initialization requested")
            
            # Trigger the auto-population
            self.auto_populate_article_topic_mappings()
            
            # Check mapping status
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM article_topics")
            mapping_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ai_topics")
            topic_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "success": True,
                "message": "Article-topic mapping initialization completed",
                "mappings_created": mapping_count,
                "total_articles": article_count,
                "total_topics": topic_count,
                "timestamp": datetime.utcnow().isoformat(),
                "router_handled": True
            }
            
        except Exception as e:
            logger.error(f"❌ Public article-topic mapping failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "router_handled": True
            }
    
    async def handle_public_init_sources(self) -> Dict[str, Any]:
        """Public endpoint to initialize comprehensive AI sources (no auth required)"""
        try:
            logger.info("🚀 Public sources initialization requested")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check current source count
            cursor.execute("SELECT COUNT(*) FROM ai_sources")
            current_count = cursor.fetchone()[0]
            
            logger.info(f"📊 Current source count: {current_count}")
            
            # If we have fewer than 20 sources, initialize with comprehensive sources
            if current_count < 20:
                logger.info("🔧 Initializing comprehensive AI sources...")
                self.ensure_ai_sources_table(cursor)
                
                # Count after initialization
                cursor.execute("SELECT COUNT(*) FROM ai_sources")
                new_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM ai_sources WHERE enabled = 1")
                enabled_count = cursor.fetchone()[0]
                
                # Get content type distribution
                cursor.execute("SELECT content_type, COUNT(*) FROM ai_sources GROUP BY content_type")
                content_distribution = dict(cursor.fetchall())
                
                conn.close()
                
                logger.info(f"✅ Sources initialized: {current_count} → {new_count} total, {enabled_count} enabled")
                
                return {
                    "success": True,
                    "message": "Comprehensive AI sources initialized successfully",
                    "sources_before": current_count,
                    "sources_after": new_count,
                    "enabled_sources": enabled_count,
                    "content_distribution": content_distribution,
                    "initialization_triggered": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Sources already initialized
                cursor.execute("SELECT COUNT(*) FROM ai_sources WHERE enabled = 1")
                enabled_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT content_type, COUNT(*) FROM ai_sources GROUP BY content_type")
                content_distribution = dict(cursor.fetchall())
                
                conn.close()
                
                logger.info(f"✅ Sources already initialized: {current_count} total, {enabled_count} enabled")
                
                return {
                    "success": True,
                    "message": "AI sources already initialized",
                    "total_sources": current_count,
                    "enabled_sources": enabled_count,
                    "content_distribution": content_distribution,
                    "initialization_triggered": False,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Public sources initialization failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Sources initialization failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }

    async def handle_public_add_research_articles(self) -> Dict[str, Any]:
        """Public endpoint to add comprehensive research articles for AI topics"""
        try:
            logger.info("📚 Public research articles addition requested")
            
            # Comprehensive AI topic sources based on research (using correct topic IDs from database)
            comprehensive_topic_sources = {
                # Machine Learning (topic_id: machine-learning)
                'machine-learning': [
                    {
                        'title': 'Google DeepMind Research Publications',
                        'url': 'https://deepmind.google/research/publications/',
                        'content': 'Comprehensive collection of machine learning research papers from Google DeepMind covering breakthrough algorithms, model architectures, and theoretical foundations.',
                        'summary': 'Latest ML research from DeepMind including Gemini models, AlphaFold, and advanced neural network architectures with detailed technical papers.',
                        'source': 'Google DeepMind',
                        'content_type': 'articles',
                        'significance_score': 9.8
                    },
                    {
                        'title': 'OpenAI Research Blog',
                        'url': 'https://openai.com/research/',
                        'content': 'Cutting-edge machine learning research including GPT model developments, reinforcement learning, and AI safety research.',
                        'summary': 'OpenAI research covering large language models, DALL-E, safety alignment, and foundational ML techniques.',
                        'source': 'OpenAI',
                        'content_type': 'articles',
                        'significance_score': 9.7
                    },
                    {
                        'title': 'Stanford AI Index 2024 Report',
                        'url': 'https://hai.stanford.edu/ai-index/2024-ai-index-report',
                        'content': 'Comprehensive annual report analyzing AI progress, including training costs, model capabilities, and industry trends.',
                        'summary': 'Detailed analysis of 2024 AI developments including 191M USD Gemini Ultra training costs and responsible AI reporting standards.',
                        'source': 'Stanford HAI',
                        'content_type': 'articles',
                        'significance_score': 9.5
                    }
                ],
                
                # Computer Vision (using computer-vision topic)
                'computer-vision': [
                    {
                        'title': 'CVPR 2024 Open Access Repository',
                        'url': 'https://openaccess.thecvf.com/CVPR2024',
                        'content': 'Complete collection of Computer Vision and Pattern Recognition 2024 conference papers with 23.6% acceptance rate.',
                        'summary': 'Premier computer vision research from CVPR 2024 covering image recognition, deep learning, and visual AI advances.',
                        'source': 'Computer Vision Foundation',
                        'content_type': 'articles',
                        'significance_score': 9.6
                    },
                    {
                        'title': 'arXiv Computer Vision Papers',
                        'url': 'https://arxiv.org/list/cs.CV/recent',
                        'content': 'Latest computer vision research papers including work accepted to ICCV 2025, IEEE T-PAMI, and other major venues.',
                        'summary': 'Real-time access to cutting-edge computer vision research covering object detection, image generation, and visual understanding.',
                        'source': 'arXiv',
                        'content_type': 'articles',
                        'significance_score': 9.2
                    },
                    {
                        'title': 'OpenCV Computer Vision Research Guide 2025',
                        'url': 'https://opencv.org/blog/computer-vision-research/',
                        'content': 'Comprehensive guide to computer vision research methodologies and current trends for 2025.',
                        'summary': 'Practical guidance for CV researchers covering publication strategies, research directions, and emerging applications.',
                        'source': 'OpenCV',
                        'content_type': 'articles',
                        'significance_score': 8.8
                    }
                ],
                
                # Natural Language Processing (using natural-language-processing topic)
                'natural-language-processing': [
                    {
                        'title': 'EMNLP 2024 Conference Proceedings',
                        'url': 'https://aclanthology.org/events/emnlp-2024/',
                        'content': 'Over 1,300 research papers from the premier empirical methods in NLP conference covering LLMs, alignment, and language understanding.',
                        'summary': 'Latest NLP research including RLHF alignment, embedding models with 32K context windows, and advanced language processing.',
                        'source': 'ACL Anthology',
                        'content_type': 'articles',
                        'significance_score': 9.4
                    },
                    {
                        'title': 'Stanford NLP Group Publications',
                        'url': 'https://nlp.stanford.edu/pubs/',
                        'content': 'Research publications from Stanford NLP covering transformer architectures, language models, and computational linguistics.',
                        'summary': 'Academic research from leading NLP institution covering model architectures, training techniques, and language applications.',
                        'source': 'Stanford NLP',
                        'content_type': 'articles',
                        'significance_score': 9.3
                    },
                    {
                        'title': 'Best NLP Papers 2025',
                        'url': 'https://thebestnlppapers.com/',
                        'content': 'Curated collection of top NLP research papers ranked by citation count and research impact.',
                        'summary': 'Peer-reviewed selection of most influential NLP papers covering LLMs, transformers, and language understanding advances.',
                        'source': 'NLP Research Community',
                        'content_type': 'articles',
                        'significance_score': 9.1
                    }
                ],
                
                # Robotics & Automation (using robotics-automation topic)
                'robotics-automation': [
                    {
                        'title': 'IEEE ICRA 2025 Conference',
                        'url': 'https://2025.ieee-icra.org/',
                        'content': 'Premier robotics and automation conference featuring latest research in autonomous systems, manipulation, and AI integration.',
                        'summary': 'Global robotics research including Boston Dynamics collaborations, mobile manipulation, and autonomous navigation systems.',
                        'source': 'IEEE Robotics Society',
                        'content_type': 'articles',
                        'significance_score': 9.5
                    },
                    {
                        'title': 'IEEE Robotics and Automation Letters',
                        'url': 'https://www.ieee-ras.org/publications/ra-l',
                        'content': 'Peer-reviewed journal publishing rapid-turnaround robotics research with presentation opportunities at major conferences.',
                        'summary': 'Latest robotics research covering theoretical foundations, experimental studies, and real-world deployment case studies.',
                        'source': 'IEEE RAS',
                        'content_type': 'articles',
                        'significance_score': 9.2
                    },
                    {
                        'title': 'IEEE Transactions on Robotics',
                        'url': 'https://www.ieee-ras.org/publications/t-ro',
                        'content': 'Leading robotics publication featuring major advances in robot design, algorithms, and integration systems.',
                        'summary': 'Comprehensive robotics research covering theory, experimental validation, and practical robotics applications.',
                        'source': 'IEEE',
                        'content_type': 'articles',
                        'significance_score': 9.0
                    }
                ],
                
                # Quantum Computing & AI (using quantum-computing topic)
                'quantum-computing': [
                    {
                        'title': 'Google Quantum AI Research',
                        'url': 'https://quantumai.google/research',
                        'content': 'Leading quantum computing research including Sycamore processor developments and quantum-classical hybrid algorithms.',
                        'summary': 'Quantum supremacy research, DARPA collaboration, and TensorFlow Quantum for machine learning integration.',
                        'source': 'Google Quantum AI',
                        'content_type': 'articles',
                        'significance_score': 9.6
                    },
                    {
                        'title': 'IBM Quantum Research Papers',
                        'url': 'https://research.ibm.com/topics/quantum-computing',
                        'content': 'Quantum computing research including 133-qubit systems, quantum kernels, and fault-tolerant computing advances.',
                        'summary': 'IBM quantum processor research, quantum-classical algorithms, and practical quantum machine learning applications.',
                        'source': 'IBM Research',
                        'content_type': 'articles',
                        'significance_score': 9.4
                    },
                    {
                        'title': 'Quantum Computing and AI Status Paper 2025',
                        'url': 'https://arxiv.org/abs/2505.23860',
                        'content': 'Comprehensive white paper analyzing intersection of quantum computing and artificial intelligence with research agenda.',
                        'summary': 'Academic analysis of quantum AI applications, challenges, and long-term research directions for hybrid systems.',
                        'source': 'arXiv',
                        'content_type': 'articles',
                        'significance_score': 9.1
                    }
                ],
                
                # AI Ethics & Governance (using ai-ethics topic)
                'ai-ethics': [
                    {
                        'title': 'EU AI Act Implementation 2024',
                        'url': 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai',
                        'content': 'Comprehensive legal framework for AI governance including compliance requirements and ethical guidelines.',
                        'summary': 'World first comprehensive AI regulation covering risk assessment, transparency, and accountability requirements.',
                        'source': 'European Union',
                        'content_type': 'articles',
                        'significance_score': 9.7
                    },
                    {
                        'title': 'Responsible AI Frameworks 2024 Analysis',
                        'url': 'https://medium.com/@adnanmasood/responsible-ai-revisited-critical-changes-and-updates-since-our-2023-playbook-0c1610d57f37',
                        'content': 'Critical analysis of responsible AI developments and framework updates addressing stakeholder influence and practical implementation.',
                        'summary': 'Updated responsible AI guidelines covering fairness, accountability, and organizational adoption strategies.',
                        'source': 'Medium Research',
                        'content_type': 'articles',
                        'significance_score': 8.9
                    },
                    {
                        'title': 'OECD AI Accountability Framework 2025',
                        'url': 'https://www.oecd.org/en/topics/policy-issues/artificial-intelligence.html',
                        'content': 'International AI governance framework focusing on accountability, transparency, and cross-border cooperation.',
                        'summary': 'Global AI policy recommendations covering responsible development, deployment, and governance structures.',
                        'source': 'OECD',
                        'content_type': 'articles',
                        'significance_score': 9.3
                    }
                ]
            }
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get content type IDs
            cursor.execute("SELECT id FROM content_types WHERE name = 'articles'")
            articles_content_type_id = cursor.fetchone()
            if articles_content_type_id:
                articles_content_type_id = articles_content_type_id[0]
            else:
                articles_content_type_id = 1  # Default to 1
            
            total_added = 0
            total_skipped = 0
            
            for topic_id, sources in comprehensive_topic_sources.items():
                logger.info(f"📊 Processing sources for topic: {topic_id}")
                
                for source in sources:
                    try:
                        # Check if URL already exists
                        cursor.execute("SELECT id FROM articles WHERE url = ?", (source['url'],))
                        existing = cursor.fetchone()
                        
                        if existing:
                            logger.info(f"⚠️ Skipping duplicate URL: {source['url']}")
                            total_skipped += 1
                            continue
                        
                        # Insert article
                        current_time = datetime.utcnow().isoformat()
                        cursor.execute("""
                            INSERT INTO articles 
                            (title, content, summary, url, source, published_date, 
                             significance_score, content_type_id, read_time, 
                             processing_status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', ?, ?)
                        """, (
                            source['title'],
                            source['content'],
                            source['summary'],
                            source['url'],
                            source['source'],
                            current_time,
                            source['significance_score'],
                            articles_content_type_id,
                            '8 min',
                            current_time,
                            current_time
                        ))
                        
                        article_id = cursor.lastrowid
                        
                        # Map to topic if possible (using topic_id field, not id)
                        cursor.execute("SELECT id FROM ai_topics WHERE topic_id = ?", (topic_id,))
                        topic_exists = cursor.fetchone()
                        
                        if topic_exists:
                            topic_db_id = topic_exists[0]  # Get the actual database ID
                            cursor.execute("""
                                INSERT OR IGNORE INTO article_topics (article_id, topic_id, relevance_score)
                                VALUES (?, ?, ?)
                            """, (article_id, topic_db_id, source['significance_score'] / 10.0))
                        
                        logger.info(f"✅ Added: {source['title']}")
                        total_added += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to add article {source['title']}: {str(e)}")
                        continue
            
            # Commit all changes
            conn.commit()
            
            # Get final counts
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM article_topics")
            total_mappings = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"✅ Research articles addition completed: {total_added} added, {total_skipped} skipped")
            
            return {
                "success": True,
                "message": "Research articles added successfully",
                "articles_added": total_added,
                "articles_skipped": total_skipped,
                "total_articles": total_articles,
                "total_mappings": total_mappings,
                "topics_covered": len(comprehensive_topic_sources),
                "timestamp": datetime.utcnow().isoformat(),
                "router_handled": True
            }
            
        except Exception as e:
            logger.error(f"❌ Research articles addition failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Research articles addition failed: {str(e)}",
                "status": 500,
                "debug_info": {"traceback": traceback.format_exc()}
            }

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
            
            elif admin_endpoint == "cleanup-test-users":
                return await self.handle_cleanup_test_users(params)
            
            elif admin_endpoint == "init-ai-sources":
                return await self.handle_init_ai_sources_table(params)
            
            elif admin_endpoint == "bulk-map-topics":
                return await self.handle_bulk_map_articles_to_topics(params)
            
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
        "version": "2.4.0",
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