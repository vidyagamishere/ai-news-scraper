from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import time

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Set CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        try:
            # Simple POST parsing that works in serverless
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
            else:
                request_data = {}
            
            # Handle admin login
            if self.path == '/api/admin/login':
                email = request_data.get('email', '')
                password = request_data.get('password', '')
                
                if not email or not password:
                    self.send_response(400)
                    response_data = {"error": "Email and password required"}
                elif email == 'admin@vidyagam.com' and password == 'AdminPass123!':
                    response_data = {
                        "admin": {
                            "id": "admin_001",
                            "email": "admin@vidyagam.com",
                            "name": "Admin User",
                            "permissions": "content_admin"
                        },
                        "token": "admin-token-" + str(int(time.time())),
                        "login_time": datetime.now().isoformat()
                    }
                else:
                    self.send_response(401)
                    response_data = {"error": "Invalid credentials"}
                    
            # Handle user login
            elif self.path == '/api/auth/login':
                email = request_data.get('email', '')
                password = request_data.get('password', '')
                
                if not email or not password:
                    self.send_response(400)
                    response_data = {"error": "Email and password required"}
                elif email == 'dhanyashreevijayan@gmail.com' and password == 'Arunmugam1!':
                    response_data = {
                        "user": {
                            "id": "user_001", 
                            "email": "dhanyashreevijayan@gmail.com",
                            "name": "Dhanyashree Vijayan",
                            "subscriptionTier": "free",
                            "emailVerified": True,
                            "preferences": {
                                "topics": [
                                    {"id": "machine-learning", "name": "Machine Learning", "selected": True},
                                    {"id": "nlp", "name": "Natural Language Processing", "selected": True}
                                ],
                                "newsletterFrequency": "daily",
                                "emailNotifications": True,
                                "contentTypes": ["articles", "videos"],
                                "onboardingCompleted": True
                            }
                        },
                        "token": "user-token-" + str(int(time.time()))
                    }
                else:
                    self.send_response(401)
                    response_data = {"error": "Invalid credentials"}
                    
            else:
                response_data = {"error": "Endpoint not found"}
                
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            self.send_response(500)
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()