import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from scrapers.canadabuys import CanadaBuysScraper


class TestCanadaBuysScraper:
    """Test CanadaBuys scraper functionality."""
    
    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing."""
        return CanadaBuysScraper()
    
    @pytest.fixture
    def sample_search_page(self):
        """Sample search results page HTML."""
        return """
        <html>
            <body>
                <div class="search-results">
                    <div class="opportunity-item">
                        <h3><a href="/opportunity/123">Sample Tender Title</a></h3>
                        <div class="opportunity-meta">
                            <span class="reference">REF-2024-001</span>
                            <span class="organization">Public Works Canada</span>
                            <span class="closing-date">2024-12-31</span>
                        </div>
                        <div class="opportunity-description">
                            This is a sample tender description for testing purposes.
                        </div>
                    </div>
                    <div class="opportunity-item">
                        <h3><a href="/opportunity/456">Another Tender</a></h3>
                        <div class="opportunity-meta">
                            <span class="reference">REF-2024-002</span>
                            <span class="organization">Transport Canada</span>
                            <span class="closing-date">2024-11-15</span>
                        </div>
                        <div class="opportunity-description">
                            Another sample tender description.
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
    
    @pytest.fixture
    def sample_detail_page(self):
        """Sample tender detail page HTML."""
        return """
        <html>
            <body>
                <div class="opportunity-details">
                    <h1>Sample Tender Title</h1>
                    <div class="opportunity-info">
                        <div class="reference">Reference: REF-2024-001</div>
                        <div class="organization">Organization: Public Works Canada</div>
                        <div class="closing-date">Closing Date: December 31, 2024</div>
                        <div class="contract-value">Contract Value: $100,000 - $500,000</div>
                        <div class="description">
                            <p>This is a detailed description of the tender opportunity.</p>
                            <p>It includes multiple paragraphs with important information.</p>
                        </div>
                        <div class="contact-info">
                            <div class="contact-name">Contact: John Doe</div>
                            <div class="contact-email">Email: john.doe@canada.ca</div>
                            <div class="contact-phone">Phone: (613) 555-0123</div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper.name == "canadabuys"
        assert scraper.base_url == "https://canadabuys.canada.ca"
        assert scraper.search_url == "https://canadabuys.canada.ca/en/tender-opportunities"
    
    def test_get_search_url(self, scraper):
        """Test search URL generation."""
        url = scraper.get_search_url()
        assert "canadabuys.canada.ca" in url
        assert "tender-opportunities" in url
    
    def test_parse_search_results(self, scraper, sample_search_page):
        """Test parsing search results page."""
        soup = BeautifulSoup(sample_search_page, 'html.parser')
        results = scraper.parse_search_results(soup)
        
        assert len(results) == 2
        assert results[0]['title'] == "Sample Tender Title"
        assert results[0]['url'] == "/opportunity/123"
        assert results[0]['reference'] == "REF-2024-001"
        assert results[0]['organization'] == "Public Works Canada"
        assert results[1]['title'] == "Another Tender"
        assert results[1]['url'] == "/opportunity/456"
    
    def test_parse_tender_details(self, scraper, sample_detail_page):
        """Test parsing tender detail page."""
        soup = BeautifulSoup(sample_detail_page, 'html.parser')
        details = scraper.parse_tender_details(soup, "https://canadabuys.canada.ca/opportunity/123")
        
        assert details['title'] == "Sample Tender Title"
        assert details['reference'] == "REF-2024-001"
        assert details['organization'] == "Public Works Canada"
        assert details['closing_date'] == "2024-12-31"
        assert details['contract_value'] == "$100,000 - $500,000"
        assert "detailed description" in details['description']
        assert details['contact_name'] == "John Doe"
        assert details['contact_email'] == "john.doe@canada.ca"
        assert details['contact_phone'] == "(613) 555-0123"
        assert details['source_url'] == "https://canadabuys.canada.ca/opportunity/123"
    
    def test_parse_date_formats(self, scraper):
        """Test parsing various date formats."""
        # Test different date formats that might appear
        test_cases = [
            ("December 31, 2024", "2024-12-31"),
            ("Dec 31, 2024", "2024-12-31"),
            ("31/12/2024", "2024-12-31"),
            ("2024-12-31", "2024-12-31"),
        ]
        
        for input_date, expected in test_cases:
            parsed = scraper.parse_date(input_date)
            assert parsed == expected
    
    @pytest.mark.asyncio
    async def test_scrape_tenders_success(self, scraper, sample_search_page, sample_detail_page):
        """Test successful tender scraping."""
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            # Mock search page
            mock_get_page.return_value = sample_search_page
            
            # Mock detail pages
            mock_get_page.side_effect = [sample_search_page, sample_detail_page, sample_detail_page]
            
            with patch.object(scraper, 'save_tender', new_callable=AsyncMock) as mock_save:
                mock_save.return_value = True
                
                result = await scraper.scrape_tenders(limit=2)
                assert isinstance(result, list)
                assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_scrape_tenders_no_results(self, scraper):
        """Test scraping when no results found."""
        empty_page = "<html><body><div class='search-results'></div></body></html>"
        
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            mock_get_page.return_value = empty_page
            
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scrape_tenders_error_handling(self, scraper):
        """Test error handling during scraping."""
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            mock_get_page.side_effect = Exception("Network error")
            
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0
    
    def test_extract_contract_value(self, scraper):
        """Test contract value extraction."""
        test_cases = [
            ("Contract Value: $100,000 - $500,000", "$100,000 - $500,000"),
            ("Estimated Value: $50,000", "$50,000"),
            ("Budget: $75,000 CAD", "$75,000 CAD"),
            ("No value specified", None),
        ]
        
        for input_text, expected in test_cases:
            result = scraper.extract_contract_value(input_text)
            assert result == expected
    
    def test_extract_contact_info(self, scraper):
        """Test contact information extraction."""
        contact_html = """
        <div class="contact-info">
            <div class="contact-name">Contact: Jane Smith</div>
            <div class="contact-email">Email: jane.smith@canada.ca</div>
            <div class="contact-phone">Phone: (613) 555-9876</div>
        </div>
        """
        
        soup = BeautifulSoup(contact_html, 'html.parser')
        contact_info = scraper.extract_contact_info(soup)
        
        assert contact_info['contact_name'] == "Jane Smith"
        assert contact_info['contact_email'] == "jane.smith@canada.ca"
        assert contact_info['contact_phone'] == "(613) 555-9876"
    
    @pytest.mark.asyncio
    async def test_run_method(self, scraper):
        """Test the main run method."""
        with patch.object(scraper, 'scrape_tenders', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = [
                {"external_id": "1", "title": "Tender 1"},
                {"external_id": "2", "title": "Tender 2"}
            ]
            with patch.object(scraper, 'save_tender', new_callable=AsyncMock) as mock_save:
                mock_save.return_value = True
                count = await scraper.run(limit=10)
                assert count == 2
                mock_scrape.assert_called_once_with(10) 