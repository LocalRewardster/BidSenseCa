import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from loguru import logger

from .base import BaseScraper


class OntarioPortalScraper(BaseScraper):
    """Scraper for Ontario Portal tender opportunities via RSS feed."""
    
    def __init__(self):
        super().__init__(source_name="ontario_portal")
        self.name = "ontario_portal"
        self.feed_url = "https://ontariotenders.app.jaggaer.com/en_US/portal/rss"
    
    def parse_rss_feed(self, rss_content: str) -> List[Dict]:
        """Parse RSS feed to extract tender information."""
        tenders = []
        
        try:
            root = ET.fromstring(rss_content)
            channel = root.find('channel')
            
            if channel is None:
                logger.warning("No channel found in RSS feed")
                return tenders
            
            items = channel.findall('item')
            logger.info(f"Found {len(items)} items in RSS feed")
            
            for item in items:
                try:
                    tender_data = self.parse_rss_item(item)
                    if tender_data:
                        tenders.append(tender_data)
                        logger.debug(f"Successfully parsed tender: {tender_data.get('title', 'Unknown')}")
                    else:
                        logger.debug("Failed to parse RSS item - returned None")
                except Exception as e:
                    logger.warning(f"Error parsing RSS item: {e}")
                    continue
        
        except ET.ParseError as e:
            logger.error(f"Error parsing RSS feed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS feed: {e}")
        
        logger.info(f"Successfully parsed {len(tenders)} tenders from RSS feed")
        return tenders
    
    def parse_rss_item(self, item: ET.Element) -> Optional[Dict]:
        """Parse individual RSS item to extract tender data."""
        try:
            # Extract basic fields
            title_elem = item.find('title')
            link_elem = item.find('link')
            guid_elem = item.find('guid')
            pub_date_elem = item.find('pubDate')
            description_elem = item.find('description')
            
            if title_elem is None or link_elem is None:
                return None
            
            title = title_elem.text.strip() if title_elem.text else ""
            link = link_elem.text.strip() if link_elem.text else ""
            guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else ""
            pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else ""
            
            # Parse description HTML to extract additional fields
            description_html = description_elem.text if description_elem is not None and description_elem.text else ""
            additional_data = self.parse_description_html(description_html)
            
            tender_data = {
                'title': title,
                'source_url': link,
                'external_id': guid or link.split('/')[-1],
                'published_date': self.parse_date(pub_date),
                'reference': additional_data.get('reference', ''),
                'organization': additional_data.get('organization', ''),
                'closing_date': additional_data.get('closing_date', ''),
                'contract_value': additional_data.get('contract_value', ''),
                'description': additional_data.get('description', ''),
            }
            
            return tender_data
        
        except Exception as e:
            logger.warning(f"Error parsing RSS item: {e}")
            return None
    
    def parse_description_html(self, html_content: str) -> Dict:
        """Parse HTML description to extract tender details."""
        data = {
            'reference': '',
            'organization': '',
            'closing_date': '',
            'contract_value': '',
            'description': ''
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text()
            data['description'] = text_content
            
            # Look for specific patterns in the text
            lines = text_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Reference
                if line.startswith('Reference:'):
                    data['reference'] = line.replace('Reference:', '').strip()
                
                # Organization
                elif line.startswith('Organization:'):
                    data['organization'] = line.replace('Organization:', '').strip()
                
                # Closing Date
                elif line.startswith('Closing Date:'):
                    date_text = line.replace('Closing Date:', '').strip()
                    data['closing_date'] = self.parse_date(date_text)
                
                # Contract Value
                elif line.startswith('Value:'):
                    value_text = line.replace('Value:', '').strip()
                    data['contract_value'] = value_text  # Don't call extract_contract_value here
            
            # Also try to extract from the original HTML content
            if not data['contract_value']:
                # Look for value in HTML tags
                value_patterns = [
                    r'<p>Value:\s*([^<]+)</p>',
                    r'Value:\s*([^<\n]+)',
                ]
                
                for pattern in value_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        data['contract_value'] = match.group(1).strip()
                        break
        
        except Exception as e:
            logger.warning(f"Error parsing description HTML: {e}")
        
        return data
    
    def parse_date(self, date_text: str) -> str:
        """Parse date in various formats to ISO format."""
        if not date_text:
            return ""
        
        # Remove common prefixes
        date_text = re.sub(r'^(Closing Date|Date|Deadline|Published):\s*', '', date_text, flags=re.IGNORECASE)
        date_text = date_text.strip()
        
        # Try different date formats
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %Z",  # Wed, 01 May 2024 12:00:00 GMT
            "%Y-%m-%d",                   # 2024-06-15
            "%d/%m/%Y",                   # 15/06/2024
            "%B %d, %Y",                  # June 15, 2024
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_text, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If no format matches, return original
        return date_text
    
    def extract_contract_value(self, text: str) -> Optional[str]:
        """Extract contract value from text."""
        if not text:
            return None
        
        # Look for common patterns
        patterns = [
            r'Value:\s*([^\n]+)',
            r'Contract Value:\s*([^\n]+)',
            r'Estimated Value:\s*([^\n]+)',
            r'Budget:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def get_feed(self, url: str) -> Optional[str]:
        """Get RSS feed content using HTTP request."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Error getting RSS feed {url}: {e}")
            return None
    
    def parse_tender(self, raw_data: Any) -> Dict[str, Any]:
        """Parse raw tender data into standardized format."""
        if isinstance(raw_data, dict):
            return raw_data
        return {}
    
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape tenders from Ontario Portal RSS feed."""
        try:
            # Get RSS feed
            feed_content = await self.get_feed(self.feed_url)
            
            if not feed_content:
                logger.error("Failed to get RSS feed")
                return []
            
            # Parse RSS feed
            tenders = self.parse_rss_feed(feed_content)
            
            if not tenders:
                logger.info("No tenders found in RSS feed")
                return []
            
            # Apply limit
            if limit:
                tenders = tenders[:limit]
            
            logger.info(f"Found {len(tenders)} tenders to process")
            
            # Process tenders
            processed_tenders = []
            for tender in tenders:
                try:
                    # Add source and timestamp
                    tender['source'] = self.source_name
                    tender['scraped_at'] = datetime.now(timezone.utc).isoformat()
                    
                    processed_tenders.append(tender)
                    logger.info(f"Parsed tender: {tender.get('title', 'Unknown')}")
                
                except Exception as e:
                    logger.error(f"Error processing tender {tender.get('external_id', 'Unknown')}: {e}")
                    continue
            
            return processed_tenders
        
        except Exception as e:
            logger.error(f"Error scraping Ontario Portal: {e}")
            return []


async def main():
    """Main function for running Ontario Portal scraper directly."""
    import asyncio
    
    # Configure logging
    logger.add(
        "logs/ontario_portal.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    async with OntarioPortalScraper() as scraper:
        count = await scraper.run(limit=10)
        print(f"Ontario Portal: {count} tenders saved")


if __name__ == "__main__":
    asyncio.run(main()) 