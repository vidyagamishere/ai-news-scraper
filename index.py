from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
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
                "timestamp": "2025-08-31T15:00:00Z"
            }
        else:
            response = {"message": "AI News API", "status": "running"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if self.path == '/auth/login':
            response = {"message": "Login successful", "token": "test-token"}
        else:
            response = {"message": "POST endpoint working"}
            
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()