"""
Email Service for AI News Scraper
Handles digest generation and email sending with Brevo
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Initialize logger first
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    from jinja2 import Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.warning("Jinja2 not available - using basic template")

try:
    from premailer import transform
    PREMAILER_AVAILABLE = True
except ImportError:
    PREMAILER_AVAILABLE = False
    logger.warning("Premailer not available - CSS inlining disabled")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("Requests not available - email sending disabled")

class EmailDigestService:
    def __init__(self):
        self.brevo_api_key = os.getenv("BREVO_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "admin@vidyagam.com")
        self.from_name = os.getenv("FROM_NAME", "Vidyagam")
        self.brevo_api_url = "https://api.brevo.com/v3/smtp/email"
        
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests library not available - email sending disabled")
            return
        
        if self.brevo_api_key:
            logger.info("Brevo email service initialized")
        else:
            logger.warning("No BREVO_API_KEY found - email sending disabled")
    
    async def _send_brevo_email(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email via Brevo API"""
        if not self.brevo_api_key or not REQUESTS_AVAILABLE:
            logger.error("Brevo not configured - cannot send email")
            return False
        
        headers = {
            'api-key': self.brevo_api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'sender': {
                'name': self.from_name,
                'email': self.from_email
            },
            'to': [
                {
                    'email': to_email,
                    'name': to_name
                }
            ],
            'subject': subject,
            'htmlContent': html_content,
            'textContent': text_content
        }
        
        try:
            response = requests.post(self.brevo_api_url, headers=headers, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"Email sent successfully to {to_email} via Brevo")
                return True
            else:
                logger.error(f"Brevo API returned status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email via Brevo: {e}")
            return False
    
    def generate_daily_digest_html(self, user_data: Dict, articles: List[Dict], multimedia_content: Dict = None) -> str:
        """Generate HTML email for daily digest"""
        
        current_date = datetime.now().strftime("%B %d, %Y")
        user_name = user_data.get('name', 'AI Enthusiast')
        
        # Filter articles based on user preferences
        filtered_articles = self._filter_content_by_preferences(articles, user_data.get('preferences', {}))
        
        # Build articles HTML
        articles_html = ""
        for i, article in enumerate(filtered_articles[:10], 1):
            significance_color = self._get_significance_color(article.get('significance_score', 0))
            
            articles_html += f"""
            <div style="margin-bottom: 24px; padding: 20px; background: #f8fafc; border-radius: 12px; border-left: 4px solid {significance_color};">
                <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 18px; font-weight: 600;">
                    <a href="{article.get('url', '#')}" style="color: #1e293b; text-decoration: none;">{article.get('title', 'Untitled')}</a>
                </h3>
                <p style="margin: 0 0 12px 0; color: #475569; font-size: 14px; line-height: 1.5;">
                    {article.get('summary', article.get('content', ''))[:250]}...
                </p>
                <div style="display: flex; align-items: center; gap: 16px; font-size: 12px; color: #64748b;">
                    <span>📰 {article.get('source', 'Unknown')}</span>
                    <span>📊 Impact: {article.get('significance_score', 0):.1f}/10</span>
                    <span>🕒 {self._format_time_ago(article.get('published_date'))}</span>
                </div>
            </div>
            """
        
        # Build multimedia HTML if provided
        multimedia_html = ""
        if multimedia_content and user_data.get('preferences', {}).get('content_types'):
            content_types = user_data['preferences']['content_types']
            
            if 'audio' in content_types or 'all' in content_types:
                if multimedia_content.get('audio'):
                    multimedia_html += """
                    <h2 style="color: #1e293b; font-size: 20px; margin: 32px 0 16px 0;">🎧 Audio Content</h2>
                    """
                    for audio in multimedia_content['audio'][:3]:
                        multimedia_html += f"""
                        <div style="margin-bottom: 16px; padding: 16px; background: #fef3c7; border-radius: 8px;">
                            <h4 style="margin: 0 0 8px 0; color: #1e293b;">
                                <a href="{audio.get('url', '#')}" style="color: #1e293b; text-decoration: none;">{audio.get('title', 'Untitled')}</a>
                            </h4>
                            <p style="margin: 0; color: #475569; font-size: 14px;">{audio.get('description', '')[:150]}...</p>
                            <div style="margin-top: 8px; font-size: 12px; color: #64748b;">
                                <span>🎙️ {audio.get('source', 'Unknown')}</span>
                                {f"• ⏱️ {audio.get('duration', 0)}min" if audio.get('duration') else ""}
                            </div>
                        </div>
                        """
            
            if 'video' in content_types or 'all' in content_types:
                if multimedia_content.get('video'):
                    multimedia_html += """
                    <h2 style="color: #1e293b; font-size: 20px; margin: 32px 0 16px 0;">📹 Video Content</h2>
                    """
                    for video in multimedia_content['video'][:3]:
                        multimedia_html += f"""
                        <div style="margin-bottom: 16px; padding: 16px; background: #ecfccb; border-radius: 8px;">
                            <h4 style="margin: 0 0 8px 0; color: #1e293b;">
                                <a href="{video.get('url', '#')}" style="color: #1e293b; text-decoration: none;">{video.get('title', 'Untitled')}</a>
                            </h4>
                            <p style="margin: 0; color: #475569; font-size: 14px;">{video.get('description', '')[:150]}...</p>
                            <div style="margin-top: 8px; font-size: 12px; color: #64748b;">
                                <span>📺 {video.get('source', 'Unknown')}</span>
                                {f"• ⏱️ {video.get('duration', 0)}min" if video.get('duration') else ""}
                            </div>
                        </div>
                        """
        
        # Generate personalized insights
        insights_html = self._generate_insights(filtered_articles, user_data.get('preferences', {}))
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Daily Digest - {current_date}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 32px; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; color: white;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 800;">🤖 AI Daily</h1>
                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Your personalized AI news digest</p>
                <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">{current_date}</p>
            </div>
            
            <!-- Greeting -->
            <div style="margin-bottom: 32px;">
                <p style="font-size: 16px; color: #1e293b;">Hello {user_name},</p>
                <p style="font-size: 16px; color: #475569;">Here's your personalized AI news digest with {len(filtered_articles)} carefully curated stories matching your interests.</p>
            </div>
            
            {insights_html}
            
            <!-- Articles -->
            <h2 style="color: #1e293b; font-size: 24px; margin-bottom: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">📰 Top Stories</h2>
            {articles_html}
            
            {multimedia_html}
            
            <!-- Footer -->
            <div style="margin-top: 48px; padding: 24px; background: #f1f5f9; border-radius: 12px; text-align: center;">
                <p style="margin: 0 0 16px 0; color: #64748b; font-size: 14px;">
                    This digest was curated by AI and personalized for your interests.
                </p>
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <a href="https://www.linkedin.com/in/vidyagam-learning-063610382/" style="color: #3b82f6; text-decoration: none;">Visit our LinkedIn</a> • 
                    <a href="mailto:admin@vidyagam.com?subject=Unsubscribe" style="color: #3b82f6; text-decoration: none;">Unsubscribe</a>
                </p>
                <p style="margin: 16px 0 0 0; color: #94a3b8; font-size: 11px;">
                    AI Daily • Making AI news accessible to everyone
                </p>
            </div>
            
        </body>
        </html>
        """
        
        # Inline CSS for better email client compatibility
        if PREMAILER_AVAILABLE:
            try:
                return transform(html_template, keep_style_tags=True, strip_important=False)
            except Exception as e:
                logger.warning(f"CSS inlining failed: {e}, using original HTML")
                return html_template
        else:
            logger.info("Premailer not available - returning HTML without CSS inlining")
            return html_template
    
    def _filter_content_by_preferences(self, articles: List[Dict], preferences: Dict) -> List[Dict]:
        """Filter articles based on user preferences"""
        if not preferences:
            return articles
        
        # Filter by categories
        categories = preferences.get('categories', ['all'])
        if 'all' not in categories:
            # Simple category matching based on keywords
            category_keywords = {
                'research': ['research', 'study', 'paper', 'academic', 'arxiv'],
                'industry': ['company', 'business', 'startup', 'funding', 'acquisition'],
                'tools': ['tool', 'platform', 'software', 'app', 'service'],
                'regulations': ['regulation', 'policy', 'law', 'government', 'ethics'],
                'startups': ['startup', 'funding', 'investment', 'venture', 'seed']
            }
            
            filtered_articles = []
            for article in articles:
                content_lower = (article.get('title', '') + ' ' + article.get('content', '')).lower()
                for category in categories:
                    if category in category_keywords:
                        if any(keyword in content_lower for keyword in category_keywords[category]):
                            filtered_articles.append(article)
                            break
            
            return filtered_articles if filtered_articles else articles[:5]  # Fallback to top 5
        
        return articles
    
    def _generate_insights(self, articles: List[Dict], preferences: Dict) -> str:
        """Generate personalized insights based on articles"""
        if not articles:
            return ""
        
        total_articles = len(articles)
        avg_score = sum(article.get('significance_score', 0) for article in articles) / total_articles
        high_impact = len([a for a in articles if a.get('significance_score', 0) >= 7])
        
        # Top sources
        sources = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        top_source = max(sources.items(), key=lambda x: x[1])[0] if sources else "Various sources"
        
        insights_html = f"""
        <div style="margin-bottom: 32px; padding: 20px; background: linear-gradient(135deg, #ddd6fe 0%, #e0e7ff 100%); border-radius: 12px;">
            <h3 style="margin: 0 0 16px 0; color: #1e293b; font-size: 18px; font-weight: 600;">📊 Today's AI Insights</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; margin-bottom: 16px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #3b82f6;">{total_articles}</div>
                    <div style="font-size: 12px; color: #64748b;">Stories Curated</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #10b981;">{high_impact}</div>
                    <div style="font-size: 12px; color: #64748b;">High Impact</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #f59e0b;">{avg_score:.1f}</div>
                    <div style="font-size: 12px; color: #64748b;">Avg. Impact Score</div>
                </div>
            </div>
            <p style="margin: 0; color: #475569; font-size: 14px; text-align: center;">
                Most active source: <strong>{top_source}</strong>
            </p>
        </div>
        """
        
        return insights_html
    
    def _get_significance_color(self, score: float) -> str:
        """Get color based on significance score"""
        if score >= 7:
            return "#059669"  # Green
        elif score >= 5:
            return "#3B82F6"  # Blue
        else:
            return "#6B7280"  # Gray
    
    def _format_time_ago(self, published_date) -> str:
        """Format time ago"""
        if not published_date:
            return "Recently"
        
        try:
            if isinstance(published_date, str):
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            
            diff = datetime.now() - published_date
            hours = diff.total_seconds() / 3600
            
            if hours < 1:
                return "Just now"
            elif hours < 24:
                return f"{int(hours)}h ago"
            else:
                return f"{int(hours/24)}d ago"
        except Exception:
            return "Recently"
    
    def generate_text_digest(self, user_data: Dict, articles: List[Dict]) -> str:
        """Generate plain text email for users who prefer text"""
        current_date = datetime.now().strftime("%B %d, %Y")
        user_name = user_data.get('name', 'AI Enthusiast')
        
        # Filter articles
        filtered_articles = self._filter_content_by_preferences(articles, user_data.get('preferences', {}))
        
        text_content = f"""
