"""Scheduled task manager for periodic scraper jobs."""

import asyncio
import signal
from datetime import datetime, time
from typing import Dict, List, Optional, Callable
from loguru import logger

from app.services.job_service import job_service


class SchedulerService:
    """Service for managing scheduled scraper jobs."""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.schedule_config = {
            "morning": time(8, 0),    # 8:00 AM
            "afternoon": time(14, 0), # 2:00 PM
            "evening": time(20, 0),   # 8:00 PM
        }
    
    async def start(self):
        """Start the scheduler service."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting scheduler service")
        
        # Start scheduled tasks
        for name, schedule_time in self.schedule_config.items():
            task = asyncio.create_task(self._run_scheduled_task(name, schedule_time))
            self.tasks[name] = task
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
        self.tasks["cleanup"] = cleanup_task
        
        logger.info(f"Started {len(self.tasks)} scheduled tasks")
    
    async def stop(self):
        """Stop the scheduler service."""
        if not self.running:
            return
        
        logger.info("Stopping scheduler service")
        self.running = False
        
        # Cancel all tasks
        for name, task in self.tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
        logger.info("Scheduler service stopped")
    
    async def _run_scheduled_task(self, name: str, schedule_time: time):
        """Run a scheduled task at the specified time."""
        logger.info(f"Started scheduled task: {name} at {schedule_time}")
        
        while self.running:
            try:
                # Calculate next run time
                now = datetime.now()
                next_run = datetime.combine(now.date(), schedule_time)
                
                # If time has passed today, schedule for tomorrow
                if next_run <= now:
                    next_run = next_run.replace(day=next_run.day + 1)
                
                # Wait until next run time
                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Next {name} run in {wait_seconds:.0f} seconds")
                
                await asyncio.sleep(wait_seconds)
                
                if self.running:
                    logger.info(f"Running scheduled task: {name}")
                    await job_service.run_scheduled_jobs()
                
            except asyncio.CancelledError:
                logger.info(f"Scheduled task {name} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled task {name}: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _cleanup_old_jobs(self):
        """Periodically cleanup old jobs."""
        logger.info("Started cleanup task")
        
        while self.running:
            try:
                # Wait 24 hours
                await asyncio.sleep(24 * 60 * 60)
                
                if self.running:
                    logger.info("Running cleanup task")
                    job_service.queue.cleanup_old_jobs(days=7)
                
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    async def run_now(self, scraper_name: str = "all") -> str:
        """Run a scraper job immediately."""
        logger.info(f"Running immediate job for: {scraper_name}")
        
        if scraper_name == "all":
            job = await job_service.run_scheduled_jobs()
        else:
            job = await job_service.create_and_start_job(scraper_name)
        
        return job.id
    
    def get_schedule_info(self) -> Dict[str, Any]:
        """Get information about the current schedule."""
        return {
            "running": self.running,
            "tasks": list(self.tasks.keys()),
            "schedule": {
                name: time.strftime("%H:%M") 
                for name, time in self.schedule_config.items()
            }
        }
    
    def update_schedule(self, new_schedule: Dict[str, str]):
        """Update the schedule configuration."""
        # Parse time strings (format: "HH:MM")
        for name, time_str in new_schedule.items():
            try:
                hour, minute = map(int, time_str.split(":"))
                self.schedule_config[name] = time(hour, minute)
            except ValueError:
                logger.error(f"Invalid time format: {time_str}")
        
        logger.info(f"Updated schedule: {self.schedule_config}")


# Global scheduler instance
scheduler_service = SchedulerService()


async def start_scheduler():
    """Start the scheduler service."""
    await scheduler_service.start()


async def stop_scheduler():
    """Stop the scheduler service."""
    await scheduler_service.stop()


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down scheduler")
        asyncio.create_task(stop_scheduler())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler) 