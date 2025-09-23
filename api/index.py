#!/usr/bin/env python3
"""
Vercel serverless function handler for AI News Scraper API
Uses modular FastAPI architecture with PostgreSQL backend
Maintains single-function deployment compatibility
"""

import os
from fastapi import Request

# Import the modular FastAPI application
from app.main import app

# Vercel serverless function handler
async def handler(request: Request):
    """
    Vercel serverless function handler that routes to modular FastAPI app
    This maintains the single-function deployment pattern while using
    the new modular architecture internally
    """
    return await app(request.scope, request.receive, request._send)

# Export for Vercel
app = app