from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import date

from app.models.tender import Tender, TenderCreate, TenderUpdate, TenderList
from app.core.database import get_tenders, get_tender_by_id, update_tender, delete_tender
from app.services.scraper_service import scraper_service

router = APIRouter()


@router.get("/", response_model=TenderList)
async def get_tenders_endpoint(
    province: Optional[str] = Query(None, description="Filter by province"),
    naics: Optional[str] = Query(None, description="Filter by NAICS code"),
    keyword: Optional[str] = Query(None, description="Search in title and description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> TenderList:
    """Get list of tenders with optional filtering."""
    try:
        # Map province to source_name for filtering
        source_name = None
        if province:
            province_mapping = {
                "federal": "canadabuys",
                "ontario": "ontario",
                "alberta": "apc",
                "bc": "bcbid",
                "manitoba": "manitoba",
                "saskatchewan": "saskatchewan",
                "quebec": "quebec"
            }
            source_name = province_mapping.get(province.lower())
        
        result = get_tenders(
            limit=limit,
            offset=offset,
            source_name=source_name,
            keyword=keyword,
            status=status
        )
        
        # Convert to Tender models
        tenders = []
        for tender_data in result["tenders"]:
            tender = Tender(**tender_data)
            tenders.append(tender)
        
        return TenderList(
            tenders=tenders,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tenders: {str(e)}")


@router.get("/{tender_id}", response_model=Tender)
async def get_tender_endpoint(tender_id: str) -> Tender:
    """Get a specific tender by ID."""
    try:
        tender_data = get_tender_by_id(tender_id)
        if not tender_data:
            raise HTTPException(status_code=404, detail="Tender not found")
        
        return Tender(**tender_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tender: {str(e)}")


@router.put("/{tender_id}", response_model=Tender)
async def update_tender_endpoint(tender_id: str, tender_update: TenderUpdate) -> Tender:
    """Update a tender."""
    try:
        # Get existing tender
        existing_data = get_tender_by_id(tender_id)
        if not existing_data:
            raise HTTPException(status_code=404, detail="Tender not found")
        
        # Update with new data
        update_data = tender_update.dict(exclude_unset=True)
        updated_data = update_tender(tender_id, update_data)
        
        return Tender(**updated_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update tender: {str(e)}")


@router.delete("/{tender_id}")
async def delete_tender_endpoint(tender_id: str):
    """Delete a tender."""
    try:
        success = delete_tender(tender_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tender not found")
        
        return {"message": "Tender deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tender: {str(e)}")


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


@router.get("/statistics/summary")
async def get_tender_statistics():
    """Get tender statistics."""
    try:
        stats = scraper_service.get_tender_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/sources/list")
async def get_available_sources():
    """Get list of available tender sources."""
    try:
        sources = scraper_service.get_all_scraper_status()
        return {
            "sources": sources,
            "total_sources": len(sources)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sources: {str(e)}") 