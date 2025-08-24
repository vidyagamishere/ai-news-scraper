# AI News Scraper Deployment Guide

## Environment Variables Setup

Before deploying to Vercel, you need to set up the following environment variables in your Vercel dashboard:

### Required Variables

1. **CLAUDE_API_KEY** - Your Claude API key from Anthropic
2. **JWT_SECRET** - A secure random string for JWT token signing (at least 32 characters)
3. **GOOGLE_CLIENT_ID** - Your Google OAuth 2.0 Client ID

### Setting Environment Variables

#### Option 1: Via Vercel CLI

```bash
# Install Vercel CLI if not already installed
npm i -g vercel

# Set environment variables
vercel env add JWT_SECRET
# Enter your secure JWT secret (generate with: openssl rand -hex 32)

vercel env add GOOGLE_CLIENT_ID
# Enter your Google OAuth Client ID

vercel env add CLAUDE_API_KEY
# Enter your Claude API key
```

#### Option 2: Via Vercel Dashboard

1. Go to your project on vercel.com
2. Navigate to Settings → Environment Variables
3. Add each variable:
   - **JWT_SECRET**: Generate a secure random string
   - **GOOGLE_CLIENT_ID**: Your Google OAuth Client ID  
   - **CLAUDE_API_KEY**: Your Claude API key from Anthropic

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized origins: Add your domain (e.g., `https://yourdomain.vercel.app`)
   - Authorized redirect URIs: Not needed for this implementation
5. Copy the Client ID and add it to your environment variables

## Frontend Configuration

Update the `env.config.js` file in your frontend project:

```javascript
window.ENV_CONFIG = {
    API_URL: 'https://your-api-domain.vercel.app',
    GOOGLE_CLIENT_ID: 'your-google-client-id.apps.googleusercontent.com',
    // ... other config
};
```

## Deployment Commands

```bash
# Deploy the API
cd ai-news-scraper
vercel --prod

# Deploy the frontend  
cd ../ai-digest
vercel --prod
```

## Database

The SQLite database will be automatically created on first run. The schema includes:
- `subscribers` - User accounts
- `subscription_preferences` - User preferences
- `email_subscriptions` - Email subscription settings
- `articles` - Scraped articles
- Audio/video content tables (if multimedia scraper is enabled)

## API Endpoints

### Authentication
- `POST /auth/google` - Google OAuth login
- `GET /auth/profile` - Get user profile

### Subscriptions  
- `POST /subscription/preferences` - Save preferences
- `GET /subscription/preferences` - Get preferences
- `DELETE /subscription/account` - Delete account

### Admin (for future use)
- `GET /admin/subscribers` - List all subscribers
- `GET /admin/subscribers/stats` - Subscriber statistics
- `POST /admin/subscribers/{id}/activate` - Activate subscriber
- `POST /admin/subscribers/{id}/deactivate` - Deactivate subscriber

### Content
- `GET /api/digest` - Get AI news digest
- `GET /api/scrape` - Manual content scraping
- `GET /api/health` - Health check

## Security Notes

- JWT tokens expire after 7 days
- Google OAuth tokens are validated server-side
- All authenticated endpoints require valid JWT token
- CORS is configured for web browser access
- SQL injection protection via parameterized queries