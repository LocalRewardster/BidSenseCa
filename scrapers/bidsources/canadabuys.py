"""
CanadaBuys bid source - fetches BC provincial opportunities from public JSON API.
"""

import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Generator
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

# Use absolute imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.opportunity import Opportunity


class CanadaBuysSource:
    """CanadaBuys bid source for BC provincial opportunities."""
    
    BASE_URL = "https://canadabuys.canada.ca/api/notices/search"
    PAGE_SIZE = 200
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "BidSense.ca/1.0 (https://bidsense.ca)",
                "Accept": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_page(self, page: int) -> List[Dict[str, Any]]:
        """
        Fetch a page of opportunities from CanadaBuys API.
        
        Args:
            page: Page number (0-based)
            
        Returns:
            List of opportunity records from the 'content' array
        """
        try:
            # Build URL with query parameters
            params = {
                "jurisdiction": "BC",
                "status": "open", 
                "size": self.PAGE_SIZE,
                "page": page
            }
            
            logger.info(f"Fetching CanadaBuys page {page} with params: {params}")
            
            response = await self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the 'content' array
            opportunities = data.get("content", [])
            
            logger.info(f"Retrieved {len(opportunities)} opportunities from page {page}")
            logger.debug(f"Page {page} metadata: {data.get('page')}, size: {data.get('size')}, total: {data.get('totalElements')}")
            
            return opportunities
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching page {page}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}")
            raise
    
    def normalize(self, record: Dict[str, Any]) -> Opportunity:
        """
        Convert raw CanadaBuys JSON record to Opportunity dataclass.
        
        Args:
            record: Raw JSON record from CanadaBuys API
            
        Returns:
            Normalized Opportunity object
        """
        try:
            # Extract basic fields
            notice_id = record.get("noticeId", "")
            title = record.get("title", "")
            summary = record.get("summary", "")
            organization = record.get("organization", "")
            jurisdiction = record.get("jurisdiction", "")
            
            # Parse closing date
            closing_date_str = record.get("closingDate", "")
            closing_date = None
            if closing_date_str:
                try:
                    # Parse ISO 8601 datetime
                    closing_date = datetime.fromisoformat(
                        closing_date_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    logger.warning(f"Could not parse closing date: {closing_date_str}")
            
            # Build tags from procurement category and GSIN
            tags = []
            procurement_category = record.get("procurementCategory") or record.get("categorieApprovisionnement")
            if procurement_category:
                tags.append(procurement_category)
            
            gsin = record.get("gsin")
            if gsin:
                tags.append(f"GSIN: {gsin}")
            
            # Build documents URL
            docs_url = f"https://canadabuys.canada.ca/en/tender-opportunities/{notice_id}"
            
            # Extract document URLs if available
            document_urls = []
            documents = record.get("documents", [])
            for doc in documents:
                doc_url = doc.get("url")
                if doc_url:
                    document_urls.append(doc_url)
            
            # Create Opportunity object
            opportunity = Opportunity(
                id=notice_id,
                title=title,
                summary=summary,
                close_date=closing_date,
                buyer=organization,
                docs_url=docs_url,
                source="canadabuys",
                tags=", ".join(tags) if tags else None,
                document_urls=document_urls if document_urls else None,
                jurisdiction=jurisdiction,
                # Additional fields from CanadaBuys
                raw_data=record
            )
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error normalizing record {record.get('noticeId', 'unknown')}: {e}")
            raise
    
    async def stream_opportunities(self) -> Generator[Opportunity, None, None]:
        """
        Stream all BC opportunities from CanadaBuys API.
        
        Yields:
            Normalized Opportunity objects
        """
        page = 0
        
        while True:
            try:
                # Fetch page of opportunities
                records = await self.fetch_page(page)
                
                # If no records returned, we've reached the end
                if not records:
                    logger.info(f"No more opportunities found at page {page}")
                    break
                
                # Normalize and yield each opportunity
                for record in records:
                    try:
                        opportunity = self.normalize(record)
                        yield opportunity
                    except Exception as e:
                        logger.error(f"Error processing opportunity {record.get('noticeId', 'unknown')}: {e}")
                        continue
                
                # Move to next page
                page += 1
                
                # Brief pause between pages to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
        
        logger.info(f"Completed streaming opportunities from CanadaBuys (processed {page} pages)")


async def stream_opportunities() -> Generator[Opportunity, None, None]:
    """
    Convenience function to stream opportunities from CanadaBuys.
    
    Yields:
        Normalized Opportunity objects
    """
    async with CanadaBuysSource() as source:
        async for opportunity in source.stream_opportunities():
            yield opportunity


if __name__ == "__main__":
    """Test the CanadaBuys source."""
    async def test():
        async with CanadaBuysSource() as source:
            # Test fetching first page
            opportunities = await source.fetch_page(0)
            print(f"Found {len(opportunities)} opportunities on first page")
            
            if opportunities:
                # Test normalization
                opportunity = source.normalize(opportunities[0])
                print(f"Normalized opportunity: {opportunity.title}")
                print(f"  ID: {opportunity.id}")
                print(f"  Buyer: {opportunity.buyer}")
                print(f"  Close date: {opportunity.close_date}")
                print(f"  Source: {opportunity.source}")
    
    asyncio.run(test()) 