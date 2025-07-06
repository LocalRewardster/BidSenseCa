import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load scrapers' environment variables
scrapers_env_path = os.path.join(project_root, 'scrapers', '.env')
if os.path.exists(scrapers_env_path):
    from dotenv import load_dotenv
    load_dotenv(scrapers_env_path)

from .job_queue import job_queue, JobStatus
from .database import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class ScraperStatus:
    """Scraper status information."""
    name: str
    status: str  # 'idle', 'running', 'completed', 'failed'
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_tenders: int = 0
    recent_tenders: int = 0
    error_message: Optional[str] = None
    last_successful_run: Optional[datetime] = None


class ScraperService:
    """Service for managing scraper execution and monitoring."""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self._scraper_status: Dict[str, ScraperStatus] = {}
        self._scraper_configs = {
            'canadabuys': {
                'name': 'CanadaBuys',
                'schedule_hours': 1,
                'enabled': True,
            },
            'ontario_portal': {
                'name': 'Ontario Portal',
                'schedule_hours': 2,
                'enabled': False,  # Disabled due to broken RSS feed
            },
            'alberta_purchasing': {
                'name': 'Alberta Purchasing Connection',
                'schedule_hours': 2,
                'enabled': True,
            },
            'bc_bid': {
                'name': 'BC Bid',
                'schedule_hours': 3,
                'enabled': True,
            },
            'manitoba': {
                'name': 'Manitoba',
                'schedule_hours': 4,
                'enabled': True,
            },
            'saskatchewan': {
                'name': 'Saskatchewan',
                'schedule_hours': 4,
                'enabled': True,
            },
            'quebec': {
                'name': 'Quebec',
                'schedule_hours': 3,
                'enabled': True,
            },
        }
        self._initialize_status()
    
    def _initialize_status(self):
        """Initialize scraper status for all configured scrapers."""
        for scraper_id, config in self._scraper_configs.items():
            self._scraper_status[scraper_id] = ScraperStatus(
                name=config['name'],
                status='idle'
            )
    
    async def get_scraper_status(self, scraper_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of scrapers."""
        if scraper_id:
            if scraper_id not in self._scraper_status:
                raise ValueError(f"Scraper {scraper_id} not found")
            
            status = self._scraper_status[scraper_id]
            return {
                scraper_id: {
                    'name': status.name,
                    'status': status.status,
                    'last_run': status.last_run.isoformat() if status.last_run else None,
                    'next_run': status.next_run.isoformat() if status.next_run else None,
                    'total_tenders': status.total_tenders,
                    'recent_tenders': status.recent_tenders,
                    'error_message': status.error_message,
                    'last_successful_run': status.last_successful_run.isoformat() if status.last_successful_run else None,
                }
            }
        
        # Return all scraper statuses
        result = {}
        for scraper_id, status in self._scraper_status.items():
            result[scraper_id] = {
                'name': status.name,
                'status': status.status,
                'last_run': status.last_run.isoformat() if status.last_run else None,
                'next_run': status.next_run.isoformat() if status.next_run else None,
                'total_tenders': status.total_tenders,
                'recent_tenders': status.recent_tenders,
                'error_message': status.error_message,
                'last_successful_run': status.last_successful_run.isoformat() if status.last_successful_run else None,
            }
        
        return result
    
    async def trigger_scraper(self, scraper_id: str) -> Dict[str, Any]:
        """Manually trigger a scraper."""
        if scraper_id not in self._scraper_configs:
            raise ValueError(f"Scraper {scraper_id} not found")
        
        if scraper_id not in self._scraper_status:
            raise ValueError(f"Scraper {scraper_id} status not initialized")
        
        status = self._scraper_status[scraper_id]
        
        # Check if scraper is already running
        if status.status == 'running':
            raise ValueError(f"Scraper {scraper_id} is already running")
        
        # Create async wrapper function for the job
        async def run_scraper_job():
            return await self._run_scraper(scraper_id)
        
        # Create and start job
        job = await job_queue.create_job(
            name=f"scraper_{scraper_id}",
            task_func=run_scraper_job,
            metadata={'scraper_id': scraper_id}
        )
        
        await job_queue.start_job(job.id)
        
        # Update status
        status.status = 'running'
        status.last_run = datetime.now(timezone.utc)
        status.error_message = None
        
        logger.info(f"Triggered scraper {scraper_id}")
        
        return {
            'job_id': job.id,
            'scraper_id': scraper_id,
            'status': 'started',
            'message': f"Scraper {scraper_id} started successfully"
        }
    
    async def _run_scraper(self, scraper_id: str) -> Dict[str, Any]:
        """Run a specific scraper."""
        status = self._scraper_status[scraper_id]
        
        try:
            logger.info(f"Starting scraper {scraper_id}")
            
            # Import and run the scraper
            scraper_module = await self._import_scraper(scraper_id)
            if not scraper_module:
                raise ImportError(f"Could not import scraper {scraper_id}")
            
            # Run the scraper
            result = await scraper_module.run()
            
            # Update status on success
            status.status = 'completed'
            status.last_successful_run = datetime.now(timezone.utc)
            status.error_message = None
            
            # Update tender counts
            await self._update_tender_counts(scraper_id)
            
            logger.info(f"Scraper {scraper_id} completed successfully")
            return result
            
        except Exception as e:
            # Update status on failure
            status.status = 'failed'
            status.error_message = str(e)
            
            logger.error(f"Scraper {scraper_id} failed: {e}")
            raise
    
    async def _import_scraper(self, scraper_id: str):
        """Import a scraper module dynamically."""
        try:
            logger.info(f"Importing scraper {scraper_id}")
            
            # Import the actual scraper based on scraper_id
            if scraper_id == 'canadabuys':
                from scrapers.scrapers.canadabuys import CanadaBuysScraper
                return CanadaBuysScraper()
            elif scraper_id == 'ontario_portal':
                from scrapers.scrapers.ontario_portal import OntarioPortalScraper
                return OntarioPortalScraper()
            elif scraper_id == 'alberta_purchasing':
                from scrapers.scrapers.apc import APCScraper
                return APCScraper()
            elif scraper_id == 'bc_bid':
                from scrapers.scrapers.bcbid import BCBidScraper
                return BCBidScraper()
            elif scraper_id == 'manitoba':
                from scrapers.scrapers.manitoba import ManitobaScraper
                return ManitobaScraper()
            elif scraper_id == 'saskatchewan':
                from scrapers.scrapers.saskatchewan import SaskatchewanScraper
                return SaskatchewanScraper()
            elif scraper_id == 'quebec':
                from scrapers.scrapers.quebec import QuebecScraper
                return QuebecScraper()
            else:
                logger.error(f"Unknown scraper ID: {scraper_id}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to import scraper {scraper_id}: {e}")
            return None
    
    async def _update_tender_counts(self, scraper_id: str):
        """Update tender counts for a scraper."""
        try:
            # Get total count
            total_result = self.db_service.supabase.table('tenders').select('id', count='exact').eq('source_name', scraper_id).execute()
            total_count = total_result.count if hasattr(total_result, 'count') else 0
            
            # Get recent count (last 7 days) - use scraped_at
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_result = self.db_service.supabase.table('tenders').select('id', count='exact').eq('source_name', scraper_id).gte('scraped_at', yesterday.isoformat()).execute()
            recent_count = recent_result.count if hasattr(recent_result, 'count') else 0
            
            # Update status
            status = self._scraper_status[scraper_id]
            status.total_tenders = total_count
            status.recent_tenders = recent_count
            
            logger.info(f"Updated counts for {scraper_id}: total={total_count}, recent={recent_count}")
            
        except Exception as e:
            logger.error(f"Failed to update tender counts for {scraper_id}: {e}")
    
    async def get_scraper_logs(self, scraper_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get scraper execution logs."""
        # Get job history from job queue
        if scraper_id:
            # Filter by scraper ID
            jobs = job_queue.get_job_history(limit=limit)
            scraper_jobs = [job for job in jobs if job.metadata.get('scraper_id') == scraper_id]
        else:
            # Get all scraper jobs
            jobs = job_queue.get_job_history(limit=limit)
            scraper_jobs = [job for job in jobs if job.metadata.get('scraper_id')]
        
        # Convert to log format
        logs = []
        for job in scraper_jobs:
            log_entry = {
                'timestamp': job.created_at.isoformat(),
                'level': 'ERROR' if job.status == JobStatus.FAILED else 'INFO',
                'message': f"Scraper {job.metadata.get('scraper_id', 'unknown')} {job.status.value}",
                'scraper': job.metadata.get('scraper_id'),
                'job_id': job.id,
                'error_message': job.error_message,
            }
            logs.append(log_entry)
        
        return logs
    
    async def get_scraper_configs(self) -> Dict[str, Any]:
        """Get scraper configurations."""
        return self._scraper_configs.copy()
    
    async def update_scraper_config(self, scraper_id: str, config: Dict[str, Any]) -> bool:
        """Update scraper configuration."""
        if scraper_id not in self._scraper_configs:
            return False
        
        # Update config
        self._scraper_configs[scraper_id].update(config)
        
        logger.info(f"Updated config for scraper {scraper_id}")
        return True


# Global scraper service instance
scraper_service = ScraperService() 