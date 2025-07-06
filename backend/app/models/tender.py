from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TenderBase(BaseModel):
    """Base tender model with common fields."""
    title: str = Field(..., description="Tender title")
    organization: Optional[str] = Field(None, description="Organization name")
    description: Optional[str] = Field(None, description="Tender description")
    contract_value: Optional[str] = Field(None, description="Contract value")
    closing_date: Optional[datetime] = Field(None, description="Closing date")
    source_name: str = Field(..., description="Source name")
    location: Optional[str] = Field(None, description="Location")
    url: Optional[str] = Field(None, description="Source URL")
    category: Optional[str] = Field(None, description="Tender category")
    reference: Optional[str] = Field(None, description="Reference number")
    contact_name: Optional[str] = Field(None, description="Contact person name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    external_id: Optional[str] = Field(None, description="External ID")
    # Rich metadata fields
    summary_raw: Optional[str] = Field(None, description="Raw summary text")
    documents_urls: Optional[List[str]] = Field(None, description="Document URLs")
    original_url: Optional[str] = Field(None, description="Original tender URL")
    # Summary information fields
    notice_type: Optional[str] = Field(None, description="Type of tender notice")
    languages: Optional[str] = Field(None, description="Languages available")
    delivery_regions: Optional[str] = Field(None, description="Delivery regions")
    opportunity_region: Optional[str] = Field(None, description="Opportunity region")
    contract_duration: Optional[str] = Field(None, description="Contract duration")
    procurement_method: Optional[str] = Field(None, description="Procurement method")
    selection_criteria: Optional[str] = Field(None, description="Selection criteria")
    commodity_unspsc: Optional[str] = Field(None, description="UNSPSC commodity codes")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    # Advanced search fields
    rank: Optional[float] = Field(None, description="Search relevance rank")
    highlight: Optional[str] = Field(None, description="Highlighted search terms")


class TenderCreate(TenderBase):
    """Model for creating a new tender."""
    pass


class TenderUpdate(TenderBase):
    """Model for updating an existing tender."""
    pass


class Tender(TenderBase):
    """Complete tender model with all fields."""
    id: str = Field(..., description="Tender ID")

    class Config:
        from_attributes = True


class TenderList(BaseModel):
    """Model for tender list response."""
    tenders: List[Tender]
    total: int
    offset: int
    limit: int
    has_more: bool
    filters_applied: Optional[dict] = None


class TenderResponse(BaseModel):
    """Model for single tender response."""
    tender: Tender


class TenderListResponse(BaseModel):
    """Model for tender list response."""
    tenders: List[Tender]
    total: int
    offset: int
    limit: int
    has_more: bool
    filters_applied: Optional[dict] = None


class TenderStatistics(BaseModel):
    """Statistics model for tender data."""
    total_tenders: int = Field(..., description="Total number of tenders")
    recent_tenders: int = Field(..., description="Number of recent tenders (last 7 days)")
    source_counts: dict = Field(..., description="Count of tenders by source")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    # Additional statistics
    total_value: Optional[str] = Field(None, description="Total contract value")
    provinces: List[str] = Field(default_factory=list, description="List of provinces with tenders")
    categories: dict = Field(default_factory=dict, description="Count of tenders by category")
    # New statistics for rich metadata
    tenders_with_documents: int = Field(0, description="Number of tenders with document attachments")
    tenders_with_contacts: int = Field(0, description="Number of tenders with contact information")


class TenderFilters(BaseModel):
    """Model for tender filtering options."""
    sources: List[str] = Field(default_factory=list, description="Available source names")
    provinces: List[str] = Field(default_factory=list, description="Available provinces")
    categories: List[str] = Field(default_factory=list, description="Available categories")
    date_range: Optional[dict] = Field(None, description="Available date range")
    # New filter options for rich metadata
    has_documents: Optional[bool] = Field(None, description="Filter tenders with/without documents")
    has_contacts: Optional[bool] = Field(None, description="Filter tenders with/without contact information")


class TendersResponse(BaseModel):
    """Model for tenders response with advanced search support."""
    tenders: List[Tender]
    total: int
    offset: int
    limit: int
    has_more: bool
    filters_applied: Dict[str, Any]
    query_info: Optional[Dict[str, Any]] = Field(None, description="Advanced search query information")


class SearchSuggestion(BaseModel):
    """Model for search suggestions."""
    text: str = Field(..., description="Suggestion text")
    type: str = Field(..., description="Suggestion type (word, title, organization)")
    frequency: Optional[int] = Field(None, description="Frequency of the suggestion")


class SearchStatistics(BaseModel):
    """Model for search statistics."""
    total_tenders: int = Field(..., description="Total number of tenders")
    tenders_with_summary: int = Field(..., description="Number of tenders with summary")
    tenders_with_documents: int = Field(..., description="Number of tenders with documents")
    tenders_with_contacts: int = Field(..., description="Number of tenders with contacts")
    avg_search_vector_length: int = Field(..., description="Average search vector length")


class SearchExample(BaseModel):
    """Model for search examples."""
    query: str = Field(..., description="Example search query")
    description: str = Field(..., description="Description of what the query does") 