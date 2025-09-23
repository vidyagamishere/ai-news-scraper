#!/usr/bin/env python3
"""
Main entry point for AI News Scraper API
Redirects to modular FastAPI application with PostgreSQL-only backend
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the new modular FastAPI application
from app.main import app

# For backwards compatibility and direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting AI News Scraper API (Modular PostgreSQL) on port {port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Set to False for production
    )