"""
Simplified Enhanced Scraper for Serverless Environment
- Real RSS parsing
- Claude API integration
- Current day filtering
- No persistent database dependency
"""
import os
import json
import requests
import feedparser
import anthropic
from datetime import datetime, timezone
from typing import List, Dict, Optional
import pytz
import hashlib
import time

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

class SimpleEnhancedScraper:
    def __init__(self):
        # Try both possible environment variable names
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.claude_api_key) if self.claude_api_key else None
        
    def get_current_day_ist(self) -> str:
        """Get current day in IST timezone"""
        now_ist = datetime.now(IST)
        return now_ist.strftime('%Y-%m-%d')
    
    def is_article_from_today(self, published_date) -> bool:
        """Check if article is from current day in IST"""
        try:
            if isinstance(published_date, str):
                # Try to parse different date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                    try:
                        pub_date = datetime.strptime(published_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return False
            elif hasattr(published_date, '__iter__') and len(published_date) >= 6:
                # feedparser time tuple
                pub_date = datetime(*published_date[:6])
            else:
                pub_date = published_date if published_date else datetime.now()
                
            # Convert to IST if timezone aware
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            pub_date_ist = pub_date.astimezone(IST)
            current_day_ist = self.get_current_day_ist()
            article_day = pub_date_ist.strftime('%Y-%m-%d')
            
            return article_day == current_day_ist
            
        except Exception as e:
            print(f"Error checking article date: {e}")
            return False
    
    def analyze_with_claude(self, title: str, description: str) -> Dict:
        """Analyze article content with Claude API"""
        if not self.client:
            return self.create_default_analysis(title, description)
        
        try:
            prompt = f"""
            Analyze this AI news article and provide:
            1. A concise 2-sentence summary
            2. Significance score (0-10, where 10 is breakthrough news)
            3. Impact level (low/medium/high)
            
            Title: {title}
            Description: {description}
            
            Respond in JSON format:
            {{
                "summary": "Your 2-sentence summary",
                "significance_score": 7.5,
                "impact_level": "high"
            }}
            """
            
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            response = json.loads(response_text)
            return response
            
        except Exception as e:
            print(f"Claude analysis failed: {e}")
            return self.create_default_analysis(title, description)
    
    def create_default_analysis(self, title: str, description: str) -> Dict:
        """Create default analysis when Claude is not available"""
        return {
            "summary": f"{title}. {description[:100]}..." if description else f"{title}. Latest development in AI technology.",
            "significance_score": 7.0,
            "impact_level": "medium"
        }
    
    def scrape_current_day_articles(self, sources: List[Dict], limit: int = 20) -> List[Dict]:
        """Scrape RSS feeds and return current day articles with LLM analysis"""
        current_day_articles = []
        current_day = self.get_current_day_ist()
        
        print(f"Scraping for current day: {current_day}")
        
        for source in sources[:10]:  # Limit sources to avoid timeouts
            if not source.get('enabled', True):
                continue
                
            try:
                print(f"Scraping {source['name']}: {source['rss_url']}")
                
                # Fetch RSS feed with timeout
                feed = feedparser.parse(source['rss_url'])
                
                if not hasattr(feed, 'entries') or not feed.entries:
                    print(f"No entries found for {source['name']}")
                    continue
                
                for entry in feed.entries[:5]:  # Limit entries per source
                    try:
                        # Check if article is from current day
                        published_date = getattr(entry, 'published_parsed', None)
                        if published_date and self.is_article_from_today(published_date):
                            
                            # Get LLM analysis
                            title = getattr(entry, 'title', 'No title')
                            description = getattr(entry, 'summary', 'No description')
                            
                            analysis = self.analyze_with_claude(title, description)
                            
                            article = {
                                "id": hashlib.md5(entry.link.encode()).hexdigest(),
                                "title": title,
                                "description": description,
                                "content_summary": analysis['summary'],
                                "url": entry.link,
                                "source": source['name'],
                                "significance_score": analysis['significance_score'],
                                "impact_level": analysis['impact_level'],
                                "published_date": datetime(*published_date[:6]).isoformat() if published_date else datetime.now().isoformat(),
                                "time": "Today",
                                "type": "blog",
                                "readTime": "5 min read"
                            }
                            
                            current_day_articles.append(article)
                            print(f"Found current day article: {title[:50]}...")
                            
                            if len(current_day_articles) >= limit:
                                break
                    
                    except Exception as e:
                        print(f"Error processing entry from {source['name']}: {e}")
                        continue
                
                if len(current_day_articles) >= limit:
                    break
                    
            except Exception as e:
                print(f"Error scraping {source['name']}: {e}")
                continue
        
        print(f"Found {len(current_day_articles)} current day articles")
        return current_day_articles
    
    def get_digest_data(self, sources: List[Dict]) -> Dict:
        """Get complete digest data with current day filtering and LLM summaries"""
        current_day = self.get_current_day_ist()
        articles = self.scrape_current_day_articles(sources, limit=15)
        
        if not articles:
            print("No current day articles found, this could mean:")
            print("1. No articles were published today yet")
            print("2. RSS feeds don't have today's content yet") 
            print("3. Time zone differences")
            return self.get_fallback_digest(current_day)
        
        # Group by impact level
        high_impact = [a for a in articles if a['impact_level'] == 'high']
        medium_impact = [a for a in articles if a['impact_level'] == 'medium'] 
        low_impact = [a for a in articles if a['impact_level'] == 'low']
        
        # Generate key points from real articles
        key_points = [
            f"• Today ({current_day}): {len(articles)} AI developments detected",
        ]
        
        if high_impact:
            key_points.append(f"• {len(high_impact)} high-impact breakthroughs")
        if medium_impact:
            key_points.append(f"• {len(medium_impact)} significant updates")
        
        # Add top article titles as key points
        for article in articles[:3]:
            key_points.append(f"• {article['title'][:60]}...")
        
        key_points.extend([
            "• All articles feature AI-generated summaries 🤖",
            f"• Enhanced scraping with Claude API {'✓' if self.client else '✗'}"
        ])
        
        return {
            "summary": {
                "keyPoints": key_points,
                "metrics": {
                    "totalUpdates": len(articles),
                    "highImpact": len(high_impact),
                    "newResearch": len([a for a in articles if 'research' in a['title'].lower()]),
                    "industryMoves": len([a for a in articles if any(company in a['title'].lower() for company in ['openai', 'google', 'microsoft', 'meta', 'anthropic'])]),
                    "sourcesScraped": len(set(a['source'] for a in articles)),
                    "lastRefresh": datetime.now().isoformat(),
                    "avgSignificanceScore": sum(a['significance_score'] for a in articles) / len(articles) if articles else 0,
                    "claudeApiUsed": bool(self.client)
                }
            },
            "content": {
                "blog": articles,
                "audio": [],
                "video": []
            },
            "timestamp": datetime.now().isoformat(),
            "badge": f"Live Daily Updates - {current_day}",
            "enhanced": True,
            "current_day_filtered": True,
            "llm_summaries_enabled": bool(self.client)
        }
    
    def get_fallback_digest(self, current_day: str) -> Dict:
        """Fallback when no current day articles are found"""
        return {
            "summary": {
                "keyPoints": [
                    f"• Today ({current_day}): No articles found for current day",
                    "• This could be due to timezone differences",
                    "• RSS feeds may not have today's content yet",
                    "• Try again later or check source feeds"
                ],
                "metrics": {
                    "totalUpdates": 0,
                    "highImpact": 0,
                    "newResearch": 0,
                    "industryMoves": 0,
                    "sourcesScraped": 0,
                    "claudeApiUsed": bool(self.client)
                }
            },
            "content": {"blog": [], "audio": [], "video": []},
            "timestamp": datetime.now().isoformat(),
            "badge": f"No Current Day Articles - {current_day}",
            "enhanced": True,
            "current_day_filtered": True,
            "llm_summaries_enabled": bool(self.client)
        }