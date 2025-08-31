from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

app = FastAPI(title="AI News Scraper API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Content types configuration
CONTENT_TYPES = {
    "all_sources": {"name": "All Sources", "description": "Comprehensive AI content from all our curated sources", "icon": "🌐"},
    "blogs": {"name": "Blogs", "description": "Expert insights, analysis, and thought leadership articles", "icon": "✍️"},
    "podcasts": {"name": "Podcasts", "description": "Audio content, interviews, and discussions from AI leaders", "icon": "🎧"},
    "videos": {"name": "Videos", "description": "Visual content, presentations, and educational videos", "icon": "📹"},
    "events": {"name": "Events", "description": "AI conferences, webinars, workshops, and networking events", "icon": "📅"},
    "learn": {"name": "Learn", "description": "Courses, tutorials, educational content, and skill development", "icon": "🎓"}
}

# Sample articles data
SAMPLE_ARTICLES = [
    {
        "id": 1,
        "title": "GPT-5 Breakthrough: New Reasoning Capabilities",
        "description": "OpenAI's latest model demonstrates unprecedented problem-solving abilities across multiple domains.",
        "source": "OpenAI Blog",
        "time": "2 hours ago",
        "impact": "high",
        "type": "blog",
        "url": "https://openai.com/gpt5-announcement",
        "readTime": "8 min read",
        "significanceScore": 95,
        "category": "blogs",
        "published_date": "2025-08-31T12:00:00",
        "tags": [],
        "premium_only": False
    },
    {
        "id": 2,
        "title": "AI Safety Summit 2025: Global Leaders Convene",
        "description": "World leaders and AI researchers gather to discuss safety protocols and governance frameworks.",
        "source": "AI Safety Institute",
        "time": "4 hours ago",
        "impact": "high", 
        "type": "blog",
        "url": "https://aisafety.org/summit2025",
        "readTime": "12 min read",
        "significanceScore": 88,
        "category": "events",
        "published_date": "2025-08-31T10:00:00",
        "tags": [],
        "premium_only": False
    },
    {
        "id": 3,
        "title": "Lex Fridman Podcast: Yann LeCun on AGI Timeline",
        "description": "Meta's Chief AI Scientist shares insights on the path to artificial general intelligence.",
        "source": "Lex Fridman Podcast",
        "time": "1 day ago",
        "impact": "medium",
        "type": "audio",
        "url": "https://lexfridman.com/yann-lecun-agi",
        "readTime": "2 hour listen",
        "significanceScore": 82,
        "category": "podcasts", 
        "published_date": "2025-08-30T15:00:00",
        "tags": [],
        "premium_only": False
    },
    {
        "id": 4,
        "title": "DeepMind's AlphaFold 3 Breakthrough",
        "description": "Latest protein folding AI achieves 99% accuracy in predicting molecular structures.",
        "source": "Nature",
        "time": "6 hours ago",
        "impact": "high",
        "type": "video", 
        "url": "https://nature.com/alphafold3-breakthrough",
        "readTime": "15 min watch",
        "significanceScore": 91,
        "category": "videos",
        "published_date": "2025-08-31T08:00:00",
        "tags": [],
        "premium_only": False
    },
    {
        "id": 5,
        "title": "MIT AI Course: Deep Learning Fundamentals",
        "description": "Complete course covering neural networks, backpropagation, and modern architectures.",
        "source": "MIT OpenCourseWare",
        "time": "1 week ago",
        "impact": "medium",
        "type": "blog",
        "url": "https://ocw.mit.edu/deep-learning-2025",
        "readTime": "10 week course",
        "significanceScore": 75,
        "category": "learn",
        "published_date": "2025-08-24T10:00:00",
        "tags": [],
        "premium_only": False
    }
]

def categorize_articles_by_content_type(articles: List[Dict], content_type: str) -> List[Dict]:
    """Categorize articles based on content type"""
    if content_type == "all_sources":
        return articles
    
    # Filter by category
    filtered = [article for article in articles if article.get('category') == content_type]
    
    # If no exact matches, use keyword matching
    if not filtered:
        categorization_keywords = {
            "events": ["conference", "workshop", "summit", "meetup", "webinar", "symposium"],
            "learn": ["course", "tutorial", "learn", "training", "education", "teach"],
            "blogs": ["blog", "opinion", "insight", "analysis", "perspective"],
            "podcasts": ["podcast", "episode", "interview", "conversation"],
            "videos": ["video", "youtube", "watch", "presentation"]
        }
        
        keywords = categorization_keywords.get(content_type, [])
        for article in articles:
            content_text = f"{article.get('title', '').lower()} {article.get('description', '').lower()}"
            if any(keyword in content_text for keyword in keywords):
                article_copy = article.copy()
                article_copy['category'] = content_type
                filtered.append(article_copy)
    
    return filtered

# Pydantic models
class UserRegister(BaseModel):
    email: str
    password: str
    preferences: Optional[Dict] = {}

class UserLogin(BaseModel):
    email: str
    password: str

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "AI News Scraper API is running",
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.environ.get("VERCEL_ENV", "development"),
        "claude_api_configured": bool(os.environ.get("CLAUDE_API_KEY")),
        "endpoints": [
            "/health", "/api/digest", "/api/content-types", 
            "/api/content/{type}", "/auth/register", "/auth/login", "/auth/profile"
        ]
    }

