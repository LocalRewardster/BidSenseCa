from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.api.v1.api import api_router
from app.services.scheduler import scraper_scheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="BidSense API",
        description="Canadian Contractor Bid-Intel SaaS API",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    @app.on_event("startup")
    async def startup_event():
        """Startup event handler."""
        logger.info("Starting BidSense API...")
        
        # Start the scraper scheduler in the background
        try:
            await scraper_scheduler.start()
            logger.info("Scraper scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scraper scheduler: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown event handler."""
        logger.info("Shutting down BidSense API...")
        
        # Stop the scraper scheduler
        try:
            await scraper_scheduler.stop()
            logger.info("Scraper scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scraper scheduler: {e}")
    
    @app.get("/")
    async def root():
        """Root endpoint with basic info."""
        return {
            "message": "BidSense API",
            "version": "0.1.0",
            "status": "running",
            "environment": settings.environment,
            "alpha_mode": settings.alpha_mode,
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        # Get scheduler status
        scheduler_status = scraper_scheduler.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scheduler": {
                "running": scheduler_status["running"],
                "initialized": scheduler_status["initialized"]
            }
        }
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler."""
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.debug else "Something went wrong",
            },
        )
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    ) 