#!/usr/bin/env python3
"""
Migration script to transfer all data from SQLite to Neon Postgres
"""
import os
import sqlite3
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from typing import Dict, List, Any

# Database configuration
SQLITE_PATH = '/Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper/ai_news.db'
NEON_URL = 'postgresql://neondb_owner:npg_bptJPa6Hlnc8@ep-dry-meadow-adtmcjn4-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

# Table schemas for Postgres (with proper data types)
POSTGRES_SCHEMAS = {
    'articles': """
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            url TEXT UNIQUE,
            published_at TIMESTAMP,
            description TEXT,
            content TEXT,
            significance_score INTEGER DEFAULT 5,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'general',
            reading_time INTEGER DEFAULT 3,
            image_url TEXT,
            keywords TEXT
        )
    """,
    'audio_content': """
        CREATE TABLE IF NOT EXISTS audio_content (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            url TEXT UNIQUE,
            published_at TIMESTAMP,
            description TEXT,
            content TEXT,
            significance_score INTEGER DEFAULT 5,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'general',
            duration_minutes INTEGER,
            image_url TEXT,
            keywords TEXT,
            audio_url TEXT
        )
    """,
    'video_content': """
        CREATE TABLE IF NOT EXISTS video_content (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            url TEXT UNIQUE,
            published_at TIMESTAMP,
            description TEXT,
            content TEXT,
            significance_score INTEGER DEFAULT 5,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'general',
            duration_minutes INTEGER,
            image_url TEXT,
            keywords TEXT,
            video_url TEXT,
            thumbnail_url TEXT,
            view_count INTEGER
        )
    """,
    'users': """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            profile_image TEXT,
            subscription_tier TEXT DEFAULT 'free',
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP,
            email_verified BOOLEAN DEFAULT FALSE
        )
    """,
    'user_passwords': """
        CREATE TABLE IF NOT EXISTS user_passwords (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    """,
    'ai_topics': """
        CREATE TABLE IF NOT EXISTS ai_topics (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    """,
    'user_sessions': """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            last_used_at TIMESTAMP
        )
    """,
    'daily_archives': """
        CREATE TABLE IF NOT EXISTS daily_archives (
            id SERIAL PRIMARY KEY,
            archive_date DATE UNIQUE,
            digest_data JSONB,
            article_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
    """,
    'digests': """
        CREATE TABLE IF NOT EXISTS digests (
            id SERIAL PRIMARY KEY,
            date DATE,
            summary_points TEXT,
            top_stories TEXT,
            content_stats JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
    """,
    'subscribers': """
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            subscription_tier TEXT DEFAULT 'free',
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT FALSE,
            last_email_sent TIMESTAMP
        )
    """,
    'subscription_preferences': """
        CREATE TABLE IF NOT EXISTS subscription_preferences (
            id SERIAL PRIMARY KEY,
            subscriber_id INTEGER REFERENCES subscribers(id) ON DELETE CASCADE,
            preference_type TEXT,
            preference_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'email_subscriptions': """
        CREATE TABLE IF NOT EXISTS email_subscriptions (
            id SERIAL PRIMARY KEY,
            subscriber_id INTEGER REFERENCES subscribers(id) ON DELETE CASCADE,
            frequency TEXT DEFAULT 'weekly',
            categories TEXT DEFAULT 'all',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sent TIMESTAMP,
            next_send TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
    """,
    'digest_cache': """
        CREATE TABLE IF NOT EXISTS digest_cache (
            id SERIAL PRIMARY KEY,
            cache_key TEXT UNIQUE,
            content JSONB,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
    """
}

def connect_sqlite() -> sqlite3.Connection:
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_PATH):
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_PATH}")
    
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def connect_postgres() -> psycopg2.extensions.connection:
    """Connect to Neon Postgres database"""
    conn = psycopg2.connect(
        NEON_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=30
    )
    return conn

def create_postgres_tables(pg_conn: psycopg2.extensions.connection):
    """Create all tables in Postgres"""
    print("🏗️  Creating Postgres table schemas...")
    cursor = pg_conn.cursor()
    
    for table_name, schema in POSTGRES_SCHEMAS.items():
        try:
            cursor.execute(schema)
            print(f"✅ Created table: {table_name}")
        except Exception as e:
            print(f"❌ Error creating table {table_name}: {e}")
            raise
    
    pg_conn.commit()
    print("✅ All tables created successfully")

def convert_sqlite_row_to_postgres(table_name: str, row: sqlite3.Row) -> Dict[str, Any]:
    """Convert SQLite row to Postgres-compatible format"""
    data = dict(row)
    
    # Handle JSON fields
    if table_name in ['users', 'subscribers'] and 'preferences' in data:
        if isinstance(data['preferences'], str):
            try:
                data['preferences'] = json.loads(data['preferences'])
            except:
                data['preferences'] = {}
    
    # Handle JSONB fields
    json_fields = {
        'daily_archives': ['digest_data', 'metadata'],
        'digests': ['content_stats', 'metadata'],
        'subscribers': ['preferences'],
        'email_subscriptions': ['metadata'],
        'digest_cache': ['content', 'metadata']
    }
    
    if table_name in json_fields:
        for field in json_fields[table_name]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except:
                    data[field] = {}
    
    # Remove auto-increment fields for tables that use SERIAL
    if table_name in ['articles', 'audio_content', 'video_content', 'daily_archives', 'digests', 'subscribers', 'subscription_preferences', 'email_subscriptions', 'digest_cache']:
        if 'id' in data:
            del data['id']
    
    return data

def migrate_table(sqlite_conn: sqlite3.Connection, pg_conn: psycopg2.extensions.connection, table_name: str):
    """Migrate a single table from SQLite to Postgres"""
    print(f"📦 Migrating table: {table_name}")
    
    # Get data from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️  No data in {table_name}")
        return
    
    # Insert into Postgres
    pg_cursor = pg_conn.cursor()
    migrated_count = 0
    
    for row in rows:
        try:
            data = convert_sqlite_row_to_postgres(table_name, row)
            
            # Create INSERT statement
            columns = list(data.keys())
            placeholders = ['%s'] * len(columns)
            values = [data[col] for col in columns]
            
            insert_sql = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT DO NOTHING
            """
            
            pg_cursor.execute(insert_sql, values)
            migrated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error migrating row: {e}")
            print(f"   📄 Row data: {dict(row)}")
            continue
    
    pg_conn.commit()
    print(f"   ✅ Migrated {migrated_count}/{len(rows)} rows")

def update_ai_topics_with_new_categories(pg_conn: psycopg2.extensions.connection):
    """Update ai_topics table with new categories from ai_sources_config.py"""
    print("🔄 Updating AI topics with new categories...")
    
    # New topics with proper categories
    new_topics = [
        ("ml_foundations", "Machine Learning", "Core ML algorithms, techniques, and foundations", "research"),
        ("deep_learning", "Deep Learning", "Neural networks, deep learning research and applications", "research"),
        ("nlp_llm", "Natural Language Processing", "Language models, NLP, and conversational AI", "language"),
        ("computer_vision", "Computer Vision", "Image recognition, visual AI, and computer vision", "research"),
        ("ai_tools", "AI Tools & Platforms", "New AI tools and platforms for developers", "platform"),
        ("ai_research", "AI Research Papers", "Latest academic research and scientific breakthroughs", "research"),
        ("ai_ethics", "AI Ethics & Safety", "Responsible AI, safety research, and ethical considerations", "policy"),
        ("robotics", "Robotics & Automation", "Physical AI, robotics, and automation systems", "robotics"),
        ("ai_business", "AI in Business", "Enterprise AI and industry applications", "company"),
        ("ai_startups", "AI Startups & Funding", "New AI companies and startup ecosystem", "startup"),
        ("ai_regulation", "AI Policy & Regulation", "Government policies and AI governance", "policy"),
        ("ai_hardware", "AI Hardware & Computing", "AI chips and hardware innovations", "hardware"),
        ("ai_automotive", "AI in Automotive", "Self-driving cars and automotive AI", "automotive"),
        ("ai_healthcare", "AI in Healthcare", "Medical AI applications and healthcare tech", "healthcare"),
        ("ai_finance", "AI in Finance", "Financial AI, trading, and fintech applications", "finance"),
        ("ai_gaming", "AI in Gaming", "Game AI, procedural generation, and gaming tech", "gaming"),
        ("ai_creative", "AI in Creative Arts", "AI for art, music, design, and creative content", "creative"),
        ("ai_cloud", "AI Cloud Services", "Cloud-based AI services and infrastructure", "cloud"),
        ("ai_events", "AI Events & Conferences", "AI conferences, workshops, and industry events", "events"),
        ("ai_learning", "AI Learning & Education", "AI courses, tutorials, and educational content", "learning"),
        ("ai_news", "AI News & Updates", "Latest AI news and industry updates", "news"),
        ("ai_international", "AI International", "Global AI developments and international news", "international"),
    ]
    
    cursor = pg_conn.cursor()
    
    # Clear existing topics
    cursor.execute("DELETE FROM ai_topics")
    
    # Insert new topics
    for topic_id, name, description, category in new_topics:
        cursor.execute("""
            INSERT INTO ai_topics (id, name, description, category, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                is_active = TRUE
        """, (topic_id, name, description, category))
    
    pg_conn.commit()
    print(f"✅ Updated ai_topics with {len(new_topics)} topics")

def verify_migration(pg_conn: psycopg2.extensions.connection):
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    cursor = pg_conn.cursor()
    
    for table_name in POSTGRES_SCHEMAS.keys():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   📊 {table_name}: {count} records")
    
    # Check ai_topics categories
    cursor.execute("SELECT DISTINCT category FROM ai_topics ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    print(f"   🏷️  AI topic categories: {categories}")

def main():
    """Main migration function"""
    print("🚀 Starting SQLite to Neon Postgres migration...")
    print(f"📂 Source: {SQLITE_PATH}")
    print(f"🐘 Target: Neon Postgres")
    
    try:
        # Connect to databases
        print("\n🔌 Connecting to databases...")
        sqlite_conn = connect_sqlite()
        pg_conn = connect_postgres()
        print("✅ Connected to both databases")
        
        # Create Postgres tables
        create_postgres_tables(pg_conn)
        
        # Get tables to migrate (exclude sqlite_sequence)
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Tables to migrate: {tables}")
        
        # Migrate each table
        for table in tables:
            if table in POSTGRES_SCHEMAS:
                migrate_table(sqlite_conn, pg_conn, table)
            else:
                print(f"⚠️  Skipping {table} - no schema defined")
        
        # Update AI topics with new categories
        update_ai_topics_with_new_categories(pg_conn)
        
        # Verify migration
        verify_migration(pg_conn)
        
        print("\n🎉 Migration completed successfully!")
        print("💡 The Neon Postgres database is now ready for production use")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)