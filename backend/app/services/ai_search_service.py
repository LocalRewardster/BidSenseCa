"""
AI Search Service

Combines GPT query parsing with hybrid ranking (cosine similarity + full-text search).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import openai
from pydantic import BaseModel, Field

from app.config import settings
from app.services.database import db_service
from app.services.ai_query_parser import ai_query_parser, SearchFilters
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class AISearchResult(BaseModel):
    """AI search result with hybrid ranking and optional explanation."""
    
    # Standard tender fields
    id: str
    title: str
    summary_raw: Optional[str] = None
    organization: Optional[str] = None
    category: Optional[str] = None
    reference: Optional[str] = None
    naics: Optional[str] = None
    province: Optional[str] = None
    value: Optional[float] = None
    deadline: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # AI search specific fields
    score: float = Field(..., description="Hybrid search score (0-1)")
    cosine_similarity: float = Field(..., description="Cosine similarity score")
    text_rank: float = Field(..., description="Full-text search rank")
    province_bonus: float = Field(default=0.0, description="Province match bonus")
    reason: Optional[str] = Field(default=None, description="AI explanation of relevance")


class AISearchResponse(BaseModel):
    """Response from AI search endpoint."""
    
    results: List[AISearchResult]
    filters: SearchFilters
    total: int
    query: str
    processing_time_ms: float


class AISearchService:
    """Service for AI-powered search with hybrid ranking."""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
    async def search(
        self, 
        query: str, 
        page: int = 1, 
        page_size: int = 20,
        explain_results: bool = True
    ) -> AISearchResponse:
        """
        Perform AI-powered search with hybrid ranking.
        
        Args:
            query: Natural language query
            page: Page number (1-based)
            page_size: Results per page
            explain_results: Whether to generate explanations for top results
            
        Returns:
            AISearchResponse with results and metadata
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Parse query using GPT
            filters = await ai_query_parser.parse_query(query)
            
            # Step 2: Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            
            # Step 3: Execute hybrid search using database function
            results = await self._execute_ai_search(filters, query_embedding, page, page_size)
            
            # Step 4: Generate explanations for top results (optional)
            if explain_results and results:
                await self._add_explanations(results[:5], query, filters)
            
            # Step 5: Get total count
            total = await self._get_total_count(filters, query)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return AISearchResponse(
                results=results,
                filters=filters,
                total=total,
                query=query,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"AI search failed for query '{query}': {e}")
            # Fallback to basic search
            return await self._fallback_search(query, page, page_size)

    @retry_async(max_retries=2, base_delay=1, max_delay=15)
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    async def _execute_ai_search(
        self, 
        filters: SearchFilters, 
        query_embedding: List[float],
        page: int,
        page_size: int
    ) -> List[AISearchResult]:
        """Execute AI search using database function."""
        try:
            # Convert embedding to PostgreSQL array format
            embedding_array = f"[{','.join(map(str, query_embedding))}]"
            
            # Build search query from keywords
            search_query = " ".join(filters.keywords) if filters.keywords else ""
            
            # Check if we have any tenders with province data
            province_check = db_service.supabase.table('tenders').select('province').not_.is_('province', 'null').limit(1).execute()
            has_province_data = len(province_check.data) > 0
            
            # Only use province filter if we have province data
            province_filter = filters.provinces[0] if filters.provinces and has_province_data else None
            
            # Call the database function
            result = db_service.supabase.rpc(
                'search_tenders_ai',
                {
                    'search_query': search_query,
                    'query_embedding': embedding_array,
                    'province_filter': province_filter,
                    'min_value': filters.min_value,
                    'max_value': filters.max_value,
                    'deadline_before': filters.deadline_before,
                    'deadline_after': filters.deadline_after,
                    'limit_count': page_size,
                    'offset_count': (page - 1) * page_size
                }
            ).execute()
            
            if not result.data:
                return []
            
            # Convert to AISearchResult objects
            results = []
            for row in result.data:
                ai_result = AISearchResult(
                    id=row['id'],
                    title=row['title'],
                    summary_raw=row.get('summary_raw'),
                    organization=row.get('buyer'),  # Note: buyer field in DB
                    category=row.get('category'),
                    reference=row.get('external_id'),  # Note: external_id in DB
                    naics=row.get('naics'),
                    province=row.get('province'),
                    value=float(row['value']) if row.get('value') else None,
                    deadline=row.get('deadline'),
                    url=row.get('url'),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at'),
                    score=float(row['score']),
                    cosine_similarity=float(row['cosine_similarity']),
                    text_rank=float(row['text_rank']),
                    province_bonus=float(row['province_bonus'])
                )
                results.append(ai_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute AI search: {e}")
            return []

    async def _get_total_count(self, filters: SearchFilters, query: str) -> int:
        """Get total count of matching results."""
        try:
            # For now, return a reasonable estimate based on the search results
            # In a production system, you'd want a proper count function
            search_query = " ".join(filters.keywords) if filters.keywords else ""
            
            # Check if we have any tenders with province data
            province_check = db_service.supabase.table('tenders').select('province').not_.is_('province', 'null').limit(1).execute()
            has_province_data = len(province_check.data) > 0
            
            # Only use province filter if we have province data
            province_filter = filters.provinces[0] if filters.provinces and has_province_data else None
            
            # Use the same search function but with a larger limit to get count
            embedding = [0.1] * 1536  # Dummy embedding for count
            embedding_array = f"[{','.join(map(str, embedding))}]"
            
            result = db_service.supabase.rpc(
                'search_tenders_ai',
                {
                    'search_query': search_query,
                    'query_embedding': embedding_array,
                    'province_filter': province_filter,
                    'min_value': filters.min_value,
                    'max_value': filters.max_value,
                    'deadline_before': filters.deadline_before,
                    'deadline_after': filters.deadline_after,
                    'limit_count': 1000,  # Large limit to get count
                    'offset_count': 0
                }
            ).execute()
            
            return len(result.data) if result.data else 0
            
        except Exception as e:
            logger.error(f"Failed to get total count: {e}")
            return 0

    @retry_async(max_retries=2, base_delay=1, max_delay=15)
    async def _add_explanations(
        self, 
        results: List[AISearchResult], 
        query: str, 
        filters: SearchFilters
    ) -> None:
        """Add AI explanations to search results."""
        try:
            # Prepare context for GPT
            context = f"Query: {query}\nFilters: {filters.model_dump_json()}\n\n"
            
            explanations = []
            for result in results:
                tender_info = f"Title: {result.title}\n"
                if result.summary_raw:
                    tender_info += f"Summary: {result.summary_raw[:500]}...\n"
                if result.organization:
                    tender_info += f"Organization: {result.organization}\n"
                if result.province:
                    tender_info += f"Province: {result.province}\n"
                if result.value:
                    tender_info += f"Value: ${result.value:,.0f}\n"
                
                explanations.append(tender_info)
            
            # Generate explanations in batch
            prompt = f"{context}Explain why each tender matches the query in one sentence:\n\n"
            for i, explanation in enumerate(explanations, 1):
                prompt += f"{i}. {explanation}\n"
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a tender search assistant. Explain why each tender matches the user's query in one concise sentence."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            # Parse explanations and assign to results
            explanation_text = response.choices[0].message.content
            if explanation_text:
                lines = explanation_text.strip().split('\n')
                for i, result in enumerate(results):
                    if i < len(lines):
                        result.reason = lines[i].strip()
                        
        except Exception as e:
            logger.error(f"Failed to add explanations: {e}")

    async def _fallback_search(self, query: str, page: int, page_size: int) -> AISearchResponse:
        """Fallback to basic search when AI search fails."""
        try:
            # Use existing advanced search as fallback
            from app.services.advanced_search_service import advanced_search_service
            
            results = await advanced_search_service.search_tenders(
                query=query,
                buyer_filter=None,
                province_filter=None,
                naics_filter=None,
                limit_count=page_size,
                offset_count=(page - 1) * page_size
            )
            
            # Convert to AISearchResult format
            ai_results = []
            for result in results:
                ai_result = AISearchResult(
                    id=result['id'],
                    title=result['title'],
                    summary_raw=result.get('summary_raw'),
                    organization=result.get('organization'),
                    category=result.get('category'),
                    reference=result.get('reference'),
                    naics=result.get('naics'),
                    province=result.get('province'),
                    value=result.get('value'),
                    deadline=result.get('deadline'),
                    url=result.get('url'),
                    created_at=result.get('created_at'),
                    updated_at=result.get('updated_at'),
                    score=float(result.get('rank', 0.5)),
                    cosine_similarity=0.0,
                    text_rank=float(result.get('rank', 0.5)),
                    province_bonus=0.0
                )
                ai_results.append(ai_result)
            
            return AISearchResponse(
                results=ai_results,
                filters=SearchFilters(keywords=[query]),
                total=len(ai_results),
                query=query,
                processing_time_ms=0.0
            )
            
        except Exception as e:
            logger.error(f"Fallback search also failed: {e}")
            return AISearchResponse(
                results=[],
                filters=SearchFilters(keywords=[query]),
                total=0,
                query=query,
                processing_time_ms=0.0
            )


# Global instance
ai_search_service = AISearchService() 