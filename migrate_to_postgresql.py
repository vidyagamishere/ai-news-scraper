#!/usr/bin/env python3
"""
Migrate SQLite database to PostgreSQL on Railway
This script handles the complete migration including schema and data
"""
import sqlite3
import json
import os
import sys
from datetime import datetime
import traceback

# Configuration
SQLITE_PATH = '/Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper/ai_news.db'
OUTPUT_FILE = '/Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper/postgresql_migration.sql'

# Complete PostgreSQL schema matching current normalized database
POSTGRESQL_SCHEMA = """
-- PostgreSQL Migration Script for AI News Scraper
-- Generated: {timestamp}
-- Source: SQLite Database -> PostgreSQL

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS article_topics CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS daily_archives CASCADE;
DROP TABLE IF EXISTS user_passwords CASCADE;
DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS ai_topics CASCADE;
DROP TABLE IF EXISTS content_types CASCADE;
DROP TABLE IF EXISTS ai_sources CASCADE;

-- ============================================
-- 1. CONTENT TYPES TABLE
-- ============================================
CREATE TABLE content_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert master content types
INSERT INTO content_types (name, display_name, description, icon, is_active) VALUES
('blogs', 'Blog Articles', 'Traditional blog posts and written articles', 'article', true),
('podcasts', 'Podcasts', 'Audio content and podcast episodes', 'headphones', true),
('videos', 'Videos', 'Video content and tutorials', 'play', true),
('events', 'Events', 'Conferences, webinars, and industry events', 'calendar', true),
('learning', 'Learning', 'Educational content and courses', 'book', true),
('demos', 'Demos', 'Interactive demonstrations and prototypes', 'code', true);

-- ============================================
-- 2. AI TOPICS TABLE
-- ============================================
CREATE TABLE ai_topics (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert comprehensive AI topics
INSERT INTO ai_topics (id, name, description, category, is_active) VALUES
('machine-learning', 'Machine Learning', 'Core ML algorithms, techniques, and foundations', 'research', true),
('deep-learning', 'Deep Learning', 'Neural networks, deep learning research and applications', 'research', true),
('nlp-llm', 'Natural Language Processing', 'Language models, NLP, and conversational AI', 'language', true),
('computer-vision', 'Computer Vision', 'Image recognition, visual AI, and computer vision', 'research', true),
('ai-tools', 'AI Tools & Platforms', 'New AI tools and platforms for developers', 'platform', true),
('ai-research', 'AI Research Papers', 'Latest academic research and scientific breakthroughs', 'research', true),
('ai-ethics-and-safety', 'AI Ethics & Safety', 'Responsible AI, safety research, and ethical considerations', 'policy', true),
('robotics', 'Robotics & Automation', 'Physical AI, robotics, and automation systems', 'robotics', true),
('ai-business', 'AI in Business', 'Enterprise AI and industry applications', 'company', true),
('ai-startups', 'AI Startups & Funding', 'New AI companies and startup ecosystem', 'startup', true),
('ai-regulation', 'AI Policy & Regulation', 'Government policies and AI governance', 'policy', true),
('ai-hardware', 'AI Hardware & Computing', 'AI chips and hardware innovations', 'hardware', true),
('ai-automotive', 'AI in Automotive', 'Self-driving cars and automotive AI', 'automotive', true),
('ai-healthcare', 'AI in Healthcare', 'Medical AI applications and healthcare tech', 'healthcare', true),
('ai-finance', 'AI in Finance', 'Financial AI, trading, and fintech applications', 'finance', true),
('ai-gaming', 'AI in Gaming', 'Game AI, procedural generation, and gaming tech', 'gaming', true),
('ai-creative', 'AI in Creative Arts', 'AI for art, music, design, and creative content', 'creative', true),
('ai-cloud', 'AI Cloud Services', 'Cloud-based AI services and infrastructure', 'cloud', true),
('ai-events', 'AI Events & Conferences', 'AI conferences, workshops, and industry events', 'events', true),
('ai-explained', 'AI Learning & Education', 'AI courses, tutorials, and educational content', 'learning', true),
('industry-news', 'AI News & Updates', 'Latest AI news and industry updates', 'news', true),
('international-ai', 'AI International', 'Global AI developments and international news', 'international', true);

-- ============================================
-- 3. USERS TABLE
-- ============================================
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    verified_email BOOLEAN DEFAULT false,
    preferences JSONB DEFAULT '{{}}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- ============================================
-- 4. USER PASSWORDS TABLE
-- ============================================
CREATE TABLE user_passwords (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 5. USER SESSIONS TABLE
-- ============================================
CREATE TABLE user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

-- ============================================
-- 6. AI SOURCES TABLE
-- ============================================
CREATE TABLE ai_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    rss_url TEXT,
    content_type VARCHAR(50) REFERENCES content_types(name),
    priority INTEGER DEFAULT 5,
    enabled BOOLEAN DEFAULT true,
    last_scraped TIMESTAMP,
    success_rate DECIMAL(5,2) DEFAULT 100.0,
    meta_tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. ARTICLES TABLE (UNIFIED)
-- ============================================
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    summary TEXT,
    source VARCHAR(255),
    published_date TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    significance_score DECIMAL(3,1) DEFAULT 5.0,
    thumbnail_url TEXT,
    audio_url TEXT,
    duration INTEGER,
    content_type_id INTEGER REFERENCES content_types(id),
    processing_status VARCHAR(50) DEFAULT 'pending',
    content_hash VARCHAR(64),
    reading_time VARCHAR(20) DEFAULT '3 min',
    impact VARCHAR(20) DEFAULT 'medium'
);

-- ============================================
-- 8. ARTICLE-TOPIC JUNCTION TABLE
-- ============================================
CREATE TABLE article_topics (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    topic_id VARCHAR(100) REFERENCES ai_topics(id) ON DELETE CASCADE,
    relevance_score DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, topic_id)
);

-- ============================================
-- 9. DAILY ARCHIVES TABLE
-- ============================================
CREATE TABLE daily_archives (
    id SERIAL PRIMARY KEY,
    archive_date DATE UNIQUE NOT NULL,
    digest_data JSONB,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{{}}'
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX idx_articles_published_date ON articles(published_date);
CREATE INDEX idx_articles_significance_score ON articles(significance_score);
CREATE INDEX idx_articles_content_type ON articles(content_type_id);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_article_topics_article_id ON article_topics(article_id);
CREATE INDEX idx_article_topics_topic_id ON article_topics(topic_id);
CREATE INDEX idx_article_topics_relevance ON article_topics(relevance_score);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_daily_archives_date ON daily_archives(archive_date);

-- ============================================
-- OPTIMIZED VIEWS FOR LLM CONTENT DELIVERY
-- ============================================

-- View 1: Enhanced Articles with Content Types and Topics
CREATE VIEW v_enhanced_articles AS
SELECT 
    a.id,
    a.title,
    COALESCE(a.content, a.summary) as content,
    a.summary,
    a.source,
    a.published_date,
    CASE 
        WHEN a.impact = 'high' THEN 'high'
        WHEN a.impact = 'low' THEN 'low'
        ELSE 'medium'
    END as impact,
    ct.name as type,
    a.url,
    a.reading_time,
    a.significance_score,
    a.thumbnail_url,
    a.audio_url,
    a.duration,
    ct.display_name as content_type_display,
    CASE 
        WHEN ct.name IN ('blogs', 'learning') THEN 'blog'
        WHEN ct.name IN ('podcasts') THEN 'audio' 
        WHEN ct.name IN ('videos', 'demos') THEN 'video'
        ELSE 'blog'
    END as frontend_section,
    GROUP_CONCAT(DISTINCT ait.topic_id) as topic_ids,
    GROUP_CONCAT(DISTINCT ait_topics.name) as topic_names, 
    GROUP_CONCAT(DISTINCT ait_topics.category) as topic_categories,
    GROUP_CONCAT(DISTINCT ait.relevance_score::text) as topic_relevance_scores,
    COUNT(DISTINCT ait.topic_id) as topic_count,
    AVG(ait.relevance_score) as avg_relevance_score
FROM articles a
LEFT JOIN content_types ct ON a.content_type_id = ct.id
LEFT JOIN article_topics ait ON a.id = ait.article_id
LEFT JOIN ai_topics ait_topics ON ait.topic_id = ait_topics.id
GROUP BY a.id, a.title, a.content, a.summary, a.source, a.published_date, a.impact, 
         ct.name, a.url, a.reading_time, a.significance_score, a.thumbnail_url, 
         a.audio_url, a.duration, ct.display_name;

-- View 2: Top Stories with Topic Classification
CREATE VIEW v_top_stories AS
SELECT 
    ea.*,
    CASE 
        WHEN ea.topic_count > 3 THEN 'multi-topic'
        WHEN ea.topic_count > 1 THEN 'cross-topic'
        WHEN ea.topic_count = 1 THEN 'focused'
        ELSE 'general'
    END as topic_classification
FROM v_enhanced_articles ea
WHERE ea.significance_score >= 5.0
ORDER BY ea.significance_score DESC, ea.published_date DESC;

-- View 3: Content by Type
CREATE VIEW v_content_by_type AS
SELECT 
    ct.name as content_type,
    ct.display_name,
    COUNT(a.id) as article_count,
    AVG(a.significance_score) as avg_significance,
    MAX(a.published_date) as latest_article
FROM content_types ct
LEFT JOIN articles a ON ct.id = a.content_type_id
GROUP BY ct.id, ct.name, ct.display_name;

-- View 4: Personalized Content (for authenticated users)
CREATE VIEW v_personalized_content AS
SELECT 
    ea.*,
    CASE 
        WHEN EXTRACT(epoch FROM (NOW() - ea.published_date)) / 3600 < 24 THEN 1.0
        WHEN EXTRACT(epoch FROM (NOW() - ea.published_date)) / 3600 < 72 THEN 0.8
        WHEN EXTRACT(epoch FROM (NOW() - ea.published_date)) / 3600 < 168 THEN 0.6
        ELSE 0.5
    END as freshness_score,
    (ea.significance_score * 0.7 + 
     COALESCE(ea.avg_relevance_score, 0.5) * 0.3) as personalization_score
FROM v_enhanced_articles ea
ORDER BY personalization_score DESC, ea.published_date DESC;

-- View 5: Topic Analytics
CREATE VIEW v_topic_analytics AS
SELECT 
    t.id as topic_id,
    t.name as display_name,
    t.category,
    COUNT(DISTINCT at.article_id) as article_count,
    AVG(at.relevance_score) as avg_relevance,
    COUNT(DISTINCT a.source) as source_count,
    MAX(a.published_date) as latest_article
FROM ai_topics t
LEFT JOIN article_topics at ON t.id = at.topic_id
LEFT JOIN articles a ON at.article_id = a.id
GROUP BY t.id, t.name, t.category;

"""

