"""Scraper integration service for running scrapers and saving data."""

import asyncio
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from loguru import logger

from app.core.database import insert_tender, get_db
from app.models.scraper_job import ScraperJob, JobStatus


class ScraperService:
    """Service for managing scraper execution and data integration."""
    
    def __init__(self):
        self.scrapers_dir = Path(__file__).parent.parent.parent.parent / "scrapers"
        self.available_scrapers = [
            "canadabuys",
            "ontario", 
            "apc",
            "bcbid",
            "manitoba",
            "saskatchewan",
            "quebec"
        ]
    
    async def run_scraper(
        self, 
        scraper_name: str, 
        limit: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a specific scraper and return results."""
        
        if scraper_name not in self.available_scrapers:
            raise ValueError(f"Unknown scraper: {scraper_name}")
        
        logger.info(f"Starting scraper: {scraper_name}")
        
        # Build command
        cmd = [
            sys.executable, "-m", "poetry", "run", "python", "-m", "scrapers.runner",
            "--scraper", scraper_name
        ]
        
        if limit:
            cmd.extend(["--limit", str(limit)])
        
        if parameters:
            # Add any additional parameters
            for key, value in parameters.items():
                cmd.extend([f"--{key}", str(value)])
        
        try:
            # Change to scrapers directory
            original_cwd = os.getcwd()
            os.chdir(self.scrapers_dir)
            
            # Run scraper
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.scrapers_dir
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse output
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            # Extract tender count from output
            tender_count = 0
            for line in output.split('\n'):
                if f"{scraper_name}:" in line and "tenders" in line:
                    try:
                        tender_count = int(line.split(':')[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                    break
            
            success = process.returncode == 0
            
            return {
                "success": success,
                "tender_count": tender_count,
                "output": output,
                "error": error,
                "return_code": process.returncode
            }
            
        except Exception as e:
            logger.error(f"Error running scraper {scraper_name}: {e}")
            return {
                "success": False,
                "tender_count": 0,
                "output": "",
                "error": str(e),
                "return_code": -1
            }
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    async def run_all_scrapers(
        self, 
        limit: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run all available scrapers."""
        
        logger.info("Starting all scrapers")
        results = {}
        total_tenders = 0
        
        for scraper_name in self.available_scrapers:
            try:
                result = await self.run_scraper(scraper_name, limit, parameters)
                results[scraper_name] = result
                total_tenders += result.get("tender_count", 0)
                
                if result["success"]:
                    logger.info(f"{scraper_name}: {result['tender_count']} tenders")
                else:
                    logger.error(f"{scraper_name}: Failed - {result['error']}")
                    
            except Exception as e:
                logger.error(f"Error with scraper {scraper_name}: {e}")
                results[scraper_name] = {
                    "success": False,
                    "tender_count": 0,
                    "output": "",
                    "error": str(e),
                    "return_code": -1
                }
        
        return {
            "success": any(r["success"] for r in results.values()),
            "results": results,
            "total_tenders": total_tenders,
            "scrapers_run": len(results)
        }
    
    def get_scraper_status(self, scraper_name: str) -> Dict[str, Any]:
        """Get status information for a specific scraper."""
        
        if scraper_name not in self.available_scrapers:
            raise ValueError(f"Unknown scraper: {scraper_name}")
        
        # Check if scraper file exists
        scraper_file = self.scrapers_dir / "scrapers" / f"{scraper_name}.py"
        is_enabled = scraper_file.exists()
        
        # Get last run info from database (TODO: implement)
        last_run = None
        last_error = None
        total_tenders = 0
        
        return {
            "scraper_name": scraper_name,
            "is_enabled": is_enabled,
            "last_run": last_run,
            "last_error": last_error,
            "total_tenders": total_tenders,
            "avg_duration": None
        }
    
    def get_all_scraper_status(self) -> List[Dict[str, Any]]:
        """Get status for all scrapers."""
        return [self.get_scraper_status(name) for name in self.available_scrapers]
    
    async def save_tender_data(self, tender_data: Dict[str, Any]) -> bool:
        """Save tender data to database."""
        try:
            # Add timestamp
            tender_data["created_at"] = datetime.now(timezone.utc).isoformat()
            tender_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Insert into database
            result = insert_tender(tender_data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to save tender data: {e}")
            return False
    
    def get_tender_statistics(self) -> Dict[str, Any]:
        """Get tender statistics from database."""
        try:
            client = get_db()
            
            # Get total count
            total_result = client.table('tenders').select('id', count='exact').execute()
            total_tenders = total_result.count if hasattr(total_result, 'count') else 0
            
            # Get count by source
            sources_result = client.table('tenders').select('source_name').execute()
            source_counts = {}
            for tender in sources_result.data:
                source = tender.get('source_name', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            # Get recent tenders (last 7 days)
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            recent_result = client.table('tenders').select('id').gte('created_at', week_ago).execute()
            recent_tenders = len(recent_result.data)
            
            return {
                "total_tenders": total_tenders,
                "source_counts": source_counts,
                "recent_tenders": recent_tenders,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get tender statistics: {e}")
            return {
                "total_tenders": 0,
                "source_counts": {},
                "recent_tenders": 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }


# Global scraper service instance
scraper_service = ScraperService() 