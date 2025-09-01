from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        if self.path == '/' or self.path == '/api':
            response = {
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
        elif self.path == '/health':
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {"api": True, "database": True}
            }
        elif self.path == '/api/digest':
            response = {
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
        elif self.path == '/docs':
            # Swagger UI HTML
            swagger_html = '''
<!DOCTYPE html>
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
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(swagger_html.encode())
            return
        elif self.path == '/openapi.json':
            response = {
                "openapi": "3.0.0",
                "info": {
                    "title": "AI News Scraper API",
                    "version": "2.0.0",
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
                                            "properties": {"token": {"type": "string"}}
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
            response = {"error": "Not found", "path": self.path}
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        if self.path == '/auth/google':
            response = {
                "access_token": "jwt-token-example",
                "token_type": "bearer",
                "user": {"email": "user@example.com", "name": "Test User"}
            }
        else:
            response = {"message": "POST endpoint", "path": self.path}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()