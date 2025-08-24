# 📧 Email Digest Setup Guide

## Overview

Your AI News Scraper now includes a comprehensive email digest system that sends personalized AI news summaries to subscribers. This guide will help you set up the email service.

## Email Service Features

### ✅ **Implemented Features:**

1. **Personalized HTML Email Digests**
   - Beautiful, responsive email templates
   - User preference-based content filtering
   - Significance scoring and insights
   - Multimedia content integration (audio/video)

2. **Welcome Email System**
   - Automatic welcome emails for new subscribers
   - Feature overview and onboarding

3. **Scheduled Delivery**
   - Daily digest at 7 AM ET
   - Frequency-based filtering (daily, weekly, etc.)
   - Rate limiting and error handling

4. **User Controls**
   - Send test digest emails
   - Preview email before sending
   - Preference-based personalization

5. **Admin Tools**
   - Bulk email sending to all subscribers
   - Email delivery tracking and analytics
   - Subscriber management

## Setup Instructions

### **Step 1: Choose Email Provider**

**Option A: SendGrid (Recommended)**
- Free tier: 100 emails/day
- Excellent deliverability
- Professional features

**Option B: Other Providers**
- Mailgun, Amazon SES, Postmark
- Requires code modifications

### **Step 2: Set Up SendGrid**

1. **Create SendGrid Account**
   - Go to [sendgrid.com](https://sendgrid.com)
   - Sign up for free account
   - Verify your email address

2. **Create API Key**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Choose "Full Access" (or restricted with Mail Send permissions)
   - Copy the API key immediately

3. **Verify Sender Identity**
   - Go to Settings → Sender Authentication
   - Add "Single Sender Verification"
   - Use email like: `noreply@yourdomain.com`
   - Or set up domain authentication for better deliverability

### **Step 3: Configure Environment Variables**

**In Vercel Dashboard:**

1. Go to your `ai-news-scraper` project
2. Settings → Environment Variables
3. Add these variables:

```
SENDGRID_API_KEY = [Your SendGrid API Key]
FROM_EMAIL = noreply@yourdomain.com
FROM_NAME = AI Daily
```

**Or via Vercel CLI:**

```bash
vercel env add SENDGRID_API_KEY
vercel env add FROM_EMAIL  
vercel env add FROM_NAME
```

### **Step 4: Deploy Updated Backend**

```bash
cd /Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-news-scraper
vercel --prod
```

### **Step 5: Deploy Updated Frontend**

```bash
cd /Users/vijayansubramaniyan/Desktop/AI-ML/Projects/ai-digest
vercel --prod
```

## Testing Your Email System

### **Manual Testing:**

1. **Sign in to your app**
2. **Click your profile → "Send Test Email"**
3. **Check your inbox** for the digest email
4. **Try "Preview Email"** to see HTML preview

### **API Testing:**

```bash
# Send digest email (replace TOKEN with your JWT)
curl -X POST "https://ai-news-scraper.vercel.app/email/send-digest" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Preview email
curl -X GET "https://ai-news-scraper.vercel.app/email/preview-digest" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Email Templates

### **Daily Digest Includes:**

- **Header**: AI Daily branding with date
- **Greeting**: Personalized with user's name
- **Insights**: Article count, high-impact stories, top sources
- **Articles**: Filtered by user preferences with:
  - Title and summary
  - Source and significance score
  - Time published
- **Multimedia**: Audio and video content (if enabled)
- **Footer**: Preferences and unsubscribe links

### **Welcome Email Includes:**

- **Welcome message** with user's name
- **Feature overview** of AI Daily
- **Call-to-action** to customize preferences
- **Professional footer** with links

## Scheduled Email Delivery

### **Current Schedule:**
- **Daily Digest**: 7:00 AM ET every day
- **Target Users**: Subscribers with "daily" frequency preference
- **Content**: Last 24 hours of curated AI news

### **Frequency Options:**
- **Daily**: Every morning at 7 AM
- **Weekly**: Future enhancement
- **Bi-weekly**: Future enhancement  
- **Monthly**: Future enhancement

## Email Personalization

### **Content Filtering:**
- **Categories**: Research, Industry, Tools, Regulations, Startups
- **Content Types**: Blog posts, Audio, Video
- **Significance Scoring**: High-impact stories prioritized

### **User Preferences:**
- Stored in `subscription_preferences` table
- Applied during email generation
- Customizable via preferences modal

## Monitoring and Analytics

### **Email Tracking:**
- **Delivery Status**: Success/failure tracking
- **Open Rates**: Via SendGrid tracking
- **Click Tracking**: Via SendGrid tracking
- **Unsubscribe Tracking**: Via email service

### **Admin Endpoints:**
```
GET /admin/subscribers/stats - Subscriber statistics
POST /admin/email/send-digest-all - Send to all subscribers
GET /admin/subscribers - List all subscribers
```

## Troubleshooting

### **Common Issues:**

**"Failed to send email" Error:**
- Check SENDGRID_API_KEY is set correctly
- Verify sender email is authenticated in SendGrid
- Check SendGrid account isn't suspended

**"Invalid from email" Error:**
- Verify FROM_EMAIL in environment variables
- Ensure email is verified in SendGrid
- Check domain authentication

**Emails not received:**
- Check spam/junk folders
- Verify recipient email is correct
- Check SendGrid activity feed for delivery status

**Rate Limiting:**
- Free SendGrid: 100 emails/day
- Add delays between sends (already implemented)
- Upgrade SendGrid plan if needed

### **Debugging:**

1. **Check Vercel Function Logs:**
   - Go to Vercel Dashboard → Functions
   - View logs for email-related errors

2. **Test API Endpoints:**
   - Use `/email/preview-digest` to test content generation
   - Use `/email/send-digest` with your account

3. **SendGrid Activity Feed:**
   - Monitor email delivery status
   - Check bounce and spam reports

## Email Deliverability Tips

### **Improve Deliverability:**

1. **Domain Authentication:**
   - Set up DKIM and SPF records
   - Use SendGrid's domain authentication

2. **Content Quality:**
   - Avoid spam trigger words
   - Include unsubscribe links
   - Maintain text/HTML balance

3. **Sender Reputation:**
   - Start with low volume
   - Monitor bounce rates
   - Handle unsubscribes properly

4. **List Hygiene:**
   - Remove bounced emails
   - Honor unsubscribe requests
   - Segment inactive users

## Future Enhancements

### **Planned Features:**
- **Email Analytics Dashboard**
- **A/B Testing for Subject Lines**
- **Advanced Segmentation**
- **Digest Frequency Optimization**
- **Unsubscribe Page**
- **Email Preference Center**

## Support

### **Resources:**
- [SendGrid Documentation](https://docs.sendgrid.com/)
- [Email Best Practices](https://sendgrid.com/blog/email-best-practices/)
- [Deliverability Guide](https://sendgrid.com/blog/email-deliverability-best-practices/)

### **Need Help?**
- Check Vercel function logs for errors
- Test with SendGrid's Email API testing tool
- Monitor SendGrid activity feed for delivery issues

---

## 🎉 **Your Email Digest System is Ready!**

With this setup, your subscribers will receive beautifully crafted, personalized AI news digests every morning. The system handles user preferences, rate limiting, and provides comprehensive tracking and analytics.

**Next Steps:**
1. Set up SendGrid account and get API key
2. Configure environment variables
3. Deploy both frontend and backend
4. Send yourself a test email
5. Monitor delivery and engagement metrics

Your AI Daily email digest system is now production-ready! 📧✨