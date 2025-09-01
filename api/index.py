from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import datetime
from typing import Dict, Optional, List

# Request models
class GoogleAuthRequest(BaseModel):
    token: str

class UserRegister(BaseModel):
    email: str
    password: str

# FastAPI app
app = FastAPI(
    title="AI News Scraper API",
    version="2.0.0",
    description="""
    ## AI News Scraper API with Swagger Documentation
    
    ### Features
    - Authentication (Google OAuth, JWT)
    - Content scraping from AI sources
    - Multimedia content processing
    - Subscription management
    
    ### Documentation
    - Swagger UI: `/docs`
    - ReDoc: `/redoc`
    - OpenAPI: `/openapi.json`
    """,
    openapi_tags=[
        {"name": "System", "description": "System endpoints"},
        {"name": "Authentication", "description": "Auth endpoints"},
        {"name": "Content", "description": "Content endpoints"},
        {"name": "Admin", "description": "Admin endpoints"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data
SAMPLE_ARTICLES = [{
    "title": "OpenAI GPT-5 Release",
    "source": "OpenAI",
    "url": "https://openai.com/gpt5",
    "significanceScore": 95
}]

# Endpoints
@app.get("/", tags=["System"])
def root():
    """API root endpoint"""
    return {
        "message": "AI News Scraper API",
        "status": "running",
        "version": "2.0.0",
        "swagger_ui": "/docs",
        "endpoints": ["/health", "/api/digest", "/auth/google"]
    }

@app.get("/health", tags=["System"])
def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/digest", tags=["Content"])
def get_digest():
    """Get AI news digest"""
    return {
        "summary": {
            "keyPoints": ["OpenAI releases GPT-5"],
            "metrics": {"totalUpdates": 1}
        },
        "topStories": SAMPLE_ARTICLES,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/google", tags=["Authentication"])
def google_auth(auth_request: GoogleAuthRequest):
    """Google OAuth authentication"""
    return {
        "access_token": "jwt-token-example",
        "user": {"email": "user@example.com"}
    }

@app.get("/admin/subscribers", tags=["Admin"])
def get_subscribers():
    """Get subscribers (admin)"""
    return {
        "subscribers": [{"id": 1, "email": "user@example.com"}],
        "total": 1
    }

# Enhanced OpenAPI
@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    """Custom OpenAPI with security"""
    from fastapi.openapi.utils import get_openapi
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# ASGI handler for Vercel (this is the key for function detection)
handler = app