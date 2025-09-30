#!/usr/bin/env python3
"""
Force database migration script to update schema on Railway
This script will add missing columns and tables to existing database
"""

import os
import logging
from db_service import get_database_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_schema_update():
    """Force update the database schema with missing columns"""
    try:
        db = get_database_service()
        
        with db.get_db_connection() as conn:
            with conn.cursor() as cursor:
                
                logger.info("🔄 Forcing database schema update...")
                
                # 1. Add updated_at column to ai_sources if missing
                try:
                    cursor.execute("""
                        ALTER TABLE ai_sources 
                        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    """)
                    logger.info("✅ Added updated_at column to ai_sources")
                except Exception as e:
                    logger.info(f"ℹ️ updated_at column already exists or error: {e}")
                
                # 2. Create ai_categories_master table if missing
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS ai_categories_master (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(100) UNIQUE NOT NULL,
                            description TEXT,
                            icon VARCHAR(20),
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    logger.info("✅ Created ai_categories_master table")
                except Exception as e:
                    logger.info(f"ℹ️ ai_categories_master table creation error: {e}")
                
                # 3. Add category_id column to ai_topics if missing
                try:
                    cursor.execute("""
                        ALTER TABLE ai_topics 
                        ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES ai_categories_master(id);
                    """)
                    logger.info("✅ Added category_id column to ai_topics")
                except Exception as e:
                    logger.info(f"ℹ️ category_id column already exists or error: {e}")
                
                # 4. Check if ai_sources table has proper structure
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'ai_sources' 
                    AND table_schema = 'public'
                    ORDER BY column_name;
                """)
                
                columns = [row['column_name'] for row in cursor.fetchall()]
                logger.info(f"📊 ai_sources columns: {columns}")
                
                # 5. Check ai_topics structure
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'ai_topics' 
                    AND table_schema = 'public'
                    ORDER BY column_name;
                """)
                
                topic_columns = [row['column_name'] for row in cursor.fetchall()]
                logger.info(f"📊 ai_topics columns: {topic_columns}")
                
                # 6. Check if ai_categories_master exists
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_name = 'ai_categories_master' 
                    AND table_schema = 'public';
                """)
                
                table_exists = cursor.fetchone()['count'] > 0
                logger.info(f"📊 ai_categories_master exists: {table_exists}")
                
                conn.commit()
                logger.info("✅ Database schema update completed successfully")
                
    except Exception as e:
        logger.error(f"❌ Schema update failed: {e}")
        raise e

if __name__ == "__main__":
    force_schema_update()