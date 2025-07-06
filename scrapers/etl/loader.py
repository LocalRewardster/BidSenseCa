"""
ETL loader for tender opportunities with environment-based source selection.
"""

import os
import asyncio
from typing import Generator, Optional
from loguru import logger

from ..models.opportunity import Opportunity


async def stream_opportunities(jurisdiction: Optional[str] = None) -> Generator[Opportunity, None, None]:
    """
    Stream opportunities based on BIDSOURCE environment variable with optional jurisdiction filtering.
    
    Environment Variables:
        BIDSOURCE: Source to use ("canadabuys" or "bcbid", defaults to "canadabuys")
    
    Args:
        jurisdiction: Optional jurisdiction filter (e.g., "BC", "ON", "FEDERAL")
    
    Yields:
        Normalized Opportunity objects
    """
    bidsource = os.getenv("BIDSOURCE", "canadabuys").lower()
    
    logger.info(f"Using bid source: {bidsource}")
    if jurisdiction:
        logger.info(f"Filtering for jurisdiction: {jurisdiction}")
    
    if bidsource == "canadabuys":
        # Use the working HTML-based CanadaBuys scraper
        from ..scrapers.canadabuys import CanadaBuysScraper
        
        async with CanadaBuysScraper() as scraper:
            # Get opportunities from the scraper
            opportunities = await scraper.scrape_tenders(limit=100)  # Increased limit for better coverage
            
            # Convert to Opportunity objects with jurisdiction filtering
            for opp in opportunities:
                try:
                    # Apply jurisdiction filter if specified
                    if jurisdiction and opp.get('jurisdiction') != jurisdiction:
                        continue
                    
                    # Create Opportunity object from scraper data
                    opportunity = Opportunity(
                        id=opp.get('external_id', f"canadabuys_{opp.get('title', '').replace(' ', '_')}"),
                        title=opp.get('title', ''),
                        summary=opp.get('description', ''),
                        close_date=opp.get('closing_date'),
                        buyer=opp.get('organization', ''),
                        docs_url=opp.get('original_url', ''),
                        source="canadabuys",
                        tags=opp.get('category', ''),
                        document_urls=opp.get('documents_urls'),
                        jurisdiction=opp.get('jurisdiction', 'FEDERAL'),  # Use detected jurisdiction
                        raw_data=opp
                    )
                    yield opportunity
                except Exception as e:
                    logger.error(f"Error converting opportunity {opp.get('title', 'unknown')}: {e}")
                    continue
    else:
        from ..bidsources.bcbid import stream_opportunities as bcbid_stream
        async for opportunity in bcbid_stream():
            yield opportunity


async def load_opportunities_to_database(limit: int = None, jurisdiction: Optional[str] = None) -> int:
    """
    Load opportunities to database with optional jurisdiction filtering.
    
    Args:
        limit: Maximum number of opportunities to load
        jurisdiction: Optional jurisdiction filter
        
    Returns:
        Number of opportunities loaded
    """
    from ..database import save_opportunity
    
    count = 0
    
    try:
        async for opportunity in stream_opportunities(jurisdiction=jurisdiction):
            if limit and count >= limit:
                break
                
            try:
                # Convert to dictionary format for database
                opportunity_dict = opportunity.to_dict()
                
                # Save to database
                success = await save_opportunity(opportunity_dict)
                
                if success:
                    count += 1
                    logger.info(f"Saved opportunity {count}: {opportunity.title} ({opportunity.jurisdiction})")
                else:
                    logger.warning(f"Failed to save opportunity: {opportunity.title}")
                    
            except Exception as e:
                logger.error(f"Error processing opportunity {opportunity.id}: {e}")
                continue
                
        logger.info(f"Completed loading {count} opportunities to database")
        return count
        
    except Exception as e:
        logger.error(f"Error in load_opportunities_to_database: {e}")
        return count


def get_available_jurisdictions() -> dict:
    """
    Get list of available jurisdictions for filtering.
    
    Returns:
        Dictionary mapping jurisdiction codes to names
    """
    return {
        'FEDERAL': 'Federal',
        'AB': 'Alberta',
        'BC': 'British Columbia',
        'MB': 'Manitoba',
        'NB': 'New Brunswick',
        'NL': 'Newfoundland and Labrador',
        'NS': 'Nova Scotia',
        'NT': 'Northwest Territories',
        'NU': 'Nunavut',
        'ON': 'Ontario',
        'PE': 'Prince Edward Island',
        'QC': 'Quebec',
        'SK': 'Saskatchewan',
        'YT': 'Yukon'
    }


if __name__ == "__main__":
    """Test the ETL loader."""
    async def test():
        logger.info("Testing ETL loader...")
        
        # Test streaming with jurisdiction filter
        jurisdictions_to_test = [None, "BC", "ON", "FEDERAL"]
        
        for jurisdiction in jurisdictions_to_test:
            logger.info(f"\nTesting jurisdiction filter: {jurisdiction or 'ALL'}")
            count = 0
            async for opportunity in stream_opportunities(jurisdiction=jurisdiction):
                print(f"Opportunity {count + 1}: {opportunity.title}")
                print(f"  Source: {opportunity.source}")
                print(f"  Buyer: {opportunity.buyer}")
                print(f"  Jurisdiction: {opportunity.jurisdiction}")
                print(f"  Close date: {opportunity.close_date}")
                print()
                
                count += 1
                if count >= 3:  # Limit to first 3 for testing
                    break
            
            print(f"Found {count} opportunities for jurisdiction: {jurisdiction or 'ALL'}")
    
    asyncio.run(test()) 