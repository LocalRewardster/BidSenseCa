"""
AI Query Parser Service

Converts natural language queries into structured search filters using GPT function calling.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

import openai
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class SearchFilters(BaseModel):
    """Structured search filters extracted from natural language query."""
    
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    provinces: List[str] = Field(default_factory=list, description="Province filters")
    naics_codes: List[str] = Field(default_factory=list, description="NAICS code filters")
    min_value: Optional[float] = Field(default=None, description="Minimum tender value")
    max_value: Optional[float] = Field(default=None, description="Maximum tender value")
    deadline_before: Optional[str] = Field(default=None, description="Deadline before date (YYYY-MM-DD)")
    deadline_after: Optional[str] = Field(default=None, description="Deadline after date (YYYY-MM-DD)")
    organizations: List[str] = Field(default_factory=list, description="Organization filters")
    categories: List[str] = Field(default_factory=list, description="Category filters")
    reference_contains: Optional[str] = Field(default=None, description="Reference number contains")


class AIQueryParser:
    """Service for parsing natural language queries into structured filters using GPT."""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
    @lru_cache(maxsize=100)
    def _get_system_prompt(self) -> str:
        """Get the system prompt for query parsing."""
        return """You are an expert tender search assistant for BidSense.ca. Your job is to parse natural language queries about government tenders and convert them into structured search filters.

AVAILABLE FILTERS:
- keywords: List of search terms to match in title, description, summary
- provinces: Canadian provinces (BC, AB, SK, MB, ON, QC, NB, NS, PE, NL, NT, NU, YT)
- naics_codes: NAICS industry codes (e.g., "236220", "541330")
- min_value/max_value: Tender value ranges in dollars
- deadline_before/deadline_after: Date filters (YYYY-MM-DD format)
- organizations: Government departments/agencies
- categories: Tender categories (Construction, Services, Goods, etc.)
- reference_contains: Reference number patterns

EXAMPLES:
Query: "Show me bridge maintenance tenders in BC closing this month over $500K"
→ keywords: ["bridge", "maintenance"], provinces: ["BC"], deadline_before: "2025-02-28", min_value: 500000

Query: "IT services in Ontario under $100K"
→ keywords: ["IT", "services"], provinces: ["ON"], max_value: 100000

Query: "construction projects in Alberta and Saskatchewan"
→ keywords: ["construction"], provinces: ["AB", "SK"]

Query: "healthcare equipment in Quebec closing next week"
→ keywords: ["healthcare", "equipment"], provinces: ["QC"], deadline_before: "2025-02-07"

IMPORTANT RULES:
1. Always extract relevant keywords from the query
2. Convert relative dates to absolute dates (YYYY-MM-DD)
3. Convert dollar amounts to numbers (e.g., "$500K" → 500000)
4. Use standard province abbreviations
5. Only include filters that are explicitly mentioned or strongly implied
6. If no specific filters are mentioned, return empty lists/None values
7. Be conservative - don't add filters unless clearly indicated"""

    @lru_cache(maxsize=100)
    def _get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for structured output."""
        return {
            "name": "parse_search_query",
            "description": "Parse natural language query into structured search filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search keywords extracted from the query"
                    },
                    "provinces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Province filters (use standard abbreviations: BC, AB, SK, MB, ON, QC, NB, NS, PE, NL, NT, NU, YT)"
                    },
                    "naics_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "NAICS industry codes"
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Minimum tender value in dollars"
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Maximum tender value in dollars"
                    },
                    "deadline_before": {
                        "type": "string",
                        "description": "Deadline before date in YYYY-MM-DD format"
                    },
                    "deadline_after": {
                        "type": "string",
                        "description": "Deadline after date in YYYY-MM-DD format"
                    },
                    "organizations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Government organizations/departments"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tender categories"
                    },
                    "reference_contains": {
                        "type": "string",
                        "description": "Reference number pattern"
                    }
                },
                "required": []
            }
        }

    @retry_async(max_retries=2, base_delay=1, max_delay=15)
    async def parse_query(self, query: str) -> SearchFilters:
        """
        Parse a natural language query into structured search filters.
        
        Args:
            query: Natural language query string
            
        Returns:
            SearchFilters object with extracted filters
            
        Raises:
            Exception: If GPT API call fails after retries
        """
        try:
            logger.info(f"Parsing query: {query}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Parse this query into search filters: {query}"}
                ],
                functions=[self._get_function_schema()],
                function_call={"name": "parse_search_query"},
                max_tokens=settings.openai_max_tokens,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            # Extract function call arguments
            function_call = response.choices[0].message.function_call
            if not function_call or function_call.name != "parse_search_query":
                raise ValueError("GPT did not return expected function call")
            
            # Parse the arguments
            args = json.loads(function_call.arguments)
            
            # Convert to SearchFilters object
            filters = SearchFilters(**args)
            
            logger.info(f"Parsed query into filters: {filters}")
            return filters
            
        except Exception as e:
            logger.error(f"Failed to parse query '{query}': {e}")
            # Fallback to keyword-only search
            return SearchFilters(keywords=[query.strip()])

    async def parse_query_with_cache(self, query: str, cache_key: Optional[str] = None) -> SearchFilters:
        """
        Parse query with optional caching.
        
        Args:
            query: Natural language query string
            cache_key: Optional cache key (if None, uses query hash)
            
        Returns:
            SearchFilters object
        """
        # TODO: Implement Redis caching here
        # For now, just call parse_query directly
        return await self.parse_query(query)


# Global instance
ai_query_parser = AIQueryParser() 