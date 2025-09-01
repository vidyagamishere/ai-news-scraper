"""
Minimal test API to verify basic functionality
"""
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI News Scraper - Minimal Test")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "AI News Scraper API - Minimal Test", 
        "status": "running",
        "version": "test"
    }

@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    """Handle CORS preflight requests"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age": "3600"
        }
    )

@app.get("/subscription/preferences")
async def get_subscription_preferences():
    """Test endpoint for preferences"""
    return {
        "message": "Subscription preferences endpoint working",
        "preferences": {
            "frequency": "daily",
            "categories": ["all"],
            "content_types": ["all"]
        }
    }

@app.post("/subscription/preferences")
async def save_subscription_preferences():
    """Test endpoint for saving preferences"""
    return {"message": "Preferences saved successfully"}

@app.get("/email/preview-digest")
async def preview_digest():
    """Test endpoint for email preview"""
    return {
        "message": "Email preview endpoint working",
        "html": "<p>Test email preview</p>"
    }

@app.post("/email/send-digest")
async def send_digest():
    """Test endpoint for sending digest"""
    return {"message": "Email service not configured, but endpoint working"}

@app.get("/api/digest")
async def get_digest():
    """Test digest endpoint"""
    return {
        "summary": {
            "keyPoints": ["• Test digest working"],
            "metrics": {"totalUpdates": 1, "highImpact": 0, "newResearch": 0, "industryMoves": 0}
        },
        "topStories": [],
        "content": {"blog": [], "audio": [], "video": []},
        "badge": "Test Digest"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)