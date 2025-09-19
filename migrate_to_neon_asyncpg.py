#!/usr/bin/env python3
"""
Migration script to transfer all data from SQLite to Neon Postgres using asyncpg
"""
import os
import sqlite3
import asyncio
import asyncpg
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
    """
}

def connect_sqlite() -> sqlite3.Connection:
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_PATH):
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_PATH}")
    
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def connect_postgres() -> asyncpg.Connection:
    """Connect to Neon Postgres database using asyncpg"""
    conn = await asyncpg.connect(NEON_URL)
    return conn

async def create_postgres_tables(pg_conn: asyncpg.Connection):
    """Create all tables in Postgres"""
    print("🏗️  Creating Postgres table schemas...")
    
    for table_name, schema in POSTGRES_SCHEMAS.items():
        try:
            await pg_conn.execute(schema)
            print(f"✅ Created table: {table_name}")
        except Exception as e:
            print(f"❌ Error creating table {table_name}: {e}")
            raise
    
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
        'subscribers': ['preferences'],
        'email_subscriptions': ['metadata']
    }
    
    if table_name in json_fields:
        for field in json_fields[table_name]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except:
                    data[field] = {}
    
    # Remove auto-increment fields for tables that use SERIAL
    serial_tables = ['articles', 'audio_content', 'video_content', 'daily_archives', 'subscribers', 'subscription_preferences', 'email_subscriptions']
    if table_name in serial_tables and 'id' in data:
        del data['id']
    
    return data

async def migrate_table(sqlite_conn: sqlite3.Connection, pg_conn: asyncpg.Connection, table_name: str):
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
    migrated_count = 0
    
    for row in rows:
        try:
            data = convert_sqlite_row_to_postgres(table_name, row)
            
            # Create INSERT statement
            columns = list(data.keys())
            placeholders = [f'${i+1}' for i in range(len(columns))]
            values = [data[col] for col in columns]
            
            insert_sql = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT DO NOTHING
            """
            
            await pg_conn.execute(insert_sql, *values)
            migrated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error migrating row: {e}")
            print(f"   📄 Row data: {dict(row)}")
            continue
    
    print(f"   ✅ Migrated {migrated_count}/{len(rows)} rows")

async def update_ai_topics_with_new_categories(pg_conn: asyncpg.Connection):
    """Update ai_topics table with new categories"""
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
    
    # Clear existing topics
    await pg_conn.execute("DELETE FROM ai_topics")
    
    # Insert new topics
    for topic_id, name, description, category in new_topics:
        await pg_conn.execute("""
            INSERT INTO ai_topics (id, name, description, category, is_active)
            VALUES ($1, $2, $3, $4, TRUE)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                is_active = TRUE
        """, topic_id, name, description, category)
    
    print(f"✅ Updated ai_topics with {len(new_topics)} topics")

async def verify_migration(pg_conn: asyncpg.Connection):
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    for table_name in POSTGRES_SCHEMAS.keys():
        try:
            count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"   📊 {table_name}: {count} records")
        except Exception as e:
            print(f"   ❌ Error checking {table_name}: {e}")
    
    # Check ai_topics categories
    try:
        categories = await pg_conn.fetch("SELECT DISTINCT category FROM ai_topics ORDER BY category")
        category_list = [row['category'] for row in categories]
        print(f"   🏷️  AI topic categories: {category_list}")
    except Exception as e:
        print(f"   ❌ Error checking categories: {e}")

async def test_connection():
    """Test asyncpg connection to Neon"""
    print("🧪 Testing asyncpg connection to Neon...")
    
    try:
        conn = await asyncpg.connect(NEON_URL)
        
        # Test basic query
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Connection successful, test query result: {result}")
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"📊 Found {len(tables)} existing tables: {[t['table_name'] for t in tables]}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    """Main migration function"""
    print("🚀 Starting SQLite to Neon Postgres migration with asyncpg...")
    print(f"📂 Source: {SQLITE_PATH}")
    print(f"🐘 Target: Neon Postgres")
    
    # Test connection first
    if not await test_connection():
        print("❌ Cannot connect to Neon database, aborting migration")
        return False
    
    try:
        # Connect to databases
        print("\n🔌 Connecting to databases...")
        sqlite_conn = connect_sqlite()
        pg_conn = await connect_postgres()
        print("✅ Connected to both databases")
        
        # Create Postgres tables
        await create_postgres_tables(pg_conn)
        
        # Get tables to migrate (exclude sqlite_sequence)
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Tables to migrate: {tables}")
        
        # Migrate each table
        for table in tables:
            if table in POSTGRES_SCHEMAS:
                await migrate_table(sqlite_conn, pg_conn, table)
            else:
                print(f"⚠️  Skipping {table} - no schema defined")
        
        # Update AI topics with new categories
        await update_ai_topics_with_new_categories(pg_conn)
        
        # Verify migration
        await verify_migration(pg_conn)
        
        print("\n🎉 Migration completed successfully!")
        print("💡 The Neon Postgres database is now ready for production use with asyncpg")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            await pg_conn.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)