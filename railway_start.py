#!/usr/bin/env python3
"""
Railway-specific startup file for AI News Scraper API
Direct import without api/ directory structure
"""

import os
import sys
import logging

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main app
from main import app

# Export for Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logging.info(f"🚀 Starting Railway deployment on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)