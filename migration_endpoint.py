#!/usr/bin/env python3
"""
Migration endpoint to create ai_sources table via API call
"""

from simple_db_service import get_database_service

def create_ai_sources_via_api():
    """Create ai_sources table with comprehensive data"""
    try:
        db = get_database_service()
        
        # Drop and recreate ai_sources table
        db.execute_query("DROP TABLE IF EXISTS ai_sources CASCADE;", fetch_results=False)
        
        # Create ai_sources table
        create_table_query = """
            CREATE TABLE ai_sources (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                rss_url TEXT NOT NULL,
                website TEXT,
                content_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) DEFAULT 'general',
                enabled BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 5,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        db.execute_query(create_table_query, fetch_results=False)
        
        # Insert comprehensive AI sources
        ai_sources = [
            ("OpenAI Blog", "https://openai.com/blog/rss.xml", "https://openai.com", "blogs", "research", True, 1, "Official OpenAI blog and announcements"),
            ("Anthropic", "https://www.anthropic.com/news", "https://www.anthropic.com", "blogs", "research", True, 1, "Anthropic AI safety and research updates"),
            ("Google AI Blog", "https://ai.googleblog.com/feeds/posts/default", "https://ai.googleblog.com", "blogs", "research", True, 1, "Google AI research and developments"),
            ("DeepMind", "https://deepmind.google/discover/blog/", "https://deepmind.google", "blogs", "research", True, 1, "DeepMind research and breakthroughs"),
            ("Meta AI", "https://ai.meta.com/blog/", "https://ai.meta.com", "blogs", "research", True, 1, "Meta AI research and product updates"),
            ("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "https://www.technologyreview.com", "blogs", "business", True, 2, "MIT Technology Review AI coverage"),
            ("VentureBeat AI", "https://venturebeat.com/ai/feed/", "https://venturebeat.com", "blogs", "business", True, 2, "AI business news and trends"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "https://techcrunch.com", "blogs", "business", True, 2, "AI startup and business news"),
            ("AI News", "https://www.artificialintelligence-news.com/feed/", "https://www.artificialintelligence-news.com", "blogs", "business", True, 2, "AI industry news and analysis"),
            ("Towards Data Science", "https://towardsdatascience.com/feed", "https://towardsdatascience.com", "blogs", "technical", True, 3, "Data science and ML tutorials"),
            ("Machine Learning Mastery", "https://machinelearningmastery.com/feed/", "https://machinelearningmastery.com", "blogs", "technical", True, 3, "Practical ML tutorials and guides"),
            ("Papers with Code", "https://paperswithcode.com/feeds/papers/", "https://paperswithcode.com", "blogs", "technical", True, 3, "Latest ML papers with code implementations"),
            ("Distill", "https://distill.pub/rss.xml", "https://distill.pub", "blogs", "technical", True, 3, "Visual explanations of ML concepts"),
            ("Lex Fridman Podcast", "https://lexfridman.com/feed/podcast/", "https://lexfridman.com", "podcasts", "education", True, 4, "AI conversations with leading researchers"),
            ("NVIDIA AI Podcast", "https://blogs.nvidia.com/ai-podcast/feed/", "https://blogs.nvidia.com", "podcasts", "technical", True, 4, "NVIDIA AI developments and applications"),
            ("Two Minute Papers", "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", "https://www.youtube.com/c/TwoMinutePapers", "videos", "education", True, 5, "AI research paper explanations"),
            ("AI Explained", "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw", "https://www.youtube.com/c/AIExplained", "videos", "education", True, 5, "AI developments and explanations"),
        ]
        
        for source in ai_sources:
            insert_query = """
                INSERT INTO ai_sources (name, rss_url, website, content_type, category, enabled, priority, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_query(insert_query, source, fetch_results=False)
        
        # Create indexes
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_enabled ON ai_sources(enabled);", fetch_results=False)
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_priority ON ai_sources(priority);", fetch_results=False)
        db.execute_query("CREATE INDEX IF NOT EXISTS idx_ai_sources_category ON ai_sources(category);", fetch_results=False)
        
        return {
            "success": True,
            "message": f"ai_sources table created successfully with {len(ai_sources)} sources",
            "sources_count": len(ai_sources)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = create_ai_sources_via_api()
    print(result)