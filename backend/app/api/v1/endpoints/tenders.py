from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from app.models.tender import (
    Tender, TenderCreate, TenderUpdate, TenderStatistics, 
    TendersResponse, TenderFilters, SearchSuggestion, 
    SearchStatistics, SearchExample
)
from app.services.tender_service import tender_service
from app.services.ai_search_service import ai_search_service, AISearchResponse

router = APIRouter()


class AISearchRequest(BaseModel):
    """Request model for AI search endpoint."""
    query: str = Query(..., description="Natural language search query")
    page: int = Query(1, ge=1, description="Page number (1-based)")
    page_size: int = Query(20, ge=1, le=100, description="Results per page")
    explain_results: bool = Query(True, description="Generate AI explanations for top results")


@router.post("/search/ai", response_model=AISearchResponse)
async def ai_search(request: AISearchRequest) -> AISearchResponse:
    """
    Perform AI-powered search with natural language query parsing and hybrid ranking.
    
    Features:
    - Natural language query parsing using GPT
    - Hybrid ranking (cosine similarity + full-text search)
    - AI explanations for top results
    - Fallback to basic search if AI fails
    
    Example queries:
    - "Show me bridge maintenance tenders in BC closing this month over $500K"
    - "IT services in Ontario under $100K"
    - "construction projects in Alberta and Saskatchewan"
    - "healthcare equipment in Quebec closing next week"
    """
    try:
        return await ai_search_service.search(
            query=request.query,
            page=request.page,
            page_size=request.page_size,
            explain_results=request.explain_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI search failed: {str(e)}")


@router.get("/", response_model=TendersResponse)
async def get_tenders(
    search: Optional[str] = Query(None, description="Search in title and organization"),
    source: Optional[str] = Query(None, description="Filter by source"),
    province: Optional[str] = Query(None, description="Filter by province/location"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: str = Query("created_at", description="Sort field (created_at, title, organization, closing_date, rank)"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    use_advanced_search: bool = Query(False, description="Use advanced search features"),
    use_ai_search: bool = Query(True, description="Use AI-powered search")
) -> TendersResponse:
    """
    Get list of tenders with optional filtering and pagination.
    
    Advanced search features (when use_advanced_search=True):
    - Boolean operators: AND, OR, NOT
    - Phrase search: "road maintenance"
    - Field prefixes: buyer:"Public Works", province:BC, naics:237*
    - Wildcards: maint*, constr?ction
    
    AI search features (when use_ai_search=True):
    - Natural language query parsing using GPT
    - Hybrid ranking (cosine similarity + full-text search)
    - Semantic similarity matching
    - Province and value filtering
    """
    if use_ai_search and search:
        # Use AI search service
        try:
            ai_response = await ai_search_service.search(
                query=search,
                page=(offset // limit) + 1,
                page_size=limit,
                explain_results=False
            )
            
            # Convert AISearchResult objects to Tender objects
            tenders = []
            for ai_result in ai_response.results:
                tender = {
                    "id": ai_result.id,
                    "title": ai_result.title,
                    "summary_raw": ai_result.summary_raw,
                    "organization": ai_result.organization,
                    "category": ai_result.category,
                    "reference": ai_result.reference,
                    "naics": ai_result.naics,
                    "province": ai_result.province,
                    "value": ai_result.value,
                    "deadline": ai_result.deadline,
                    "url": ai_result.url,
                    "created_at": ai_result.created_at,
                    "updated_at": ai_result.updated_at,
                    "source_name": "AI Search",
                    "contract_value": str(ai_result.value) if ai_result.value else None,
                    "closing_date": ai_result.deadline,
                    "location": ai_result.province,
                    "description": ai_result.summary_raw,
                    "external_id": ai_result.reference,
                    "buyer": ai_result.organization,
                    "rank": ai_result.score,
                    "highlight": f"AI Score: {ai_result.score:.3f}, Similarity: {ai_result.cosine_similarity:.3f}"
                }
                tenders.append(tender)
            
            # Convert AI search response to TendersResponse format
            return TendersResponse(
                tenders=tenders,
                total=ai_response.total,
                offset=offset,
                limit=limit,
                has_more=offset + limit < ai_response.total,
                filters_applied={
                    "ai_search": True,
                    "query": search,
                    "parsed_filters": ai_response.filters.model_dump() if ai_response.filters else {}
                },
                query_info={
                    "original_query": search,
                    "parsed_query": "AI processed query",
                    "filters": ai_response.filters.model_dump() if ai_response.filters else {},
                    "field_filters": {},
                    "wildcards": [],
                    "has_errors": False
                }
            )
        except Exception as e:
            # Fallback to regular search if AI search fails
            return await tender_service.get_tenders(
                limit=limit,
                offset=offset,
                search=search,
                source=source,
                province=province,
                category=category,
                sort_by=sort_by,
                sort_order=sort_order,
                use_advanced_search=use_advanced_search
            )
    else:
        # Use regular search
        return await tender_service.get_tenders(
            limit=limit,
            offset=offset,
            search=search,
            source=source,
            province=province,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
            use_advanced_search=use_advanced_search
        )


@router.get("/statistics", response_model=TenderStatistics)
async def get_tender_statistics() -> TenderStatistics:
    """Get tender statistics including counts, source distribution, and recent activity."""
    return await tender_service.get_tender_statistics()


@router.get("/filters", response_model=TenderFilters)
async def get_tender_filters() -> TenderFilters:
    """Get available filter options for tenders."""
    return await tender_service.get_tender_filters()


@router.get("/search-suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions to return")
) -> dict:
    """Get search suggestions based on tender titles and organizations."""
    return await tender_service.get_search_suggestions(q, limit)


@router.get("/search-statistics", response_model=dict)
async def get_search_statistics() -> dict:
    """Get search-related statistics including full-text search metrics."""
    return await tender_service.get_search_statistics()


@router.get("/search-examples", response_model=dict)
async def get_search_examples() -> dict:
    """Get example search queries for documentation."""
    return await tender_service.get_search_examples()


@router.get("/{tender_id}", response_model=Tender)
async def get_tender(tender_id: str) -> Tender:
    """Get a specific tender by ID with full details."""
    tender = await tender_service.get_tender_by_id(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.get("/{tender_id}/related")
async def get_related_tenders(
    tender_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of related tenders to return")
) -> dict:
    """Get related tenders based on organization, category, or similar criteria."""
    return await tender_service.get_related_tenders(tender_id, limit)


@router.post("/", response_model=Tender)
async def create_tender(tender: TenderCreate) -> Tender:
    """Create a new tender."""
    created_tender = await tender_service.create_tender(tender)
    if not created_tender:
        raise HTTPException(status_code=500, detail="Failed to create tender")
    return created_tender


@router.put("/{tender_id}", response_model=Tender)
async def update_tender(tender_id: str, tender: TenderUpdate) -> Tender:
    """Update an existing tender."""
    updated_tender = await tender_service.update_tender(tender_id, tender)
    if not updated_tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return updated_tender


@router.delete("/{tender_id}")
async def delete_tender(tender_id: str):
    """Delete a tender."""
    success = await tender_service.delete_tender(tender_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tender not found")
    return {"message": "Tender deleted successfully"}


@router.post("/{tender_id}/bookmark")
async def bookmark_tender(tender_id: str) -> dict:
    """Bookmark a tender for the current user."""
    # TODO: Implement bookmark logic with user authentication
    return {"message": "Tender bookmarked successfully"}


@router.delete("/{tender_id}/bookmark")
async def unbookmark_tender(tender_id: str) -> dict:
    """Remove bookmark for a tender."""
    # TODO: Implement unbookmark logic with user authentication
    return {"message": "Tender unbookmarked successfully"} 