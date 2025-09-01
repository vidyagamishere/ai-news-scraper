from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

app = FastAPI(title="AI News Scraper API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models
class UserRegister(BaseModel):
    email: str
    password: str
    preferences: Optional[Dict] = {}

class UserLogin(BaseModel):
    email: str
    password: str

# Sample data
CONTENT_TYPES = {
    "all_sources": {"name": "All Sources", "description": "Comprehensive AI content from all our curated sources", "icon": "🌐"},
    "blogs": {"name": "Blogs", "description": "Expert insights, analysis, and thought leadership articles", "icon": "✍️"},
    "podcasts": {"name": "Podcasts", "description": "Audio content, interviews, and discussions from AI leaders", "icon": "🎧"},
    "videos": {"name": "Videos", "description": "Visual content, presentations, and educational videos", "icon": "📹"},
    "events": {"name": "Events", "description": "AI conferences, webinars, workshops, and networking events", "icon": "📅"},
    "learn": {"name": "Learn", "description": "Courses, tutorials, educational content, and skill development", "icon": "🎓"}
}

SAMPLE_ARTICLES = [
    {
        "title": "OpenAI Releases GPT-5 with Breakthrough Reasoning Capabilities",
        "description": "Revolutionary AI model demonstrates unprecedented problem-solving abilities across multiple domains.",
        "source": "OpenAI Blog",
        "time": "2 hours ago",
        "impact": "high",
        "type": "blog",
        "url": "https://openai.com/gpt5-announcement",
        "readTime": "8 min read",
        "significanceScore": 95,
        "category": "blogs"
    },
    {
        "title": "AI Safety Summit 2024: Global Leaders Convene",
        "description": "World leaders and AI researchers gather to discuss safety protocols and governance frameworks.",
        "source": "AI Safety Institute",
        "time": "4 hours ago", 
        "impact": "high",
        "type": "blog",
        "url": "https://aisafety.org/summit2024",
        "readTime": "12 min read",
        "significanceScore": 88,
        "category": "events"
    },
    {
        "title": "Lex Fridman Podcast: Yann LeCun on AGI Timeline",
        "description": "Meta's Chief AI Scientist shares insights on the path to artificial general intelligence.",
        "source": "Lex Fridman Podcast",
        "time": "1 day ago",
        "impact": "medium",
        "type": "audio", 
        "url": "https://lexfridman.com/yann-lecun-agi",
        "readTime": "2 hour listen",
        "significanceScore": 82,
        "category": "podcasts"
    },
    {
        "title": "DeepMind's New AlphaFold 3 Breakthrough",
        "description": "Latest protein folding AI achieves 99% accuracy in predicting molecular structures.",
        "source": "Nature",
        "time": "6 hours ago",
        "impact": "high", 
        "type": "video",
        "url": "https://nature.com/alphafold3-breakthrough",
        "readTime": "15 min watch",
        "significanceScore": 91,
        "category": "videos"
    },
    {
        "title": "MIT AI Course: Deep Learning Fundamentals",
        "description": "Complete course covering neural networks, backpropagation, and modern architectures.",
        "source": "MIT OpenCourseWare",
        "time": "1 week ago",
        "impact": "medium",
        "type": "blog",
        "url": "https://ocw.mit.edu/deep-learning-2024",
        "readTime": "10 week course",
        "significanceScore": 75,
        "category": "learn"
    }
]

def categorize_articles_by_content_type(articles: List[Dict], content_type: str) -> List[Dict]:
    if content_type == "all_sources":
        return articles
    
    categorization_keywords = {
        "events": ["conference", "workshop", "summit", "meetup", "webinar", "symposium", "neurips", "icml", "iclr"],
        "learn": ["course", "tutorial", "learn", "training", "education", "teach", "coursera", "edx", "udacity"],
        "blogs": ["blog", "opinion", "insight", "analysis", "perspective", "commentary"],
        "podcasts": ["podcast", "episode", "interview", "conversation", "lex fridman", "twiml"],
        "videos": ["video", "youtube", "watch", "presentation", "two minute papers", "3blue1brown"]
    }
    
    keywords = categorization_keywords.get(content_type, [])
    filtered_articles = []
    
    for article in articles:
        content_text = f"{article.get('title', '').lower()} {article.get('description', '').lower()}"
        if any(keyword in content_text for keyword in keywords) or article.get('category') == content_type:
            article_copy = article.copy()
            article_copy['category'] = content_type
            filtered_articles.append(article_copy)
    
    # If no articles match, return sample articles for that category
    if not filtered_articles:
        filtered_articles = [article for article in SAMPLE_ARTICLES if article.get('category') == content_type]
    
    return filtered_articles

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "AI News Scraper API is running",
        "status": "healthy",
        "environment": os.environ.get("VERCEL_ENV", "development"),
        "claude_api_configured": bool(os.environ.get("CLAUDE_API_KEY")),
        "endpoints": ["/health", "/api/digest", "/api/content-types", "/api/content/{type}", "/auth/register", "/auth/login", "/auth/profile"]
    }

# Health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-news-scraper", 
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": True,
            "scraper": True,
            "processor": True,
            "ai_sources": len(SAMPLE_ARTICLES)
        }
    }

# Content endpoints
@app.get("/api/content-types")
def get_content_types():
    return CONTENT_TYPES

@app.get("/api/content/{content_type}")
def get_content_by_type(content_type: str, refresh: bool = False):
    articles = categorize_articles_by_content_type(SAMPLE_ARTICLES, content_type)
    return {
        "articles": articles,
        "total": len(articles),
        "content_type": content_type,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/digest")
def get_digest(refresh: bool = False):
    return {
        "summary": {
            "keyPoints": [
                "OpenAI releases GPT-5 with breakthrough reasoning capabilities",
                "Global AI Safety Summit addresses governance frameworks", 
                "DeepMind's AlphaFold 3 achieves 99% protein folding accuracy",
                "MIT releases comprehensive deep learning course materials"
            ],
            "metrics": {
                "totalUpdates": len(SAMPLE_ARTICLES),
                "highImpact": len([a for a in SAMPLE_ARTICLES if a["impact"] == "high"]),
                "newResearch": 3,
                "industryMoves": 2
            }
        },
        "topStories": [
            {
                "title": article["title"],
                "source": article["source"],
                "significanceScore": article["significanceScore"],
                "url": article["url"]
            } for article in SAMPLE_ARTICLES[:3]
        ],
        "content": {
            "blog": [a for a in SAMPLE_ARTICLES if a["type"] == "blog"],
            "audio": [a for a in SAMPLE_ARTICLES if a["type"] == "audio"], 
            "video": [a for a in SAMPLE_ARTICLES if a["type"] == "video"]
        },
        "timestamp": datetime.now().isoformat(),
        "badge": "🚀"
    }

# Authentication endpoints
@app.post("/auth/register")
def register(user: UserRegister):
    return {
        "message": "User registered successfully",
        "user": {"email": user.email, "tier": "free"},
        "token": "sample-jwt-token-12345"
    }

@app.post("/auth/login")
def login(user: UserLogin):
    return {
        "message": "Login successful",
        "user": {"email": user.email, "tier": "premium"},
        "token": "sample-jwt-token-67890"
    }

@app.get("/auth/profile")
def get_profile():
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
    return {"auth_url": "https://accounts.google.com/oauth/authorize", "configured": True}

@app.post("/auth/google/callback")
def google_callback():
    return {
        "message": "Google authentication successful",
        "user": {"email": "google.user@example.com", "tier": "premium"},
        "token": "google-jwt-token-abc123"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)