#!/bin/bash

echo "🚀 Deploying AI News Scraper with Admin Validation..."

# Step 1: Backup current files
echo "📦 Creating backups..."
cp ai_sources_config.py ai_sources_config_backup.py 2>/dev/null || echo "No existing ai_sources_config.py to backup"
cp api/index.py api/index_backup.py 2>/dev/null || echo "No existing api/index.py to backup"
cp requirements.txt requirements_backup.txt 2>/dev/null || echo "No existing requirements.txt to backup"
cp vercel.json vercel_backup.json 2>/dev/null || echo "No existing vercel.json to backup"

# Step 2: Update files with new versions
echo "📝 Updating files..."
cp ai_sources_config_updated.py ai_sources_config.py
cp api/index_with_validation.py api/index.py
cp requirements_updated.txt requirements.txt
cp vercel_updated.json vercel.json

# Step 3: Add and commit changes
echo "📋 Committing changes..."
git add .
git commit -m "Update AI News Scraper with admin validation and free sources

🎯 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Step 4: Deploy to Vercel
echo "🌐 Deploying to Vercel..."
echo "Please run: vercel --prod"
echo ""
echo "🎉 Backend updated with:"
echo "   ✅ 45+ free AI sources"  
echo "   ✅ Admin validation panel"
echo "   ✅ Real-time RSS testing"
echo "   ✅ Enhanced scraping"
echo ""
echo "🎛️ After deployment, access admin panel at:"
echo "   https://your-domain.vercel.app/admin-validation"