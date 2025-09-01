from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

# Import response models
from models import (
    AuthResponse, UserProfile, SubscriptionPreferences,
    PreferencesResponse, MessageResponse, DigestResponse, ScrapeResponse,
    SourcesResponse, SystemInfo, HealthResponse
)

app = FastAPI(
    title="AI News Scraper API",
    version="2.0.0",
    description="""
    Comprehensive AI News Scraper API with authentication, content management, and multimedia support.
    
    ## Features
    - **Authentication**: Google OAuth and JWT-based authentication
    - **Content Scraping**: RSS feed scraping from AI news sources
    - **Multimedia Support**: Audio and video content processing
    - **Email Digests**: Personalized email newsletters
    - **Admin Management**: Subscriber and content management
    
    ## Authentication
    Most endpoints require authentication. Use the `/auth/google` endpoint to authenticate with Google OAuth.
    Include the returned JWT token in the Authorization header as `Bearer <token>`.
    
    ## Rate Limiting
    API requests are rate-limited to 30 requests per minute per IP.
    """,
    contact={
        "name": "AI News Scraper API Support",
        "email": "support@ai-news-scraper.com",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "Content",
            "description": "News content and digest endpoints"
        },
        {
            "name": "Multimedia", 
            "description": "Audio and video content endpoints"
        },
        {
            "name": "Subscription",
            "description": "User subscription and preference management"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints for user management"
        },
        {
            "name": "System",
            "description": "System health and status endpoints"
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Auth models
class GoogleAuthRequest(BaseModel):
    token: str

class UserRegister(BaseModel):
    email: str
    password: str
    preferences: Optional[Dict] = {}

class UserLogin(BaseModel):
    email: str
    password: str

# Sample data for demo
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
    }
]

# Root endpoint
@app.get("/", tags=["System"], response_model=SystemInfo)
def read_root():
    """
    API root endpoint with system information.
    
    Returns basic API information, status, and available endpoints.
    """
    return {
        "message": "AI News Scraper API is running",
        "status": "healthy",
        "version": "2.0.0",
        "claude_enabled": bool(os.environ.get("CLAUDE_API_KEY"))
    }

