import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging
from contextlib import asynccontextmanager
import inspect, types, json

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job data structure."""
    id: str
    name: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    task_func: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary, ensuring all fields are serializable (recursively for result)."""
        data = asdict(self)
        data['status'] = self.status.value
        # Remove task_func from dict as it's not serializable
        if 'task_func' in data:
            del data['task_func']
        def safe_serialize(val):
            if isinstance(val, dict):
                return {k: safe_serialize(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [safe_serialize(v) for v in val]
            elif isinstance(val, tuple):
                return tuple(safe_serialize(v) for v in val)
            elif isinstance(val, set):
                return [safe_serialize(v) for v in val]
            try:
                json.dumps(val)
                return val
            except Exception:
                if inspect.iscoroutine(val):
                    return '<coroutine>'
                if inspect.isfunction(val) or inspect.ismethod(val):
                    return '<function>'
                if isinstance(val, types.GeneratorType):
                    return '<generator>'
                return str(val)
        if 'result' in data:
            data['result'] = safe_serialize(data['result'])
        # Also ensure datetime fields are isoformat strings
        for dt_field in ['created_at', 'started_at', 'completed_at']:
            if data.get(dt_field) and isinstance(data[dt_field], datetime):
                data[dt_field] = data[dt_field].isoformat()
        # Debug logging
        try:
            logger.debug(f"Serializing job to dict: {data}")
            json.dumps(data)  # Try to serialize to JSON
        except Exception as e:
            logger.error(f"Serialization error in Job.to_dict: {e}. Data: {data}")
        return data


class JobQueue:
    """Simple in-memory job queue with persistence capabilities."""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._job_history: List[Job] = []
        self._max_history_size = 1000
        
    async def create_job(
        self, 
        name: str, 
        task_func: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            name=name,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            task_func=task_func
        )
        
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} for {name}")
        return job
    
    async def start_job(self, job_id: str) -> bool:
        """Start a pending job."""
        if job_id not in self._jobs:
            logger.error(f"Job {job_id} not found")
            return False
            
        job = self._jobs[job_id]
        if job.status != JobStatus.PENDING:
            logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return False
        
        # Create async task for job execution
        task = asyncio.create_task(self._execute_job(job_id))
        self._running_jobs[job_id] = task
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        
        logger.info(f"Started job {job_id}")
        return True
    
    async def _execute_job(self, job_id: str):
        """Execute a job."""
        job = self._jobs[job_id]
        try:
            # Execute the task function
            if job.task_func:
                if asyncio.iscoroutinefunction(job.task_func):
                    result = await job.task_func()
                else:
                    result = job.task_func()
                
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
                
                logger.info(f"Job {job_id} completed successfully")
            else:
                raise ValueError("No task function provided")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(e)
            
            logger.error(f"Job {job_id} failed: {e}")
            
        finally:
            # Clean up
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
            
            # Add to history
            self._add_to_history(job)
    
    def _add_to_history(self, job: Job):
        """Add completed job to history."""
        self._job_history.append(job)
        
        # Maintain history size limit
        if len(self._job_history) > self._max_history_size:
            self._job_history.pop(0)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id not in self._jobs:
            return False
            
        job = self._jobs[job_id]
        if job.status != JobStatus.RUNNING:
            return False
        
        # Cancel the running task
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            del self._running_jobs[job_id]
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Cancelled job {job_id}")
        return True
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs(
        self, 
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """Get jobs with optional filtering."""
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Sort by creation date (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return jobs[:limit]
    
    def get_job_history(
        self, 
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """Get job history with optional filtering."""
        history = self._job_history.copy()
        
        if status:
            history = [job for job in history if job.status == status]
        
        return history[:limit]
    
    def get_running_jobs(self) -> List[Job]:
        """Get all currently running jobs."""
        return [job for job in self._jobs.values() if job.status == JobStatus.RUNNING]
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        jobs_to_remove = []
        for job_id, job in self._jobs.items():
            if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and 
                job.completed_at and job.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._jobs[job_id]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")


# Global job queue instance
job_queue = JobQueue() 