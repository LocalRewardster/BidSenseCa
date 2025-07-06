"""Job queue management service for scraper jobs."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from loguru import logger

from app.models.scraper_job import ScraperJob, JobStatus, ScraperJobCreate
from app.services.scraper_service import scraper_service


class JobQueue:
    """Simple in-memory job queue for scraper jobs."""
    
    def __init__(self):
        self.jobs: Dict[str, ScraperJob] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
    
    async def create_job(self, job_data: ScraperJobCreate) -> ScraperJob:
        """Create a new scraper job."""
        job_id = str(uuid.uuid4())
        
        job = ScraperJob(
            id=job_id,
            scraper_name=job_data.scraper_name,
            limit=job_data.limit,
            parameters=job_data.parameters,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} for scraper {job_data.scraper_name}")
        
        return job
    
    async def start_job(self, job_id: str) -> bool:
        """Start a pending job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status != JobStatus.PENDING:
            return False
        
        # Update job status
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        
        # Create async task
        task = asyncio.create_task(self._execute_job(job_id))
        self.running_jobs[job_id] = task
        
        logger.info(f"Started job {job_id}")
        return True
    
    async def _execute_job(self, job_id: str):
        """Execute a scraper job."""
        job = self.jobs[job_id]
        
        try:
            logger.info(f"Executing job {job_id} for scraper {job.scraper_name}")
            
            # Run scraper
            result = await scraper_service.run_scraper(
                job.scraper_name,
                job.limit,
                job.parameters
            )
            
            # Update job with results
            job.completed_at = datetime.now(timezone.utc)
            job.tenders_scraped = result.get("tender_count", 0)
            job.tenders_saved = result.get("tender_count", 0)  # Assuming all scraped are saved
            job.logs = result.get("output", "")
            
            if result["success"]:
                job.status = JobStatus.COMPLETED
                logger.info(f"Job {job_id} completed successfully: {job.tenders_saved} tenders")
            else:
                job.status = JobStatus.FAILED
                job.error_message = result.get("error", "Unknown error")
                logger.error(f"Job {job_id} failed: {job.error_message}")
        
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            logger.error(f"Job {job_id} failed with exception: {e}")
        
        finally:
            # Remove from running jobs
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status != JobStatus.RUNNING:
            return False
        
        # Cancel the task
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            del self.running_jobs[job_id]
        
        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Cancelled job {job_id}")
        return True
    
    def get_job(self, job_id: str) -> Optional[ScraperJob]:
        """Get a specific job by ID."""
        return self.jobs.get(job_id)
    
    def get_jobs(
        self, 
        limit: int = 50, 
        offset: int = 0,
        status: Optional[JobStatus] = None
    ) -> Dict[str, Any]:
        """Get jobs with filtering and pagination."""
        jobs = list(self.jobs.values())
        
        # Apply status filter
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by creation date (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        total = len(jobs)
        paginated_jobs = jobs[offset:offset + limit]
        
        return {
            "jobs": paginated_jobs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old completed/failed jobs."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and 
                job.created_at < cutoff_date):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")


# Global job queue instance
job_queue = JobQueue()


class JobService:
    """Service for managing scraper jobs."""
    
    def __init__(self):
        self.queue = job_queue
    
    async def create_and_start_job(
        self, 
        scraper_name: str,
        limit: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ScraperJob:
        """Create and immediately start a scraper job."""
        job_data = ScraperJobCreate(
            scraper_name=scraper_name,
            limit=limit,
            parameters=parameters
        )
        
        job = await self.queue.create_job(job_data)
        await self.queue.start_job(job.id)
        
        return job
    
    async def create_job(self, job_data: ScraperJobCreate) -> ScraperJob:
        """Create a new scraper job."""
        return await self.queue.create_job(job_data)
    
    async def start_job(self, job_id: str) -> bool:
        """Start a pending job."""
        return await self.queue.start_job(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        return await self.queue.cancel_job(job_id)
    
    def get_job(self, job_id: str) -> Optional[ScraperJob]:
        """Get a specific job by ID."""
        return self.queue.get_job(job_id)
    
    def get_jobs(
        self, 
        limit: int = 50, 
        offset: int = 0,
        status: Optional[JobStatus] = None
    ) -> Dict[str, Any]:
        """Get jobs with filtering and pagination."""
        return self.queue.get_jobs(limit, offset, status)
    
    async def run_scheduled_jobs(self):
        """Run scheduled scraper jobs."""
        logger.info("Running scheduled scraper jobs")
        
        # Run all scrapers
        result = await scraper_service.run_all_scrapers()
        
        # Create job record
        job_data = ScraperJobCreate(
            scraper_name="all",
            parameters={"scheduled": True}
        )
        
        job = await self.queue.create_job(job_data)
        job.status = JobStatus.COMPLETED if result["success"] else JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.tenders_scraped = result["total_tenders"]
        job.tenders_saved = result["total_tenders"]
        job.logs = f"Scheduled run: {result['scrapers_run']} scrapers, {result['total_tenders']} tenders"
        
        if not result["success"]:
            job.error_message = "Some scrapers failed"
        
        logger.info(f"Scheduled job completed: {result['total_tenders']} tenders")
        return job


# Global job service instance
job_service = JobService() 