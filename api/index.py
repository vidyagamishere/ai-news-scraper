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
        
        elif path == '/api/content-types':
            response_data = {
                "all_sources": {"name": "All Sources", "description": "Comprehensive AI content", "icon": "🌐"},
                "blogs": {"name": "Blogs", "description": "Expert insights and analysis", "icon": "✍️"},
                "podcasts": {"name": "Podcasts", "description": "Audio content and interviews", "icon": "🎧"},
                "videos": {"name": "Videos", "description": "Visual content and presentations", "icon": "📹"},
                "events": {"name": "Events", "description": "AI conferences and workshops", "icon": "📅"},
                "learn": {"name": "Learn", "description": "Courses and tutorials", "icon": "🎓"}
            }
        
        elif path.startswith('/api/content/'):
            content_type = path.split('/')[-1]
            query_params = parse_qs(request.get('query', ''))
            refresh = query_params.get('refresh', [False])[0]
            
            # Sample content based on type
            if content_type == 'events':
                articles = [{
                    "title": "AI Conference 2024: The Future of Machine Learning",
                    "source": "AI Events",
                    "url": "https://aiconf2024.com",
                    "type": content_type,
                    "date": "2024-12-15",
                    "location": "San Francisco, CA",
                    "significanceScore": 8.2
                }]
            elif content_type == 'learn':
                articles = [{
                    "title": "Deep Learning Fundamentals Course",
                    "source": "AI Academy",
                    "url": "https://ailearning.com/deep-learning",
                    "type": content_type,
                    "duration": "6 weeks",
                    "level": "intermediate",
                    "significanceScore": 7.9
                }]
            else:
                articles = [{
                    "title": "OpenAI GPT-5 Release",
                    "source": "OpenAI",
                    "url": "https://openai.com/gpt5",
                    "type": content_type,
                    "significanceScore": 9.1
                }]
            
            response_data = {
                "articles": articles,
                "total": len(articles),
                "content_type": content_type,
                "sources": ["AI Events", "OpenAI", "Google AI"],
                "user_tier": "premium",
                "timestamp": datetime.now().isoformat()
            }
        
        elif path == '/api/scrape':
            response_data = {
                "message": "Manual scrape completed",
                "articles_found": 25,
                "articles_processed": 25,
                "sources": ["OpenAI", "Google AI", "Anthropic", "DeepMind"],
                "timestamp": datetime.now().isoformat()
            }
        
        elif path == '/api/sources':
            response_data = {
                "sources": [
                    {"name": "OpenAI Blog", "url": "https://openai.com/blog", "enabled": True, "priority": 1},
                    {"name": "Google AI Blog", "url": "https://ai.googleblog.com", "enabled": True, "priority": 1},
                    {"name": "Anthropic", "url": "https://anthropic.com/news", "enabled": True, "priority": 1}
                ],
                "enabled_count": 3
            }
        
        elif path == '/api/multimedia/audio':
            response_data = {
                "audio_content": [{
                    "title": "Lex Fridman: AGI Timeline Discussion",
                    "description": "In-depth conversation about artificial general intelligence.",
                    "source": "Lex Fridman Podcast",
                    "url": "https://lexfridman.com/agi-timeline",
                    "duration": 7200,
                    "significance_score": 8.5
                }],
                "total_count": 1
            }
        
        elif path == '/api/multimedia/video':
            response_data = {
                "video_content": [{
                    "title": "Two Minute Papers: Latest AI Breakthrough",
                    "description": "Analysis of recent AI research developments.",
                    "source": "Two Minute Papers",
                    "url": "https://youtube.com/watch?v=ai-breakthrough",
                    "duration": 360,
                    "significance_score": 7.8
                }],
                "total_count": 1
            }
        
        elif path == '/api/multimedia/scrape':
            response_data = {
                "message": "Multimedia scraping completed",
                "audio_found": 15,
                "video_found": 12,
                "audio_processed": 15,
                "video_processed": 12
            }
        
        elif path == '/api/multimedia/sources':
            response_data = {
                "sources": {
                    "audio": [{"name": "Lex Fridman Podcast", "enabled": True}],
                    "video": [{"name": "Two Minute Papers", "enabled": True}]
                },
                "audio_sources": 1,
                "video_sources": 1
            }
        
        elif path == '/subscription/preferences':
            response_data = {
                "preferences": {
                    "frequency": "daily",
                    "content_types": ["all"],
                    "categories": ["all"]
                }
            }
        
        elif path == '/api/user-preferences':
            response_data = {
                "content_types": ["blogs", "videos", "events", "learn"],
                "frequency": "daily",
                "topics": ["machine-learning", "nlp", "computer-vision"],
                "notification_preferences": {
                    "email": True,
                    "push": False
                }
            }
        
        elif path == '/auth/profile':
            response_data = {
                "id": 1,
                "name": "Test User",
                "email": "user@example.com",
                "tier": "premium",
                "preferences": {
                    "content_types": ["blogs", "videos", "events", "learn"],
                    "frequency": "daily"
                },
                "created_at": "2024-01-01T00:00:00Z"
            }
        
        elif path == '/topics':
            response_data = [
                {"id": "machine-learning", "name": "Machine Learning", "description": "ML algorithms and applications"},
                {"id": "nlp", "name": "Natural Language Processing", "description": "Text and language AI"},
                {"id": "computer-vision", "name": "Computer Vision", "description": "Image and video AI"},
                {"id": "robotics", "name": "Robotics", "description": "AI in robotics and automation"},
                {"id": "ethics", "name": "AI Ethics", "description": "Ethical considerations in AI"}
            ]
        
        elif path == '/api/auto-update/status':
            response_data = {
                "status": "active",
                "last_update": datetime.now().isoformat(),
                "next_update": "2024-01-02T00:00:00Z",
                "auto_update_enabled": True,
                "update_frequency": "every 4 hours"
            }
        
        elif path == '/admin/subscribers':
            response_data = {
                "subscribers": [
                    {"id": 1, "email": "user1@example.com", "active": True},
                    {"id": 2, "email": "user2@example.com", "active": True}
                ],
                "total": 2
            }
        
        elif path == '/admin/subscribers/stats':
            response_data = {
                "total_subscribers": 150,
                "active_subscribers": 142,
                "frequency_breakdown": {"daily": 89, "weekly": 45}
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
                    "/": {"get": {"tags": ["System"], "summary": "API root endpoint", "responses": {"200": {"description": "API information"}}}},
                    "/health": {"get": {"tags": ["System"], "summary": "Health check", "responses": {"200": {"description": "Health status"}}}},
                    "/api/health": {"get": {"tags": ["System"], "summary": "Health check", "responses": {"200": {"description": "Health status"}}}},
                    "/api/digest": {"get": {"tags": ["Content"], "summary": "Get AI news digest", "responses": {"200": {"description": "News digest"}}}},
                    "/api/content-types": {"get": {"tags": ["Content"], "summary": "Get content types", "responses": {"200": {"description": "Available content types"}}}},
                    "/api/content/{content_type}": {"get": {"tags": ["Content"], "summary": "Get content by type", "parameters": [{"name": "content_type", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Filtered content"}}}},
                    "/api/scrape": {"get": {"tags": ["Content"], "summary": "Manual content scraping", "responses": {"200": {"description": "Scraping results"}}}},
                    "/api/sources": {"get": {"tags": ["Content"], "summary": "Get RSS sources", "responses": {"200": {"description": "RSS sources list"}}}},
                    "/api/multimedia/audio": {"get": {"tags": ["Multimedia"], "summary": "Get audio content", "responses": {"200": {"description": "Audio content"}}}},
                    "/api/multimedia/video": {"get": {"tags": ["Multimedia"], "summary": "Get video content", "responses": {"200": {"description": "Video content"}}}},
                    "/api/multimedia/scrape": {"get": {"tags": ["Multimedia"], "summary": "Scrape multimedia", "responses": {"200": {"description": "Multimedia scraping results"}}}},
                    "/api/multimedia/sources": {"get": {"tags": ["Multimedia"], "summary": "Get multimedia sources", "responses": {"200": {"description": "Multimedia sources"}}}},
                    "/auth/google": {"post": {"tags": ["Authentication"], "summary": "Google OAuth", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"token": {"type": "string"}}, "required": ["token"]}}}}, "responses": {"200": {"description": "Auth response"}}}},
                    "/auth/register": {"post": {"tags": ["Authentication"], "summary": "Register user", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "password": {"type": "string"}}, "required": ["email", "password"]}}}}, "responses": {"200": {"description": "Registration response"}}}},
                    "/auth/login": {"post": {"tags": ["Authentication"], "summary": "Login user", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "password": {"type": "string"}}, "required": ["email", "password"]}}}}, "responses": {"200": {"description": "Login response"}}}},
                    "/auth/profile": {"get": {"tags": ["Authentication"], "summary": "Get user profile", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "User profile"}}}},
                    "/auth/signup": {"post": {"tags": ["Authentication"], "summary": "User signup", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}, "password": {"type": "string"}}, "required": ["name", "email", "password"]}}}}, "responses": {"200": {"description": "Signup response"}}}},
                    "/auth/preferences": {"put": {"tags": ["Authentication"], "summary": "Update user preferences", "security": [{"bearerAuth": []}], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"content_types": {"type": "array", "items": {"type": "string"}}, "frequency": {"type": "string"}, "topics": {"type": "array", "items": {"type": "string"}}}}}}}, "responses": {"200": {"description": "Updated user object"}}}},
                    "/subscription/preferences": {"get": {"tags": ["Subscription"], "summary": "Get preferences", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "User preferences"}}}, "post": {"tags": ["Subscription"], "summary": "Save preferences", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Success message"}}}},
                    "/subscription/account": {"delete": {"tags": ["Subscription"], "summary": "Delete account", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Deletion confirmation"}}}},
                    "/admin/subscribers": {"get": {"tags": ["Admin"], "summary": "Get all subscribers", "responses": {"200": {"description": "Subscribers list"}}}},
                    "/admin/subscribers/stats": {"get": {"tags": ["Admin"], "summary": "Get subscriber stats", "responses": {"200": {"description": "Subscriber statistics"}}}},
                    "/admin/subscribers/{subscriber_id}/activate": {"post": {"tags": ["Admin"], "summary": "Activate subscriber", "parameters": [{"name": "subscriber_id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Activation response"}}}},
                    "/admin/subscribers/{subscriber_id}/deactivate": {"post": {"tags": ["Admin"], "summary": "Deactivate subscriber", "parameters": [{"name": "subscriber_id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Deactivation response"}}}},
                    "/topics": {"get": {"tags": ["System"], "summary": "Get AI topics", "responses": {"200": {"description": "Available AI topics"}}}},
                    "/api/user-preferences": {"get": {"tags": ["User"], "summary": "Get user preferences", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "User preferences"}}}},
                    "/api/auto-update/status": {"get": {"tags": ["System"], "summary": "Get auto-update status", "responses": {"200": {"description": "Auto-update status"}}}},
                    "/api/auto-update/trigger": {"post": {"tags": ["System"], "summary": "Trigger auto-update", "responses": {"200": {"description": "Auto-update triggered"}}}},
                    "/subscription/upgrade": {"post": {"tags": ["Subscription"], "summary": "Upgrade subscription", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Upgrade response"}}}}
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
                    {"name": "Authentication", "description": "Auth endpoints"},
                    {"name": "User", "description": "User preference endpoints"},
                    {"name": "Subscription", "description": "Subscription endpoints"},
                    {"name": "Admin", "description": "Admin endpoints"},
                    {"name": "Multimedia", "description": "Multimedia endpoints"}
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
        # Parse request body
        body = request.get('body', '{}')
        try:
            request_data = json.loads(body) if body else {}
        except:
            request_data = {}
        
        if path == '/auth/google':
            response_data = {
                "access_token": "jwt-token-example",
                "token_type": "bearer",
                "user": {"email": "user@example.com", "name": "Test User"}
            }
        elif path == '/auth/register':
            response_data = {
                "message": "User registered successfully",
                "user": {"email": request_data.get("email", "user@example.com"), "tier": "free"},
                "token": "jwt-token-12345"
            }
        elif path == '/auth/login':
            response_data = {
                "user": {
                    "id": 1,
                    "name": "Test User",
                    "email": request_data.get("email", "user@example.com"),
                    "tier": "premium",
                    "preferences": {
                        "content_types": ["blogs", "videos", "events", "learn"],
                        "frequency": "daily"
                    }
                },
                "token": "jwt-token-67890"
            }
        elif path == '/auth/signup':
            response_data = {
                "user": {
                    "id": 2,
                    "name": request_data.get("name", "New User"),
                    "email": request_data.get("email", "newuser@example.com"),
                    "tier": "free",
                    "preferences": {
                        "content_types": ["blogs"],
                        "frequency": "daily"
                    }
                },
                "token": "jwt-token-new-user"
            }
        elif path == '/api/auto-update/trigger':
            response_data = {
                "message": "Auto-update triggered successfully",
                "status": {
                    "last_update": datetime.now().isoformat(),
                    "articles_processed": 15,
                    "sources_updated": 5
                }
            }
        elif path == '/subscription/upgrade':
            response_data = {
                "user": {
                    "id": 1,
                    "name": "Test User",
                    "email": "user@example.com",
                    "tier": "premium",
                    "preferences": {
                        "content_types": ["blogs", "videos", "events", "learn"],
                        "frequency": "daily"
                    }
                },
                "message": "Successfully upgraded to premium"
            }
        elif path == '/subscription/preferences':
            response_data = {"message": "Subscription preferences saved successfully"}
        elif path.startswith('/admin/subscribers/') and path.endswith('/activate'):
            subscriber_id = path.split('/')[-2]
            response_data = {"message": f"Subscriber {subscriber_id} activated successfully"}
        elif path.startswith('/admin/subscribers/') and path.endswith('/deactivate'):
            subscriber_id = path.split('/')[-2]
            response_data = {"message": f"Subscriber {subscriber_id} deactivated successfully"}
        else:
            response_data = {"message": "POST endpoint", "path": path}
    
    elif method == 'DELETE':
        if path == '/subscription/account':
            response_data = {"message": "Account deleted successfully"}
        else:
            response_data = {"error": "Method not allowed for this path"}
    
    elif method == 'PUT':
        # Parse request body
        body = request.get('body', '{}')
        try:
            request_data = json.loads(body) if body else {}
        except:
            request_data = {}
        
        if path == '/subscription/preferences':
            response_data = {"message": "Preferences updated successfully"}
        elif path == '/auth/preferences':
            response_data = {
                "user": {
                    "id": 1,
                    "name": "Test User",
                    "email": "user@example.com",
                    "tier": "premium",
                    "preferences": {
                        "content_types": request_data.get("content_types", ["blogs", "videos"]),
                        "frequency": request_data.get("frequency", "daily"),
                        "topics": request_data.get("topics", ["machine-learning"])
                    }
                }
            }
        else:
            response_data = {"error": "Method not allowed for this path"}
    
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