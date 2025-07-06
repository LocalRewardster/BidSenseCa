"""Tender models for BidSense API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TenderBase(BaseModel):
    """Base tender model."""
    title: str = Field(..., description="Tender title")
    reference: Optional[str] = Field(None, description="Tender reference number")
    organization: Optional[str] = Field(None, description="Issuing organization")
    closing_date: Optional[str] = Field(None, description="Closing date in ISO format")
    contract_value: Optional[str] = Field(None, description="Contract value")
    description: Optional[str] = Field(None, description="Tender description")
    contact_name: Optional[str] = Field(None, description="Contact person name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    source_url: Optional[str] = Field(None, description="Original tender URL")
    source_name: str = Field(..., description="Source scraper name")
    external_id: Optional[str] = Field(None, description="External ID from source")


class TenderCreate(TenderBase):
    """Model for creating a new tender."""
    pass


class TenderUpdate(BaseModel):
    """Model for updating a tender."""
    title: Optional[str] = None
    reference: Optional[str] = None
    organization: Optional[str] = None
    closing_date: Optional[str] = None
    contract_value: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    external_id: Optional[str] = None


class Tender(TenderBase):
    """Complete tender model with database fields."""
    id: str = Field(..., description="Tender ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class TenderList(BaseModel):
    """Model for tender list responses."""
    tenders: list[Tender] = Field(..., description="List of tenders")
    total: int = Field(..., description="Total number of tenders")
    limit: int = Field(..., description="Number of results returned")
    offset: int = Field(..., description="Number of results skipped") 