def escape_sql_string(value):
    """Escape string values for PostgreSQL"""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        # Escape single quotes and handle special characters for PostgreSQL
        escaped = value.replace("'", "''").replace("\\", "\\\\")
        return f"'{escaped}'"
    elif isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    elif isinstance(value, (int, float)):
        return str(value) if value is not None else 'NULL'
    elif isinstance(value, dict):
        # Convert dict to JSON string for JSONB fields
        json_str = json.dumps(value).replace("'", "''")
        return f"'{json_str}'"
    else:
        return f"'{str(value)}'" if value is not None else 'NULL'

def export_table_data(conn, table_name, postgres_table_name=None):
    """Export table data as PostgreSQL INSERT statements"""
    if postgres_table_name is None:
        postgres_table_name = table_name
        
    print(f"📦 Exporting {table_name} -> {postgres_table_name}...")
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"⚠️ Table {table_name} not found: {e}")
        return [f"-- Table {table_name} not found in SQLite database\\n"]
    
    if not rows:
        return [f"-- No data in {table_name}\\n"]
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    sql_lines = [f"-- Data for {postgres_table_name} ({len(rows)} rows)"]
    
    # Special handling for different table types
    for row in rows:
        values = []
        filtered_columns = []
        
        for i, value in enumerate(row):
            column_name = columns[i]
            
            # Skip auto-increment IDs for PostgreSQL SERIAL columns
            if postgres_table_name in ['articles', 'ai_sources', 'content_types', 'daily_archives'] and column_name == 'id':
                continue
                
            filtered_columns.append(column_name)
            
            # Handle special field mappings and transformations
            if postgres_table_name == 'articles':
                # Map SQLite article fields to PostgreSQL schema
                if column_name == 'published_at':
                    filtered_columns[-1] = 'published_date'
                elif column_name == 'description':
                    filtered_columns[-1] = 'summary'  
                elif column_name == 'image_url':
                    filtered_columns[-1] = 'thumbnail_url'
                elif column_name == 'category':
                    # Map category to content_type_id (we'll use a subquery)
                    filtered_columns[-1] = 'content_type_id'
                    content_type_map = {
                        'blogs': 1, 'podcasts': 2, 'videos': 3, 
                        'events': 4, 'learning': 5, 'demos': 6
                    }
                    value = content_type_map.get(value, 1)  # Default to blogs
                    
            # Handle JSONB fields for users table
            if postgres_table_name == 'users' and column_name == 'preferences':
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        values.append(f"'{json.dumps(parsed)}'::jsonb")
                    except:
                        values.append("'{{}}'::jsonb")
                else:
                    values.append(escape_sql_string(value))
            # Handle JSONB fields for daily_archives
            elif postgres_table_name == 'daily_archives' and column_name in ['digest_data', 'metadata']:
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        values.append(f"'{json.dumps(parsed)}'::jsonb")
                    except:
                        values.append("'{{}}'::jsonb")
                else:
                    values.append("'{{}}'::jsonb")
            else:
                values.append(escape_sql_string(value))
        
        if values and filtered_columns:
            insert_columns = ', '.join(filtered_columns)
            values_str = ', '.join(values)
            sql_lines.append(f"INSERT INTO {postgres_table_name} ({insert_columns}) VALUES ({values_str}) ON CONFLICT DO NOTHING;")
    
    sql_lines.append("")  # Empty line
    return sql_lines

