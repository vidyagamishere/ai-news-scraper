from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AI News Scraper API is running", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-news-scraper"}