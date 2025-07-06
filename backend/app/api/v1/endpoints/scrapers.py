from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
import logging

from app.services.scraper_service import scraper_service
from app.services.job_queue import job_queue, JobStatus
from app.services.scheduler import scraper_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_scraper_status(scraper_id: Optional[str] = None) -> Dict[str, Any]:
    """Get status of all scrapers or a specific scraper."""
    try:
        status = await scraper_service.get_scraper_status(scraper_id)
        return {
            "success": True,
            "data": status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{scraper_id}/trigger")
async def trigger_scraper(scraper_id: str) -> Dict[str, Any]:
    """Manually trigger a scraper."""
    try:
        result = await scraper_service.trigger_scraper(scraper_id)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering scraper {scraper_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trigger-all")
async def trigger_all_scrapers() -> Dict[str, Any]:
    """Trigger all enabled scrapers."""
    try:
        results = await scraper_scheduler.trigger_all_scrapers()
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        logger.error(f"Error triggering all scrapers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/logs")
async def get_scraper_logs(
    scraper_id: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get scraper execution logs."""
    try:
        logs = await scraper_service.get_scraper_logs(scraper_id, limit)
        return {
            "success": True,
            "data": logs
        }
    except Exception as e:
        logger.error(f"Error getting scraper logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs")
async def get_jobs(
    status: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get job queue status."""
    try:
        # Convert status string to enum if provided
        job_status = None
        if status:
            try:
                job_status = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        jobs = job_queue.get_jobs(status=job_status, limit=limit)
        job_data = [job.to_dict() for job in jobs]
        
        return {
            "success": True,
            "data": {
                "jobs": job_data,
                "total": len(job_data),
                "running": len(job_queue.get_running_jobs())
            }
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get a specific job by ID."""
    try:
        job = job_queue.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "data": job.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel a running job."""
    try:
        success = await job_queue.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or not running")
        
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "status": "cancelled"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status."""
    try:
        status = scraper_scheduler.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/scheduler/start")
async def start_scheduler() -> Dict[str, Any]:
    """Start the scraper scheduler."""
    try:
        await scraper_scheduler.start()
        return {
            "success": True,
            "data": {
                "message": "Scheduler started successfully",
                "status": "running"
            }
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/scheduler/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the scraper scheduler."""
    try:
        await scraper_scheduler.stop()
        return {
            "success": True,
            "data": {
                "message": "Scheduler stopped successfully",
                "status": "stopped"
            }
        }
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/configs")
async def get_scraper_configs() -> Dict[str, Any]:
    """Get scraper configurations."""
    try:
        configs = await scraper_service.get_scraper_configs()
        return {
            "success": True,
            "data": configs
        }
    except Exception as e:
        logger.error(f"Error getting scraper configs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/configs/{scraper_id}")
async def update_scraper_config(
    scraper_id: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Update scraper configuration."""
    try:
        success = await scraper_service.update_scraper_config(scraper_id, config)
        if not success:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        return {
            "success": True,
            "data": {
                "message": f"Configuration updated for {scraper_id}",
                "scraper_id": scraper_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scraper config {scraper_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def scraper_health_check() -> Dict[str, Any]:
    """Health check for scraper services."""
    try:
        # Check scheduler status
        scheduler_status = scraper_scheduler.get_status()
        
        # Check job queue status
        running_jobs = len(job_queue.get_running_jobs())
        total_jobs = len(job_queue.get_jobs())
        
        # Check scraper status
        scraper_status = await scraper_service.get_scraper_status()
        
        health_status = {
            "scheduler": {
                "running": scheduler_status["running"],
                "initialized": scheduler_status["initialized"]
            },
            "job_queue": {
                "running_jobs": running_jobs,
                "total_jobs": total_jobs
            },
            "scrapers": {
                "total": len(scraper_status),
                "running": len([s for s in scraper_status.values() if s["status"] == "running"]),
                "failed": len([s for s in scraper_status.values() if s["status"] == "failed"])
            }
        }
        
        return {
            "success": True,
            "data": health_status
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 