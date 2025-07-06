import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import signal
import sys

from .scraper_service import scraper_service
from .job_queue import job_queue

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Scheduled task configuration."""
    name: str
    func: Callable
    interval_hours: int
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class TaskScheduler:
    """Task scheduler for running periodic jobs."""
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def add_task(
        self, 
        name: str, 
        func: Callable, 
        interval_hours: int,
        enabled: bool = True
    ) -> None:
        """Add a scheduled task."""
        task = ScheduledTask(
            name=name,
            func=func,
            interval_hours=interval_hours,
            enabled=enabled,
            next_run=datetime.now(timezone.utc) + timedelta(hours=interval_hours)
        )
        
        self._tasks[name] = task
        logger.info(f"Added scheduled task: {name} (every {interval_hours} hours)")
    
    async def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self._tasks:
            del self._tasks[name]
            logger.info(f"Removed scheduled task: {name}")
            return True
        return False
    
    async def enable_task(self, name: str) -> bool:
        """Enable a scheduled task."""
        if name in self._tasks:
            self._tasks[name].enabled = True
            logger.info(f"Enabled scheduled task: {name}")
            return True
        return False
    
    async def disable_task(self, name: str) -> bool:
        """Disable a scheduled task."""
        if name in self._tasks:
            self._tasks[name].enabled = False
            logger.info(f"Disabled scheduled task: {name}")
            return True
        return False
    
    async def run_task_now(self, name: str) -> bool:
        """Run a task immediately."""
        if name not in self._tasks:
            logger.error(f"Task {name} not found")
            return False
        
        task = self._tasks[name]
        if not task.enabled:
            logger.warning(f"Task {name} is disabled")
            return False
        
        try:
            logger.info(f"Running task {name} immediately")
            await self._execute_task(task)
            return True
        except Exception as e:
            logger.error(f"Failed to run task {name}: {e}")
            return False
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        logger.info("Starting task scheduler")
        
        # Start scheduler loop
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        logger.info("Stopping task scheduler")
        self._running = False
        
        # Cancel running tasks
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                
                # Check for tasks that need to run
                for task in self._tasks.values():
                    if (task.enabled and 
                        task.next_run and 
                        now >= task.next_run):
                        
                        # Execute task
                        asyncio.create_task(self._execute_task(task))
                
                # Sleep for a short interval
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        try:
            task.last_run = datetime.now(timezone.utc)
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task.func):
                await task.func()
            else:
                task.func()
            
            # Schedule next run
            task.next_run = datetime.now(timezone.utc) + timedelta(hours=task.interval_hours)
            
            logger.info(f"Completed scheduled task: {task.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled task {task.name}: {e}")
            
            # Still schedule next run even if failed
            task.next_run = datetime.now(timezone.utc) + timedelta(hours=task.interval_hours)
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop."""
        while self._running:
            try:
                # Clean up old jobs
                job_queue.cleanup_old_jobs(max_age_hours=24)
                
                # Sleep for cleanup interval
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all scheduled tasks."""
        status = {}
        for name, task in self._tasks.items():
            status[name] = {
                'name': task.name,
                'enabled': task.enabled,
                'interval_hours': task.interval_hours,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
            }
        return status
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


class ScraperScheduler:
    """Specialized scheduler for scraper tasks."""
    
    def __init__(self):
        self.scheduler = TaskScheduler()
        self._initialized = False
        self.scraper_service = scraper_service
    
    async def initialize(self) -> None:
        """Initialize scraper scheduler with configured scrapers."""
        if self._initialized:
            return
        
        # Get scraper configurations
        configs = await self.scraper_service.get_scraper_configs()
        
        # Add tasks for each enabled scraper
        for scraper_id, config in configs.items():
            if config.get('enabled', True):
                await self.scheduler.add_task(
                    name=f"scraper_{scraper_id}",
                    func=lambda sid=scraper_id: self.scraper_service.trigger_scraper(sid),
                    interval_hours=config.get('schedule_hours', 1)
                )
        
        self._initialized = True
        logger.info("Scraper scheduler initialized")
    
    async def start(self) -> None:
        """Start the scraper scheduler."""
        await self.initialize()
        await self.scheduler.start()
    
    async def stop(self) -> None:
        """Stop the scraper scheduler."""
        await self.scheduler.stop()
    
    async def trigger_all_scrapers(self) -> Dict[str, Any]:
        """Trigger all enabled scrapers immediately."""
        configs = await self.scraper_service.get_scraper_configs()
        results = {}
        
        for scraper_id, config in configs.items():
            if config.get('enabled', True):
                try:
                    result = await self.scraper_service.trigger_scraper(scraper_id)
                    results[scraper_id] = result
                except Exception as e:
                    results[scraper_id] = {
                        'error': str(e),
                        'status': 'failed'
                    }
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'running': self.scheduler.is_running(),
            'initialized': self._initialized,
            'tasks': self.scheduler.get_task_status()
        }


# Global scheduler instances
task_scheduler = TaskScheduler()
scraper_scheduler = ScraperScheduler() 