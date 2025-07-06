"""
Advanced Search Service

This service provides advanced search capabilities including:
- Boolean operators (AND, OR, NOT)
- Phrase search with quotes
- Field prefixes (buyer:, province:, naics:)
- Wildcards (* and ?)
- Full-text search with highlighting
- Search suggestions
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from app.services.database import db_service
from app.utils.query_parser import parse_search_query, ParsedQuery

logger = logging.getLogger(__name__)


class AdvancedSearchService:
    """Service for advanced search operations."""
    
    async def search_tenders_advanced(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "rank",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Perform advanced search using the query parser and full-text search.
        
        Args:
            query: Search query string (can include boolean operators, field prefixes, etc.)
            limit: Maximum number of results
            offset: Number of results to skip
            sort_by: Sort field (rank, closing_date, created_at, title)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Parse the search query
            parsed_query = parse_search_query(query)
            
            if parsed_query.has_errors:
                logger.warning(f"Query parsing errors: {parsed_query.error_message}")
                return {
                    "tenders": [],
                    "total": 0,
                    "offset": offset,
                    "limit": limit,
                    "query_info": {
                        "original_query": query,
                        "parsed_query": parsed_query.fts_query,
                        "filters": parsed_query.filter_clauses,
                        "field_filters": parsed_query.field_filters,
                        "wildcards": parsed_query.wildcards,
                        "has_errors": True,
                        "error_message": parsed_query.error_message
                    }
                }
            
            # Build the search query using the database function
            search_params = {
                "search_query": parsed_query.fts_query if parsed_query.fts_query else "''",
                "buyer_filter": parsed_query.filter_clauses.get("organization"),
                "province_filter": parsed_query.filter_clauses.get("province"),
                "naics_filter": parsed_query.filter_clauses.get("naics"),
                "limit_count": limit,
                "offset_count": offset
            }
            
            # Execute the advanced search function
            result = await self._execute_advanced_search(search_params)
            
            # Apply additional field filters if any
            if parsed_query.field_filters:
                result = await self._apply_field_filters(result, parsed_query.field_filters)
            
            # Apply sorting
            if sort_by != "rank":
                result = await self._apply_sorting(result, sort_by, sort_order)
            
            # Get total count for pagination
            total_count = await self._get_search_count(parsed_query)
            
            return {
                "tenders": result,
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "query_info": {
                    "original_query": query,
                    "parsed_query": parsed_query.fts_query,
                    "filters": parsed_query.filter_clauses,
                    "field_filters": parsed_query.field_filters,
                    "wildcards": parsed_query.wildcards,
                    "has_errors": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return {
                "tenders": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
                "query_info": {
                    "original_query": query,
                    "has_errors": True,
                    "error_message": str(e)
                }
            }
    
    async def _execute_advanced_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the advanced search database function."""
        try:
            # Call the search_tenders_advanced function
            response = db_service.supabase.rpc(
                'search_tenders_advanced',
                params
            ).execute()
            
            # Map the results to frontend format
            mapped_results = []
            for tender in response.data:
                mapped_tender = {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("organization"),
                    "description": tender.get("description"),
                    "summary_raw": tender.get("summary_raw"),
                    "category": tender.get("category"),
                    "reference": tender.get("reference"),
                    "naics": tender.get("naics"),
                    "province": tender.get("province"),
                    "closing_date": tender.get("closing_date"),
                    "contract_value": tender.get("contract_value"),
                    "source_name": tender.get("source_name"),
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "documents_urls": tender.get("documents_urls"),
                    "original_url": tender.get("original_url"),
                    "created_at": tender.get("closing_date"),  # Use closing_date as created_at for now
                    "updated_at": tender.get("closing_date"),
                    "url": tender.get("original_url"),
                    "location": tender.get("province"),
                    # Search-specific fields
                    "rank": tender.get("rank", 0.0),
                    "highlight": tender.get("highlight", ""),
                }
                mapped_results.append(mapped_tender)
            
            return mapped_results
            
        except Exception as e:
            logger.error(f"Error executing advanced search: {e}")
            return []
    
    async def _apply_field_filters(self, results: List[Dict[str, Any]], field_filters: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Apply additional field filters to search results."""
        filtered_results = []
        
        for tender in results:
            include_tender = True
            
            for field, values in field_filters.items():
                tender_value = tender.get(field, "").lower()
                if not any(value.lower() in tender_value for value in values):
                    include_tender = False
                    break
            
            if include_tender:
                filtered_results.append(tender)
        
        return filtered_results
    
    async def _apply_sorting(self, results: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Apply sorting to search results."""
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "closing_date":
            results.sort(key=lambda x: x.get("closing_date") or "", reverse=reverse)
        elif sort_by == "created_at":
            results.sort(key=lambda x: x.get("created_at") or "", reverse=reverse)
        elif sort_by == "title":
            results.sort(key=lambda x: x.get("title", "").lower(), reverse=reverse)
        elif sort_by == "organization":
            results.sort(key=lambda x: x.get("organization", "").lower(), reverse=reverse)
        # rank is already sorted by the database function
        
        return results
    
    async def _get_search_count(self, parsed_query: ParsedQuery) -> int:
        """Get total count for search results."""
        try:
            # Build a count query based on the parsed query
            count_params = {
                "search_query": parsed_query.fts_query if parsed_query.fts_query else "''",
                "buyer_filter": parsed_query.filter_clauses.get("organization"),
                "province_filter": parsed_query.filter_clauses.get("province"),
                "naics_filter": parsed_query.filter_clauses.get("naics"),
                "limit_count": 1000,  # Large limit to get all results for counting
                "offset_count": 0
            }
            
            response = db_service.supabase.rpc(
                'search_tenders_advanced',
                count_params
            ).execute()
            
            return len(response.data)
            
        except Exception as e:
            logger.error(f"Error getting search count: {e}")
            return 0
    
    async def get_advanced_search_suggestions(
        self, 
        query_prefix: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get advanced search suggestions using the database function.
        
        Args:
            query_prefix: The query prefix to get suggestions for
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestion objects
        """
        try:
            # Call the get_search_suggestions_advanced function
            response = db_service.supabase.rpc(
                'get_search_suggestions_advanced',
                {
                    "query_prefix": query_prefix,
                    "limit_count": limit
                }
            ).execute()
            
            suggestions = []
            for suggestion in response.data:
                suggestions.append({
                    "text": suggestion.get("suggestion", ""),
                    "type": suggestion.get("type", "word"),
                    "frequency": suggestion.get("frequency", 1)
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting advanced search suggestions: {e}")
            return []
    
    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get search-related statistics."""
        try:
            # Call the get_search_statistics function
            response = db_service.supabase.rpc('get_search_statistics').execute()
            
            if response.data:
                stats = response.data[0]
                return {
                    "total_tenders": stats.get("total_tenders", 0),
                    "tenders_with_summary": stats.get("tenders_with_summary", 0),
                    "tenders_with_documents": stats.get("tenders_with_documents", 0),
                    "tenders_with_contacts": stats.get("tenders_with_contacts", 0),
                    "avg_search_vector_length": stats.get("avg_search_vector_length", 0)
                }
            
            return {
                "total_tenders": 0,
                "tenders_with_summary": 0,
                "tenders_with_documents": 0,
                "tenders_with_contacts": 0,
                "avg_search_vector_length": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting search statistics: {e}")
            return {
                "total_tenders": 0,
                "tenders_with_summary": 0,
                "tenders_with_documents": 0,
                "tenders_with_contacts": 0,
                "avg_search_vector_length": 0
            }
    
    async def get_search_examples(self) -> List[Dict[str, str]]:
        """Get example search queries for documentation."""
        return [
            {
                "query": 'Show me bridge maintenance tenders in BC closing this month over $500K',
                "description": "Natural language query for specific requirements"
            },
            {
                "query": 'IT services in Ontario under $100K',
                "description": "Find IT services with budget constraints"
            },
            {
                "query": 'construction projects in Alberta and Saskatchewan',
                "description": "Multi-province construction search"
            },
            {
                "query": 'healthcare equipment in Quebec closing next week',
                "description": "Time-sensitive healthcare search"
            },
            {
                "query": 'software development services for government',
                "description": "Broad category search with context"
            },
            {
                "query": 'environmental consulting in western provinces',
                "description": "Regional service search"
            }
        ]


# Global advanced search service instance
advanced_search_service = AdvancedSearchService() 