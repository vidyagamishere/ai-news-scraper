#!/usr/bin/env python3
"""
Minimal test API to debug 504 errors
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

app = FastAPI(title="AI News Scraper Test API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "AI News Scraper Test API", 
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test/health")
async def test_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment_variables": {
            "GOOGLE_CLIENT_ID": "✅ Set" if os.getenv("GOOGLE_CLIENT_ID") else "❌ Missing",
            "JWT_SECRET": "✅ Set" if os.getenv("JWT_SECRET") else "❌ Missing",
            "CLAUDE_API_KEY": "✅ Set" if os.getenv("CLAUDE_API_KEY") else "❌ Missing"
        },
        "imports": {
            "jwt": "✅ Available",
            "google_auth": "✅ Available",
            "fastapi": "✅ Available"
        }
    }

@app.get("/test/oauth")
async def test_oauth():
    """Test OAuth dependencies"""
    try:
        import jwt
        import google.oauth2.id_token
        import google.auth.transport.requests
        
        return {
            "status": "✅ OAuth dependencies available",
            "google_client_id": os.getenv("GOOGLE_CLIENT_ID", "Not set")[:20] + "..." if os.getenv("GOOGLE_CLIENT_ID") else "Not set",
            "jwt_secret": "✅ Set" if os.getenv("JWT_SECRET") else "❌ Missing"
        }
    except ImportError as e:
        return {
            "status": "❌ Import error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)