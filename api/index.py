# Vercel serverless function handler for AI News Scraper API
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the FastAPI app with Swagger documentation
    from swagger_main import app
    
    # Export for Vercel
    handler = app
    
except ImportError as e:
    # Simple fallback if imports fail
    print(f"Failed to import swagger_main app: {e}")
    
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create a minimal working app with Swagger
    fallback_app = FastAPI(
        title="AI News Scraper API - Simplified",
        version="1.0.0",
        description="Simplified AI News Scraper API with Swagger documentation"
    )
    
    fallback_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    
    @fallback_app.get("/", tags=["System"])
    def root():
        return {
            "message": "AI News Scraper API - Simplified Mode",
            "status": "running",
            "version": "1.0.0",
            "swagger_available": True
        }
    
    @fallback_app.get("/health", tags=["System"])
    def health():
        return {"status": "ok", "mode": "simplified"}
    
    @fallback_app.get("/api/digest", tags=["Content"])
    def get_digest():
        return {
            "summary": {
                "keyPoints": ["API is running in simplified mode"],
                "metrics": {"totalUpdates": 0}
            },
            "topStories": [],
            "content": {"blog": [], "audio": [], "video": []},
            "timestamp": "2025-08-31T20:00:00Z",
            "badge": "Simplified"
        }
    
    handler = fallback_app