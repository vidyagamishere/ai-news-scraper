from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="AI News Scraper API", 
    version="2.0.0",
    description="AI News Scraper API with Swagger Documentation"
)

@app.get("/")
def root():
    return {
        "message": "AI News Scraper API",
        "status": "running",
        "swagger": "/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health") 
def health():
    return {"status": "ok"}

@app.get("/api/digest")
def digest():
    return {
        "summary": {"keyPoints": ["API is working"]},
        "timestamp": datetime.now().isoformat()
    }

handler = app