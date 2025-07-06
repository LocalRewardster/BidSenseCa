import asyncio
import argparse
from typing import List, Dict

from loguru import logger

# Import new scrapers
from .canadabuys import CanadaBuysScraper
from .ontario_portal import OntarioPortalScraper
from .apc import APCScraper
from .bcbid import BCBidScraper
from .manitoba import ManitobaScraper
from .saskatchewan import SaskatchewanScraper
from .quebec import QuebecScraper


class ScraperRunner:
    """Runner for executing scrapers."""
    
    def __init__(self):
        self.scrapers = {
            "canadabuys": CanadaBuysScraper,
            "ontario": OntarioPortalScraper,
            "apc": APCScraper,
            "bcbid": BCBidScraper,
            "manitoba": ManitobaScraper,
            "saskatchewan": SaskatchewanScraper,
            "quebec": QuebecScraper,
        }
    
    async def run_scraper(self, scraper_name: str, limit: int = None) -> int:
        """Run a specific scraper."""
        if scraper_name not in self.scrapers:
            logger.error(f"Unknown scraper: {scraper_name}")
            return 0
        
        scraper_class = self.scrapers[scraper_name]
        
        try:
            async with scraper_class() as scraper:
                count = await scraper.run(limit=limit)
                logger.info(f"{scraper_name} scraper completed: {count} tenders saved")
                return count
        except Exception as e:
            logger.error(f"Error running {scraper_name} scraper: {e}")
            return 0
    
    async def run_all_scrapers(self, limit: int = None) -> Dict[str, int]:
        """Run all available scrapers."""
        results = {}
        
        for scraper_name in self.scrapers:
            logger.info(f"Starting {scraper_name} scraper")
            count = await self.run_scraper(scraper_name, limit)
            results[scraper_name] = count
        
        total = sum(results.values())
        logger.info(f"All scrapers completed. Total tenders saved: {total}")
        
        return results


async def main():
    """Main function to run scrapers."""
    parser = argparse.ArgumentParser(description="BidSense Scrapers")
    parser.add_argument(
        "--scraper", 
        choices=["canadabuys", "ontario", "apc", "bcbid", "manitoba", "saskatchewan", "quebec", "all"], 
        default="all",
        help="Scraper to run"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=None,
        help="Limit number of tenders to scrape"
    )
    parser.add_argument(
        "--headless", 
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logger.add(
        "logs/scraper.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    runner = ScraperRunner()
    
    if args.scraper == "all":
        results = await runner.run_all_scrapers(limit=args.limit)
        for scraper, count in results.items():
            print(f"{scraper}: {count} tenders")
    else:
        count = await runner.run_scraper(args.scraper, limit=args.limit)
        print(f"{args.scraper}: {count} tenders")


if __name__ == "__main__":
    asyncio.run(main()) 