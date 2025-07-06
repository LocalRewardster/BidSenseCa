"""
BC Bid source - legacy wrapper for the existing BC Bid scraper.
"""

import asyncio
from typing import Generator
from loguru import logger

from ..models.opportunity import Opportunity
from ..scrapers.bc_bid import BCBidScraper


async def stream_opportunities() -> Generator[Opportunity, None, None]:
    """
    Stream opportunities from BC Bid (legacy mode).
    
    Yields:
        Normalized Opportunity objects
    """
    logger.info("Using BC Bid source (legacy mode)")
    
    try:
        async with BCBidScraper() as scraper:
            # Get session
            if not await scraper.get_session():
                logger.error("Failed to establish BC Bid session")
                return
            
            # Fetch opportunities
            page = 1
            while True:
                page_results = await scraper.fetch_page(page)
                
                if not page_results:
                    logger.info(f"No more opportunities found at page {page}")
                    break
                
                # Convert to Opportunity objects
                for record in page_results:
                    try:
                        # Convert dictionary to Opportunity
                        opportunity = Opportunity(
                            id=record.get("external_id", record.get("id", "")),
                            title=record.get("title", "Unknown Title"),
                            summary=record.get("description", record.get("summary")),
                            close_date=record.get("closing_date"),
                            buyer=record.get("organization", record.get("buyer")),
                            docs_url=record.get("url", record.get("original_url")),
                            source="bcbid",
                            tags=record.get("category"),
                            document_urls=record.get("documents_urls"),
                            jurisdiction="BC",
                            raw_data=record
                        )
                        
                        yield opportunity
                        
                    except Exception as e:
                        logger.error(f"Error processing BC Bid opportunity: {e}")
                        continue
                
                page += 1
                
                # Limit to first few pages for testing
                if page > 3:
                    logger.info("Reached page limit for BC Bid")
                    break
                    
    except Exception as e:
        logger.error(f"Error in BC Bid source: {e}")
        return 