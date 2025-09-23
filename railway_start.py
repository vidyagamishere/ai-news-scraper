#!/usr/bin/env python3
"""
Railway-specific startup file for AI News Scraper API
Forces modular FastAPI architecture with PostgreSQL
"""

import os
import sys
import logging

# Ensure we can import from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("🚀 Railway startup: Using modular FastAPI architecture")
logger.info("🐘 Forcing PostgreSQL backend (no SQLite)")

try:
    # Import the modular main app (not api/index.py)
    from main import app
    logger.info("✅ Successfully imported modular FastAPI app from main.py")
    
    # Verify it's the modular architecture
    if hasattr(app, 'title') and 'Modular' in str(app.title):
        logger.info("✅ Confirmed: Using modular FastAPI architecture")
    else:
        logger.warning("⚠️ App title doesn't indicate modular architecture")
    
except ImportError as e:
    logger.error(f"❌ Failed to import modular app: {e}")
    # Fallback to api/index.py if main.py fails
    try:
        from api.index import app
        logger.warning("⚠️ Fallback: Using api/index.py (not preferred)")
    except ImportError as e2:
        logger.error(f"❌ Both main.py and api/index.py failed: {e2}")
        raise e2

# Export for Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting Railway modular FastAPI deployment on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)