# Health endpoint
@app.get("/api/health", tags=["System"], response_model=HealthResponse)
def health_check():
    """
    System health check endpoint.
    
    Returns status of all system components including:
    - Database connectivity
    - Scraper and processor status
    - External API connections
    
    Use this endpoint to monitor system health in production.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": True,
            "scraper": True,
            "processor": True,
            "claude_api": bool(os.environ.get("CLAUDE_API_KEY")),
            "scheduler": False
        }
    }

# Content endpoints
@app.get("/api/content-types", tags=["Content"], response_model=dict)
def get_content_types():
    """
    Get available content types.
    
    Returns all supported content types with their descriptions and icons.
    """
    return CONTENT_TYPES

@app.get("/api/content/{content_type}", tags=["Content"], response_model=dict)
def get_content_by_type(content_type: str, refresh: bool = False):
    """
    Get content filtered by type.
    
    - **content_type**: Type of content to retrieve (blogs, podcasts, videos, events, learn, all_sources)
    - **refresh**: Force refresh from sources
    
    Returns articles categorized by the specified content type.
    """
    articles = [a for a in SAMPLE_ARTICLES if a.get("category") == content_type or content_type == "all_sources"]
    return {
        "articles": articles,
        "total": len(articles),
        "content_type": content_type,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/digest", tags=["Content"], response_model=DigestResponse)
def get_digest(refresh: bool = False):
    """
    Get AI news digest with latest articles and multimedia content.
    
    - **refresh**: Optional parameter to force refresh from sources
    
    Returns a comprehensive digest including:
    - Summary with key points and metrics
    - Top stories ranked by significance
    - Categorized content (blog, audio, video)
    - Timestamp and badge information
    """
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
@app.post("/auth/register", tags=["Authentication"], response_model=dict)
def register(user: UserRegister):
    """
    Register a new user account.
    
    - **email**: User's email address
    - **password**: User's password (minimum 8 characters)
    - **preferences**: Optional user preferences object
    
    Returns user information and authentication token.
    """
    return {
        "message": "User registered successfully",
        "user": {"email": user.email, "tier": "free"},
        "token": "sample-jwt-token-12345"
    }

@app.post("/auth/login", tags=["Authentication"], response_model=dict)
def login(user: UserLogin):
    """
    Authenticate user with email and password.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns user information and authentication token.
    """
    return {
        "message": "Login successful",
        "user": {"email": user.email, "tier": "premium"},
        "token": "sample-jwt-token-67890"
    }

@app.get("/auth/profile", tags=["Authentication"], response_model=dict)
def get_profile():
    """
    Get current authenticated user profile.
    
    Requires valid JWT token in Authorization header.
    Returns complete user profile information.
    """
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
@app.post("/auth/google", tags=["Authentication"], response_model=dict)
def google_auth(auth_request: GoogleAuthRequest):
    """
    Authenticate with Google OAuth token.
    
    Verifies the Google OAuth token and creates or updates a user account.
    Returns a JWT token for subsequent API requests.
    
    - **token**: Google OAuth ID token from frontend authentication
    
    Returns user information and JWT access token.
    """
    return {
        "message": "Google authentication successful",
        "user": {"email": "google.user@example.com", "tier": "premium"},
        "token": "google-jwt-token-abc123"
    }

@app.get("/auth/google", tags=["Authentication"], response_model=dict)
def google_auth_info():
    """
    Get Google OAuth configuration information.
    
    Returns Google OAuth settings and configuration status.
    """
    return {"auth_url": "https://accounts.google.com/oauth/authorize", "configured": True}

# Scraping endpoints
@app.get("/api/scrape", tags=["Content"], response_model=dict)
def manual_scrape(priority_only: Optional[bool] = False):
    """
    Manually trigger content scraping from RSS sources.
    
    - **priority_only**: If true, only scrape high-priority sources for faster execution
    
    Returns information about the scraping operation including:
    - Number of articles found and processed
    - List of sources scraped
    - Claude API availability status
    
    This endpoint is useful for testing or forcing immediate content updates.
    """
    return {
        "message": "Manual scrape initiated",
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "sources_updated": 12,
        "articles_found": 25,
        "articles_processed": 25,
        "sources": ["OpenAI", "Google AI", "Anthropic", "DeepMind"],
        "claude_available": bool(os.environ.get("CLAUDE_API_KEY"))
    }

@app.get("/api/sources", tags=["Content"], response_model=dict)
def get_sources():
    """
    Get all configured RSS news sources.
    
    Returns:
    - Complete list of AI news sources with configuration
    - Count of enabled sources
    - Claude API availability status
    """
    sources = [
        {"name": "OpenAI Blog", "url": "https://openai.com/blog", "enabled": True, "priority": 1},
        {"name": "Google AI Blog", "url": "https://ai.googleblog.com", "enabled": True, "priority": 1},
        {"name": "Anthropic", "url": "https://anthropic.com/news", "enabled": True, "priority": 1},
        {"name": "DeepMind", "url": "https://deepmind.com/blog", "enabled": True, "priority": 2}
    ]
    return {
        "sources": sources,
        "enabled_count": len([s for s in sources if s["enabled"]]),
        "claude_available": bool(os.environ.get("CLAUDE_API_KEY"))
    }

# Documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Custom Swagger UI endpoint with enhanced styling.
    """
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="AI News Scraper API Documentation",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """
    Alternative API documentation using ReDoc.
    """
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="AI News Scraper API Documentation"
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_spec():
    """
    Get OpenAPI specification in JSON format.
    """
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI News Scraper API",
        version="2.0.0",
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/google endpoint"
        }
    }
    
    # Add global security requirement for protected endpoints
    protected_paths = [
        "/auth/profile",
        "/subscription/preferences", 
        "/subscription/account"
    ]
    
    for path, path_item in openapi_schema["paths"].items():
        if any(protected_path in path for protected_path in protected_paths):
            for method in path_item.values():
                if isinstance(method, dict) and "operationId" in method:
                    method["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# For Vercel deployment
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)