# Local Development Setup Guide

This guide will help you set up the complete Vidyagam AI News Platform locally with React frontend, Python backend, and PostgreSQL database.

## Architecture Overview

- **Frontend**: React TypeScript SPA with Vite (Port 5173)
- **Backend**: FastAPI Python application (Port 8000)
- **Database**: PostgreSQL (Port 5432)
- **Authentication**: Google OAuth + JWT tokens
- **Email**: SendGrid for OTP verification

## Prerequisites

### Required Software
- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Python** (3.9 or higher) - [Download](https://python.org/)
- **PostgreSQL** (v14 or higher) - [Download](https://postgresql.org/)
- **Git** - [Download](https://git-scm.com/)

### Optional Tools
- **Docker & Docker Compose** (alternative to local PostgreSQL)
- **Postman** or **Thunder Client** (API testing)
- **pgAdmin** or **TablePlus** (database management)

## Project Structure

```
ai-news-scraper/           # Backend (FastAPI)
├── app/                   # Modular backend code
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── models/           # Pydantic schemas
│   └── dependencies/     # Dependency injection
├── main.py               # FastAPI entry point
├── db_service.py         # Database service
└── requirements.txt      # Python dependencies

ai-news-react/            # Frontend (React)
├── src/
│   ├── components/       # React components
│   ├── pages/           # Route components
│   ├── contexts/        # State management
│   └── services/        # API clients
├── package.json         # Node dependencies
└── vite.config.ts       # Vite configuration
```

## Step 1: Database Setup

### Option A: Local PostgreSQL Installation

1. **Install PostgreSQL**
   ```bash
   # macOS (using Homebrew)
   brew install postgresql
   brew services start postgresql
   
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   
   # Windows
   # Download installer from postgresql.org
   ```

2. **Create Database and User**
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql
   
   # Create database and user
   CREATE DATABASE vidyagam_local;
   CREATE USER vidyagam_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE vidyagam_local TO vidyagam_user;
   \q
   ```

3. **Get Connection String**
   ```
   postgresql://vidyagam_user:your_secure_password@localhost:5432/vidyagam_local
   ```

### Option B: Docker PostgreSQL

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: vidyagam_local
         POSTGRES_USER: vidyagam_user
         POSTGRES_PASSWORD: your_secure_password
       ports:
         - "5432:5432"
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:
   ```

2. **Start PostgreSQL**
   ```bash
   docker-compose up -d
   ```

## Step 2: Backend Setup (FastAPI)

1. **Navigate to Backend Directory**
   ```bash
   cd ai-news-scraper
   ```

2. **Create Virtual Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # macOS/Linux:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create Environment File**
   ```bash
   cp .env.example .env  # If example exists, or create new
   ```

5. **Configure Environment Variables (.env)**
   ```env
   # Database
   POSTGRES_URL=postgresql://vidyagam_user:your_secure_password@localhost:5432/vidyagam_local
   
   # Debug Mode
   DEBUG=true
   LOG_LEVEL=DEBUG
   
   # JWT Security
   JWT_SECRET=your-super-secret-jwt-key-for-local-development
   
   # Google OAuth (Get from Google Cloud Console)
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   
   # Email Service (Get from SendGrid)
   SENDGRID_API_KEY=your-sendgrid-api-key
   
   # CORS Origins
   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
   
   # Server Config
   PORT=8000
   ```

6. **Initialize Database**
   ```bash
   # The database schema will be created automatically on first run
   python main.py
   ```

7. **Verify Backend**
   ```bash
   # Start development server
   python main.py
   
   # Or using uvicorn directly
   uvicorn main:app --reload --port 8000
   ```

   Visit: http://localhost:8000/docs (FastAPI Swagger UI)

## Step 3: Frontend Setup (React)

1. **Navigate to Frontend Directory**
   ```bash
   cd ../ai-news-react  # Adjust path as needed
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Configure Environment Variables**
   Create `.env.local`:
   ```env
   # API Configuration
   VITE_API_BASE_URL=http://localhost:8000
   
   # Google OAuth (same as backend)
   VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   
   # Development Mode
   VITE_DEBUG=true
   ```

4. **Update API Configuration**
   Check `src/services/api.ts` and ensure it points to local backend:
   ```typescript
   const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
   ```

5. **Start Development Server**
   ```bash
   npm run dev
   ```

   Visit: http://localhost:5173

## Step 4: Google OAuth Setup

1. **Google Cloud Console Setup**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized origins:
     - `http://localhost:5173` (frontend)
     - `http://localhost:8000` (backend)

2. **Update Environment Variables**
   Add the Google Client ID to both frontend and backend `.env` files.

## Step 5: Email Service Setup (Optional)

1. **SendGrid Setup**
   - Sign up at [SendGrid](https://sendgrid.com/)
   - Create API key
   - Add to backend `.env` file

2. **Testing Mode**
   The backend runs in testing mode by default, which skips email sending and logs OTP codes to console.

## Step 6: Development Workflow

### Starting All Services

1. **Terminal 1: Database**
   ```bash
   # If using Docker
   docker-compose up -d
   
   # If using local PostgreSQL, ensure it's running
   brew services start postgresql  # macOS
   ```

2. **Terminal 2: Backend**
   ```bash
   cd ai-news-scraper
   source venv/bin/activate  # Activate virtual environment
   python main.py
   ```

3. **Terminal 3: Frontend**
   ```bash
   cd ai-news-react
   npm run dev
   ```

### Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432

## Step 7: Testing the Setup

### Backend Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "database": "postgresql"}
```

### Frontend Health Check
- Visit http://localhost:5173
- Should load the AI News Platform homepage

### Authentication Flow Test
1. Click "Sign In" on frontend
2. Try email authentication with any email
3. Check backend logs for OTP (in testing mode)
4. Complete authentication flow

### Admin Features Test
1. Authenticate with admin@vidyagam.com
2. Access admin dashboard
3. Try sources management
4. Test content scraping

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL status
   brew services list | grep postgresql  # macOS
   sudo systemctl status postgresql      # Linux
   
   # Check connection string in .env
   # Ensure database exists and user has permissions
   ```

2. **CORS Errors**
   ```bash
   # Ensure ALLOWED_ORIGINS includes frontend URL
   ALLOWED_ORIGINS=http://localhost:5173
   ```

3. **Module Not Found (Python)**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   pip list  # Check installed packages
   ```

4. **Frontend Build Errors**
   ```bash
   # Clear node modules and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

### Debug Mode

Enable debug logging by setting:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

This will show detailed logs for:
- Database queries and connections
- JWT token creation/verification
- API request/response details
- Authentication flow steps

### Database Management

**View Tables:**
```bash
psql postgresql://vidyagam_user:your_secure_password@localhost:5432/vidyagam_local

\dt  # List tables
\d users  # Describe users table
SELECT * FROM ai_sources;  # View sources
```

**Reset Database:**
```bash
# Drop and recreate database
sudo -u postgres psql
DROP DATABASE vidyagam_local;
CREATE DATABASE vidyagam_local;
GRANT ALL PRIVILEGES ON DATABASE vidyagam_local TO vidyagam_user;
```

## Development Tips

### Hot Reloading
- **Backend**: Use `uvicorn main:app --reload` for auto-restart on code changes
- **Frontend**: Vite provides hot module replacement by default

### API Testing
Use the interactive API docs at http://localhost:8000/docs or tools like Postman to test endpoints.

### Code Quality
```bash
# Backend linting
pip install black flake8
black . && flake8 .

# Frontend linting
npm run lint
```

### Database Migrations
The database schema is automatically created/updated on startup. For production, consider using proper migration tools like Alembic.

## Production Deployment

When ready to deploy:

1. **Backend**: Deploy to Railway with PostgreSQL addon
2. **Frontend**: Deploy to Vercel with environment variables
3. **Database**: Use Railway PostgreSQL or external service
4. **Environment**: Update all URLs to production domains

Refer to `DEPLOYMENT.md` for detailed production deployment instructions.