def main():
    """Export SQLite data to PostgreSQL migration script"""
    print("🚀 Starting SQLite to PostgreSQL migration script...")
    
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ SQLite database not found: {SQLITE_PATH}")
        print("💡 Make sure you're running this from the correct directory")
        return False
    
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get list of tables in SQLite database
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
        sqlite_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found SQLite tables: {sqlite_tables}")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # Write schema
            f.write(POSTGRESQL_SCHEMA.format(timestamp=datetime.now().isoformat()))
            f.write("\\n")
            
            # Write data migration
            f.write("-- ============================================\\n")
            f.write("-- DATA MIGRATION FROM SQLITE\\n")
            f.write("-- ============================================\\n\\n")
            
            # Define table mapping (SQLite -> PostgreSQL)
            table_mappings = {
                'users': 'users',
                'user_passwords': 'user_passwords', 
                'user_sessions': 'user_sessions',
                'articles': 'articles',
                'audio_content': 'articles',  # Merge into unified articles table
                'video_content': 'articles',  # Merge into unified articles table
                'daily_archives': 'daily_archives',
                'ai_topics': None,  # Skip - already inserted in schema
                'content_types': None,  # Skip - already inserted in schema
                'ai_sources': 'ai_sources',
                'article_topics': 'article_topics'
            }
            
            # Export each table
            for sqlite_table in sqlite_tables:
                postgres_table = table_mappings.get(sqlite_table)
                if postgres_table is None:
                    print(f"⏭️ Skipping {sqlite_table} (handled in schema)")
                    continue
                    
                sql_lines = export_table_data(conn, sqlite_table, postgres_table)
                for line in sql_lines:
                    f.write(line + "\\n")
            
            # Write final migration notes
            f.write("-- ============================================\\n")
            f.write("-- MIGRATION COMPLETION\\n")
            f.write("-- ============================================\\n\\n")
            f.write("-- Update sequences for SERIAL columns\\n")
            f.write("SELECT setval('articles_id_seq', (SELECT MAX(id) FROM articles));\\n")
            f.write("SELECT setval('content_types_id_seq', (SELECT MAX(id) FROM content_types));\\n")
            f.write("SELECT setval('ai_sources_id_seq', (SELECT MAX(id) FROM ai_sources));\\n")
            f.write("SELECT setval('article_topics_id_seq', (SELECT MAX(id) FROM article_topics));\\n")
            f.write("SELECT setval('daily_archives_id_seq', (SELECT MAX(id) FROM daily_archives));\\n")
            f.write("\\n-- Migration completed successfully!\\n")
        
        conn.close()
        
        print(f"✅ Migration script generated successfully!")
        print(f"📄 Output file: {OUTPUT_FILE}")
        print(f"📊 File size: {os.path.getsize(OUTPUT_FILE)} bytes")
        print()
        print("🔄 Next steps:")
        print("1. Create PostgreSQL service on Railway")
        print("2. Get connection details from Railway dashboard")
        print("3. Run this SQL file against your PostgreSQL database:")
        print(f"   psql postgresql://user:pass@host:port/db < {OUTPUT_FILE}")
        print("4. Update backend environment variables")
        print("5. Test the application")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration script generation failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)