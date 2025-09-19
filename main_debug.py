#!/usr/bin/env python3
"""
DEBUG VERSION: AI News Scraper API with extensive logging for Vercel debugging
"""
import os
import sys
import logging
from datetime import datetime

# Set up comprehensive logging FIRST
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Log startup immediately
logger.info("🚀 STARTING AI News Scraper API Debug Version")
logger.info(f"📍 Python version: {sys.version}")
logger.info(f"📍 Working directory: {os.getcwd()}")
logger.info(f"📍 __name__: {__name__}")
logger.info(f"📍 __file__: {__file__}")

try:
    logger.info("📦 Importing FastAPI...")
    from fastapi import FastAPI, HTTPException
    logger.info("✅ FastAPI imported successfully")
    
    logger.info("📦 Importing CORS middleware...")
    from fastapi.middleware.cors import CORSMiddleware
    logger.info("✅ CORS middleware imported successfully")
    
    logger.info("📦 Importing dotenv...")
    from dotenv import load_dotenv
    logger.info("✅ dotenv imported successfully")
    
except Exception as e:
    logger.error(f"❌ Import error: {e}")
    raise

# Load environment
logger.info("🔧 Loading environment variables...")
load_dotenv()

# Log environment status
postgres_url = os.getenv("POSTGRES_URL")
jwt_secret = os.getenv("JWT_SECRET") 
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

logger.info(f"🔑 POSTGRES_URL configured: {bool(postgres_url)}")
logger.info(f"🔑 JWT_SECRET configured: {bool(jwt_secret)}")
logger.info(f"🔑 GOOGLE_CLIENT_ID configured: {bool(google_client_id)}")
logger.info(f"🔑 ALLOWED_ORIGINS: {allowed_origins}")

# Create FastAPI app with detailed logging
logger.info("🏗️  Creating FastAPI application...")
try:
    app = FastAPI(
        title="AI News Scraper API - Debug Version", 
        version="2.0.0-debug",
        description="Debug version with extensive logging for Vercel deployment",
        debug=True
    )
    logger.info("✅ FastAPI application created successfully")
except Exception as e:
    logger.error(f"❌ Error creating FastAPI app: {e}")
    raise

# Configure CORS with logging
logger.info("🌐 Configuring CORS...")
try:
    origins_list = allowed_origins.split(",") if allowed_origins != "*" else ["*"]
    origins_list = [origin.strip() for origin in origins_list]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info(f"✅ CORS configured with origins: {origins_list}")
except Exception as e:
    logger.error(f"❌ Error configuring CORS: {e}")
    raise

# Global state
db_initialized = False
initialization_error = None

@app.get("/")
async def root():
    """Root endpoint with detailed debugging info"""
    logger.info("📍 Root endpoint called")
    
    try:
        return {
            "message": "AI News Scraper API - Debug Version",
            "status": "running",
            "version": "2.0.0-debug",
            "timestamp": datetime.now().isoformat(),
            "debug_info": {
                "python_version": sys.version,
                "fastapi_detected": True,
                "working_directory": os.getcwd(),
                "environment_variables": {
                    "postgres_url_configured": bool(postgres_url),
                    "jwt_secret_configured": bool(jwt_secret),
                    "google_client_id_configured": bool(google_client_id),
                },
                "db_initialized": db_initialized,
                "initialization_error": str(initialization_error) if initialization_error else None
            },
            "deployment_status": "vercel_detection_successful"
        }
    except Exception as e:
        logger.error(f"❌ Error in root endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Root endpoint error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check with debug information"""
    logger.info("📍 Health check endpoint called")
    
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0-debug",
            "debug_health": {
                "fastapi_running": True,
                "endpoints_accessible": True,
                "logging_working": True,
                "environment_loaded": True
            },
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "executable": sys.executable
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in health check: {e}")
        raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")

@app.get("/api/debug-info")
async def debug_info():
    """Detailed debug information endpoint"""
    logger.info("📍 Debug info endpoint called")
    
    try:
        import_status = {}
        
        # Test imports
        try:
            import asyncpg
            import_status["asyncpg"] = f"✅ Available: {asyncpg.__version__}"
        except ImportError as e:
            import_status["asyncpg"] = f"❌ Not available: {e}"
        
        try:
            import requests
            import_status["requests"] = f"✅ Available: {requests.__version__}"
        except ImportError as e:
            import_status["requests"] = f"❌ Not available: {e}"
            
        try:
            import pydantic
            import_status["pydantic"] = f"✅ Available: {pydantic.__version__}"
        except ImportError as e:
            import_status["pydantic"] = f"❌ Not available: {e}"

        return {
            "debug_timestamp": datetime.now().isoformat(),
            "app_info": {
                "title": app.title,
                "version": app.version,
                "debug_mode": app.debug if hasattr(app, 'debug') else "unknown"
            },
            "environment": {
                "working_dir": os.getcwd(),
                "python_path": sys.path[:3],  # First 3 entries
                "env_vars": {
                    "POSTGRES_URL": "configured" if postgres_url else "missing",
                    "JWT_SECRET": "configured" if jwt_secret else "missing", 
                    "GOOGLE_CLIENT_ID": "configured" if google_client_id else "missing"
                }
            },
            "imports": import_status,
            "files_check": {
                "requirements_txt": os.path.exists("requirements.txt"),
                "runtime_txt": os.path.exists("runtime.txt"),
                "vercel_json": os.path.exists("vercel.json")
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in debug info: {e}")
        raise HTTPException(status_code=500, detail=f"Debug info error: {str(e)}")

@app.get("/api/test-simple")
async def test_simple():
    """Simplest possible test endpoint"""
    logger.info("📍 Simple test endpoint called")
    return {"test": "success", "timestamp": datetime.now().isoformat()}

# Add startup event with logging
@app.on_event("startup")
async def startup_event():
    """Startup event with detailed logging"""
    global db_initialized, initialization_error
    
    logger.info("🚀 Application startup event triggered")
    
    try:
        logger.info("🔧 Checking environment configuration...")
        
        if not postgres_url:
            logger.warning("⚠️  POSTGRES_URL not configured")
        else:
            logger.info("✅ POSTGRES_URL configured")
            
        if not jwt_secret:
            logger.warning("⚠️  JWT_SECRET not configured")
        else:
            logger.info("✅ JWT_SECRET configured")
            
        # For now, mark as initialized without actual DB connection
        # to isolate FastAPI detection issues
        db_initialized = True
        logger.info("✅ Startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        initialization_error = e
        db_initialized = False

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event with logging"""
    logger.info("🛑 Application shutdown event triggered")

# Log that the app is defined
logger.info("✅ FastAPI app fully configured and ready")
logger.info(f"📋 Available routes: {[route.path for route in app.routes]}")

# Export app for Vercel (multiple patterns for compatibility)
application = app  # WSGI/ASGI pattern
handler = app      # Vercel handler pattern

# Vercel detection function
def create_app():
    """Factory function for app creation"""
    logger.info("🏭 App factory called")
    return app

# Standard Vercel handler
async def main(request):
    """Async handler for Vercel"""
    logger.info("🔧 Async handler called")
    return app

if __name__ == "__main__":
    logger.info("🖥️  Running in local development mode")
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
else:
    logger.info("🌐 Running in serverless mode (Vercel)")
    logger.info(f"📍 Module name: {__name__}")
    logger.info(f"📍 App object: {app}")
    logger.info(f"📍 Application object: {application}")
    logger.info(f"📍 Handler object: {handler}")
    logger.info("✅ App ready for Vercel deployment")