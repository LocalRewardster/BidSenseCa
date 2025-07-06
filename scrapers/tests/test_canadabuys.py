"""
Tests for CanadaBuys bid source.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from ..bidsources.canadabuys import CanadaBuysSource, stream_opportunities
from ..models.opportunity import Opportunity


class TestCanadaBuysSource:
    """Unit tests for CanadaBuys source."""
    
    @pytest.fixture
    def source(self):
        """Create a CanadaBuys source instance for testing."""
        return CanadaBuysSource()
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock response data from CanadaBuys API."""
        return {
            "content": [
                {
                    "noticeId": "729181",
                    "title": "Environmental Consulting Services – Fraser Valley",
                    "summary": "Provision of consulting for stream restoration and environmental assessment services in the Fraser Valley region.",
                    "organization": "Ministry of Water, Land and Resource Stewardship",
                    "jurisdiction": "BC",
                    "closingDate": "2025-08-14T21:00:00Z",
                    "procurementCategory": "Services",
                    "gsin": "R199",
                    "documents": [
                        {
                            "type": "RFP",
                            "url": "https://canadabuys.canada.ca/documents/rfp-729181.pdf"
                        }
                    ]
                },
                {
                    "noticeId": "729182",
                    "title": "IT Infrastructure Upgrade",
                    "summary": "Upgrade of IT infrastructure and network systems for government offices.",
                    "organization": "Ministry of Technology",
                    "jurisdiction": "BC",
                    "closingDate": "2025-07-30T18:00:00Z",
                    "procurementCategory": "Goods",
                    "gsin": "N701",
                    "documents": []
                }
            ],
            "page": 0,
            "size": 200,
            "totalElements": 68
        }
    
    @pytest.mark.asyncio
    async def test_fetch_page_success(self, source, mock_response_data):
        """Test successful page fetch."""
        # Mock httpx.AsyncClient
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        source.session = mock_session
        
        # Execute
        result = await source.fetch_page(0)
        
        # Assert
        assert len(result) == 2
        assert result[0]["noticeId"] == "729181"
        assert result[1]["noticeId"] == "729182"
        
        # Verify API call
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "jurisdiction=BC" in str(call_args)
        assert "status=open" in str(call_args)
        assert "size=200" in str(call_args)
        assert "page=0" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_fetch_page_http_error(self, source):
        """Test page fetch with HTTP error."""
        # Mock httpx.AsyncClient with error
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")
        mock_session.get.return_value = mock_response
        
        source.session = mock_session
        
        # Execute and assert
        with pytest.raises(Exception):
            await source.fetch_page(0)
    
    def test_normalize_opportunity(self, source, mock_response_data):
        """Test opportunity normalization."""
        # Execute
        opportunity = source.normalize(mock_response_data["content"][0])
        
        # Assert
        assert isinstance(opportunity, Opportunity)
        assert opportunity.id == "729181"
        assert opportunity.title == "Environmental Consulting Services – Fraser Valley"
        assert opportunity.summary == "Provision of consulting for stream restoration and environmental assessment services in the Fraser Valley region."
        assert opportunity.buyer == "Ministry of Water, Land and Resource Stewardship"
        assert opportunity.source == "canadabuys"
        assert opportunity.jurisdiction == "BC"
        assert "Services" in opportunity.tags
        assert "GSIN: R199" in opportunity.tags
        assert opportunity.docs_url == "https://canadabuys.canada.ca/en/tender-opportunities/729181"
        assert len(opportunity.document_urls) == 1
        assert "rfp-729181.pdf" in opportunity.document_urls[0]
        
        # Check closing date parsing
        assert opportunity.close_date is not None
        assert isinstance(opportunity.close_date, datetime)
        assert opportunity.close_date.year == 2025
        assert opportunity.close_date.month == 8
        assert opportunity.close_date.day == 14
    
    def test_normalize_opportunity_no_documents(self, source, mock_response_data):
        """Test opportunity normalization with no documents."""
        record = mock_response_data["content"][1]  # Second record has no documents
        
        # Execute
        opportunity = source.normalize(record)
        
        # Assert
        assert opportunity.document_urls is None
    
    def test_normalize_opportunity_invalid_date(self, source):
        """Test opportunity normalization with invalid date."""
        record = {
            "noticeId": "test123",
            "title": "Test Opportunity",
            "closingDate": "invalid-date"
        }
        
        # Execute
        opportunity = source.normalize(record)
        
        # Assert
        assert opportunity.close_date is None
    
    @pytest.mark.asyncio
    async def test_stream_opportunities(self, source, mock_response_data):
        """Test opportunity streaming."""
        # Mock fetch_page to return data then empty
        source.fetch_page = AsyncMock(side_effect=[
            mock_response_data["content"],  # First page
            []  # Second page (empty)
        ])
        
        # Execute
        opportunities = []
        async for opportunity in source.stream_opportunities():
            opportunities.append(opportunity)
        
        # Assert
        assert len(opportunities) == 2
        assert all(isinstance(opp, Opportunity) for opp in opportunities)
        assert opportunities[0].source == "canadabuys"
        assert opportunities[1].source == "canadabuys"
    
    @pytest.mark.asyncio
    async def test_stream_opportunities_error_handling(self, source):
        """Test opportunity streaming with error handling."""
        # Mock fetch_page to raise exception
        source.fetch_page = AsyncMock(side_effect=Exception("API Error"))
        
        # Execute
        opportunities = []
        async for opportunity in source.stream_opportunities():
            opportunities.append(opportunity)
        
        # Assert - should handle error gracefully and return empty
        assert len(opportunities) == 0


class TestCanadaBuysIntegration:
    """Integration tests for CanadaBuys source."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_fetch(self):
        """Test live API fetch (requires VCR cassette)."""
        try:
            async with CanadaBuysSource() as source:
                # Fetch first page
                opportunities = await source.fetch_page(0)
                
                # Assert we got some data
                assert isinstance(opportunities, list)
                
                if opportunities:
                    # Test normalization of first opportunity
                    opportunity = source.normalize(opportunities[0])
                    
                    # Assert basic structure
                    assert isinstance(opportunity, Opportunity)
                    assert opportunity.id is not None
                    assert opportunity.title is not None
                    assert opportunity.source == "canadabuys"
                    assert opportunity.jurisdiction == "BC"
                    
                    # Assert future closing date
                    if opportunity.close_date:
                        assert opportunity.close_date > datetime.now(timezone.utc)
                    
                    print(f"✅ Live test successful: {opportunity.title}")
                else:
                    print("⚠️ No opportunities found in live test")
                    
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_stream_opportunities(self):
        """Test live opportunity streaming."""
        try:
            count = 0
            async for opportunity in stream_opportunities():
                assert isinstance(opportunity, Opportunity)
                assert opportunity.source == "canadabuys"
                assert opportunity.jurisdiction == "BC"
                
                count += 1
                if count >= 3:  # Limit to first 3 for testing
                    break
            
            assert count > 0, "No opportunities found in live stream test"
            print(f"✅ Live stream test successful: {count} opportunities")
            
        except Exception as e:
            pytest.fail(f"Live stream test failed: {e}")


if __name__ == "__main__":
    """Run tests."""
    pytest.main([__file__, "-v"]) 