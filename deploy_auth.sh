#!/bin/bash

# Deploy AI News Scraper with Authentication
echo "🚀 Deploying AI News Scraper with Authentication..."

# Check if we're in the right directory
if [ ! -f "api/main_with_auth.py" ]; then
    echo "❌ Error: main_with_auth.py not found. Please run this from the ai-news-scraper directory."
    exit 1
fi

# Create backup of original vercel.json
if [ -f "vercel.json" ]; then
    cp vercel.json vercel_backup.json
    echo "📦 Backed up original vercel.json"
fi

# Use the new authentication-enabled configuration
cp vercel_auth.json vercel.json
echo "🔧 Updated Vercel configuration for authentication"

# Check if required files exist
echo "📋 Checking required files..."
REQUIRED_FILES=(
    "api/main_with_auth.py"
    "api/auth_service.py" 
    "api/auth_models.py"
    "api/auth_endpoints.py"
    "api/requirements_auth.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    else
        echo "✅ Found: $file"
    fi
done

# Update requirements.txt with authentication dependencies
cp api/requirements_auth.txt requirements.txt
echo "📝 Updated requirements.txt with authentication dependencies"

# Set up environment variables reminder
echo ""
echo "⚠️  IMPORTANT: Set these environment variables in your deployment platform:"
echo ""
echo "Required Variables:"
echo "- JWT_SECRET=your-super-secure-jwt-secret-key"
echo "- GOOGLE_CLIENT_ID=your-google-oauth-client-id"
echo "- ANTHROPIC_API_KEY=your-anthropic-api-key"
echo "- DATABASE_PATH=ai_news.db"
echo ""
echo "Optional Variables:"
echo "- EMAIL_ENABLED=true"
echo "- SENDGRID_API_KEY=your-sendgrid-key"
echo "- CORS_ORIGINS=https://your-frontend-domain.com"
echo ""

# Deploy to Vercel (if Vercel CLI is available)
if command -v vercel &> /dev/null; then
    echo "🚀 Deploying to Vercel..."
    vercel --prod
    echo ""
    echo "✅ Deployment initiated!"
    echo "🔍 Check your deployment status at: https://vercel.com/dashboard"
else
    echo "💡 Vercel CLI not found. You can:"
    echo "1. Install Vercel CLI: npm i -g vercel"
    echo "2. Or deploy manually by pushing to your connected Git repository"
fi

echo ""
echo "🎉 Authentication-enabled backend setup complete!"
echo "📖 Next: Update your frontend environment variables and deploy"