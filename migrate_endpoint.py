#!/usr/bin/env python3
"""
Simple migration endpoint for Vercel deployment
"""
import os
from api.database_service import DatabaseService
from api.auth_service_postgres import AuthService

def run_migration():
    """Run the migration to setup Neon database"""
    print("🚀 Setting up Neon Postgres database...")
    
    # Get environment variables
    database_url = os.getenv("POSTGRES_URL")
    if not database_url:
        return {"error": "POSTGRES_URL not configured"}
    
    try:
        # Initialize database service
        db = DatabaseService(database_url)
        print(f"✅ Connected to database: {'PostgreSQL' if db.is_postgres else 'SQLite'}")
        
        if not db.is_postgres:
            return {"error": "Expected PostgreSQL database, got SQLite"}
        
        # Initialize auth service (this will create tables and default topics)
        auth_service = AuthService(
            database_url=database_url,
            jwt_secret=os.getenv("JWT_SECRET", "test-secret"),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", "")
        )
        
        # Test getting topics to ensure everything is working
        topics = auth_service.get_available_topics()
        
        # Get category statistics
        categories = {}
        for topic in topics:
            cat = topic.category.value
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        # Check table counts
        table_counts = {}
        tables_to_check = ['users', 'ai_topics', 'articles', 'audio_content', 'video_content']
        for table in tables_to_check:
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = result[0]['count']
            except:
                table_counts[table] = "Error"
        
        return {
            "success": True,
            "message": "Neon Postgres database initialized successfully",
            "database_type": "PostgreSQL",
            "topics_count": len(topics),
            "categories": categories,
            "table_counts": table_counts,
            "sample_topics": [{"name": t.name, "category": t.category.value} for t in topics[:5]]
        }
        
    except Exception as e:
        return {
            "error": f"Migration failed: {str(e)}",
            "type": type(e).__name__
        }

# For testing locally or as a simple script
if __name__ == "__main__":
    import json
    result = run_migration()
    print(json.dumps(result, indent=2))