import asyncio
import re
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger
import httpx
import aiohttp

from .base import BaseScraper

# Import AI province detection service
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))
from app.services.ai_province_service import ai_province_service


class CanadaBuysScraper(BaseScraper):
    """Scraper for CanadaBuys tender opportunities with rich metadata extraction."""
    
    # Canadian provinces and territories mapping
    JURISDICTIONS = {
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
        'YT': 'Yukon',
        'FEDERAL': 'Federal'
    }
    
    # Keywords that indicate federal jurisdiction
    FEDERAL_KEYWORDS = [
        'government of canada', 'canada', 'federal', 'department of', 'ministry of',
        'parks canada', 'transport canada', 'health canada', 'public works',
        'defence', 'national defence', 'dnd', 'rcmp', 'cbsa', 'cbs', 'csis',
        'correctional service', 'veterans affairs', 'indigenous services',
        'crown corporation', 'canada post', 'via rail', 'atomic energy'
    ]
    
    def __init__(self):
        super().__init__(source_name="canadabuys")
        self.name = "canadabuys"
        self.base_url = "https://canadabuys.canada.ca"
        self.search_url = "https://canadabuys.canada.ca/en/tender-opportunities"
        # CanadaBuys Open Procurement API endpoint (if available)
        self.api_base_url = "https://api.canadabuys.canada.ca"
        self.max_retries = 3
        self.retry_delay = 1  # Base delay in seconds
    
    def get_search_url(self) -> str:
        """Get the search URL for tender opportunities."""
        return self.search_url
    
    async def detect_province_ai(self, tender_data: Dict[str, Any]) -> str:
        """
        Detect province using AI analysis instead of rule-based patterns.
        
        Args:
            tender_data: Dictionary containing tender information
            
        Returns:
            Province code (e.g., 'NS', 'ON', 'BC')
        """
        try:
            result = await ai_province_service.detect_province(tender_data)
            
            # Log the AI reasoning for debugging
            self.logger.info(f"AI Province Detection - {tender_data.get('title', 'Unknown')[:50]}...")
            self.logger.info(f"  → {result.province} (confidence: {result.confidence:.2f})")
            self.logger.info(f"  → Reasoning: {result.reasoning}")
            
            return result.province
            
        except Exception as e:
            self.logger.error(f"AI province detection failed: {e}")
            # Fallback to rule-based detection
            return self.detect_jurisdiction(tender_data.get('organization', ''), tender_data.get('title', ''))

    def detect_jurisdiction(self, organization: str, title: str) -> str:
        """
        Legacy rule-based jurisdiction detection (kept as fallback).
        
        Args:
            organization: Organization name
            title: Tender title
            
        Returns:
            Jurisdiction code
        """
        # Combine organization and title for analysis
        combined_text = f"{organization} {title}".lower()
        
        # Jurisdiction patterns (simplified - AI is now primary)
        jurisdiction_patterns = {
            'BC': ['british columbia', 'bc', 'vancouver', 'victoria', 'burnaby', 'richmond', 'surrey'],
            'AB': ['alberta', 'ab', 'calgary', 'edmonton', 'alberta health services'],
            'SK': ['saskatchewan', 'sk', 'saskatoon', 'regina'],
            'MB': ['manitoba', 'mb', 'winnipeg'],
            'ON': ['ontario', 'on', 'ont', 'toronto', 'ottawa', 'hamilton', 'london'],
            'QC': ['quebec', 'qc', 'montreal', 'quebec city'],
            'NB': ['new brunswick', 'nb', 'fredericton', 'saint john'],
            'NS': ['nova scotia', 'ns', 'halifax', 'halifax regional municipality'],
            'PE': ['prince edward island', 'pei', 'pe', 'charlottetown'],
            'NL': ['newfoundland', 'nl', 'st. john\'s', 'labrador'],
            'NT': ['northwest territories', 'nt', 'yellowknife'],
            'NU': ['nunavut', 'nu', 'iqaluit'],
            'YT': ['yukon', 'yt', 'whitehorse']
        }
        
        # Check for jurisdiction patterns
        for jurisdiction, patterns in jurisdiction_patterns.items():
            if any(pattern in combined_text for pattern in patterns):
                return jurisdiction
        
        # Default to Ontario if no match found
        return 'ON'
    
    async def parse_search_results_ai(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse search results using AI province detection.
        
        Args:
            soup: BeautifulSoup object of the search results page
            
        Returns:
            List of tender dictionaries with AI-detected provinces
        """
        results = []
        
        # Find all tender result rows
        tender_rows = soup.find_all('tr', class_='searchResultsRow')
        
        for row in tender_rows:
            try:
                # Extract basic tender information
                title_cell = row.find('td', class_='searchResultsTitle')
                if not title_cell:
                    continue
                
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                url = urljoin(self.base_url, title_link.get('href', ''))
                
                # Extract additional information
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                category = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                organization = cells[2].get_text(strip=True) if len(cells) > 2 else ''
                open_date = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                closing_date = cells[4].get_text(strip=True) if len(cells) > 4 else ''
                
                # Prepare tender data for AI analysis
                tender_data = {
                    'title': title,
                    'organization': organization,
                    'category': category,
                    'url': url
                }
                
                # Use AI to detect province
                province = await self.detect_province_ai(tender_data)
                
                results.append({
                    'title': title,
                    'url': url,
                    'category': category,
                    'open_date': open_date,
                    'closing_date': closing_date,
                    'organization': organization,
                    'location': province,  # Map to location for database province field
                    'jurisdiction': province,
                    'jurisdiction_name': self.JURISDICTIONS.get(province, 'Unknown')
                })
                
            except Exception as e:
                self.logger.error(f"Error parsing tender row: {e}")
                continue
        
        return results
    
    async def fetch_tender_api_data(self, tender_id: str) -> Optional[Dict]:
        """Fetch tender data from CanadaBuys API if available."""
        try:
            # Extract tender ID from URL if it's a full URL
            if '/' in tender_id:
                tender_id = tender_id.split('/')[-1]
            
            # Try to fetch from API (this is a placeholder - actual API endpoint may differ)
            api_url = f"{self.api_base_url}/tenders/{tender_id}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched API data for tender {tender_id}")
                    return data
                else:
                    logger.warning(f"API request failed for tender {tender_id}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Error fetching API data for tender {tender_id}: {e}")
            return None
    
    def extract_documents_from_html(self, soup: BeautifulSoup) -> List[str]:
        """Extract document URLs from HTML page (PDF and DOCX only)."""
        documents = []
        try:
            # Look for common document link patterns - only PDF and DOCX
            document_selectors = [
                'a[href*=".pdf"]',
                'a[href*=".docx"]',
                'a[href*="attachment"]',
                'a[href*="document"]',
                'a[href*="file"]',
                '.document-link a',
                '.attachment-link a',
                '.file-download a'
            ]
            
            for selector in document_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    # Only include PDF and DOCX files
                    if href and any(ext in href.lower() for ext in ['.pdf', '.docx']):
                        # Make URL absolute if it's relative
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(self.base_url, href)
                        
                        if href not in documents:
                            documents.append(href)
            
            # Also look for download buttons or text that might indicate documents
            download_texts = soup.find_all(string=re.compile(r'download|attachment|document|file', re.IGNORECASE))
            for text_elem in download_texts:
                parent = text_elem.parent
                if parent and parent.name == 'a':
                    href = parent.get('href', '')
                    # Only include PDF and DOCX files
                    if href and any(ext in href.lower() for ext in ['.pdf', '.docx']):
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(self.base_url, href)
                        if href not in documents:
                            documents.append(href)
            
            logger.info(f"Extracted {len(documents)} document URLs from HTML (PDF/DOCX only)")
            return documents
            
        except Exception as e:
            logger.warning(f"Error extracting documents from HTML: {e}")
            return []
    
    def extract_summary_raw(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract raw summary text from the tender description."""
        try:
            # Look for description/summary sections
            summary_selectors = [
                '.tender-detail-description',
                '.field--name-body',
                '.description',
                '.summary',
                '.content',
                '[class*="description"]',
                '[class*="summary"]'
            ]
            
            for selector in summary_selectors:
                elem = soup.select_one(selector)
                if elem:
                    # Get text content and clean it up
                    text = elem.get_text(separator=' ', strip=True)
                    if text and len(text) > 50:  # Ensure it's substantial content
                        # Remove extra whitespace
                        text = re.sub(r'\s+', ' ', text).strip()
                        logger.info(f"Extracted summary_raw: {len(text)} characters")
                        return text
            
            # Fallback: look for any paragraph with substantial content
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 100:  # Substantial paragraph
                    text = re.sub(r'\s+', ' ', text).strip()
                    logger.info(f"Extracted summary_raw from paragraph: {len(text)} characters")
                    return text
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting summary_raw: {e}")
            return None
    
    def parse_tender_details(self, soup: BeautifulSoup, url: str) -> Dict:
        """Parse tender detail page to extract full information with rich metadata."""
        details = {
            'title': '',
            'reference': '',
            'organization': '',
            'closing_date': '',
            'contract_value': '',
            'description': '',
            'summary_raw': None,  # New field for raw summary
            'contact_name': '',
            'contact_email': '',
            'contact_phone': '',
            'documents_urls': [],  # New field for document URLs
            'original_url': url,   # New field for canonical URL
            'source_url': url,
            # New summary information fields
            'notice_type': None,
            'languages': None,
            'delivery_regions': None,
            'opportunity_region': None,
            'contract_duration': None,
            'procurement_method': None,
            'selection_criteria': None,
            'commodity_unspsc': None
        }
        
        try:
            # Extract external_id from URL
            # URL format: https://canadabuys.canada.ca/en/tender-opportunities/tender-notice/ws4767663936-doc4772445749
            # Extract the last part as external_id
            url_parts = url.split('/')
            if url_parts:
                details['external_id'] = url_parts[-1]
            
            # Extract title from h1
            title_elem = soup.find('h1')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # Extract solicitation number (reference)
            ref_elem = soup.find('div', class_='field--name-field-tender-solicitation-number')
            if ref_elem:
                ref_item = ref_elem.find('span', class_='field--item')
                if ref_item:
                    details['reference'] = ref_item.get_text(strip=True)
            
            # Extract organization from contact section
            org_elem = soup.find('div', class_='views-field-field-tender-contact-orgname')
            if org_elem:
                org_content = org_elem.find('div', class_='field-content')
                if org_content:
                    details['organization'] = org_content.get_text(strip=True)
            
            # If no organization found in contact section, try the general info
            if not details['organization']:
                org_elem = soup.find('div', class_='tender-contact__name-info')
                if org_elem:
                    # Look for organization text
                    org_text = org_elem.get_text()
                    if 'Organization' in org_text:
                        # Extract organization name after "Organization"
                        lines = org_text.split('\n')
                        for i, line in enumerate(lines):
                            if 'Organization' in line and i + 1 < len(lines):
                                details['organization'] = lines[i + 1].strip()
                                break
            
            # Extract closing date
            closing_elem = soup.find('div', class_='closing-date-field')
            if closing_elem:
                date_elem = closing_elem.find('span', class_='dateclass')
                time_elem = closing_elem.find('span', class_='timeclass')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    time_text = time_elem.get_text(strip=True) if time_elem else ""
                    details['closing_date'] = f"{date_text} {time_text}".strip()
            
            # Extract description
            desc_elem = soup.find('div', class_='tender-detail-description')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Extract raw summary (new field)
            details['summary_raw'] = self.extract_summary_raw(soup)
            
            # Extract document URLs (new field)
            details['documents_urls'] = self.extract_documents_from_html(soup)
            
            # Extract contact information
            contact_info = self.extract_contact_info(soup)
            details.update(contact_info)
            
            # Extract summary information
            summary_info = self.extract_summary_info(soup)
            details.update(summary_info)
            
            # Normalize empty strings to None for better database handling
            for key, value in details.items():
                if isinstance(value, str) and not value.strip():
                    details[key] = None
            
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
        """Extract contact information from the page with improved parsing."""
        contact_info = {
            'contact_name': None,
            'contact_email': None,
            'contact_phone': None
        }
        try:
            # Look for the specific CanadaBuys contact structure
            # Contact name
            contact_name_elem = soup.find('div', class_='field--name-field-tender-contact-contactname')
            if contact_name_elem:
                name_item = contact_name_elem.find('div', class_='field--item')
                if name_item:
                    contact_info['contact_name'] = name_item.get_text(strip=True)
            
            # Contact email
            contact_email_elem = soup.find('div', class_='field--name-field-tender-contact-email')
            if contact_email_elem:
                email_item = contact_email_elem.find('div', class_='field--item')
                if email_item:
                    contact_info['contact_email'] = email_item.get_text(strip=True)
            
            # Contact phone
            contact_phone_elem = soup.find('div', class_='field--name-field-tender-contact-phone')
            if contact_phone_elem:
                phone_item = contact_phone_elem.find('div', class_='field--item')
                if phone_item:
                    # Clean up phone number (remove formatting)
                    phone_text = phone_item.get_text(strip=True)
                    # Remove common formatting
                    phone_text = re.sub(r'[^\d\-\(\)\s\+]', '', phone_text)
                    contact_info['contact_phone'] = phone_text.strip()
            
            # Fallback: Look for any contact information in the page
            if not any(contact_info.values()):
                # Look for email links
                email_links = soup.find_all('a', href=lambda x: x and 'mailto:' in x)
                for link in email_links:
                    if not contact_info['contact_email']:
                        contact_info['contact_email'] = link.get('href', '').replace('mailto:', '')
                
                # Look for phone numbers in text
                phone_pattern = re.compile(r'[\d\-\(\)\s\+]{10,}')
                phone_elements = soup.find_all(string=phone_pattern)
                for elem in phone_elements:
                    phone_match = phone_pattern.search(elem)
                    if phone_match and not contact_info['contact_phone']:
                        contact_info['contact_phone'] = phone_match.group().strip()
            
            # Normalize empty strings to None
            for key, value in contact_info.items():
                if isinstance(value, str) and not value.strip():
                    contact_info[key] = None
                    
        except Exception as e:
            logger.warning(f"Error extracting contact info: {e}")
        return contact_info
    
    async def get_page_with_retry(self, url: str) -> Optional[str]:
        """Get page content using Playwright with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                success = await self.safe_navigate(url)
                if success:
                    # Wait for the table to appear (up to 10 seconds)
                    try:
                        await self.page.wait_for_selector('table.eps-table.views-table.views-view-table', timeout=10000)
                        logger.info("Found tender opportunities table")
                    except Exception as e:
                        logger.warning(f"Table not found after waiting: {e}")
                        # Save HTML for debugging
                        content = await self.page.content()
                        debug_filename = f"canadabuys_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                        with open(debug_filename, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Saved debug HTML to {debug_filename}")
                    
                    return await self.page.content()
                
                # If we get here, safe_navigate returned False
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Navigation failed, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error getting page {url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Retrying in {delay}s")
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to get page {url} after {self.max_retries} attempts")
        return None
    
    async def get_page(self, url: str) -> Optional[str]:
        """Get page content using Playwright (legacy method for backward compatibility)."""
        return await self.get_page_with_retry(url)
    
    def parse_tender(self, raw_data: Any) -> Dict[str, Any]:
        """Parse raw tender data into standardized format."""
        # This method is required by the base class but not used in our implementation
        # We handle parsing in parse_tender_details instead
        if isinstance(raw_data, dict):
            return raw_data
        return {}
    
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape tenders from CanadaBuys with rich metadata extraction."""
        try:
            # Get search page
            search_url = self.get_search_url()
            search_html = await self.get_page_with_retry(search_url)
            
            if not search_html:
                logger.error("Failed to get search page")
                return []
            
            # Parse search results
            soup = BeautifulSoup(search_html, 'html.parser')
            opportunities = await self.parse_search_results_ai(soup)
            
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
                    detail_html = await self.get_page_with_retry(detail_url)
                    
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
                    
                    # Ensure all new fields are present
                    if 'summary_raw' not in tender_data:
                        tender_data['summary_raw'] = None
                    if 'documents_urls' not in tender_data:
                        tender_data['documents_urls'] = []
                    if 'original_url' not in tender_data:
                        tender_data['original_url'] = detail_url
                    
                    tenders.append(tender_data)
                    logger.info(f"Parsed tender: {tender_data.get('title', 'Unknown')} with {len(tender_data.get('documents_urls', []))} documents")
                
                except Exception as e:
                    logger.error(f"Error processing opportunity {opportunity.get('url', 'Unknown')}: {e}")
                    continue
            
            return tenders
        
        except Exception as e:
            logger.error(f"Error scraping CanadaBuys: {e}")
            return []
    
    def extract_summary_info(self, soup: BeautifulSoup) -> Dict:
        """Extract summary information from the sidebar."""
        summary_info = {
            'notice_type': None,
            'languages': None,
            'delivery_regions': None,
            'opportunity_region': None,
            'contract_duration': None,
            'procurement_method': None,
            'selection_criteria': None,
            'commodity_unspsc': None
        }
        try:
            # Look for the summary information section
            summary_section = soup.find('section', class_='views-element-container')
            if not summary_section:
                return summary_info
            
            # Extract notice type
            notice_type_elem = summary_section.find('div', class_='views-field-field-tender-notice-type')
            if notice_type_elem:
                notice_item = notice_type_elem.find('div', class_='field--item')
                if notice_item:
                    summary_info['notice_type'] = notice_item.get_text(strip=True)
            
            # Extract languages
            languages_elem = summary_section.find('div', class_='views-field-field-tender-notice-languages')
            if languages_elem:
                languages_content = languages_elem.find('div', class_='field-content')
                if languages_content:
                    summary_info['languages'] = languages_content.get_text(strip=True)
            
            # Extract delivery regions
            delivery_regions_elem = summary_section.find('div', class_='views-field-field-tender-delivery-regions')
            if delivery_regions_elem:
                delivery_content = delivery_regions_elem.find('div', class_='field-content')
                if delivery_content:
                    # Get all region items
                    region_items = delivery_content.find_all('div', class_='field--item')
                    if region_items:
                        regions = [item.get_text(strip=True) for item in region_items]
                        summary_info['delivery_regions'] = ', '.join(regions)
            
            # Extract opportunity region
            opportunity_elem = summary_section.find('div', class_='views-field-field-tender-opportunity-regions')
            if opportunity_elem:
                opportunity_content = opportunity_elem.find('div', class_='field-content')
                if opportunity_content:
                    summary_info['opportunity_region'] = opportunity_content.get_text(strip=True)
            
            # Extract contract duration
            duration_elem = summary_section.find('div', class_='views-field-field-tender-contract-duration')
            if duration_elem:
                duration_content = duration_elem.find('div', class_='field-content')
                if duration_content:
                    summary_info['contract_duration'] = duration_content.get_text(strip=True)
            
            # Extract procurement method
            procurement_elem = summary_section.find('div', class_='views-field-field-tender-procurement-method')
            if procurement_elem:
                procurement_item = procurement_elem.find('div', class_='field--item')
                if procurement_item:
                    summary_info['procurement_method'] = procurement_item.get_text(strip=True)
            
            # Extract selection criteria
            selection_elem = summary_section.find('div', class_='views-field-field-tender-selection-criteria')
            if selection_elem:
                selection_item = selection_elem.find('div', class_='field--item')
                if selection_item:
                    summary_info['selection_criteria'] = selection_item.get_text(strip=True)
            
            # Extract commodity UNSPSC
            unspsc_elem = summary_section.find('div', class_='views-field-field-tender-unspsc')
            if unspsc_elem:
                unspsc_content = unspsc_elem.find('div', class_='field-content')
                if unspsc_content:
                    # Get UNSPSC links
                    unspsc_links = unspsc_content.find_all('a', class_='unspsc_link_clr')
                    if unspsc_links:
                        unspsc_items = []
                        for link in unspsc_links:
                            span = link.find('span', attrs={'aria-hidden': 'true'})
                            if span:
                                unspsc_items.append(span.get_text(strip=True))
                        summary_info['commodity_unspsc'] = ', '.join(unspsc_items)
            
            # Normalize empty strings to None
            for key, value in summary_info.items():
                if isinstance(value, str) and not value.strip():
                    summary_info[key] = None
                    
        except Exception as e:
            logger.warning(f"Error extracting summary info: {e}")
        return summary_info

    async def scrape_search_results(self, limit: int = 100) -> List[Dict]:
        """
        Scrape search results from CanadaBuys with AI province detection.
        
        Args:
            limit: Maximum number of opportunities to scrape
            
        Returns:
            List of tender dictionaries with AI-detected provinces
        """
        opportunities = []
        
        try:
            # Build search URL
            search_url = self.build_search_url(limit)
            self.logger.info(f"Scraping search results from: {search_url}")
            
            # Fetch search results
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch search results: {response.status}")
                        return opportunities
                    
                    search_html = await response.text()
            
            # Parse search results with AI province detection
            soup = BeautifulSoup(search_html, 'html.parser')
            opportunities = await self.parse_search_results_ai(soup)
            
            if not opportunities:
                self.logger.warning("No opportunities found in search results")
                return opportunities
            
            self.logger.info(f"Found {len(opportunities)} opportunities with AI province detection")
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error scraping search results: {e}")
            return opportunities


async def main():
    """Main function for running CanadaBuys scraper directly."""
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