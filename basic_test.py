#!/usr/bin/env python3
"""
Basic test API for Vercel deployment
"""
import os
from datetime import datetime
from fastapi import FastAPI

# Create FastAPI app
app = FastAPI(title="Test API", version="1.0.0")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Basic test API working",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "postgres_url_configured": bool(os.getenv("POSTGRES_URL")),
            "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
            "google_client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID"))
        }
    }

@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# For Vercel
handler = app