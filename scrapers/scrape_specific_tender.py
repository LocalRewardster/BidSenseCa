import asyncio
import sys
from scrapers.canadabuys import CanadaBuysScraper

async def scrape_specific_tender(url: str):
    """Scrape a specific tender by URL and save to database."""
    async with CanadaBuysScraper() as scraper:
        print(f"Scraping tender: {url}")
        
        # Get the page content
        html = await scraper.get_page_with_retry(url)
        if html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse the tender details
            tender_data = scraper.parse_tender_details(soup, url)
            
            # Save to database
            await scraper.save_tender(tender_data)
            print(f"Successfully saved tender: {tender_data.get('title', 'Unknown')}")
        else:
            print("Failed to get page content")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scrape_specific_tender.py <tender_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(scrape_specific_tender(url)) 