"""Scraper job models for BidSense API."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Scraper job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScraperJobBase(BaseModel):
    """Base scraper job model."""
    scraper_name: str = Field(..., description="Name of the scraper to run")
    limit: Optional[int] = Field(None, description="Limit number of tenders to scrape")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional scraper parameters")


class ScraperJobCreate(ScraperJobBase):
    """Model for creating a new scraper job."""
    pass


class ScraperJob(ScraperJobBase):
    """Complete scraper job model with database fields."""
    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current job status")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    tenders_scraped: int = Field(0, description="Number of tenders scraped")
    tenders_saved: int = Field(0, description="Number of tenders saved")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    logs: Optional[str] = Field(None, description="Job execution logs")
    created_at: datetime = Field(..., description="Job creation timestamp")
    
    class Config:
        from_attributes = True


class ScraperJobList(BaseModel):
    """Model for scraper job list responses."""
    jobs: list[ScraperJob] = Field(..., description="List of scraper jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Number of results returned")
    offset: int = Field(..., description="Number of results skipped")


class ScraperStatus(BaseModel):
    """Model for scraper status information."""
    scraper_name: str = Field(..., description="Scraper name")
    is_enabled: bool = Field(..., description="Whether scraper is enabled")
    last_run: Optional[datetime] = Field(None, description="Last successful run")
    last_error: Optional[str] = Field(None, description="Last error message")
    total_tenders: int = Field(0, description="Total tenders from this scraper")
    avg_duration: Optional[float] = Field(None, description="Average run duration in seconds") 