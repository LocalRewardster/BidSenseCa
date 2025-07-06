"""
Opportunity dataclass for standardized tender opportunity representation.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Opportunity:
    """Standardized opportunity representation."""
    
    # Core fields
    id: str
    title: str
    summary: Optional[str] = None
    close_date: Optional[datetime] = None
    buyer: Optional[str] = None
    docs_url: Optional[str] = None
    source: str = "unknown"
    
    # Additional metadata
    tags: Optional[str] = None
    document_urls: Optional[List[str]] = None
    jurisdiction: Optional[str] = None
    
    # Raw data for debugging/extension
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for database storage."""
        return {
            "external_id": self.id,
            "title": self.title,
            "description": self.summary,
            "closing_date": self.close_date,
            "organization": self.buyer,
            "original_url": self.docs_url,
            "source_name": self.source,
            "category": self.tags,
            "documents_urls": self.document_urls,
            "location": self.jurisdiction,
            "raw_data": self.raw_data
        } 