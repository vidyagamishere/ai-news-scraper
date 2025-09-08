from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Set CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # Parse path
        path = self.path.strip('/')
        if path.startswith('api/'):
            path = path[4:]  # Remove 'api/' prefix
            
        try:
            if path == '' or path == 'health':
                response_data = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Simple API is working",
                    "components": {
                        "api": True,
                        "enhanced_scraping": False,
                        "scheduler": False
                    }
                }
            else:
                response_data = {
                    "error": "Endpoint not found",
                    "path": path,
                    "available_endpoints": ["health"]
                }
            
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            error_response = {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_POST(self):
        self.do_GET()  # Same handler for now
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()