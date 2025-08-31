"""
Newsletter service for AI News Scraper
Handles email delivery for different subscription tiers
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from auth_models import User, SubscriptionTier

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, To, From, Subject, HtmlContent
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

logger = logging.getLogger(__name__)

class NewsletterService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
        self.reply_to_email = os.getenv("REPLY_TO_EMAIL", "support@yourdomain.com")
        
        # SMTP fallback configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        
        if self.email_enabled:
            if SENDGRID_AVAILABLE and self.sendgrid_api_key:
                self.email_provider = "sendgrid"
                self.sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
                logger.info("Newsletter service initialized with SendGrid")
            elif self.smtp_username and self.smtp_password:
                self.email_provider = "smtp"
                logger.info("Newsletter service initialized with SMTP")
            else:
                self.email_provider = None
                logger.warning("Email service enabled but no valid configuration found")
        else:
            self.email_provider = None
            logger.info("Newsletter service disabled")
    
    def get_subscribers_by_frequency(self, frequency: str) -> List[Dict]:
        """Get subscribers by newsletter frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, name, subscription_tier, preferences
            FROM users 
            WHERE is_active = 1
            AND json_extract(preferences, '$.newsletter_frequency') = ?
            AND json_extract(preferences, '$.email_notifications') = 1
        ''', (frequency,))
        
        subscribers = []
        for row in cursor.fetchall():
            preferences = json.loads(row[4]) if row[4] else {}
            subscribers.append({
                'id': row[0],
                'email': row[1],
                'name': row[2],
                'subscription_tier': row[3],
                'preferences': preferences
            })
        
        conn.close()
        return subscribers
    
    def get_digest_content(self, user_tier: str, personalized: bool = False) -> Dict:
        """Get digest content based on subscription tier"""
        # This would integrate with your existing digest generation
        # For now, return a mock structure
        
        base_content = {
            'subject': f"{'Premium ' if user_tier == 'premium' else ''}AI News Digest - {datetime.now().strftime('%B %d, %Y')}",
            'total_articles': 15 if user_tier == 'premium' else 8,
            'sections': {
                'top_stories': 10 if user_tier == 'premium' else 5,
                'research': 8 if user_tier == 'premium' else 3,
                'tools': 6 if user_tier == 'premium' else 2,
                'industry': 5 if user_tier == 'premium' else 2,
            }
        }
        
        if user_tier == 'premium':
            base_content['premium_sections'] = {
                'ai_events': 3,
                'learning_resources': 4,
                'exclusive_interviews': 1
            }
        
        return base_content
    
    def generate_email_html(self, user: Dict, digest_content: Dict) -> str:
        """Generate HTML email content"""
        user_name = user['name'].split()[0] if user['name'] else 'there'
        is_premium = user['subscription_tier'] == 'premium'
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{digest_content['subject']}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #f8fafc;
                }}
                .container {{
                    background: white;
                    border-radius: 12px;
                    padding: 32px;
                    margin: 20px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 32px;
                    padding-bottom: 24px;
                    border-bottom: 2px solid #e5e7eb;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2563eb;
                    margin-bottom: 8px;
                }}
                .greeting {{
                    font-size: 18px;
                    color: #4b5563;
                }}
                .premium-badge {{
                    background: linear-gradient(135deg, #fbbf24, #f59e0b);
                    color: white;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    display: inline-block;
                    margin-left: 8px;
                }}
                .section {{
                    margin-bottom: 32px;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 16px;
                    border-left: 4px solid #2563eb;
                    padding-left: 12px;
                }}
                .article {{
                    padding: 16px;
                    background: #f9fafb;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    border-left: 3px solid #2563eb;
                }}
                .article-title {{
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 8px;
                }}
                .article-meta {{
                    font-size: 14px;
                    color: #6b7280;
                }}
                .cta-section {{
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                    color: white;
                    padding: 24px;
                    border-radius: 8px;
                    text-align: center;
                    margin: 32px 0;
                }}
                .cta-button {{
                    background: white;
                    color: #2563eb;
                    padding: 12px 24px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    display: inline-block;
                    margin-top: 12px;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 24px;
                    border-top: 1px solid #e5e7eb;
                    font-size: 14px;
                    color: #6b7280;
                }}
                .unsubscribe {{
                    color: #9ca3af;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">⚡ AI News Digest</div>
                    {f'<span class="premium-badge">PREMIUM</span>' if is_premium else ''}
                    <div class="greeting">Hello {user_name}! 👋</div>
                </div>
                
                <div class="section">
                    <p>Here's your personalized AI news digest with <strong>{digest_content['total_articles']} stories</strong> curated just for you.</p>
                </div>
                
                <div class="section">
                    <div class="section-title">🔥 Top Stories</div>
                    <div class="article">
                        <div class="article-title">Latest breakthrough in transformer architecture shows 40% efficiency improvement</div>
                        <div class="article-meta">OpenAI Research • 2 hours ago • High Impact</div>
                    </div>
                    <div class="article">
                        <div class="article-title">Google announces Gemini 2.0 with enhanced reasoning capabilities</div>
                        <div class="article-meta">Google AI • 4 hours ago • High Impact</div>
                    </div>
                    <div class="article">
                        <div class="article-title">New AI safety framework proposed by leading researchers</div>
                        <div class="article-meta">Nature AI • 6 hours ago • Research</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">🔬 Research & Development</div>
                    <div class="article">
                        <div class="article-title">Multimodal AI models show promise in medical diagnosis</div>
                        <div class="article-meta">MIT Technology Review • 1 day ago</div>
                    </div>
                    <div class="article">
                        <div class="article-title">Quantum-enhanced machine learning algorithms demonstrate superiority</div>
                        <div class="article-meta">Science Journal • 1 day ago</div>
                    </div>
                </div>
        """
        
        if is_premium:
            html += """
                <div class="section">
                    <div class="section-title">🎯 Premium: AI Events This Week</div>
                    <div class="article">
                        <div class="article-title">NeurIPS 2024 Workshop on AI Safety</div>
                        <div class="article-meta">December 15, 2024 • Virtual Event</div>
                    </div>
                    <div class="article">
                        <div class="article-title">Enterprise AI Summit - San Francisco</div>
                        <div class="article-meta">December 18, 2024 • In-person</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">📚 Learning Resources</div>
                    <div class="article">
                        <div class="article-title">Advanced Prompt Engineering Masterclass</div>
                        <div class="article-meta">New Course • DeepLearning.AI</div>
                    </div>
                </div>
            """
        else:
            html += f"""
                <div class="cta-section">
                    <h3>Unlock Premium Features</h3>
                    <p>Get daily digests, exclusive AI events, and premium learning resources.</p>
                    <a href="https://your-frontend-url.com/upgrade" class="cta-button">Upgrade to Premium</a>
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <p>
                        <a href="https://your-frontend-url.com">Read online</a> • 
                        <a href="https://your-frontend-url.com/preferences">Manage preferences</a>
                    </p>
                    <p class="unsubscribe">
                        <a href="https://your-frontend-url.com/unsubscribe?token=user_{user['id']}">Unsubscribe</a> • 
                        AI News Digest • Made with ❤️ for the AI community
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email_sendgrid(self, to_email: str, to_name: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid"""
        try:
            from_email = From(self.from_email, "AI News Digest")
            to_email_obj = To(to_email, to_name)
            subject_obj = Subject(subject)
            html_content_obj = HtmlContent(html_content)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email_obj,
                subject=subject_obj,
                html_content=html_content_obj
            )
            
            # Add reply-to
            mail.reply_to = self.reply_to_email
            
            response = self.sg.send(mail)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"SendGrid email error: {e}")
            return False
    
    def send_email_smtp(self, to_email: str, to_name: str, subject: str, html_content: str) -> bool:
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"AI News Digest <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Reply-To'] = self.reply_to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"SMTP email error: {e}")
            return False
    
    def send_newsletter(self, user: Dict, digest_content: Dict) -> bool:
        """Send newsletter to a user"""
        if not self.email_enabled or not self.email_provider:
            logger.info(f"Email disabled, skipping newsletter for {user['email']}")
            return False
        
        html_content = self.generate_email_html(user, digest_content)
        subject = digest_content['subject']
        
        if self.email_provider == "sendgrid":
            return self.send_email_sendgrid(user['email'], user['name'], subject, html_content)
        elif self.email_provider == "smtp":
            return self.send_email_smtp(user['email'], user['name'], subject, html_content)
        
        return False
    
    def send_daily_newsletters(self) -> Dict:
        """Send daily newsletters to premium subscribers"""
        if not self.email_enabled:
            return {"sent": 0, "failed": 0, "message": "Email service disabled"}
        
        premium_subscribers = [
            user for user in self.get_subscribers_by_frequency('daily')
            if user['subscription_tier'] == 'premium'
        ]
        
        sent = 0
        failed = 0
        
        for user in premium_subscribers:
            try:
                digest_content = self.get_digest_content('premium', personalized=True)
                if self.send_newsletter(user, digest_content):
                    sent += 1
                    logger.info(f"Daily newsletter sent to {user['email']}")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to send daily newsletter to {user['email']}: {e}")
                failed += 1
        
        return {
            "sent": sent,
            "failed": failed,
            "total_subscribers": len(premium_subscribers),
            "message": f"Daily newsletters: {sent} sent, {failed} failed"
        }
    
    def send_weekly_newsletters(self) -> Dict:
        """Send weekly newsletters to all subscribers"""
        if not self.email_enabled:
            return {"sent": 0, "failed": 0, "message": "Email service disabled"}
        
        weekly_subscribers = self.get_subscribers_by_frequency('weekly')
        
        sent = 0
        failed = 0
        
        for user in weekly_subscribers:
            try:
                digest_content = self.get_digest_content(user['subscription_tier'], personalized=True)
                if self.send_newsletter(user, digest_content):
                    sent += 1
                    logger.info(f"Weekly newsletter sent to {user['email']}")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to send weekly newsletter to {user['email']}: {e}")
                failed += 1
        
        return {
            "sent": sent,
            "failed": failed,
            "total_subscribers": len(weekly_subscribers),
            "message": f"Weekly newsletters: {sent} sent, {failed} failed"
        }
    
    def send_welcome_email(self, user: Dict) -> bool:
        """Send welcome email to new user"""
        if not self.email_enabled or not self.email_provider:
            return False
        
        subject = "Welcome to AI News Digest! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .container {{ background: white; padding: 32px; border-radius: 12px; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 32px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #2563eb; }}
                .cta {{ background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block; margin: 16px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">⚡ AI News Digest</div>
                </div>
                <h2>Welcome aboard, {user['name'].split()[0]}! 🚀</h2>
                <p>Thank you for joining AI News Digest! You're now part of a community that stays ahead in the rapidly evolving world of artificial intelligence.</p>
                
                <h3>What's Next?</h3>
                <ul>
                    <li>✅ Customize your topic preferences</li>
                    <li>✅ Choose your newsletter frequency</li>
                    <li>✅ Explore premium features</li>
                </ul>
                
                <p>Your next digest will arrive according to your preferences. Ready to dive in?</p>
                
                <a href="https://your-frontend-url.com/preferences" class="cta">Complete Your Setup</a>
                
                <p>Questions? Just reply to this email - we're here to help!</p>
                
                <p>Welcome to the future of AI news,<br>The AI News Digest Team</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_newsletter(user, {"subject": subject, "html": html_content})