import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.apc import APCScraper


class TestAPCScraper:
    @pytest.fixture
    def scraper(self):
        return APCScraper()

    @pytest.fixture
    def sample_search_page(self):
        return """
        <html>
            <body>
                <div class="search-results">
                    <div class="tender-item">
                        <h3><a href="/tender/12345">Road Construction Project</a></h3>
                        <div class="tender-meta">
                            <span class="reference">APC-2024-001</span>
                            <span class="organization">Alberta Transportation</span>
                            <span class="closing-date">2024-07-15</span>
                        </div>
                        <div class="tender-description">
                            Major road construction project in Edmonton area.
                        </div>
                    </div>
                    <div class="tender-item">
                        <h3><a href="/tender/67890">IT Infrastructure Upgrade</a></h3>
                        <div class="tender-meta">
                            <span class="reference">APC-2024-002</span>
                            <span class="organization">Alberta Digital Government</span>
                            <span class="closing-date">2024-08-20</span>
                        </div>
                        <div class="tender-description">
                            IT infrastructure upgrade for government offices.
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_detail_page(self):
        return """
        <html>
            <body>
                <div class="tender-details">
                    <h1>Road Construction Project</h1>
                    <div class="tender-info">
                        <div class="reference">Reference: APC-2024-001</div>
                        <div class="organization">Organization: Alberta Transportation</div>
                        <div class="closing-date">Closing Date: July 15, 2024</div>
                        <div class="contract-value">Contract Value: $2,500,000</div>
                        <div class="description">
                            <p>This is a detailed description of the road construction project.</p>
                            <p>It includes multiple phases and significant infrastructure work.</p>
                        </div>
                        <div class="contact-info">
                            <div class="contact-name">Contact: Jane Smith</div>
                            <div class="contact-email">Email: jane.smith@gov.ab.ca</div>
                            <div class="contact-phone">Phone: (780) 555-0123</div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

    def test_scraper_initialization(self, scraper):
        assert scraper.name == "apc"
        assert scraper.base_url == "https://alberta.bidsandtenders.ca"

    def test_get_search_url(self, scraper):
        url = scraper.get_search_url()
        assert "alberta.bidsandtenders.ca" in url

    def test_parse_search_results(self, scraper, sample_search_page):
        soup = BeautifulSoup(sample_search_page, 'html.parser')
        results = scraper.parse_search_results(soup)
        
        assert len(results) == 2
        assert results[0]['title'] == "Road Construction Project"
        assert results[0]['url'] == "/tender/12345"
        assert results[0]['reference'] == "APC-2024-001"
        assert results[0]['organization'] == "Alberta Transportation"
        assert results[1]['title'] == "IT Infrastructure Upgrade"
        assert results[1]['url'] == "/tender/67890"

    def test_parse_tender_details(self, scraper, sample_detail_page):
        soup = BeautifulSoup(sample_detail_page, 'html.parser')
        details = scraper.parse_tender_details(soup, "https://alberta.bidsandtenders.ca/tender/12345")
        
        assert details['title'] == "Road Construction Project"
        assert details['reference'] == "APC-2024-001"
        assert details['organization'] == "Alberta Transportation"
        assert details['closing_date'] == "2024-07-15"
        assert details['contract_value'] == "$2,500,000"
        assert "detailed description" in details['description']
        assert details['contact_name'] == "Jane Smith"
        assert details['contact_email'] == "jane.smith@gov.ab.ca"
        assert details['contact_phone'] == "(780) 555-0123"
        assert details['source_url'] == "https://alberta.bidsandtenders.ca/tender/12345"

    def test_parse_date_formats(self, scraper):
        test_cases = [
            ("July 15, 2024", "2024-07-15"),
            ("Jul 15, 2024", "2024-07-15"),
            ("15/07/2024", "2024-07-15"),
            ("2024-07-15", "2024-07-15"),
        ]
        for input_date, expected in test_cases:
            parsed = scraper.parse_date(input_date)
            assert parsed == expected

    @pytest.mark.asyncio
    async def test_scrape_tenders_success(self, scraper, sample_search_page, sample_detail_page):
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            mock_get_page.return_value = sample_search_page
            mock_get_page.side_effect = [sample_search_page, sample_detail_page, sample_detail_page]
            
            with patch.object(scraper, 'save_tender', new_callable=AsyncMock) as mock_save:
                mock_save.return_value = True
                result = await scraper.scrape_tenders(limit=2)
                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_scrape_tenders_no_results(self, scraper):
        empty_page = "<html><body><div class='search-results'></div></body></html>"
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            mock_get_page.return_value = empty_page
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scrape_tenders_error_handling(self, scraper):
        with patch.object(scraper, 'get_page', new_callable=AsyncMock) as mock_get_page:
            mock_get_page.side_effect = Exception("Network error")
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_extract_contract_value(self, scraper):
        test_cases = [
            ("Contract Value: $2,500,000", "$2,500,000"),
            ("Estimated Value: $500,000", "$500,000"),
            ("Budget: $750,000 CAD", "$750,000 CAD"),
            ("No value specified", None),
        ]
        for input_text, expected in test_cases:
            result = scraper.extract_contract_value(input_text)
            assert result == expected

    def test_extract_contact_info(self, scraper):
        contact_html = """
        <div class="contact-info">
            <div class="contact-name">Contact: John Doe</div>
            <div class="contact-email">Email: john.doe@gov.ab.ca</div>
            <div class="contact-phone">Phone: (780) 555-9876</div>
        </div>
        """
        
        soup = BeautifulSoup(contact_html, 'html.parser')
        contact_info = scraper.extract_contact_info(soup)
        
        assert contact_info['contact_name'] == "John Doe"
        assert contact_info['contact_email'] == "john.doe@gov.ab.ca"
        assert contact_info['contact_phone'] == "(780) 555-9876"

    @pytest.mark.asyncio
    async def test_run_method(self, scraper):
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