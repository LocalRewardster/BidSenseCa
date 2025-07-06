import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.supabase: Client = create_client(
            settings.supabase_url, 
            settings.supabase_service_role_key
        )
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.request_count = 0
        self.last_request_time = 0
        
        # Configure logging
        logger.add(
            f"logs/{source_name}.log",
            rotation="1 day",
            retention="7 days",
            level=settings.log_level
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def setup_browser(self):
        """Setup Playwright browser and context."""
        playwright = await async_playwright().start()
        
        # Launch browser
        if settings.browser_type == "chromium":
            self.browser = await playwright.chromium.launch(
                headless=settings.headless
            )
        elif settings.browser_type == "firefox":
            self.browser = await playwright.firefox.launch(
                headless=settings.headless
            )
        elif settings.browser_type == "webkit":
            self.browser = await playwright.webkit.launch(
                headless=settings.headless
            )
        else:
            raise ValueError(f"Unsupported browser type: {settings.browser_type}")
        
        # Create context with proxy if available
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if settings.apify_api_token:
            # TODO: Implement Apify proxy integration
            pass
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(settings.scraper_timeout_seconds * 1000)
        
        logger.info(f"Browser setup complete for {self.source_name}")
    
    async def cleanup(self):
        """Cleanup browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info(f"Browser cleanup complete for {self.source_name}")
    
    async def rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Calculate minimum delay between requests
        min_delay = 60.0 / settings.requests_per_minute
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def safe_navigate(self, url: str) -> bool:
        """Safely navigate to a URL with retry logic."""
        try:
            await self.rate_limit()
            response = await self.page.goto(url, wait_until="networkidle")
            return response and response.status == 200
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def safe_click(self, selector: str) -> bool:
        """Safely click an element with retry logic."""
        try:
            await self.page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")
            raise
    
    async def save_tender(self, tender_data: Dict[str, Any]) -> bool:
        """Save tender data to Supabase."""
        try:
            # Use the new column names that were added in the migration
            db_tender_data = {
                "source_name": self.source_name,  # Use the new source_name column
                "external_id": tender_data.get("external_id"),
                "title": tender_data.get("title"),
                "organization": tender_data.get("organization"),  # Use the new organization column
                "province": tender_data.get("location"),  # Map location to province
                "naics": tender_data.get("naics"),
                "closing_date": tender_data.get("closing_date"),  # Use the new closing_date column
                "description": tender_data.get("description"),  # Use the new description column
                "summary_raw": tender_data.get("summary_raw"),  # New field for raw summary
                "documents_urls": tender_data.get("documents_urls"),  # New field for document URLs
                "original_url": tender_data.get("original_url"),  # New field for canonical URL
                "tags_ai": tender_data.get("tags_ai"),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "category": tender_data.get("category"),  # Use the new category column
                "reference": tender_data.get("reference"),  # Use the new reference column
                "contact_name": tender_data.get("contact_name"),  # Use the new contact_name column
                "contact_email": tender_data.get("contact_email"),  # Use the new contact_email column
                "contact_phone": tender_data.get("contact_phone"),  # Use the new contact_phone column
                "source_url": tender_data.get("source_url"),  # Use the new source_url column
                "contract_value": tender_data.get("contract_value"),  # Use the new contract_value column
                # Summary information fields
                "notice_type": tender_data.get("notice_type"),
                "languages": tender_data.get("languages"),
                "delivery_regions": tender_data.get("delivery_regions"),
                "opportunity_region": tender_data.get("opportunity_region"),
                "contract_duration": tender_data.get("contract_duration"),
                "procurement_method": tender_data.get("procurement_method"),
                "selection_criteria": tender_data.get("selection_criteria"),
                "commodity_unspsc": tender_data.get("commodity_unspsc"),
            }
            
            # Remove None values
            db_tender_data = {k: v for k, v in db_tender_data.items() if v is not None}
            
            # Check if tender already exists
            existing = self.supabase.table("tenders").select("id").eq("external_id", tender_data.get("external_id")).eq("source_name", self.source_name).execute()
            
            if existing.data:
                # Update existing tender with new rich metadata fields
                tender_id = existing.data[0]["id"]
                
                # Only update fields that have new data (rich metadata fields)
                update_data = {}
                rich_metadata_fields = [
                    "summary_raw", "documents_urls", "original_url", 
                    "contact_name", "contact_email", "contact_phone",
                    "notice_type", "languages", "delivery_regions", 
                    "opportunity_region", "contract_duration", 
                    "procurement_method", "selection_criteria", "commodity_unspsc"
                ]
                
                for field in rich_metadata_fields:
                    if field in db_tender_data and db_tender_data[field] is not None:
                        update_data[field] = db_tender_data[field]
                
                # Also update scraped_at timestamp
                update_data["scraped_at"] = db_tender_data["scraped_at"]
                
                if update_data:
                    response = self.supabase.table("tenders").update(update_data).eq("id", tender_id).execute()
                    if response.data:
                        logger.info(f"Updated tender {tender_data.get('external_id')} with rich metadata")
                        return True
                    else:
                        logger.error(f"Failed to update tender {tender_data.get('external_id')}")
                        return False
                else:
                    logger.info(f"Tender {tender_data.get('external_id')} already exists, no new data to update")
                    return True
            
            # Insert new tender
            response = self.supabase.table("tenders").insert(db_tender_data).execute()
            
            if response.data:
                logger.info(f"Saved tender: {tender_data.get('title', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to save tender: {tender_data.get('title', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving tender: {e}")
            return False
    
    @abstractmethod
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape tenders from the source. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def parse_tender(self, raw_data: Any) -> Dict[str, Any]:
        """Parse raw tender data into standardized format. Must be implemented by subclasses."""
        pass
    
    async def run(self, limit: Optional[int] = None) -> int:
        """Run the scraper and return number of tenders scraped."""
        logger.info(f"Starting {self.source_name} scraper")
        
        try:
            tenders = await self.scrape_tenders(limit)
            saved_count = 0
            
            for tender in tenders:
                if await self.save_tender(tender):
                    saved_count += 1
            
            logger.info(f"{self.source_name} scraper completed: {saved_count} tenders saved")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error in {self.source_name} scraper: {e}")
            raise 