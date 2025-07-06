import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from loguru import logger

from .base import BaseScraper


class QuebecScraper(BaseScraper):
    """Scraper for Quebec tender opportunities."""
    
    def __init__(self):
        super().__init__(source_name="quebec")
        self.name = "quebec"
        self.base_url = "https://quebec.bidsandtenders.ca"
        self.search_url = "https://quebec.bidsandtenders.ca/Module/Tenders/fr/Search"
    
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
                    details['reference'] = ref_elem.get_text(strip=True).replace('Référence:', '').strip()
                
                # Organization
                org_elem = info_div.find('div', class_='organization')
                if org_elem:
                    details['organization'] = org_elem.get_text(strip=True).replace('Organisation:', '').strip()
                
                # Closing date
                date_elem = info_div.find('div', class_='closing-date')
                if date_elem:
                    date_text = date_elem.get_text(strip=True).replace('Date de fermeture:', '').strip()
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
        date_text = re.sub(r'^(Date de fermeture|Date|Échéance):\s*', '', date_text, flags=re.IGNORECASE)
        date_text = date_text.strip()
        
        # French month mappings
        french_months = {
            'janvier': '01', 'jan.': '01',
            'février': '02', 'fév.': '02',
            'mars': '03', 'mar.': '03',
            'avril': '04', 'avr.': '04',
            'mai': '05',
            'juin': '06',
            'juillet': '07', 'juil.': '07',
            'août': '08', 'aoû.': '08',
            'septembre': '09', 'sept.': '09',
            'octobre': '10', 'oct.': '10',
            'novembre': '11', 'nov.': '11',
            'décembre': '12', 'déc.': '12'
        }
        
        # Try to parse French date format: "15 octobre 2024" or "15 oct. 2024"
        for month_name, month_num in french_months.items():
            if month_name in date_text.lower():
                # Replace French month with number - handle both full and abbreviated forms
                if month_name.endswith('.'):
                    # For abbreviated forms like "oct.", use a different pattern
                    pattern = rf'\b{month_name[:-1]}\.'
                else:
                    # For full forms like "octobre", use word boundary
                    pattern = rf'\b{month_name}\b'
                
                date_with_number = re.sub(
                    pattern, 
                    month_num, 
                    date_text.lower(), 
                    flags=re.IGNORECASE
                )
                # Extract day, month, and year - handle both "15 10 2024" and "15 10 2024" formats
                match = re.search(r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})', date_with_number)
                if match:
                    day, month, year = match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try different date formats
        date_formats = [
            "%d/%m/%Y",   # 15/10/2024
            "%Y-%m-%d",   # 2024-10-15
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
        
        # Look for common patterns in French
        patterns = [
            r'Valeur du contrat:\s*([^\n]+)',
            r'Valeur estimée:\s*([^\n]+)',
            r'Budget:\s*([^\n]+)',
            r'Valeur:\s*([^\n]+)',
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
                contact_info['contact_email'] = re.sub(r'^Courriel:\s*', '', email_text, flags=re.IGNORECASE)
            
            # Contact phone
            phone_elem = contact_div.find('div', class_='contact-phone')
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True)
                contact_info['contact_phone'] = re.sub(r'^Téléphone:\s*', '', phone_text, flags=re.IGNORECASE)
        
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
        if isinstance(raw_data, dict):
            return raw_data
        return {}
    
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape tenders from Quebec."""
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
            logger.error(f"Error scraping Quebec: {e}")
            return []


async def main():
    """Main function for running Quebec scraper directly."""
    import asyncio
    
    # Configure logging
    logger.add(
        "logs/quebec.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    async with QuebecScraper() as scraper:
        count = await scraper.run(limit=10)
        print(f"Quebec: {count} tenders saved")


if __name__ == "__main__":
    asyncio.run(main()) 