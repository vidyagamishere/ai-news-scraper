#!/usr/bin/env python3
"""
Minimal test to isolate deployment issues
"""
from fastapi import FastAPI

app = FastAPI(title="Minimal Test API")

@app.get("/")
async def root():
    return {"message": "Minimal test working", "status": "ok"}

@app.get("/api/test")
async def test():
    return {"test": "success", "dependencies": "minimal"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)