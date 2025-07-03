import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper


class CanadaBuysScraper(BaseScraper):
    """Scraper for CanadaBuys tender opportunities."""
    
    def __init__(self):
        super().__init__(source_name="canadabuys")
        self.name = "canadabuys"
        self.base_url = "https://canadabuys.canada.ca"
        self.search_url = "https://canadabuys.canada.ca/en/tender-opportunities"
    
    def get_search_url(self) -> str:
        """Get the search URL for tender opportunities."""
        return self.search_url
    
    def parse_search_results(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse search results page to extract tender links."""
        results = []
        
        # Look for opportunity items in search results
        opportunity_items = soup.find_all('div', class_='opportunity-item')
        
        for item in opportunity_items:
            try:
                # Extract title and link
                title_elem = item.find('h3')
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                url = link_elem.get('href', '')
                
                # Extract metadata
                meta_div = item.find('div', class_='opportunity-meta')
                reference = ""
                organization = ""
                closing_date = ""
                
                if meta_div:
                    ref_elem = meta_div.find('span', class_='reference')
                    if ref_elem:
                        reference = ref_elem.get_text(strip=True)
                    
                    org_elem = meta_div.find('span', class_='organization')
                    if org_elem:
                        organization = org_elem.get_text(strip=True)
                    
                    date_elem = meta_div.find('span', class_='closing-date')
                    if date_elem:
                        closing_date = date_elem.get_text(strip=True)
                
                # Extract description
                desc_div = item.find('div', class_='opportunity-description')
                description = desc_div.get_text(strip=True) if desc_div else ""
                
                results.append({
                    'title': title,
                    'url': url,
                    'reference': reference,
                    'organization': organization,
                    'closing_date': closing_date,
                    'description': description
                })
                
            except Exception as e:
                logger.warning(f"Error parsing opportunity item: {e}")
                continue
        
        return results
    
    def parse_tender_details(self, soup: BeautifulSoup, url: str) -> Dict:
        """Parse tender detail page to extract full information."""
        details = {
            'title': '',
            'reference': '',
            'organization': '',
            'closing_date': '',
            'contract_value': '',
            'description': '',
            'contact_name': '',
            'contact_email': '',
            'contact_phone': '',
            'source_url': url
        }
        
        try:
            # Extract title
            title_elem = soup.find('h1')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # Extract information from opportunity-info section
            info_div = soup.find('div', class_='opportunity-info')
            if info_div:
                # Reference
                ref_elem = info_div.find('div', class_='reference')
                if ref_elem:
                    details['reference'] = ref_elem.get_text(strip=True).replace('Reference:', '').strip()
                
                # Organization
                org_elem = info_div.find('div', class_='organization')
                if org_elem:
                    details['organization'] = org_elem.get_text(strip=True).replace('Organization:', '').strip()
                
                # Closing date
                date_elem = info_div.find('div', class_='closing-date')
                if date_elem:
                    date_text = date_elem.get_text(strip=True).replace('Closing Date:', '').strip()
                    details['closing_date'] = self.parse_date(date_text)
                
                # Contract value
                value_elem = info_div.find('div', class_='contract-value')
                if value_elem:
                    value_text = value_elem.get_text(strip=True)
                    details['contract_value'] = self.extract_contract_value(value_text)
                
                # Description
                desc_elem = info_div.find('div', class_='description')
                if desc_elem:
                    details['description'] = desc_elem.get_text(strip=True)
                
                # Contact information
                contact_info = self.extract_contact_info(info_div)
                details.update(contact_info)
            
        except Exception as e:
            logger.error(f"Error parsing tender details: {e}")
        
        return details
    
    def parse_date(self, date_text: str) -> str:
        """Parse date in various formats to ISO format."""
        if not date_text:
            return ""
        
        # Remove common prefixes
        date_text = re.sub(r'^(Closing Date|Date|Deadline):\s*', '', date_text, flags=re.IGNORECASE)
        date_text = date_text.strip()
        
        # Try different date formats
        date_formats = [
            "%B %d, %Y",  # December 31, 2024
            "%b %d, %Y",  # Dec 31, 2024
            "%d/%m/%Y",   # 31/12/2024
            "%Y-%m-%d",   # 2024-12-31
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
            r'Contract Value:\s*([^\n]+)',
            r'Estimated Value:\s*([^\n]+)',
            r'Budget:\s*([^\n]+)',
            r'Value:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extract contact information from the page."""
        contact_info = {
            'contact_name': '',
            'contact_email': '',
            'contact_phone': ''
        }
        
        try:
            contact_div = soup.find('div', class_='contact-info')
            if not contact_div:
                return contact_info
            
            # Contact name
            name_elem = contact_div.find('div', class_='contact-name')
            if name_elem:
                name_text = name_elem.get_text(strip=True)
                contact_info['contact_name'] = re.sub(r'^Contact:\s*', '', name_text, flags=re.IGNORECASE)
            
            # Contact email
            email_elem = contact_div.find('div', class_='contact-email')
            if email_elem:
                email_text = email_elem.get_text(strip=True)
                contact_info['contact_email'] = re.sub(r'^Email:\s*', '', email_text, flags=re.IGNORECASE)
            
            # Contact phone
            phone_elem = contact_div.find('div', class_='contact-phone')
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True)
                contact_info['contact_phone'] = re.sub(r'^Phone:\s*', '', phone_text, flags=re.IGNORECASE)
        
        except Exception as e:
            logger.warning(f"Error extracting contact info: {e}")
        
        return contact_info
    
    async def get_page(self, url: str) -> Optional[str]:
        """Get page content using Playwright."""
        try:
            success = await self.safe_navigate(url)
            if success:
                return await self.page.content()
            return None
        except Exception as e:
            logger.error(f"Error getting page {url}: {e}")
            return None
    
    def parse_tender(self, raw_data: Any) -> Dict[str, Any]:
        """Parse raw tender data into standardized format."""
        # This method is required by the base class but not used in our implementation
        # We handle parsing in parse_tender_details instead
        if isinstance(raw_data, dict):
            return raw_data
        return {}
    
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape tenders from CanadaBuys."""
        try:
            # Get search page
            search_url = self.get_search_url()
            search_html = await self.get_page(search_url)
            
            if not search_html:
                logger.error("Failed to get search page")
                return []
            
            # Parse search results
            soup = BeautifulSoup(search_html, 'html.parser')
            opportunities = self.parse_search_results(soup)
            
            if not opportunities:
                logger.info("No opportunities found on search page")
                return []
            
            # Apply limit
            if limit:
                opportunities = opportunities[:limit]
            
            logger.info(f"Found {len(opportunities)} opportunities to process")
            
            # Process each opportunity
            tenders = []
            for opportunity in opportunities:
                try:
                    # Get detail page
                    detail_url = urljoin(self.base_url, opportunity['url'])
                    detail_html = await self.get_page(detail_url)
                    
                    if not detail_html:
                        logger.warning(f"Failed to get detail page for {detail_url}")
                        continue
                    
                    # Parse details
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    tender_data = self.parse_tender_details(detail_soup, detail_url)
                    
                    # Merge with search data
                    tender_data.update(opportunity)
                    
                    # Add external_id for deduplication
                    tender_data['external_id'] = opportunity.get('reference', '') or opportunity.get('url', '')
                    
                    tenders.append(tender_data)
                    logger.info(f"Parsed tender: {tender_data.get('title', 'Unknown')}")
                
                except Exception as e:
                    logger.error(f"Error processing opportunity {opportunity.get('url', 'Unknown')}: {e}")
                    continue
            
            return tenders
        
        except Exception as e:
            logger.error(f"Error scraping CanadaBuys: {e}")
            return []


async def main():
    """Main function for running CanadaBuys scraper directly."""
    import asyncio
    
    # Configure logging
    logger.add(
        "logs/canadabuys.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    async with CanadaBuysScraper() as scraper:
        count = await scraper.run(limit=10)
        print(f"CanadaBuys: {count} tenders saved")


if __name__ == "__main__":
    asyncio.run(main()) 