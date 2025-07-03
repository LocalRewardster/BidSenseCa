import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.ontario_portal import OntarioPortalScraper


class TestOntarioPortalScraper:
    @pytest.fixture
    def scraper(self):
        return OntarioPortalScraper()

    @pytest.fixture
    def sample_rss_feed(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Ontario Tenders</title>
            <item>
              <title>Construction of New School</title>
              <link>https://ontariotenders.app.jaggaer.com/en_US/portal/viewNotice/12345</link>
              <guid>12345</guid>
              <pubDate>Wed, 01 May 2024 12:00:00 GMT</pubDate>
              <description><![CDATA[
                <p>Reference: ONT-2024-001</p>
                <p>Organization: Ministry of Education</p>
                <p>Closing Date: 2024-06-15</p>
                <p>Value: $1,000,000</p>
              ]]></description>
            </item>
            <item>
              <title>IT Services RFP</title>
              <link>https://ontariotenders.app.jaggaer.com/en_US/portal/viewNotice/67890</link>
              <guid>67890</guid>
              <pubDate>Thu, 02 May 2024 09:00:00 GMT</pubDate>
              <description><![CDATA[
                <p>Reference: ONT-2024-002</p>
                <p>Organization: Ministry of Digital Government</p>
                <p>Closing Date: 2024-06-20</p>
                <p>Value: $250,000</p>
              ]]></description>
            </item>
          </channel>
        </rss>'''

    def test_scraper_initialization(self, scraper):
        assert scraper.name == "ontario_portal"
        assert scraper.feed_url.startswith("https://ontariotenders.app.jaggaer.com")

    def test_parse_rss_feed(self, scraper, sample_rss_feed):
        tenders = scraper.parse_rss_feed(sample_rss_feed)
        assert len(tenders) == 2
        assert tenders[0]['title'] == "Construction of New School"
        assert tenders[0]['reference'] == "ONT-2024-001"
        assert tenders[0]['organization'] == "Ministry of Education"
        assert tenders[0]['closing_date'] == "2024-06-15"
        assert tenders[0]['contract_value'] == "$1,000,000"
        assert tenders[0]['source_url'] == "https://ontariotenders.app.jaggaer.com/en_US/portal/viewNotice/12345"
        assert tenders[1]['title'] == "IT Services RFP"
        assert tenders[1]['reference'] == "ONT-2024-002"

    def test_parse_date_formats(self, scraper):
        test_cases = [
            ("Wed, 01 May 2024 12:00:00 GMT", "2024-05-01"),
            ("2024-06-15", "2024-06-15"),
        ]
        for input_date, expected in test_cases:
            parsed = scraper.parse_date(input_date)
            assert parsed == expected

    @pytest.mark.asyncio
    async def test_scrape_tenders_success(self, scraper, sample_rss_feed):
        with patch.object(scraper, 'get_feed', new_callable=AsyncMock) as mock_get_feed:
            mock_get_feed.return_value = sample_rss_feed
            with patch.object(scraper, 'save_tender', new_callable=AsyncMock) as mock_save:
                mock_save.return_value = True
                result = await scraper.scrape_tenders(limit=2)
                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_scrape_tenders_no_results(self, scraper):
        empty_feed = '''<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel></channel></rss>'''
        with patch.object(scraper, 'get_feed', new_callable=AsyncMock) as mock_get_feed:
            mock_get_feed.return_value = empty_feed
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scrape_tenders_error_handling(self, scraper):
        with patch.object(scraper, 'get_feed', new_callable=AsyncMock) as mock_get_feed:
            mock_get_feed.side_effect = Exception("Network error")
            result = await scraper.scrape_tenders(limit=10)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_extract_contract_value(self, scraper):
        test_cases = [
            ("Value: $1,000,000", "$1,000,000"),
            ("Value: $250,000", "$250,000"),
            ("No value specified", None),
        ]
        for input_text, expected in test_cases:
            result = scraper.extract_contract_value(input_text)
            assert result == expected

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