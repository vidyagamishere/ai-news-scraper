#!/bin/bash

echo "🔍 Testing AI News Scraper Deployment..."

# Get your backend URL (update if different)
BACKEND_URL="https://ai-news-scraper-n3wbzjj45.vercel.app"

echo "🌐 Testing: $BACKEND_URL"

echo ""
echo "1️⃣ Testing root endpoint:"
curl -s "$BACKEND_URL/" | grep -E '"status"|"version"|"total_sources"' || echo "❌ Root endpoint test failed"

echo ""
echo "2️⃣ Testing health endpoint:"
curl -s "$BACKEND_URL/api/health" | grep -E '"status"|"total_sources"|"validation"' || echo "❌ Health endpoint test failed"

echo ""
echo "3️⃣ Testing sources endpoint:"
curl -s "$BACKEND_URL/api/sources" | grep -E '"total_count"|"free_sources_count"' || echo "❌ Sources endpoint test failed"

echo ""
echo "4️⃣ Testing digest endpoint:"
curl -s "$BACKEND_URL/api/digest" | grep -E '"totalUpdates"|"enhanced"|"admin_features"' || echo "❌ Digest endpoint test failed"

echo ""
echo "5️⃣ Testing admin panel (should return HTML):"
curl -s "$BACKEND_URL/admin-validation" | head -1 | grep -q "<!DOCTYPE html" && echo "✅ Admin panel accessible" || echo "❌ Admin panel not accessible"

echo ""
echo "📊 Deployment Test Complete!"
echo "If you see ✅ for most tests, the deployment worked!"
echo "If you see ❌, there may be deployment issues."