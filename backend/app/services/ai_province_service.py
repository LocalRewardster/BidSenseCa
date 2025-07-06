"""
AI Province Detection Service

Uses OpenAI GPT to analyze tender content and accurately assign Canadian provinces.
"""

import logging
from typing import Optional, Dict, Any
import asyncio
from functools import lru_cache

import openai
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class ProvinceDetectionResult(BaseModel):
    """Result of AI province detection."""
    
    province: str = Field(..., description="Detected province code (e.g., 'NS', 'ON', 'BC')")
    confidence: float = Field(..., description="Confidence score (0-1)")
    reasoning: str = Field(..., description="Explanation of why this province was chosen")


class AIProvinceService:
    """Service for AI-powered province detection from tender content."""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
    @lru_cache(maxsize=1)
    def _get_system_prompt(self) -> str:
        """Get the system prompt for province detection."""
        return """You are an expert at analyzing Canadian government tender documents to determine which province they belong to.

Your task is to analyze tender information and determine the most likely Canadian province based on:
1. Organization/buyer name (e.g., "Halifax Regional Municipality" = Nova Scotia)
2. Location references in title or description
3. Geographic context clues
4. Government department jurisdiction

PROVINCE CODES:
- BC: British Columbia
- AB: Alberta  
- SK: Saskatchewan
- MB: Manitoba
- ON: Ontario
- QC: Quebec
- NB: New Brunswick
- NS: Nova Scotia
- PE: Prince Edward Island
- NL: Newfoundland and Labrador
- NT: Northwest Territories
- NU: Nunavut
- YT: Yukon Territory

IMPORTANT RULES:
1. Prioritize specific location references over generic organization names
2. "Halifax Regional Municipality" = NS (Nova Scotia)
3. "RCMP" locations depend on context - look for specific location clues
4. Federal departments can operate anywhere - look for location context
5. If unclear, choose the most likely province based on available evidence
6. Always provide a confidence score (0-1) and reasoning

Return your analysis in the specified JSON format."""

    def _get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for province detection."""
        return {
            "name": "detect_province",
            "description": "Detect the Canadian province for a tender based on content analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {
                        "type": "string",
                        "enum": ["BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "NT", "NU", "YT"],
                        "description": "The detected Canadian province code"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score for the detection (0-1)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of why this province was chosen"
                    }
                },
                "required": ["province", "confidence", "reasoning"]
            }
        }

    @retry_async(max_retries=2, base_delay=1, max_delay=15)
    async def detect_province(self, tender_data: Dict[str, Any]) -> ProvinceDetectionResult:
        """
        Detect the province for a tender using AI analysis.
        
        Args:
            tender_data: Dictionary containing tender information
            
        Returns:
            ProvinceDetectionResult with detected province, confidence, and reasoning
        """
        try:
            # Extract relevant information for analysis
            analysis_text = self._prepare_analysis_text(tender_data)
            
            logger.info(f"Analyzing tender for province detection: {tender_data.get('title', 'Unknown')[:100]}...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Analyze this tender and detect the Canadian province:\n\n{analysis_text}"}
                ],
                functions=[self._get_function_schema()],
                function_call={"name": "detect_province"},
                max_tokens=300,
                temperature=0.1  # Low temperature for consistent results
            )
            
            # Extract function call result
            function_call = response.choices[0].message.function_call
            if not function_call or function_call.name != "detect_province":
                raise ValueError("GPT did not return expected function call")
            
            # Parse the result
            import json
            result_data = json.loads(function_call.arguments)
            
            result = ProvinceDetectionResult(**result_data)
            
            logger.info(f"Detected province: {result.province} (confidence: {result.confidence:.2f}) - {result.reasoning}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect province for tender: {e}")
            # Return a fallback result
            return ProvinceDetectionResult(
                province="ON",  # Default to Ontario as fallback
                confidence=0.1,
                reasoning=f"AI detection failed: {str(e)}. Defaulted to Ontario."
            )

    def _prepare_analysis_text(self, tender_data: Dict[str, Any]) -> str:
        """Prepare text for AI analysis from tender data."""
        analysis_parts = []
        
        # Title
        if tender_data.get('title'):
            analysis_parts.append(f"Title: {tender_data['title']}")
        
        # Organization/Buyer
        if tender_data.get('organization'):
            analysis_parts.append(f"Organization: {tender_data['organization']}")
        elif tender_data.get('buyer'):
            analysis_parts.append(f"Buyer: {tender_data['buyer']}")
        
        # Summary/Description
        if tender_data.get('summary_raw'):
            # Limit summary to avoid token limits
            summary = tender_data['summary_raw'][:1000]
            analysis_parts.append(f"Summary: {summary}")
        elif tender_data.get('description'):
            description = tender_data['description'][:1000]
            analysis_parts.append(f"Description: {description}")
        
        # Category
        if tender_data.get('category'):
            analysis_parts.append(f"Category: {tender_data['category']}")
        
        # URL (might contain location clues)
        if tender_data.get('url'):
            analysis_parts.append(f"URL: {tender_data['url']}")
        
        # Current province (if any, for context)
        if tender_data.get('province'):
            analysis_parts.append(f"Current Province Assignment: {tender_data['province']}")
        
        return "\n".join(analysis_parts)

    async def detect_province_batch(self, tender_list: list[Dict[str, Any]]) -> list[ProvinceDetectionResult]:
        """
        Detect provinces for multiple tenders in parallel.
        
        Args:
            tender_list: List of tender dictionaries
            
        Returns:
            List of ProvinceDetectionResult objects
        """
        # Process in batches to avoid rate limits
        batch_size = 5
        results = []
        
        for i in range(0, len(tender_list), batch_size):
            batch = tender_list[i:i + batch_size]
            batch_tasks = [self.detect_province(tender) for tender in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch detection failed: {result}")
                    results.append(ProvinceDetectionResult(
                        province="ON",
                        confidence=0.1,
                        reasoning=f"Batch processing failed: {str(result)}"
                    ))
                else:
                    results.append(result)
            
            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)
        
        return results


# Global instance
ai_province_service = AIProvinceService() 