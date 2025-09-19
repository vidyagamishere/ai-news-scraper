#!/usr/bin/env python3
"""
Simple test deployment to check if Vercel deployment works
"""
from fastapi import FastAPI

app = FastAPI(title="Test Deploy", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Test deployment working"}

@app.get("/health")
async def health():
    return {"status": "healthy", "test": True}

@app.get("/api/health")
async def api_health():
    return {"status": "healthy", "api": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)