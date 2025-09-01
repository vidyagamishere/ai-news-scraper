import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs

def handler(request, context):
    """
    Vercel serverless function handler for AI News Scraper API
    """
    
    # Parse request
    method = request.get('httpMethod', 'GET')
    path = request.get('path', '/')
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS requests
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Route handling
    if method == 'GET':
        if path == '/' or path == '/api':
            response_data = {
                "message": "AI News Scraper API with Swagger Documentation",
                "status": "running", 
                "version": "2.0.1",
                "swagger_ui": "/docs",
                "openapi_spec": "/openapi.json",
                "endpoints": {
                    "system": ["/", "/health"],
                    "content": ["/api/digest", "/api/scrape"],
                    "auth": ["/auth/google", "/auth/login"],
                    "admin": ["/admin/subscribers"]
                }
            }
        
        elif path == '/health' or path == '/api/health':
            response_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {"api": True, "database": True}
            }
        
        elif path == '/api/digest':
            response_data = {
                "summary": {
                    "keyPoints": ["OpenAI releases GPT-5 with breakthrough reasoning"],
                    "metrics": {"totalUpdates": 1, "highImpact": 1}
                },
                "topStories": [{
                    "title": "OpenAI GPT-5 Release",
                    "source": "OpenAI",
                    "url": "https://openai.com/gpt5"
                }],
                "timestamp": datetime.now().isoformat()
            }
        
        elif path == '/docs':
            # Return Swagger UI HTML
            swagger_html = '''<!DOCTYPE html>
<html>
<head>
    <title>AI News Scraper API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ]
        });
    </script>
</body>
</html>'''
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': swagger_html
            }
        
        elif path == '/openapi.json':
            response_data = {
                "openapi": "3.0.0",
                "info": {
                    "title": "AI News Scraper API",
                    "version": "2.0.1",
                    "description": "Comprehensive AI News Scraper API with authentication and content management"
                },
                "paths": {
                    "/": {
                        "get": {
                            "tags": ["System"],
                            "summary": "API root endpoint",
                            "responses": {"200": {"description": "API information"}}
                        }
                    },
                    "/health": {
                        "get": {
                            "tags": ["System"],
                            "summary": "Health check",
                            "responses": {"200": {"description": "Health status"}}
                        }
                    },
                    "/api/digest": {
                        "get": {
                            "tags": ["Content"],
                            "summary": "Get AI news digest",
                            "responses": {"200": {"description": "News digest"}}
                        }
                    },
                    "/auth/google": {
                        "post": {
                            "tags": ["Authentication"],
                            "summary": "Google OAuth authentication",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"token": {"type": "string"}},
                                            "required": ["token"]
                                        }
                                    }
                                }
                            },
                            "responses": {"200": {"description": "Authentication response"}}
                        }
                    }
                },
                "components": {
                    "securitySchemes": {
                        "bearerAuth": {
                            "type": "http",
                            "scheme": "bearer",
                            "bearerFormat": "JWT"
                        }
                    }
                },
                "tags": [
                    {"name": "System", "description": "System endpoints"},
                    {"name": "Content", "description": "Content endpoints"},
                    {"name": "Authentication", "description": "Auth endpoints"}
                ]
            }
        
        else:
            response_data = {"error": "Not found", "path": path}
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps(response_data)
            }
    
    elif method == 'POST':
        if path == '/auth/google':
            response_data = {
                "access_token": "jwt-token-example",
                "token_type": "bearer",
                "user": {"email": "user@example.com", "name": "Test User"}
            }
        else:
            response_data = {"message": "POST endpoint", "path": path}
    
    else:
        response_data = {"error": "Method not allowed"}
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps(response_data)
        }
    
    # Return successful response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response_data)
    }