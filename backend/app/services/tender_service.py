from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from app.models.tender import Tender, TenderCreate, TenderUpdate, TenderStatistics, TendersResponse, TenderFilters
from app.services.database import db_service
from app.services.advanced_search_service import advanced_search_service

logger = logging.getLogger(__name__)


class TenderService:
    """Service for tender operations."""
    
    async def get_tenders(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        source: Optional[str] = None,
        province: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "scraped_at",
        sort_order: str = "desc",
        use_advanced_search: bool = False
    ) -> TendersResponse:
        """
        Get tenders with filtering and pagination.
        
        Args:
            use_advanced_search: If True, use advanced search with query parsing
        """
        try:
            # Use advanced search if requested and search query is provided
            if use_advanced_search and search:
                result = await advanced_search_service.search_tenders_advanced(
                    query=search,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                # Convert to Tender models
                tenders = []
                for tender_data in result["tenders"]:
                    # Map advanced search fields to Tender model
                    mapped_tender = {
                        "id": tender_data.get("id"),
                        "title": tender_data.get("title"),
                        "organization": tender_data.get("organization"),
                        "description": tender_data.get("description"),
                        "contract_value": tender_data.get("contract_value"),
                        "closing_date": tender_data.get("closing_date"),
                        "source_name": tender_data.get("source_name"),
                        "location": tender_data.get("location"),
                        "url": tender_data.get("url"),
                        "created_at": tender_data.get("created_at"),
                        "updated_at": tender_data.get("updated_at"),
                        "category": tender_data.get("category"),
                        "reference": tender_data.get("reference"),
                        "contact_name": tender_data.get("contact_name"),
                        "contact_email": tender_data.get("contact_email"),
                        "contact_phone": tender_data.get("contact_phone"),
                        "external_id": tender_data.get("external_id"),
                        "summary_raw": tender_data.get("summary_raw"),
                        "documents_urls": tender_data.get("documents_urls"),
                        "original_url": tender_data.get("original_url"),
                        "notice_type": tender_data.get("notice_type"),
                        "languages": tender_data.get("languages"),
                        "delivery_regions": tender_data.get("delivery_regions"),
                        "opportunity_region": tender_data.get("opportunity_region"),
                        "contract_duration": tender_data.get("contract_duration"),
                        "procurement_method": tender_data.get("procurement_method"),
                        "selection_criteria": tender_data.get("selection_criteria"),
                        "commodity_unspsc": tender_data.get("commodity_unspsc"),
                        # Advanced search specific fields
                        "rank": tender_data.get("rank"),
                        "highlight": tender_data.get("highlight"),
                    }
                    tenders.append(Tender(**mapped_tender))
                
                # Calculate if there are more results
                has_more = (offset + limit) < result["total"]
                
                # Build filters applied
                filters_applied = {}
                if search:
                    filters_applied["search"] = search
                if source:
                    filters_applied["source"] = source
                if province:
                    filters_applied["province"] = province
                if category:
                    filters_applied["category"] = category
                if sort_by != "scraped_at":
                    filters_applied["sort_by"] = sort_by
                if sort_order != "desc":
                    filters_applied["sort_order"] = sort_order
                
                return TendersResponse(
                    tenders=tenders,
                    total=result["total"],
                    offset=result["offset"],
                    limit=result["limit"],
                    has_more=has_more,
                    filters_applied=filters_applied,
                    query_info=result.get("query_info")
                )
            
            # Fall back to regular search
            result = await db_service.get_tenders(
                limit=limit,
                offset=offset,
                search=search,
                source=source,
                province=province,
                category=category,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Convert database fields to frontend model fields
            tenders = []
            for tender_data in result["tenders"]:
                mapped_tender = {
                    "id": tender_data.get("id"),
                    "title": tender_data.get("title"),
                    "organization": tender_data.get("organization"),
                    "description": tender_data.get("description"),
                    "contract_value": tender_data.get("contract_value"),
                    "closing_date": tender_data.get("closing_date"),
                    "source_name": tender_data.get("source_name"),
                    "location": tender_data.get("location"),
                    "url": tender_data.get("url"),
                    "created_at": tender_data.get("created_at"),
                    "updated_at": tender_data.get("updated_at"),
                    "category": tender_data.get("category"),
                    "reference": tender_data.get("reference"),
                    "contact_name": tender_data.get("contact_name"),
                    "contact_email": tender_data.get("contact_email"),
                    "contact_phone": tender_data.get("contact_phone"),
                    "external_id": tender_data.get("external_id"),
                    "summary_raw": tender_data.get("summary_raw"),
                    "documents_urls": tender_data.get("documents_urls"),
                    "original_url": tender_data.get("original_url"),
                    "notice_type": tender_data.get("notice_type"),
                    "languages": tender_data.get("languages"),
                    "delivery_regions": tender_data.get("delivery_regions"),
                    "opportunity_region": tender_data.get("opportunity_region"),
                    "contract_duration": tender_data.get("contract_duration"),
                    "procurement_method": tender_data.get("procurement_method"),
                    "selection_criteria": tender_data.get("selection_criteria"),
                    "commodity_unspsc": tender_data.get("commodity_unspsc"),
                }
                tenders.append(Tender(**mapped_tender))
            
            # Calculate if there are more results
            has_more = (offset + limit) < result["total"]
            
            # Build filters applied
            filters_applied = {}
            if search:
                filters_applied["search"] = search
            if source:
                filters_applied["source"] = source
            if province:
                filters_applied["province"] = province
            if category:
                filters_applied["category"] = category
            if sort_by != "scraped_at":
                filters_applied["sort_by"] = sort_by
            if sort_order != "desc":
                filters_applied["sort_order"] = sort_order
            
            return TendersResponse(
                tenders=tenders,
                total=result["total"],
                offset=result["offset"],
                limit=result["limit"],
                has_more=has_more,
                filters_applied=filters_applied
            )
            
        except Exception as e:
            logger.error(f"Error in tender service get_tenders: {e}")
            return TendersResponse(
                tenders=[],
                total=0,
                offset=offset,
                limit=limit,
                has_more=False,
                filters_applied={}
            )
    
    async def get_tender_by_id(self, tender_id: str) -> Optional[Tender]:
        """Get a specific tender by ID."""
        try:
            tender_data = await db_service.get_tender_by_id(tender_id)
            if tender_data:
                return Tender(**tender_data)
            return None
        except Exception as e:
            logger.error(f"Error in tender service get_tender_by_id: {e}")
            return None
    
    async def get_tender_statistics(self) -> TenderStatistics:
        """Get tender statistics."""
        try:
            stats = await db_service.get_tender_statistics()
            return TenderStatistics(**stats)
        except Exception as e:
            logger.error(f"Error in tender service get_tender_statistics: {e}")
            return TenderStatistics(
                total_tenders=0,
                recent_tenders=0,
                source_counts={},
                last_updated=None
            )
    
    async def create_tender(self, tender_data: TenderCreate) -> Optional[Tender]:
        """Create a new tender."""
        try:
            created_tender = await db_service.create_tender(tender_data.dict())
            if created_tender:
                return Tender(**created_tender)
            return None
        except Exception as e:
            logger.error(f"Error in tender service create_tender: {e}")
            return None
    
    async def update_tender(self, tender_id: str, tender_data: TenderUpdate) -> Optional[Tender]:
        """Update an existing tender."""
        try:
            updated_tender = await db_service.update_tender(tender_id, tender_data.dict(exclude_unset=True))
            if updated_tender:
                return Tender(**updated_tender)
            return None
        except Exception as e:
            logger.error(f"Error in tender service update_tender: {e}")
            return None
    
    async def delete_tender(self, tender_id: str) -> bool:
        """Delete a tender."""
        try:
            return await db_service.delete_tender(tender_id)
        except Exception as e:
            logger.error(f"Error in tender service delete_tender: {e}")
            return False
    
    async def get_tender_filters(self) -> TenderFilters:
        """Get available filter options for tenders."""
        try:
            filters = await db_service.get_tender_filters()
            return TenderFilters(**filters)
        except Exception as e:
            logger.error(f"Error in tender service get_tender_filters: {e}")
            return TenderFilters(
                sources=[],
                provinces=[],
                categories=[],
                date_range=None
            )
    
    async def get_search_suggestions(self, query: str, limit: int = 10) -> dict:
        """Get search suggestions based on tender titles and organizations."""
        try:
            # Try advanced search suggestions first
            advanced_suggestions = await advanced_search_service.get_advanced_search_suggestions(query, limit)
            
            if advanced_suggestions:
                return {
                    "success": True,
                    "data": advanced_suggestions
                }
            
            # Fall back to regular suggestions
            result = await db_service.get_search_suggestions(query, limit)
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"Error in tender service get_search_suggestions: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }
    
    async def get_related_tenders(self, tender_id: str, limit: int = 5) -> dict:
        """Get related tenders based on organization, category, or similar criteria."""
        try:
            result = await db_service.get_related_tenders(tender_id, limit)
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"Error in tender service get_related_tenders: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }
    
    async def get_search_statistics(self) -> dict:
        """Get search-related statistics."""
        try:
            stats = await advanced_search_service.get_search_statistics()
            return {
                "success": True,
                "data": stats
            }
        except Exception as e:
            logger.error(f"Error in tender service get_search_statistics: {e}")
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }
    
    async def get_search_examples(self) -> dict:
        """Get example search queries for documentation."""
        try:
            examples = await advanced_search_service.get_search_examples()
            return {
                "success": True,
                "data": examples
            }
        except Exception as e:
            logger.error(f"Error in tender service get_search_examples: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }


# Global tender service instance
tender_service = TenderService() 