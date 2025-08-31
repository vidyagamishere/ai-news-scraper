from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        if self.path == '/health':
            response = {"status": "healthy", "service": "ai-news-scraper"}
        elif self.path == '/api/content-types':
            response = {
                "all_sources": {"name": "All Sources", "icon": "🌐"},
                "blogs": {"name": "Blogs", "icon": "✍️"},
                "podcasts": {"name": "Podcasts", "icon": "🎧"},
                "videos": {"name": "Videos", "icon": "📹"},
                "events": {"name": "Events", "icon": "📅"},
                "learn": {"name": "Learn", "icon": "🎓"}
            }
        elif self.path == '/api/digest':
            response = {
                "summary": {"keyPoints": ["AI news working"], "metrics": {"totalUpdates": 5}},
                "topStories": [{"title": "API Working", "source": "Test", "url": "https://example.com"}],
                "content": {"blog": [], "audio": [], "video": []},
                "timestamp": "2025-08-31T15:00:00Z",
                "badge": "Latest"
            }
        elif self.path.startswith('/api/digest/'):
            content_type = self.path.split('/')[-1]
            response = {
                "summary": {"keyPoints": [f"{content_type.title()} content available"], "metrics": {"totalUpdates": 3}},
                "topStories": [{"title": f"Sample {content_type.title()}", "source": "Demo", "url": "https://example.com"}],
                "content": {"blog": [], "audio": [], "video": []},
                "timestamp": "2025-08-31T15:00:00Z",
                "badge": "Latest"
            }
        elif self.path == '/auth/profile':
            response = {
                "id": 1,
                "email": "demo@example.com",
                "name": "Demo User",
                "subscriptionTier": "premium",
                "createdAt": "2025-08-31T10:00:00Z",
                "preferences": {
                    "topics": [{"id": 1, "name": "Machine Learning", "selected": True}]
                }
            }
        elif self.path == '/topics':
            response = [
                {"id": 1, "name": "Machine Learning", "description": "ML and deep learning updates"},
                {"id": 2, "name": "AI Research", "description": "Latest research papers and findings"}
            ]
        else:
            response = {"message": "AI News API", "status": "running"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except:
            data = {}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        if self.path == '/auth/login':
            response = {
                "user": {
                    "id": 1,
                    "email": data.get("email", "demo@example.com"),
                    "name": "Demo User",
                    "subscriptionTier": "premium",
                    "createdAt": "2025-08-31T10:00:00Z",
                    "preferences": {
                        "topics": [{"id": 1, "name": "Machine Learning", "selected": True}]
                    }
                },
                "token": "demo-auth-token-12345"
            }
        elif self.path == '/auth/signup':
            response = {
                "user": {
                    "id": 2,
                    "email": data.get("email", "newuser@example.com"),
                    "name": data.get("name", "New User"),
                    "subscriptionTier": "free",
                    "createdAt": "2025-08-31T15:00:00Z",
                    "preferences": {
                        "topics": []
                    }
                },
                "token": "demo-auth-token-67890"
            }
        elif self.path == '/auth/google':
            response = {
                "user": {
                    "id": 3,
                    "email": "google@example.com",
                    "name": "Google User",
                    "subscriptionTier": "free",
                    "createdAt": "2025-08-31T15:00:00Z",
                    "preferences": {
                        "topics": []
                    }
                },
                "token": "demo-google-token-54321"
            }
        else:
            response = {"message": "POST endpoint working"}
            
        self.wfile.write(json.dumps(response).encode())
    
    def do_PUT(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except:
            data = {}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        if self.path == '/auth/preferences':
            response = {
                "id": 1,
                "email": "demo@example.com",
                "name": "Demo User",
                "subscriptionTier": "premium",
                "createdAt": "2025-08-31T10:00:00Z",
                "preferences": data
            }
        else:
            response = {"message": "PUT endpoint working"}
            
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()