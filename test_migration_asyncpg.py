#!/usr/bin/env python3
"""
Test script for asyncpg migration to Neon
"""
import os
import asyncio

# Set environment
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://neondb_owner:npg_bptJPa6Hlnc8@ep-dry-meadow-adtmcjn4-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

async def test_migration():
    """Test asyncpg migration"""
    try:
        import asyncpg
        print("🧪 Testing asyncpg migration to Neon...")
        
        # Test connection
        conn = await asyncpg.connect(POSTGRES_URL)
        
        # Test basic query
        result = await conn.fetchval("SELECT 1 as test")
        print(f"✅ Connection successful: {result}")
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"📊 Found {len(tables)} existing tables: {[t['table_name'] for t in tables]}")
        
        # Test creating ai_topics table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_topics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Test inserting a sample topic
        await conn.execute("""
            INSERT INTO ai_topics (id, name, description, category, is_active)
            VALUES ($1, $2, $3, $4, TRUE)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category
        """, "test_ml", "Test Machine Learning", "Test ML topic for migration", "research")
        
        # Test querying the topics
        topics = await conn.fetch("SELECT * FROM ai_topics WHERE id = $1", "test_ml")
        print(f"✅ Topic test successful: {len(topics)} topics found")
        
        await conn.close()
        
        return {
            "success": True,
            "message": "asyncpg migration test completed successfully",
            "tables_count": len(tables),
            "connection_test": "passed"
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "asyncpg not available (expected in local environment)",
            "note": "This will work on Vercel with Python 3.12"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(test_migration())
    print("🎯 Migration test result:")
    for key, value in result.items():
        print(f"   {key}: {value}")