from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Testing auth import"}

@app.get("/api/test-auth")
def test_auth():
    try:
        from api.auth_service_postgres import AuthService
        return {"auth_import": "success"}
    except Exception as e:
        return {"auth_import": "failed", "error": str(e)}

@app.get("/api/test-db")
def test_db():
    try:
        from api.database_service import DatabaseService
        db = DatabaseService("test.db")
        return {"database_import": "success", "type": "PostgreSQL" if db.is_postgres else "SQLite"}
    except Exception as e:
        return {"database_import": "failed", "error": str(e)}