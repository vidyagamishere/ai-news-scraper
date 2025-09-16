# 🚂 Railway Deployment Guide

## Quick Deploy to Railway

### Method 1: GitHub Integration (Recommended)

1. **Connect to Railway:**
   ```bash
   # Visit https://railway.app
   # Click "Deploy from GitHub repo"
   # Select this repository: ai-news-scraper
   ```

2. **Set Environment Variables:**
   ```bash
   JWT_SECRET=ai-news-jwt-secret-2025-production-secure
   GOOGLE_CLIENT_ID=450435096536-tbor1sbkbq27si62ps7khr5fdat5indb.apps.googleusercontent.com
   ALLOWED_ORIGINS=https://www.vidyagam.com,https://ai-news-react.vercel.app
   ```

3. **Deploy Command:**
   ```bash
   # Railway will automatically detect and use:
   # - Procfile for start command
   # - requirements.txt for dependencies
   # - runtime.txt for Python version
   ```

### Method 2: Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Initialize and Deploy:**
   ```bash
   cd ai-news-scraper
   railway init
   railway up
   ```

3. **Set Environment Variables:**
   ```bash
   railway variables set JWT_SECRET=ai-news-jwt-secret-2025-production-secure
   railway variables set GOOGLE_CLIENT_ID=450435096536-tbor1sbkbq27si62ps7khr5fdat5indb.apps.googleusercontent.com
   railway variables set ALLOWED_ORIGINS=https://www.vidyagam.com,https://ai-news-react.vercel.app
   ```

## Configuration Files

- `railway.json` - Railway deployment configuration
- `Procfile` - Process definition for Railway
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification

## Features Enabled on Railway

✅ **Persistent Storage** - SQLite database persists between deployments
✅ **Real-time Logs** - View logs in Railway dashboard
✅ **Auto-scaling** - Handles traffic automatically
✅ **Health Checks** - Automatic health monitoring at `/health`
✅ **HTTPS** - Automatic SSL certificates
✅ **Custom Domains** - Can add custom domain if needed

## Expected Railway URL Format

Your backend will be available at:
```
https://your-project-name-production.up.railway.app
```

## Testing After Deployment

1. **Health Check:**
   ```bash
   curl https://your-railway-url.railway.app/health
   ```

2. **API Endpoint:**
   ```bash
   curl "https://your-railway-url.railway.app/api/index?endpoint=health"
   ```

3. **Root Endpoint:**
   ```bash
   curl https://your-railway-url.railway.app/
   ```

## Next Steps

After Railway deployment:
1. Get the Railway URL from dashboard
2. Update frontend `VITE_API_BASE` to use Railway URL
3. Redeploy frontend to Vercel
4. Test end-to-end integration