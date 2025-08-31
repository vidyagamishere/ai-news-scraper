from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is working", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "ai-news-scraper"}