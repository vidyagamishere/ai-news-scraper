#!/usr/bin/env python3
"""
Vercel serverless function handler for AI News Scraper API
Uses modular FastAPI architecture with PostgreSQL backend
Routes to main.py for Railway compatibility
"""

import os
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modular FastAPI application from main.py
from main import app

# Export for Vercel
app = app