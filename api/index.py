# Vercel serverless function handler for AI News Scraper API
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the FastAPI app from main.py
    from main import app
    
    # Export for Vercel
    handler = app
    
except ImportError as e:
    # Fallback if main.py import fails
    print(f"Failed to import main app: {e}")
    
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create a minimal fallback app
    fallback_app = FastAPI(
        title="AI News Scraper API - Fallback",
        version="1.0.0",
        description="Fallback API when main application fails to load"
    )
    
    fallback_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    
    @fallback_app.get("/")
    def root():
        return {
            "message": "AI News Scraper API - Fallback Mode",
            "status": "running",
            "version": "1.0.0",
            "note": "Main application failed to load"
        }
    
    @fallback_app.get("/health")
    def health():
        return {"status": "ok", "mode": "fallback"}
    
    handler = fallback_app