AI DAILY DIGEST - {current_date}

Hello {user_name},

Here's your personalized AI news digest with {len(filtered_articles)} carefully curated stories.

TOP STORIES
-----------

"""
        
        for i, article in enumerate(filtered_articles[:8], 1):
            text_content += f"""
{i}. {article.get('title', 'Untitled')}
   Source: {article.get('source', 'Unknown')} | Impact: {article.get('significance_score', 0):.1f}/10
   {article.get('summary', article.get('content', ''))[:200]}...
   Read more: {article.get('url', '#')}

"""
        
        # Add insights
        total_articles = len(filtered_articles)
        high_impact = len([a for a in filtered_articles if a.get('significance_score', 0) >= 7])
        
        text_content += f"""
TODAY'S INSIGHTS
---------------
• {total_articles} stories curated for you
• {high_impact} high-impact developments
• Personalized based on your preferences

---

This digest was curated by AI and personalized for your interests.

Connect with us: https://www.linkedin.com/in/vidyagam-learning-063610382/
Unsubscribe: Reply with "UNSUBSCRIBE"

AI Daily • Making AI news accessible to everyone
        """
        
        return text_content
    
    async def send_digest_email(self, user_data: Dict, articles: List[Dict], multimedia_content: Dict = None) -> bool:
        """Send digest email to user"""
        try:
            user_email = user_data.get('email')
            user_name = user_data.get('name', 'AI Enthusiast')
            
            if not user_email:
                logger.error("No email address provided")
                return False
            
            # Generate content
            html_content = self.generate_daily_digest_html(user_data, articles, multimedia_content)
            text_content = self.generate_text_digest(user_data, articles)
            
            # Create email
            current_date = datetime.now().strftime("%B %d, %Y")
            subject = f"🤖 AI Daily Digest - {current_date}"
            
            # Send via Brevo
            return await self._send_brevo_email(user_email, user_name, subject, html_content, text_content)
                
        except Exception as e:
            logger.error(f"Error sending digest email: {e}")
            return False
    
    def generate_welcome_email_html(self, user_data: Dict) -> str:
        """Generate welcome email for new subscribers"""
        user_name = user_data.get('name', 'AI Enthusiast')
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to AI Daily</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 32px; padding: 24px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 16px; color: white;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 800;">🤖 Welcome to AI Daily!</h1>
                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Your journey into AI news begins now</p>
            </div>
            
            <!-- Welcome Message -->
            <div style="margin-bottom: 32px;">
                <p style="font-size: 16px; color: #1e293b;">Hello {user_name},</p>
                <p style="font-size: 16px; color: #475569;">
                    Welcome to AI Daily! We're excited to have you join our community of AI enthusiasts and professionals.
                </p>
                <p style="font-size: 16px; color: #475569;">
                    You'll receive curated AI news digests based on your preferences, featuring:
                </p>
            </div>
            
            <!-- Features -->
            <div style="margin-bottom: 32px;">
                <div style="display: block;">
                    <div style="padding: 16px; margin-bottom: 16px; background: #f0fdf4; border-radius: 8px; border-left: 4px solid #10b981;">
                        <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">📰 Curated Articles</h3>
                        <p style="margin: 0; color: #475569; font-size: 14px;">Latest AI research, industry news, and breakthrough announcements</p>
                    </div>
                    <div style="padding: 16px; margin-bottom: 16px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                        <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">🎧 Audio & Podcasts</h3>
                        <p style="margin: 0; color: #475569; font-size: 14px;">AI-focused podcasts and audio content from leading experts</p>
                    </div>
                    <div style="padding: 16px; margin-bottom: 16px; background: #ecfccb; border-radius: 8px; border-left: 4px solid #84cc16;">
                        <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">📹 Video Content</h3>
                        <p style="margin: 0; color: #475569; font-size: 14px;">Conference talks, tutorials, and AI demonstrations</p>
                    </div>
                    <div style="padding: 16px; background: #dbeafe; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">🔍 Smart Curation</h3>
                        <p style="margin: 0; color: #475569; font-size: 14px;">AI-powered significance scoring and personalized recommendations</p>
                    </div>
                </div>
            </div>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 32px 0;">
                <a href="https://www.linkedin.com/in/vidyagam-learning-063610382/" style="display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">Connect with Vidyagam</a>
            </div>
            
            <!-- Footer -->
            <div style="margin-top: 48px; padding: 24px; background: #f1f5f9; border-radius: 12px; text-align: center;">
                <p style="margin: 0 0 16px 0; color: #64748b; font-size: 14px;">
                    Thank you for subscribing to AI Daily. Your first digest will arrive soon!
                </p>
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <a href="https://www.linkedin.com/in/vidyagam-learning-063610382/" style="color: #3b82f6; text-decoration: none;">Visit our LinkedIn</a> • 
                    <a href="mailto:admin@vidyagam.com?subject=Unsubscribe" style="color: #3b82f6; text-decoration: none;">Unsubscribe</a>
                </p>
            </div>
            
        </body>
        </html>
        """
        
        try:
            return transform(html_template, keep_style_tags=True, strip_important=False)
        except Exception as e:
            logger.warning(f"CSS inlining failed: {e}, using original HTML")
            return html_template
    
    async def send_welcome_email(self, user_data: Dict) -> bool:
        """Send welcome email to new subscriber"""
        try:
            user_email = user_data.get('email')
            user_name = user_data.get('name', 'AI Enthusiast')
            
            if not user_email:
                logger.error("No email address provided")
                return False
            
            # Generate content
            html_content = self.generate_welcome_email_html(user_data)
            
            # Create email
            subject = "🤖 Welcome to Vidyagam - Your AI News Journey Begins!"
            
            plain_text = f"""
Welcome to Vidyagam!

Hello {user_name},

Welcome to Vidyagam! We're excited to have you join our community of AI enthusiasts and professionals.

You'll receive curated AI news digests featuring:
• Latest AI research and breakthroughs  
• Industry news and company updates
• Audio content and podcasts
• Video tutorials and conference talks
• AI-powered curation and personalization

Thank you for subscribing to Vidyagam!

Best regards,
The Vidyagam Team
            """
            
            # Send via Brevo
            return await self._send_brevo_email(user_email, user_name, subject, html_content, plain_text)
                
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    def generate_otp_email_html(self, user_data: Dict, otp: str) -> str:
        """Generate OTP verification email HTML"""
        user_name = user_data.get('name', 'AI Enthusiast')
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification - Vidyagam</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 32px; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; color: white;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 800;">🧠 Vidyagam</h1>
                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Email Verification Required</p>
            </div>
            
            <!-- OTP Code -->
            <div style="text-align: center; margin-bottom: 32px;">
                <p style="font-size: 16px; color: #1e293b;">Hello {user_name},</p>
                <p style="font-size: 16px; color: #475569; margin-bottom: 24px;">
                    Please use the verification code below to complete your account setup:
                </p>
                
                <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 24px; margin: 24px 0;">
                    <div style="font-size: 36px; font-weight: 800; color: #1e293b; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {otp}
                    </div>
                    <p style="margin: 12px 0 0 0; font-size: 14px; color: #64748b;">
                        This code will expire in 10 minutes
                    </p>
                </div>
                
                <p style="font-size: 14px; color: #475569;">
                    Enter this code on the verification page to activate your account.
                </p>
            </div>
            
            <!-- Security Note -->
            <div style="margin-bottom: 32px; padding: 16px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #ef4444;">
                <p style="margin: 0; color: #dc2626; font-size: 14px; font-weight: 600;">🔒 Security Notice</p>
                <p style="margin: 8px 0 0 0; color: #991b1b; font-size: 13px;">
                    Never share this verification code with anyone. Our team will never ask for this code via email or phone.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="margin-top: 32px; padding: 24px; background: #f1f5f9; border-radius: 12px; text-align: center;">
                <p style="margin: 0 0 16px 0; color: #64748b; font-size: 14px;">
                    If you didn't request this verification, please ignore this email.
                </p>
                <p style="margin: 16px 0 0 0; color: #94a3b8; font-size: 11px;">
                    Vidyagam • Connecting AI Innovation
                </p>
            </div>
            
        </body>
        </html>
        """
        
        # Inline CSS for better email client compatibility
        if PREMAILER_AVAILABLE:
            try:
                return transform(html_template, keep_style_tags=True, strip_important=False)
            except Exception as e:
                logger.warning(f"CSS inlining failed: {e}, using original HTML")
                return html_template
        else:
            return html_template
    
    async def send_otp_email(self, user_data: Dict, otp: str) -> bool:
        """Send OTP verification email to user"""
        try:
            user_email = user_data.get('email')
            user_name = user_data.get('name', 'AI Enthusiast')
            
            if not user_email:
                logger.error("No email address provided")
                return False
            
            # Generate content
            html_content = self.generate_otp_email_html(user_data, otp)
            
            # Plain text version
            plain_text = f"""
Email Verification - Vidyagam

Hello {user_name},

Please use the verification code below to complete your account setup:

{otp}

This code will expire in 10 minutes.

Enter this code on the verification page to activate your account.

SECURITY NOTICE: Never share this verification code with anyone. Our team will never ask for this code via email or phone.

If you didn't request this verification, please ignore this email.

Vidyagam • Connecting AI Innovation
            """
            
            # Create email
            subject = "🔐 Your Vidyagam Verification Code"
            
            # Send via Brevo
            return await self._send_brevo_email(user_email, user_name, subject, html_content, plain_text)
                
        except Exception as e:
            logger.error(f"Error sending OTP email: {e}")
            return False