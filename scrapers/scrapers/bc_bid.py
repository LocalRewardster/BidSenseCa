import asyncio
import json
import time
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
from loguru import logger
import httpx
from playwright.async_api import Page
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup
import hashlib

from .base import BaseScraper


class BCBidScraper(BaseScraper):
    """
    Scraper for BC Bid tender opportunities using Playwright for authentication and HTML scraping.
    
    IMPORTANT: BC Bid implements robust anti-bot measures that prevent automated access to real opportunities.
    This scraper can establish sessions and handle authentication, but real opportunities require valid credentials.
    Without authentication, only navigation links are accessible.
    
    Status: Limited functionality due to anti-bot protection
    - ✅ Session establishment works
    - ✅ Authentication flow works (with valid credentials)
    - ❌ Public access blocked by browser check
    - ❌ Real opportunities require authentication
    
    For more details, see: BC_BID_ANALYSIS_SUMMARY.md
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__(source_name="bcbid")
        self.name = "bcbid"
        self.base_url = "https://www.bcbid.gov.bc.ca"
        self.login_url = "https://www.bcbid.gov.bc.ca/page.aspx/en/usr/login"
        self.opportunities_url = "https://www.bcbid.gov.bc.ca/page.aspx/en/rfp/request_browse_public"
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None
        self.session_cookies: Optional[Dict[str, str]] = None
        self.max_retries = 3
        self.retry_delay = 1  # Base delay in seconds
        
        # Concurrency settings
        self.max_concurrent_workers = 2
        self.semaphore = asyncio.Semaphore(self.max_concurrent_workers)
        
        # Status tracking
        self.authenticated = False
        self.browser_check_detected = False
    
    async def get_session(self) -> bool:
        """
        Use Playwright to obtain session cookies and authenticate if credentials provided.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("Getting BC Bid session with Playwright...")
            
            # Navigate to the main page to establish session
            success = await self.safe_navigate(self.base_url)
            if not success:
                logger.error("Failed to navigate to BC Bid main page")
                return False
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            # Get session cookies
            cookies = await self.context.cookies()
            self.session_cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
            logger.info(f"Obtained {len(self.session_cookies)} session cookies")
            
            # Get ASP.NET viewstate and other form data
            viewstate = await self.page.query_selector('input[name="__VIEWSTATE"]')
            if viewstate:
                self.session_token = await viewstate.get_attribute("value")
                logger.info("Obtained ASP.NET ViewState")
            
            # If credentials provided, attempt login
            if self.username and self.password:
                login_success = await self.authenticate()
                if not login_success:
                    logger.warning("Authentication failed, continuing with public access")
                    return True  # Continue with public access
                else:
                    logger.info("Successfully authenticated to BC Bid")
                    return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error getting BC Bid session: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """
        Authenticate to BC Bid using provided credentials.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("Attempting to authenticate to BC Bid...")
            
            # First navigate to the login page
            login_url = "https://www.bcbid.gov.bc.ca/page.aspx/en/ctn/links_public_browse"
            success = await self.safe_navigate(login_url)
            if not success:
                logger.error("Failed to navigate to login page")
                return False
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            # Click on "Login with a Business or Basic BCeID" link
            bceid_link = await self.page.query_selector('a[href*="logon7.gov.bc.ca"]')
            if not bceid_link:
                logger.error("Could not find BCeID login link")
                return False
            
            # Click the BCeID login link
            await bceid_link.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Wait for the login form to appear
            await self.page.wait_for_selector('input[name="user"]', timeout=10000)
            await self.page.wait_for_selector('input[name="password"]', timeout=10000)
            
            # Fill in username and password
            await self.page.fill('input[name="user"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            
            # Submit the form
            submit_button = await self.page.query_selector('input[type="submit"][name="btnSubmit"]')
            if not submit_button:
                logger.error("Could not find submit button")
                return False
            
            await submit_button.click()
            
            # Wait for navigation after login
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful by looking for error messages or successful redirect
            current_url = self.page.url
            
            # Check for error messages
            error_elements = await self.page.query_selector_all('.bg-error:not(.hidden)')
            if error_elements:
                error_text = await error_elements[0].text_content()
                logger.error(f"Login failed with error: {error_text}")
                return False
            
            # Check if we're still on the login page (failed login)
            if "logon7.gov.bc.ca" in current_url:
                logger.error("Still on login page after submission - authentication failed")
                return False
            
            # Check if we've been redirected to BC Bid (successful login)
            if "bcbid.gov.bc.ca" in current_url:
                logger.info("Successfully authenticated to BC Bid")
                self.authenticated = True
                return True
            
            logger.warning(f"Unexpected URL after login: {current_url}")
            return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_page(self, page_no: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch a page of tender opportunities by scraping HTML.
        Returns list of tender records or None if failed.
        
        Note: BC Bid blocks public access with browser checks. This method will only
        return navigation links unless authenticated access is available.
        """
        try:
            await self.rate_limit()
            
            # Try different BC Bid public pages that might contain opportunities
            if page_no == 1:
                # Start with the main opportunities page
                url = "https://www.bcbid.gov.bc.ca/page.aspx/en/rfp/request_browse_public"
            else:
                # For pagination, we'll need to handle ASP.NET postbacks
                url = "https://www.bcbid.gov.bc.ca/page.aspx/en/rfp/request_browse_public"
            
            logger.info(f"Fetching opportunities page {page_no} from {url}")
            
            # Navigate to the page
            success = await self.safe_navigate(url)
            if not success:
                logger.error(f"Failed to navigate to opportunities page")
                return None
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            # Check if we got redirected to a browser check page
            current_url = self.page.url
            if "browser_check" in current_url:
                self.browser_check_detected = True
                logger.warning("⚠️ BC Bid browser check detected - public access is blocked")
                logger.info("BC Bid implements anti-bot measures that prevent automated access to opportunities")
                logger.info("Only navigation links are available without authentication")
                
                # Return navigation links instead of opportunities
                page_content = await self.page.content()
                soup = BeautifulSoup(page_content, 'html.parser')
                navigation_links = self.extract_navigation_links(soup)
                
                if navigation_links:
                    logger.info(f"Found {len(navigation_links)} navigation links")
                    return navigation_links
                else:
                    logger.warning("No navigation links found on browser check page")
                    return []
            
            # If we got past the browser check (unlikely), try to extract opportunities
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Extract opportunities from the page
            opportunities = self.parse_opportunities_page(soup)
            
            if opportunities:
                logger.info(f"Successfully extracted {len(opportunities)} opportunities from page {page_no}")
                return opportunities
            else:
                logger.warning(f"No opportunities found on page {page_no}")
                return []
                    
        except Exception as e:
            logger.error(f"Error fetching page {page_no}: {e}")
            return None
    
    def parse_opportunities_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse opportunities from the BC Bid HTML page.
        Returns list of opportunity records.
        """
        opportunities = []
        
        try:
            # Look for opportunity tables or lists
            # BC Bid likely uses tables or divs with specific classes
            opportunity_selectors = [
                'table tr',  # Table rows
                '.opportunity',  # Opportunity class
                '.tender',  # Tender class
                '.bid',  # Bid class
                '[data-opportunity]',  # Data attributes
                '.result-item',  # Result items
                '.listing-item',  # Listing items
                '.row',  # Bootstrap rows
                'tr[onclick]',  # Clickable table rows
                '.grid-row',  # Grid rows
                '.content-row',  # Content rows
            ]
            
            for selector in opportunity_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        opportunity = self.parse_opportunity_element(element)
                        if opportunity:
                            opportunities.append(opportunity)
                    
                    if opportunities:
                        break
            
            # If no structured data found, try to extract from any links
            if not opportunities:
                links = soup.find_all('a', href=True)
                opportunity_links = []
                
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for links that might be opportunities
                    # Filter out navigation and non-opportunity links
                    if any(keyword in href.lower() for keyword in ['opportunity', 'tender', 'bid', 'rfp', 'request', 'detail']) and \
                       not any(nav_keyword in text.lower() for nav_keyword in ['opportunities', 'login', 'home', 'navigation', 'menu', 'accessibility', 'copyright']):
                        
                        # Try to extract opportunity ID from URL
                        opp_id = self.extract_opportunity_id(href)
                        
                        opportunity_links.append({
                            'url': urljoin(self.base_url, href),
                            'title': text,
                            'href': href,
                            'external_id': opp_id
                        })
                
                logger.info(f"Found {len(opportunity_links)} potential opportunity links")
                
                # Convert links to opportunity records
                for link in opportunity_links:
                    opportunities.append({
                        'title': link['title'],
                        'url': link['url'],
                        'href': link['href'],
                        'external_id': link['external_id'],
                        'source': 'link_extraction'
                    })
            
            # If still no opportunities, try to extract from text content
            if not opportunities:
                opportunities = self.extract_opportunities_from_text(soup)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error parsing opportunities page: {e}")
            return []
    
    def extract_opportunities_from_text(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract opportunities from text content when structured data is not available.
        """
        opportunities = []
        
        try:
            # Look for text patterns that might indicate opportunities
            text_content = soup.get_text()
            
            # Split text into lines and look for opportunity-like patterns
            lines = text_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for patterns that might indicate opportunities
                opportunity_patterns = [
                    r'RFP\s+#?\d+',  # RFP #123
                    r'Request\s+for\s+Proposal',  # Request for Proposal
                    r'Tender\s+#?\d+',  # Tender #123
                    r'Bid\s+#?\d+',  # Bid #123
                    r'Opportunity\s+#?\d+',  # Opportunity #123
                    r'Contract\s+#?\d+',  # Contract #123
                    r'\d{4}-\d{2}-\d{2}',  # Date patterns
                    r'Closing:\s*\d{4}-\d{2}-\d{2}',  # Closing dates
                    r'Deadline:\s*\d{4}-\d{2}-\d{2}',  # Deadlines
                ]
                
                for pattern in opportunity_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # This line might contain opportunity info
                        opportunity = {
                            'title': line[:100] + '...' if len(line) > 100 else line,
                            'description': line,
                            'external_id': hashlib.md5(line.encode()).hexdigest()[:12],
                            'source': 'text_extraction'
                        }
                        opportunities.append(opportunity)
                        break
            
            logger.info(f"Extracted {len(opportunities)} opportunities from text content")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error extracting opportunities from text: {e}")
            return []
    
    def extract_opportunity_id(self, href: str) -> Optional[str]:
        """
        Extract opportunity ID from URL.
        """
        try:
            # Look for common patterns in BC Bid URLs
            patterns = [
                r'id=([A-Z0-9\-]+)',  # id=ABC123
                r'opportunity=([A-Z0-9\-]+)',  # opportunity=ABC123
                r'tender=([A-Z0-9\-]+)',  # tender=ABC123
                r'bid=([A-Z0-9\-]+)',  # bid=ABC123
                r'rfp=([A-Z0-9\-]+)',  # rfp=ABC123
                r'request=([A-Z0-9\-]+)',  # request=ABC123
                r'/([A-Z0-9]{6,})',  # /ABC123DEF
                r'([A-Z]{2,3}\d{4,})',  # BC2024001
                r'detail=([A-Z0-9\-]+)',  # detail=ABC123
            ]
            
            for pattern in patterns:
                match = re.search(pattern, href, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            # If no pattern matches, use a hash of the URL as fallback
            return hashlib.md5(href.encode()).hexdigest()[:12]
            
        except Exception as e:
            logger.debug(f"Error extracting opportunity ID from {href}: {e}")
            return None
    
    def parse_opportunity_element(self, element) -> Optional[Dict[str, Any]]:
        """
        Parse a single opportunity element from the HTML.
        Returns opportunity data or None if parsing failed.
        """
        try:
            opportunity = {}
            
            # Extract title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find('a')
            if title_elem:
                title = title_elem.get_text(strip=True)
                # Skip navigation titles
                if any(nav_keyword in title.lower() for nav_keyword in ['opportunities', 'login', 'home', 'navigation', 'menu', 'accessibility']):
                    return None
                opportunity['title'] = title
            
            # Extract link
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                opportunity['url'] = urljoin(self.base_url, href)
                opportunity['href'] = href
                opportunity['external_id'] = self.extract_opportunity_id(href)
            
            # Extract other fields from text content
            text_content = element.get_text()
            
            # Look for common patterns in the text
            patterns = {
                'reference': r'reference[:\s]+([A-Z0-9\-]+)',
                'organization': r'organization[:\s]+([^,\n]+)',
                'closing_date': r'closing[:\s]+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
                'deadline': r'deadline[:\s]+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
                'location': r'location[:\s]+([^,\n]+)',
                'category': r'category[:\s]+([^,\n]+)',
                'buyer': r'buyer[:\s]+([^,\n]+)',
                'contract_value': r'value[:\s]+([^,\n]+)',
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    opportunity[field] = match.group(1).strip()
            
            # If we have at least a title or URL, consider it valid
            if opportunity.get('title') or opportunity.get('url'):
                return opportunity
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing opportunity element: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_detail(self, opp_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific opportunity by scraping its detail page.
        Returns opportunity details or None if failed.
        """
        try:
            await self.rate_limit()
            
            logger.info(f"Fetching details for opportunity: {opp_url}")
            
            # Navigate to the detail page
            success = await self.safe_navigate(opp_url)
            if not success:
                logger.error(f"Failed to navigate to opportunity detail page")
                return None
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            # Parse the detail page
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Extract detailed information
            details = self.parse_opportunity_detail(soup, opp_url)
            
            if details:
                logger.info(f"Successfully extracted details for opportunity")
                return details
            else:
                logger.warning(f"No details found for opportunity")
                return None
                    
        except Exception as e:
            logger.error(f"Error fetching details for opportunity {opp_url}: {e}")
            return None
    
    def parse_opportunity_detail(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse detailed information from an opportunity detail page.
        Returns detailed opportunity data or None if parsing failed.
        """
        try:
            details = {
                'url': url,
                'source_url': url
            }
            
            # Extract title
            title_elem = soup.find(['h1', 'h2', 'h3']) or soup.find('title')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # Extract description/summary
            content_selectors = [
                '.content',
                '.description', 
                '.summary',
                '.details',
                'main',
                'article',
                '.opportunity-details',
                '.tender-details'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    details['description'] = content_elem.get_text(strip=True)
                    break
            
            # Extract specific fields using patterns
            text_content = soup.get_text()
            
            # Look for specific field patterns
            field_patterns = {
                'reference': r'reference[:\s]+([A-Z0-9\-]+)',
                'organization': r'organization[:\s]+([^,\n]+)',
                'buyer': r'buyer[:\s]+([^,\n]+)',
                'closing_date': r'closing[:\s]+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
                'deadline': r'deadline[:\s]+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
                'location': r'location[:\s]+([^,\n]+)',
                'province': r'province[:\s]+([^,\n]+)',
                'category': r'category[:\s]+([^,\n]+)',
                'contact_name': r'contact[:\s]+([^,\n]+)',
                'contact_email': r'email[:\s]+([^\s\n]+)',
                'contact_phone': r'phone[:\s]+([^\s\n]+)',
                'contract_value': r'value[:\s]+([^,\n]+)',
                'budget': r'budget[:\s]+([^,\n]+)',
            }
            
            for field, pattern in field_patterns.items():
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    details[field] = match.group(1).strip()
            
            # Extract any links to documents
            document_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                    document_links.append(urljoin(url, href))
            
            if document_links:
                details['documents_urls'] = document_links
            
            return details if details.get('title') or details.get('description') else None
            
        except Exception as e:
            logger.error(f"Error parsing opportunity detail: {e}")
            return None
    
    async def save_tender(self, record: Dict[str, Any]) -> bool:
        """
        Save tender record to database using the base class method.
        Returns True if successful, False otherwise.
        """
        try:
            # Transform the scraped record to the expected format
            tender_data = self.transform_scraped_record(record)
            
            # Use the base class save method
            success = await super().save_tender(tender_data)
            
            if success:
                logger.info(f"Successfully saved tender: {tender_data.get('title', 'Unknown')}")
            else:
                logger.warning(f"Failed to save tender: {tender_data.get('title', 'Unknown')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving tender: {e}")
            return False
    
    def transform_scraped_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform scraped record to the expected database format.
        """
        # Ensure we have a valid external_id
        external_id = record.get("reference") or record.get("id") or record.get("external_id")
        if not external_id:
            # Generate a fallback ID from the URL
            url = record.get("url") or record.get("source_url")
            if url:
                external_id = hashlib.md5(url.encode()).hexdigest()[:12]
            else:
                external_id = "bcbid_unknown"
        
        return {
            "external_id": external_id,
            "title": record.get("title", "Unknown Title"),
            "organization": record.get("organization") or record.get("buyer"),
            "location": record.get("location") or record.get("province"),
            "naics": record.get("naics"),
            "closing_date": record.get("closing_date") or record.get("deadline"),
            "description": record.get("description"),
            "summary_raw": record.get("description"),
            "documents_urls": record.get("documents_urls"),
            "original_url": record.get("url") or record.get("source_url"),
            "category": record.get("category"),
            "reference": record.get("reference"),
            "contact_name": record.get("contact_name"),
            "contact_email": record.get("contact_email"),
            "contact_phone": record.get("contact_phone"),
            "source_url": record.get("source_url") or record.get("url"),
            "contract_value": record.get("contract_value") or record.get("budget"),
            # Additional fields
            "notice_type": record.get("notice_type"),
            "languages": record.get("languages"),
            "delivery_regions": record.get("delivery_regions"),
            "opportunity_region": record.get("location") or record.get("province"),
            "contract_duration": record.get("contract_duration"),
            "procurement_method": record.get("procurement_method"),
            "selection_criteria": record.get("selection_criteria"),
            "commodity_unspsc": record.get("commodity_unspsc"),
        }
    
    async def scrape_tenders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main scraping method that orchestrates the entire process.
        Returns list of scraped tender records.
        
        Note: Due to BC Bid's anti-bot measures, this method will primarily return
        navigation links unless authenticated access is available.
        """
        scraped_tenders = []
        
        try:
            # Step 1: Get session with Playwright
            if not await self.get_session():
                logger.error("Failed to establish session, aborting scrape")
                return scraped_tenders
            
            # Step 2: Check authentication status
            if self.authenticated:
                logger.info("✅ Using authenticated session for BC Bid")
            else:
                logger.warning("⚠️ Using public access - limited to navigation links only")
                logger.info("BC Bid blocks automated access to real opportunities")
                logger.info("Consider providing valid credentials for full access")
            
            # Step 3: Fetch first page of opportunities
            logger.info("Fetching first page of opportunities...")
            page_results = await self.fetch_page(1)
            
            if not page_results:
                logger.warning("No results found on first page")
                return scraped_tenders
            
            # Step 4: Check what type of results we got
            if self.browser_check_detected:
                logger.info(f"Found {len(page_results)} navigation links (browser check detected)")
                logger.info("These are navigation links, not actual opportunities")
                
                # Convert navigation links to tender format for database storage
                for link in page_results:
                    tender_data = self.transform_scraped_record(link)
                    success = await self.save_tender(tender_data)
                    if success:
                        scraped_tenders.append(tender_data)
                
                logger.info(f"Saved {len(scraped_tenders)} navigation links to database")
                return scraped_tenders
            
            # Step 5: Process actual opportunities (if any)
            logger.info(f"Found {len(page_results)} opportunities on first page")
            
            # Process each opportunity with concurrency control
            tasks = []
            for opportunity in page_results:
                # Apply limit if specified
                if limit and len(scraped_tenders) >= limit:
                    break
                
                task = self.process_opportunity(opportunity)
                tasks.append(task)
            
            # Execute tasks with concurrency control
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing opportunity: {result}")
                    elif result:
                        scraped_tenders.append(result)
            
            logger.info(f"Scraping complete. Total tenders scraped: {len(scraped_tenders)}")
            
            # Provide summary based on results
            if self.browser_check_detected:
                logger.info("📋 Summary: BC Bid browser check detected - only navigation links available")
                logger.info("💡 To access real opportunities, provide valid BC Bid credentials")
            elif scraped_tenders:
                logger.info("✅ Summary: Successfully scraped opportunities from BC Bid")
            else:
                logger.info("⚠️ Summary: No opportunities found - BC Bid may require authentication")
            
            return scraped_tenders
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return scraped_tenders
    
    async def process_opportunity(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single opportunity with concurrency control.
        Returns processed tender data or None if failed.
        """
        async with self.semaphore:
            try:
                # Get opportunity URL
                opp_url = opportunity.get("url")
                if not opp_url:
                    logger.warning("No URL found in opportunity record")
                    return None
                
                # Fetch detailed information
                details = await self.fetch_detail(opp_url)
                if not details:
                    logger.warning(f"Failed to fetch details for opportunity {opp_url}")
                    return None
                
                # Merge basic info with details
                full_record = {**opportunity, **details}
                
                # Save to database
                success = await self.save_tender(full_record)
                if not success:
                    logger.warning(f"Failed to save opportunity {opp_url}")
                    return None
                
                return full_record
                
            except Exception as e:
                logger.error(f"Error processing opportunity: {e}")
                return None
    
    def parse_tender(self, raw_data: Any) -> Dict[str, Any]:
        """
        Parse raw tender data (not used in this implementation as we use HTML scraping).
        Returns parsed tender data.
        """
        # This method is not used in the HTML scraping approach
        # but kept for compatibility with base class
        if isinstance(raw_data, dict):
            return self.transform_scraped_record(raw_data)
        return {}
    
    def extract_navigation_links(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract navigation links when opportunities are not accessible.
        Returns list of navigation link records.
        """
        navigation_links = []
        
        try:
            # Look for navigation links that might be opportunities
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Filter for potential opportunity-related links
                if any(keyword in href.lower() or keyword in text.lower() 
                       for keyword in ['opportunity', 'tender', 'bid', 'rfp', 'request', 'contract', 'award']):
                    
                    # Skip navigation and non-opportunity links
                    if any(nav_keyword in text.lower() for nav_keyword in ['login', 'home', 'navigation', 'menu', 'accessibility']):
                        continue
                    
                    navigation_links.append({
                        'title': text,
                        'url': urljoin(self.base_url, href),
                        'href': href,
                        'external_id': self.extract_opportunity_id(href),
                        'source': 'navigation_link',
                        'description': f"Navigation link to {text}",
                        'type': 'navigation'
                    })
            
            logger.info(f"Extracted {len(navigation_links)} navigation links")
            return navigation_links
            
        except Exception as e:
            logger.error(f"Error extracting navigation links: {e}")
            return []


async def main():
    """Main function to run the BC Bid scraper."""
    # You can provide credentials here if you have them
    # scraper = BCBidScraper(username="your_username", password="your_password")
    scraper = BCBidScraper()  # Public access only
    async with scraper:
        tenders = await scraper.scrape_tenders()
        logger.info(f"Scraped {len(tenders)} tenders from BC Bid")


if __name__ == "__main__":
    asyncio.run(main()) 