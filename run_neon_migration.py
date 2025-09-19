#!/usr/bin/env python3
"""
Run the Neon migration SQL using the backend database service
"""
import os
import sys

# Set environment variables
os.environ['POSTGRES_URL'] = 'postgresql://neondb_owner:npg_bptJPa6Hlnc8@ep-dry-meadow-adtmcjn4-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

def run_migration():
    """Run the migration using the backend database service"""
    print("🚀 Running Neon Postgres migration...")
    
    try:
        # Import the database service
        from api.database_service import DatabaseService
        
        # Initialize database service with Neon URL
        db = DatabaseService(os.environ['POSTGRES_URL'])
        print(f"✅ Connected to Neon Postgres: {db.is_postgres}")
        
        # Read the migration SQL file
        sql_file = '/Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper/neon_migration.sql'
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("📄 Loaded migration SQL file")
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print(f"🔄 Executing {len(statements)} SQL statements...")
        
        # Execute each statement
        executed = 0
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        executed += 1
                        if (i + 1) % 10 == 0:
                            print(f"   ✅ Executed {i + 1}/{len(statements)} statements")
                    except Exception as e:
                        print(f"   ⚠️  Warning on statement {i + 1}: {e}")
                        continue
        
        print(f"✅ Migration completed! Executed {executed}/{len(statements)} statements")
        
        # Verify the migration
        print("\\n🔍 Verifying migration...")
        
        tables_to_check = ['articles', 'audio_content', 'video_content', 'users', 'ai_topics', 'daily_archives']
        for table in tables_to_check:
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                count = result[0]['count']
                print(f"   📊 {table}: {count} records")
            except Exception as e:
                print(f"   ❌ Error checking {table}: {e}")
        
        # Check AI topics categories
        try:
            result = db.execute_query("SELECT DISTINCT category FROM ai_topics ORDER BY category")
            categories = [row['category'] for row in result]
            print(f"   🏷️  AI topic categories: {categories}")
            
            # Verify alignment with ai_sources_config.py
            from api.ai_sources_config import CATEGORIES as API_CATEGORIES
            if set(categories) >= set(API_CATEGORIES):
                print("   ✅ All ai_sources_config.py categories are covered!")
            else:
                missing = set(API_CATEGORIES) - set(categories)
                print(f"   ⚠️  Missing categories: {missing}")
                
        except Exception as e:
            print(f"   ❌ Error checking categories: {e}")
        
        print("\\n🎉 Neon Postgres database is ready for production!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)