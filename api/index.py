from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import re
from datetime import datetime, timedelta
import hashlib
import uuid

class handler(BaseHTTPRequestHandler):
    # In-memory storage for demo (use real database in production)
    users_db = {}
    tokens_db = {}
    
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
    
    def _get_user_from_token(self, token):
        """Extract user from Authorization token"""
        if token and token.startswith('Bearer '):
            token = token[7:]
        return self.tokens_db.get(token)
    
    def _create_token(self, user_id):
        """Create a new auth token"""
        token = str(uuid.uuid4())
        self.tokens_db[token] = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        return token
    
    def _validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _hash_password(self, password):
        """Simple password hashing (use proper bcrypt in production)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response with proper headers"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error_response(self, message, status_code=400):
        """Send error response"""
        self._send_json_response({'error': message, 'message': message}, status_code)
    
    def do_GET(self):
        auth_token = self.headers.get('Authorization')
        
        try:
            if self.path == '/health':
                self._send_json_response({
                    "status": "healthy", 
                    "service": "ai-news-scraper",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            elif self.path == '/api/content-types':
                self._send_json_response({
                    "all_sources": {"name": "All Sources", "icon": "🌐"},
                    "blogs": {"name": "Blogs", "icon": "✍️"},
                    "podcasts": {"name": "Podcasts", "icon": "🎧"},
                    "videos": {"name": "Videos", "icon": "📹"},
                    "events": {"name": "Events", "icon": "📅"},
                    "learn": {"name": "Learn", "icon": "🎓"}
                })
                
            elif self.path == '/api/digest':
                # Sample digest data with categorized content
                self._send_json_response({
                    "summary": {
                        "keyPoints": [
                            "OpenAI releases GPT-4 Turbo with enhanced reasoning",
                            "Google DeepMind announces breakthrough in protein folding",
                            "Meta unveils new multimodal AI assistant"
                        ], 
                        "metrics": {"totalUpdates": 15, "newSources": 5, "trending": 8}
                    },
                    "topStories": [
                        {
                            "title": "OpenAI GPT-4 Turbo: Enhanced Reasoning Capabilities",
                            "source": "OpenAI Blog",
                            "url": "https://openai.com/blog/gpt-4-turbo",
                            "description": "Latest improvements in AI reasoning and problem-solving",
                            "timestamp": "2025-08-31T12:00:00Z",
                            "category": "blogs"
                        },
                        {
                            "title": "Google DeepMind's Protein Folding Breakthrough",
                            "source": "Nature",
                            "url": "https://nature.com/articles/protein-folding-ai",
                            "description": "Revolutionary advances in computational biology",
                            "timestamp": "2025-08-31T10:30:00Z",
                            "category": "blogs"
                        }
                    ],
                    "content": {
                        "blogs": [
                            {"title": "The Future of AI Ethics", "source": "AI Ethics Lab", "url": "https://aiethics.com/future"},
                            {"title": "Machine Learning in Healthcare", "source": "Health AI", "url": "https://healthai.com/ml"}
                        ],
                        "podcasts": [
                            {"title": "Lex Fridman - AI Safety Discussion", "source": "Lex Fridman Podcast", "url": "https://lexfridman.com/ai-safety"},
                            {"title": "TWiML - Latest AI Research", "source": "This Week in ML", "url": "https://twimlai.com/latest"}
                        ],
                        "videos": [
                            {"title": "Two Minute Papers - GPT-4 Analysis", "source": "Two Minute Papers", "url": "https://youtube.com/watch?v=gpt4-analysis"},
                            {"title": "3Blue1Brown - Neural Networks Explained", "source": "3Blue1Brown", "url": "https://youtube.com/watch?v=neural-networks"}
                        ],
                        "events": [
                            {"title": "NeurIPS 2025 Conference", "source": "NeurIPS", "url": "https://neurips.cc/2025"},
                            {"title": "AI Safety Summit", "source": "AI Safety Institute", "url": "https://aisafety.gov/summit"}
                        ],
                        "learn": [
                            {"title": "Deep Learning Specialization", "source": "Coursera", "url": "https://coursera.org/learn/deep-learning"},
                            {"title": "MIT 6.034 Artificial Intelligence", "source": "MIT OpenCourseWare", "url": "https://ocw.mit.edu/ai"}
                        ]
                    },
                    "timestamp": "2025-08-31T15:00:00Z",
                    "badge": "Latest"
                })
                
            elif self.path.startswith('/api/digest/'):
                content_type = self.path.split('/')[-1]
                content_map = {
                    "blogs": [
                        {"title": "AI Research Breakthrough", "source": "Research Lab", "url": "https://example.com/research"},
                        {"title": "Machine Learning Advances", "source": "ML Today", "url": "https://example.com/ml"}
                    ],
                    "podcasts": [
                        {"title": "AI Podcast Episode 1", "source": "AI Cast", "url": "https://example.com/podcast1"},
                        {"title": "Tech Talk on Neural Networks", "source": "Tech Pod", "url": "https://example.com/tech"}
                    ],
                    "videos": [
                        {"title": "AI Video Tutorial", "source": "Learn AI", "url": "https://example.com/video1"},
                        {"title": "Deep Learning Explained", "source": "AI Academy", "url": "https://example.com/deep"}
                    ],
                    "events": [
                        {"title": "AI Conference 2025", "source": "AI Org", "url": "https://example.com/conf"},
                        {"title": "ML Workshop", "source": "Workshop Hub", "url": "https://example.com/workshop"}
                    ],
                    "learn": [
                        {"title": "AI Course Basics", "source": "Online Uni", "url": "https://example.com/course"},
                        {"title": "Neural Network Tutorial", "source": "Learn Hub", "url": "https://example.com/tutorial"}
                    ]
                }
                
                self._send_json_response({
                    "summary": {
                        "keyPoints": [f"{content_type.title()} content curated for you"],
                        "metrics": {"totalUpdates": len(content_map.get(content_type, [])), "category": content_type}
                    },
                    "topStories": content_map.get(content_type, [])[:2],
                    "content": {content_type: content_map.get(content_type, [])},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "badge": f"{content_type.title()}"
                })
                
            elif self.path == '/auth/profile':
                user_info = self._get_user_from_token(auth_token)
                if not user_info:
                    self._send_error_response("Unauthorized", 401)
                    return
                
                user = self.users_db.get(user_info['user_id'])
                if not user:
                    self._send_error_response("User not found", 404)
                    return
                
                self._send_json_response(user)
                
            elif self.path == '/topics':
                self._send_json_response([
                    {"id": 1, "name": "Machine Learning", "description": "ML and deep learning updates", "selected": False},
                    {"id": 2, "name": "AI Research", "description": "Latest research papers and findings", "selected": False},
                    {"id": 3, "name": "Natural Language Processing", "description": "NLP and language model developments", "selected": False},
                    {"id": 4, "name": "Computer Vision", "description": "Visual AI and image processing news", "selected": False},
                    {"id": 5, "name": "AI Ethics", "description": "Responsible AI and ethical considerations", "selected": False},
                    {"id": 6, "name": "Robotics", "description": "AI in robotics and automation", "selected": False}
                ])
                
            else:
                self._send_json_response({"message": "AI News API", "status": "running", "endpoints": ["/health", "/api/digest", "/auth/*", "/topics"]})
                
        except Exception as e:
            self._send_error_response(f"Server error: {str(e)}", 500)
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except json.JSONDecodeError:
                self._send_error_response("Invalid JSON format", 400)
                return
            
            if self.path == '/auth/login':
                # Validate required fields
                email = data.get('email', '').strip().lower()
                password = data.get('password', '')
                
                if not email or not password:
                    self._send_error_response("Email and password are required", 400)
                    return
                
                if not self._validate_email(email):
                    self._send_error_response("Invalid email format", 400)
                    return
                
                # Find user by email
                user = None
                user_id = None
                for uid, user_data in self.users_db.items():
                    if user_data.get('email', '').lower() == email:
                        user = user_data
                        user_id = uid
                        break
                
                if not user:
                    self._send_error_response("Invalid email or password", 401)
                    return
                
                # Check password
                if user.get('password_hash') != self._hash_password(password):
                    self._send_error_response("Invalid email or password", 401)
                    return
                
                # Create token and return user data
                token = self._create_token(user_id)
                user_response = {k: v for k, v in user.items() if k != 'password_hash'}
                
                self._send_json_response({
                    "user": user_response,
                    "token": token
                })
                
            elif self.path == '/auth/signup':
                # Validate required fields
                name = data.get('name', '').strip()
                email = data.get('email', '').strip().lower()
                password = data.get('password', '')
                
                if not name or not email or not password:
                    self._send_error_response("Name, email, and password are required", 400)
                    return
                
                if len(name) < 2:
                    self._send_error_response("Name must be at least 2 characters long", 400)
                    return
                
                if not self._validate_email(email):
                    self._send_error_response("Invalid email format", 400)
                    return
                
                if len(password) < 8:
                    self._send_error_response("Password must be at least 8 characters long", 400)
                    return
                
                # Check if user already exists
                for user_data in self.users_db.values():
                    if user_data.get('email', '').lower() == email:
                        self._send_error_response("User with this email already exists", 409)
                        return
                
                # Create new user
                user_id = str(uuid.uuid4())
                user = {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "subscriptionTier": "free",
                    "createdAt": datetime.utcnow().isoformat() + "Z",
                    "preferences": {
                        "topics": [],
                        "notifications": True,
                        "digestFrequency": "daily"
                    },
                    "password_hash": self._hash_password(password)
                }
                
                self.users_db[user_id] = user
                token = self._create_token(user_id)
                
                # Return user data without password hash
                user_response = {k: v for k, v in user.items() if k != 'password_hash'}
                
                self._send_json_response({
                    "user": user_response,
                    "token": token
                }, 201)
                
            elif self.path == '/auth/google':
                # Google OAuth simulation
                id_token = data.get('idToken', '')
                
                if not id_token:
                    self._send_error_response("Google ID token is required", 400)
                    return
                
                # Simulate Google user creation/login
                user_id = str(uuid.uuid4())
                user = {
                    "id": user_id,
                    "email": "google.user@example.com",
                    "name": "Google User",
                    "subscriptionTier": "free",
                    "createdAt": datetime.utcnow().isoformat() + "Z",
                    "preferences": {
                        "topics": [],
                        "notifications": True,
                        "digestFrequency": "daily"
                    },
                    "provider": "google"
                }
                
                self.users_db[user_id] = user
                token = self._create_token(user_id)
                
                self._send_json_response({
                    "user": user,
                    "token": token
                })
                
            elif self.path == '/api/scrape':
                # Simulate manual scraping
                self._send_json_response({
                    "message": "Manual scrape initiated",
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "sources_updated": 12
                })
                
            else:
                self._send_error_response("Endpoint not found", 404)
                
        except Exception as e:
            self._send_error_response(f"Server error: {str(e)}", 500)
    
    def do_PUT(self):
        try:
            auth_token = self.headers.get('Authorization')
            user_info = self._get_user_from_token(auth_token)
            
            if not user_info:
                self._send_error_response("Unauthorized", 401)
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except json.JSONDecodeError:
                self._send_error_response("Invalid JSON format", 400)
                return
            
            if self.path == '/auth/preferences':
                user = self.users_db.get(user_info['user_id'])
                if not user:
                    self._send_error_response("User not found", 404)
                    return
                
                # Update user preferences
                if 'topics' in data:
                    user['preferences']['topics'] = data['topics']
                if 'notifications' in data:
                    user['preferences']['notifications'] = data['notifications']
                if 'digestFrequency' in data:
                    user['preferences']['digestFrequency'] = data['digestFrequency']
                
                user_response = {k: v for k, v in user.items() if k != 'password_hash'}
                self._send_json_response(user_response)
                
            elif self.path == '/subscription/upgrade':
                user = self.users_db.get(user_info['user_id'])
                if not user:
                    self._send_error_response("User not found", 404)
                    return
                
                user['subscriptionTier'] = 'premium'
                user_response = {k: v for k, v in user.items() if k != 'password_hash'}
                self._send_json_response(user_response)
                
            else:
                self._send_error_response("Endpoint not found", 404)
                
        except Exception as e:
            self._send_error_response(f"Server error: {str(e)}", 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
        
    def do_DELETE(self):
        try:
            auth_token = self.headers.get('Authorization')
            user_info = self._get_user_from_token(auth_token)
            
            if not user_info:
                self._send_error_response("Unauthorized", 401)
                return
            
            if self.path == '/auth/logout':
                # Remove token
                if auth_token and auth_token.startswith('Bearer '):
                    token = auth_token[7:]
                    if token in self.tokens_db:
                        del self.tokens_db[token]
                
                self._send_json_response({"message": "Logged out successfully"})
            else:
                self._send_error_response("Endpoint not found", 404)
                
        except Exception as e:
            self._send_error_response(f"Server error: {str(e)}", 500)