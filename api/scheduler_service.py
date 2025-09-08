"""
Scheduled scraping service for AI News Scraper
Runs scraping at 6 AM and 6 PM IST daily
"""
import schedule
import time
import threading
import pytz
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

class ScheduledScrapingService:
    def __init__(self, enhanced_scraper, ai_sources):
        self.enhanced_scraper = enhanced_scraper
        self.ai_sources = ai_sources
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_run_6am = None
        self.last_run_6pm = None
        
    def scheduled_scraping_job(self, run_type: str):
        """Execute scheduled scraping job"""
        try:
            now_ist = datetime.now(IST)
            logger.info(f"Starting scheduled scraping ({run_type}) at {now_ist}")
            
            # Get enabled sources
            enabled_sources = [source for source in self.ai_sources if source.get('enabled', True)]
            
            # Run scraping with current day filtering
            result = self.enhanced_scraper.scrape_with_llm_filtering(
                sources=enabled_sources,
                filter_current_day=True
            )
            
            if result.get('success'):
                logger.info(f"Scheduled scraping ({run_type}) completed successfully")
                logger.info(f"Articles found: {result.get('articles_found', 0)}")
                logger.info(f"Articles processed: {result.get('articles_processed', 0)}")
                
                # Update last run time
                if run_type == "6am":
                    self.last_run_6am = now_ist.isoformat()
                else:
                    self.last_run_6pm = now_ist.isoformat()
                    
            else:
                logger.error(f"Scheduled scraping ({run_type}) failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Scheduled scraping ({run_type}) error: {e}")
    
    def start_scheduler(self):
        """Start the scheduled scraping service"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting scheduled scraping service")
        
        # Schedule scraping at 6:00 AM IST
        schedule.every().day.at("06:00").do(
            self.scheduled_scraping_job, 
            run_type="6am"
        ).tag('daily-scraping')
        
        # Schedule scraping at 6:00 PM IST  
        schedule.every().day.at("18:00").do(
            self.scheduled_scraping_job,
            run_type="6pm"
        ).tag('daily-scraping')
        
        self.running = True
        
        # Start scheduler in background thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduled scraping service started - running at 6:00 AM and 6:00 PM IST daily")
    
    def _run_scheduler(self):
        """Internal method to run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the scheduled scraping service"""
        if not self.running:
            return
        
        logger.info("Stopping scheduled scraping service")
        self.running = False
        schedule.clear('daily-scraping')
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        logger.info("Scheduled scraping service stopped")
    
    def get_scheduler_status(self) -> dict:
        """Get current scheduler status"""
        now_ist = datetime.now(IST)
        next_runs = []
        
        if self.running:
            # Calculate next scheduled runs
            for job in schedule.get_jobs('daily-scraping'):
                next_run = job.next_run
                if next_run:
                    # Convert to IST
                    next_run_ist = next_run.astimezone(IST)
                    next_runs.append({
                        "job": f"Daily scraping",
                        "next_run": next_run_ist.isoformat(),
                        "next_run_formatted": next_run_ist.strftime("%Y-%m-%d %I:%M %p IST")
                    })
        
        return {
            "running": self.running,
            "current_time_ist": now_ist.isoformat(),
            "current_time_formatted": now_ist.strftime("%Y-%m-%d %I:%M %p IST"),
            "last_run_6am": self.last_run_6am,
            "last_run_6pm": self.last_run_6pm,
            "next_scheduled_runs": next_runs,
            "schedule_times": ["06:00 IST", "18:00 IST"]
        }
    
    def trigger_manual_run(self, run_type: str = "manual") -> dict:
        """Manually trigger a scraping run"""
        try:
            logger.info(f"Manual scraping triggered: {run_type}")
            
            # Get enabled sources
            enabled_sources = [source for source in self.ai_sources if source.get('enabled', True)]
            
            # Run scraping
            result = self.enhanced_scraper.scrape_with_llm_filtering(
                sources=enabled_sources,
                filter_current_day=True
            )
            
            return {
                "success": True,
                "trigger_type": "manual",
                "triggered_at": datetime.now(IST).isoformat(),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Manual scraping failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trigger_type": "manual",
                "triggered_at": datetime.now(IST).isoformat()
            }


# Global scheduler service instance
scheduled_scraping_service: Optional[ScheduledScrapingService] = None

def initialize_scheduler(enhanced_scraper, ai_sources):
    """Initialize the global scheduler service"""
    global scheduled_scraping_service
    
    if not enhanced_scraper:
        logger.warning("Cannot initialize scheduler: enhanced_scraper not available")
        return None
    
    scheduled_scraping_service = ScheduledScrapingService(enhanced_scraper, ai_sources)
    scheduled_scraping_service.start_scheduler()
    
    return scheduled_scraping_service

def get_scheduler_service() -> Optional[ScheduledScrapingService]:
    """Get the global scheduler service instance"""
    return scheduled_scraping_service