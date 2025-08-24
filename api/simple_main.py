"""
Simplified main.py without email dependencies for debugging
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI News Scraper - Debug Version")

# CORS
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
        "message": "AI News Scraper Debug API", 
        "status": "running",
        "version": "debug"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "components": {
            "api": "✅ Running",
            "environment": {
                "SENDGRID_API_KEY": "✅ Set" if os.getenv("SENDGRID_API_KEY") else "❌ Missing",
                "FROM_EMAIL": os.getenv("FROM_EMAIL", "Not set"),
                "GOOGLE_CLIENT_ID": "✅ Set" if os.getenv("GOOGLE_CLIENT_ID") else "❌ Missing"
            }
        }
    }

@app.get("/debug/imports")
async def debug_imports():
    """Debug import issues"""
    import_status = {}
    
    # Test basic imports
    try:
        import sqlite3
        import_status["sqlite3"] = "✅ Available"
    except ImportError as e:
        import_status["sqlite3"] = f"❌ Failed: {e}"
    
    try:
        import anthropic
        import_status["anthropic"] = "✅ Available"
    except ImportError as e:
        import_status["anthropic"] = f"❌ Failed: {e}"
    
    try:
        import jwt
        import_status["jwt"] = "✅ Available"
    except ImportError as e:
        import_status["jwt"] = f"❌ Failed: {e}"
    
    try:
        import sendgrid
        import_status["sendgrid"] = "✅ Available"
    except ImportError as e:
        import_status["sendgrid"] = f"❌ Failed: {e}"
    
    try:
        from jinja2 import Template
        import_status["jinja2"] = "✅ Available"
    except ImportError as e:
        import_status["jinja2"] = f"❌ Failed: {e}"
    
    try:
        from premailer import transform
        import_status["premailer"] = "✅ Available"
    except ImportError as e:
        import_status["premailer"] = f"❌ Failed: {e}"
    
    return {
        "import_status": import_status,
        "python_version": os.sys.version,
        "environment_variables": {
            var: "✅ Set" if os.getenv(var) else "❌ Not set"
            for var in ["SENDGRID_API_KEY", "FROM_EMAIL", "FROM_NAME", "GOOGLE_CLIENT_ID", "JWT_SECRET"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)