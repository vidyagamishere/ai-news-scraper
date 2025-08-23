# Production Deployment Guide

## 🚀 Quick Deploy Options

### Option 1: Railway (Recommended for beginners)
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Deploy from this directory
railway up

# 4. Set environment variables in Railway dashboard
# - CLAUDE_API_KEY
# - ALLOWED_ORIGINS (your frontend domain)
```

### Option 2: Render
```bash
# 1. Connect your GitHub repo to Render
# 2. Use the render.yaml configuration
# 3. Set environment variables in Render dashboard
```

### Option 3: Docker + VPS
```bash
# 1. Copy files to your server
scp -r . user@your-server:/path/to/app

# 2. On your server, create .env file
cp .env.production .env
# Edit .env with your values

# 3. Build and run with Docker Compose
docker-compose up -d

# 4. Check status
docker-compose ps
curl http://your-server:8000/api/health
```

### Option 4: Vercel (Serverless)
```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Deploy
vercel --prod

# 3. Set environment variables
vercel env add CLAUDE_API_KEY
vercel env add ALLOWED_ORIGINS
```

---

## 🔧 Environment Setup

### Required Environment Variables
```bash
# Essential
CLAUDE_API_KEY=your_claude_api_key_here
ALLOWED_ORIGINS=https://your-frontend.com

# Optional (with defaults)
CLAUDE_MODEL=claude-3-haiku-20240307
LOG_LEVEL=INFO
CACHE_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### Getting Claude API Key
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create account and get API key
3. Add to environment variables

---

## 🐳 Docker Deployment

### Simple Docker Run
```bash
# Build image
docker build -t ai-news-scraper .

# Run container
docker run -d \
  --name ai-news-scraper \
  -p 8000:8000 \
  -e CLAUDE_API_KEY=your_key_here \
  -e ALLOWED_ORIGINS=https://your-frontend.com \
  -v ai_news_data:/app/data \
  ai-news-scraper
```

### Docker Compose (Production)
```bash
# Create .env file with your values
cp .env.production .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## ☁️ Cloud Platform Specific

### Railway Deployment
1. **Connect GitHub**: Link your repository
2. **Configure Build**: Uses Dockerfile automatically
3. **Set Variables**:
   ```
   CLAUDE_API_KEY=your_key
   ALLOWED_ORIGINS=https://your-frontend.com
   ```
4. **Custom Domain**: Add your domain in Railway dashboard

### Render Deployment
1. **New Web Service**: Connect GitHub repo
2. **Configure**: Uses `deploy/render.yaml`
3. **Environment**: Set in dashboard
4. **Persistent Disk**: Automatically configured for database

### DigitalOcean App Platform
```yaml
name: ai-news-scraper
services:
- name: web
  source_dir: /
  github:
    repo: your-username/ai-news-scraper
    branch: main
  run_command: python main.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: CLAUDE_API_KEY
    value: your_key_here
  - key: ALLOWED_ORIGINS
    value: https://your-frontend.com
```

### AWS ECS/Fargate
```bash
# 1. Push to ECR
aws ecr create-repository --repository-name ai-news-scraper
docker tag ai-news-scraper:latest your-account.dkr.ecr.region.amazonaws.com/ai-news-scraper:latest
docker push your-account.dkr.ecr.region.amazonaws.com/ai-news-scraper:latest

# 2. Create ECS task definition and service
# Use AWS Console or CLI with provided task-definition.json
```

---

## 🔒 Security Checklist

### Production Security
- [ ] Set secure ALLOWED_ORIGINS (no wildcards)
- [ ] Use HTTPS (SSL certificates)
- [ ] Rate limiting configured
- [ ] Environment variables secured
- [ ] Database file permissions set
- [ ] API monitoring enabled

### SSL/HTTPS Setup
```bash
# For Nginx with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 📊 Monitoring & Logging

### Health Monitoring
```bash
# Set up health check monitoring
curl -f http://your-domain.com/api/health || exit 1

# Monitor logs
docker-compose logs -f ai-news-scraper
```

### Log Rotation (VPS)
```bash
# Add to /etc/logrotate.d/ai-news-scraper
/app/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
}
```

### Optional: Sentry Integration
```bash
# Add to environment
SENTRY_DSN=your_sentry_dsn_here

# Install sentry-sdk in requirements.txt
pip install sentry-sdk[fastapi]
```

---

## 🔄 Updates & Maintenance

### Updating the Application
```bash
# Docker Compose
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d

# Railway/Render
# Just push to GitHub - auto-deploys
```

### Database Backup
```bash
# Backup SQLite database
docker-compose exec ai-news-scraper cp /app/data/ai_news.db /app/data/backup_$(date +%Y%m%d).db

# Download backup
docker cp ai-news-scraper:/app/data/backup_$(date +%Y%m%d).db ./backup.db
```

### Performance Tuning
```bash
# Increase rate limits for high traffic
RATE_LIMIT_REQUESTS_PER_MINUTE=120

# Optimize caching
CACHE_ENABLED=true

# Reduce scraping frequency if needed
# Edit scheduler in main.py
```

---

## 🐛 Troubleshooting

### Common Issues

**502 Bad Gateway**
```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs ai-news-scraper

# Restart service
docker-compose restart ai-news-scraper
```

**Claude API Errors**
```bash
# Verify API key
curl -H "x-api-key: YOUR_KEY" https://api.anthropic.com/v1/messages

# Check rate limits
# Review Claude API usage in dashboard
```

**Database Issues**
```bash
# Check database file permissions
ls -la /app/data/

# Reset database
docker-compose down
docker volume rm ai-news-scraper_ai_news_data
docker-compose up -d
```

**CORS Issues**
```bash
# Verify ALLOWED_ORIGINS
echo $ALLOWED_ORIGINS

# Check browser console for CORS errors
# Update ALLOWED_ORIGINS to include your frontend domain
```

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG
```

---

## 📱 Frontend Connection

### API Base URL Configuration
```javascript
// Frontend environment variables
REACT_APP_API_URL=https://your-api-domain.com
VUE_APP_API_URL=https://your-api-domain.com
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

### Test API Connection
```bash
# Test from frontend domain
curl -H "Origin: https://your-frontend.com" \
     https://your-api-domain.com/api/health

# Should return CORS headers
```

---

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (Nginx, Cloudflare)
- Implement Redis for shared caching
- Use external database (PostgreSQL)

### Vertical Scaling
- Increase container memory/CPU
- Optimize rate limiting
- Implement request queuing

### Cost Optimization
- Use smaller instances for development
- Implement intelligent caching
- Monitor API usage costs (Claude API)

---

## 🎯 Success Criteria

Your deployment is successful when:
- [ ] Health check returns 200
- [ ] Frontend can fetch `/api/digest`
- [ ] Scheduled scraping works (check logs)
- [ ] Multimedia content appears
- [ ] CORS allows frontend requests
- [ ] Database persists between restarts

**Test Command:**
```bash
curl -s https://your-domain.com/api/digest | jq '.content | keys'
# Should return: ["audio", "blog", "video"]
```