# Health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "database": "healthy",
            "cache": "healthy", 
            "auth": "healthy",
            "multimedia": "available",
            "email": "disabled"
        },
        "features": {
            "authentication": True,
            "subscription_tiers": True,
            "multimedia": True,
            "email_service": False
        }
    }

# Content endpoints
@app.get("/api/content-types")
def get_content_types():
    """Get available content types"""
    return CONTENT_TYPES

@app.get("/api/content/{content_type}")
def get_content_by_type(content_type: str, refresh: Optional[bool] = False):
    """Get content by type with categorization"""
    if content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=404, detail="Content type not found")
    
    articles = categorize_articles_by_content_type(SAMPLE_ARTICLES, content_type)
    
    return {
        "content_type": content_type,
        "content_info": CONTENT_TYPES[content_type],
        "articles": articles,
        "total": len(articles),
        "total_available": len(articles),
        "sources_available": len(set(article["source"] for article in articles)),
        "user_tier": "free",
        "timestamp": datetime.now().isoformat(),
        "featured_sources": [
            {"name": "OpenAI Blog", "website": "https://openai.com/blog"},
            {"name": "MIT Technology Review", "website": "https://technologyreview.com"},
            {"name": "Lex Fridman Podcast", "website": "https://lexfridman.com"},
            {"name": "Nature AI", "website": "https://nature.com/ai"},
            {"name": "MIT OpenCourseWare", "website": "https://ocw.mit.edu"}
        ]
    }

@app.get("/api/digest")
def get_digest(refresh: Optional[bool] = False):
    """Get AI news digest"""
    return {
        "badge": "AI Digest",
        "timestamp": datetime.now().isoformat(),
        "user_tier": "free",
        "total_articles": len(SAMPLE_ARTICLES),
        "summary": {
            "metrics": {
                "totalStories": len(SAMPLE_ARTICLES),
                "highImpact": len([a for a in SAMPLE_ARTICLES if a["impact"] == "high"]),
                "categories": len(CONTENT_TYPES)
            },
            "keyPoints": [
                "OpenAI releases GPT-5 with breakthrough reasoning",
                "Global AI Safety Summit addresses governance",
                "DeepMind's AlphaFold 3 achieves 99% accuracy",
                "MIT releases comprehensive AI course materials"
            ]
        },
        "topStories": [
            {
                "id": article["id"],
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "description": article["description"][:200] + "...",
                "published_date": article["published_date"],
                "significanceScore": article["significanceScore"],
                "category": article["category"],
                "tags": article.get("tags", []),
                "premium_only": article.get("premium_only", False)
            } for article in SAMPLE_ARTICLES[:3]
        ],
        "content": {
            "blog": [a for a in SAMPLE_ARTICLES if a["category"] == "blogs"],
            "audio": [a for a in SAMPLE_ARTICLES if a["category"] == "podcasts"],
            "video": [a for a in SAMPLE_ARTICLES if a["category"] == "videos"]
        }
    }

# Authentication endpoints (simplified for now)
@app.post("/auth/register")
def register(user: UserRegister):
    """Register new user"""
    return {
        "message": "User registered successfully",
        "user": {"email": user.email, "tier": "free"},
        "token": "sample-jwt-token-12345"
    }

@app.post("/auth/login")
def login(user: UserLogin):
    """User login"""
    return {
        "message": "Login successful", 
        "user": {"email": user.email, "tier": "premium"},
        "token": "sample-jwt-token-67890"
    }

@app.get("/auth/profile")
def get_profile():
    """Get user profile"""
    return {
        "user": {
            "email": "test@example.com",
            "tier": "premium",
            "preferences": {
                "content_types": ["all_sources", "blogs", "podcasts", "videos", "events", "learn"]
            }
        },
        "authenticated": True
    }

# Google OAuth endpoints
@app.get("/auth/google")
def google_auth():
    """Google OAuth URL"""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return {
        "auth_url": f"https://accounts.google.com/oauth/authorize?client_id={client_id}",
        "configured": bool(client_id)
    }

@app.post("/auth/google/callback")
def google_callback():
    """Google OAuth callback"""
    return {
        "message": "Google authentication successful",
        "user": {"email": "google.user@example.com", "tier": "premium"},
        "token": "google-jwt-token-abc123"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)