#!/usr/bin/env python3
"""
Basic test to isolate import issues
"""
import os
import sys

def handler(request):
    """Basic handler for Vercel"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"message": "Basic test working", "python_version": "' + sys.version + '"}'
    }

# Test basic imports
try:
    import fastapi
    fastapi_status = "✅ FastAPI available"
except ImportError as e:
    fastapi_status = f"❌ FastAPI import error: {e}"

try:
    import psycopg2
    postgres_status = "✅ PostgreSQL driver available"
except ImportError as e:
    postgres_status = f"❌ PostgreSQL import error: {e}"

try:
    import requests
    requests_status = "✅ Requests available"
except ImportError as e:
    requests_status = f"❌ Requests import error: {e}"

try:
    import email_validator
    email_status = "✅ Email validator available"
except ImportError as e:
    email_status = f"❌ Email validator import error: {e}"

print(f"Import status:")
print(f"  {fastapi_status}")
print(f"  {postgres_status}")
print(f"  {requests_status}")
print(f"  {email_status}")

if __name__ == "__main__":
    print("Basic test script executed successfully")