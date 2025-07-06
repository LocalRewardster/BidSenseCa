"""Scraper management endpoints."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any

from app.models.scraper_job import ScraperJob, ScraperJobCreate, ScraperJobList, ScraperStatus
from app.services.scraper_service import scraper_service
from app.services.job_service import job_service
from app.services.scheduler_service import scheduler_service

router = APIRouter()


@router.get("/status", response_model=List[ScraperStatus])
async def get_scraper_status():
    """Get status of all scrapers."""
    try:
        return scraper_service.get_all_scraper_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scraper status: {str(e)}")


@router.get("/status/{scraper_name}", response_model=ScraperStatus)
async def get_scraper_status_by_name(scraper_name: str):
    """Get status of a specific scraper."""
    try:
        return scraper_service.get_scraper_status(scraper_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scraper status: {str(e)}")


@router.post("/run/{scraper_name}")
async def run_scraper(
    scraper_name: str,
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, description="Limit number of tenders to scrape")
):
    """Run a specific scraper."""
    try:
        # Create and start job in background
        job = await job_service.create_and_start_job(scraper_name, limit)
        
        return {
            "message": f"Started scraper {scraper_name}",
            "job_id": job.id,
            "status": job.status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scraper: {str(e)}")


@router.post("/run-all")
async def run_all_scrapers(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, description="Limit number of tenders per scraper")
):
    """Run all available scrapers."""
    try:
        job = await job_service.run_scheduled_jobs()
        
        return {
            "message": "Started all scrapers",
            "job_id": job.id,
            "status": job.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scrapers: {str(e)}")


@router.get("/jobs", response_model=ScraperJobList)
async def get_scraper_jobs(
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by job status")
):
    """Get list of scraper jobs."""
    try:
        from app.models.scraper_job import JobStatus
        
        job_status = None
        if status:
            try:
                job_status = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        result = job_service.get_jobs(limit, offset, job_status)
        
        return ScraperJobList(
            jobs=result["jobs"],
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=ScraperJob)
async def get_scraper_job(job_id: str):
    """Get a specific scraper job."""
    try:
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@router.post("/jobs/{job_id}/start")
async def start_scraper_job(job_id: str):
    """Start a pending scraper job."""
    try:
        success = await job_service.start_job(job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot start job")
        
        return {"message": "Job started successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")


@router.post("/jobs/{job_id}/cancel")
async def cancel_scraper_job(job_id: str):
    """Cancel a running scraper job."""
    try:
        success = await job_service.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel job")
        
        return {"message": "Job cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and configuration."""
    try:
        return scheduler_service.get_schedule_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the scheduler service."""
    try:
        await scheduler_service.start()
        return {"message": "Scheduler started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the scheduler service."""
    try:
        await scheduler_service.stop()
        return {"message": "Scheduler stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.put("/scheduler/schedule")
async def update_scheduler_schedule(schedule: Dict[str, str]):
    """Update the scheduler configuration."""
    try:
        scheduler_service.update_schedule(schedule)
        return {"message": "Schedule updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.post("/scheduler/run-now")
async def run_scheduler_now(scraper_name: str = "all"):
    """Run a scheduled job immediately."""
    try:
        job_id = await scheduler_service.run_now(scraper_name)
        return {
            "message": f"Started immediate job for {scraper_name}",
            "job_id": job_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run job: {str(e)}") 