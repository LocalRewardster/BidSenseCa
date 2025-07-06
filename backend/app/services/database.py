from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations using Supabase."""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    
    async def get_tenders(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        source: Optional[str] = None,
        province: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "scraped_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get tenders with optional filtering and pagination."""
        try:
            query = self.supabase.table("tenders").select("*")
            
            # Apply search filter (use organization column)
            if search:
                query = query.or_(f"title.ilike.%{search}%,organization.ilike.%{search}%")
            
            # Apply source filter (use source_name column, fallback to source)
            if source:
                query = query.or_(f"source_name.eq.{source},source.eq.{source}")
            
            # Apply province filter
            if province:
                query = query.eq("province", province)
            
            # Apply category filter
            if category:
                query = query.eq("category", category)
            
            # Apply sorting (use scraped_at for created_at sorting)
            if sort_by == "created_at":
                sort_by = "scraped_at"
            
            if sort_order.lower() == "desc":
                query = query.order(sort_by, desc=True)
            else:
                query = query.order(sort_by, desc=False)
            
            # Apply pagination
            query = query.range(offset, offset + limit - 1)
            
            # Execute query
            response = query.execute()
            
            # Debug logging
            logger.info(f"Database query returned {len(response.data)} tenders")
            if response.data:
                logger.info(f"First tender columns: {list(response.data[0].keys())}")
                logger.info(f"First tender source_name: {response.data[0].get('source_name')}")
                logger.info(f"First tender scraped_at: {response.data[0].get('scraped_at')}")
            
            # Map database fields to frontend expectations, using fallback logic
            mapped_tenders = []
            for tender in response.data:
                # Get scraped_at timestamp for created_at/updated_at mapping
                scraped_at = tender.get("scraped_at")
                
                mapped_tender = {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("organization") or tender.get("buyer"),
                    "description": tender.get("description") or tender.get("summary_ai"),
                    "contract_value": tender.get("contract_value"),
                    "closing_date": tender.get("closing_date") or tender.get("deadline"),
                    "source_name": tender.get("source_name") or tender.get("source"),
                    "location": tender.get("province"),
                    "url": tender.get("source_url"),
                    "created_at": scraped_at,  # Map scraped_at to created_at
                    "updated_at": scraped_at,  # Map scraped_at to updated_at
                    "category": tender.get("category"),
                    "reference": tender.get("reference"),
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "external_id": tender.get("external_id"),
                    # New rich metadata fields
                    "summary_raw": tender.get("summary_raw"),
                    "documents_urls": tender.get("documents_urls"),
                    "original_url": tender.get("original_url"),
                }
                mapped_tenders.append(mapped_tender)
            
            # Get total count for pagination
            count_query = self.supabase.table("tenders").select("id", count="exact")
            if search:
                count_query = count_query.or_(f"title.ilike.%{search}%,organization.ilike.%{search}%")
            if source:
                count_query = count_query.or_(f"source_name.eq.{source},source.eq.{source}")
            if province:
                count_query = count_query.eq("province", province)
            if category:
                count_query = count_query.eq("category", category)
            count_response = count_query.execute()
            total_count = count_response.count or 0
            
            return {
                "tenders": mapped_tenders,
                "total": total_count,
                "offset": offset,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Error fetching tenders: {e}")
            return {
                "tenders": [],
                "total": 0,
                "offset": offset,
                "limit": limit
            }
    
    async def get_tender_by_id(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific tender by ID."""
        try:
            response = self.supabase.table("tenders").select("*").eq("id", tender_id).execute()
            if response.data:
                tender = response.data[0]
                # Map database fields to frontend expectations
                return {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("organization"),  # Use new organization column
                    "description": tender.get("description"),  # Use new description column
                    "contract_value": tender.get("contract_value"),
                    "closing_date": tender.get("closing_date"),  # Use new closing_date column
                    "source_name": tender.get("source_name"),  # Use new source_name column
                    "location": tender.get("province"),  # Map province to location
                    "url": tender.get("source_url"),
                    "created_at": tender.get("scraped_at"),  # Map scraped_at to created_at
                    "updated_at": tender.get("scraped_at"),  # Use scraped_at as updated_at
                    "category": tender.get("category"),
                    "reference": tender.get("reference"),
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "external_id": tender.get("external_id"),
                    # New rich metadata fields
                    "summary_raw": tender.get("summary_raw"),
                    "documents_urls": tender.get("documents_urls"),
                    "original_url": tender.get("original_url"),
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching tender {tender_id}: {e}")
            return None
    
    async def get_tender_statistics(self) -> Dict[str, Any]:
        """Get tender statistics."""
        try:
            # Get total count
            total_response = self.supabase.table("tenders").select("id", count="exact").execute()
            total_tenders = total_response.count or 0
            
            # Get recent tenders (last 7 days) - use scraped_at
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_response = self.supabase.table("tenders").select("id").gte("scraped_at", week_ago.isoformat()).execute()
            recent_tenders = len(recent_response.data)
            
            # Get source counts - use source_name column
            source_response = self.supabase.table("tenders").select("source_name").execute()
            source_counts = {}
            for tender in source_response.data:
                source = tender.get("source_name", "Unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
            
            # Get last updated - use scraped_at
            last_updated_response = self.supabase.table("tenders").select("scraped_at").order("scraped_at", desc=True).limit(1).execute()
            last_updated = last_updated_response.data[0]["scraped_at"] if last_updated_response.data else None
            
            return {
                "total_tenders": total_tenders,
                "recent_tenders": recent_tenders,
                "source_counts": source_counts,
                "last_updated": last_updated
            }
            
        except Exception as e:
            logger.error(f"Error fetching tender statistics: {e}")
            return {
                "total_tenders": 0,
                "recent_tenders": 0,
                "source_counts": {},
                "last_updated": None
            }
    
    async def create_tender(self, tender_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new tender."""
        try:
            # Map frontend fields to database fields
            db_tender_data = {
                "source": tender_data.get("source_name"),  # Map source_name to source
                "external_id": tender_data.get("external_id"),
                "title": tender_data.get("title"),
                "buyer": tender_data.get("organization"),  # Map organization to buyer
                "province": tender_data.get("location"),  # Map location to province
                "naics": tender_data.get("naics"),
                "deadline": tender_data.get("closing_date"),  # Map closing_date to deadline
                "summary_ai": tender_data.get("description"),  # Map description to summary_ai
                "tags_ai": tender_data.get("tags_ai"),
                "scraped_at": tender_data.get("scraped_at"),
                "category": tender_data.get("category"),
                "reference": tender_data.get("reference"),
                "contact_name": tender_data.get("contact_name"),
                "contact_email": tender_data.get("contact_email"),
                "contact_phone": tender_data.get("contact_phone"),
                "source_url": tender_data.get("source_url"),
                "contract_value": tender_data.get("contract_value"),
            }
            
            # Remove None values
            db_tender_data = {k: v for k, v in db_tender_data.items() if v is not None}
            
            response = self.supabase.table("tenders").insert(db_tender_data).execute()
            if response.data:
                # Map back to frontend format
                tender = response.data[0]
                return {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("buyer"),
                    "description": tender.get("summary_ai"),
                    "contract_value": tender.get("contract_value"),
                    "closing_date": tender.get("deadline"),
                    "source_name": tender.get("source_name"),
                    "location": tender.get("province"),
                    "url": tender.get("source_url"),
                    "created_at": tender.get("scraped_at"),
                    "updated_at": tender.get("scraped_at"),
                    "category": tender.get("category"),
                    "reference": tender.get("reference"),
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "external_id": tender.get("external_id"),
                    # New rich metadata fields
                    "summary_raw": tender.get("summary_raw"),
                    "documents_urls": tender.get("documents_urls"),
                    "original_url": tender.get("original_url"),
                }
            return None
        except Exception as e:
            logger.error(f"Error creating tender: {e}")
            return None
    
    async def update_tender(self, tender_id: str, tender_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing tender."""
        try:
            # Map frontend fields to database fields
            db_tender_data = {}
            field_mapping = {
                "source_name": "source",
                "organization": "buyer",
                "location": "province",
                "closing_date": "deadline",
                "description": "summary_ai",
            }
            
            for frontend_field, db_field in field_mapping.items():
                if frontend_field in tender_data:
                    db_tender_data[db_field] = tender_data[frontend_field]
            
            # Add other fields that don't need mapping
            for field in ["title", "external_id", "naics", "tags_ai", "scraped_at", "category", 
                         "reference", "contact_name", "contact_email", "contact_phone", 
                         "source_url", "contract_value"]:
                if field in tender_data:
                    db_tender_data[field] = tender_data[field]
            
            response = self.supabase.table("tenders").update(db_tender_data).eq("id", tender_id).execute()
            if response.data:
                # Map back to frontend format
                tender = response.data[0]
                return {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("buyer"),
                    "description": tender.get("summary_ai"),
                    "contract_value": tender.get("contract_value"),
                    "closing_date": tender.get("deadline"),
                    "source_name": tender.get("source_name"),
                    "location": tender.get("province"),
                    "url": tender.get("source_url"),
                    "created_at": tender.get("scraped_at"),
                    "updated_at": tender.get("scraped_at"),
                    "category": tender.get("category"),
                    "reference": tender.get("reference"),
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "external_id": tender.get("external_id"),
                    # New rich metadata fields
                    "summary_raw": tender.get("summary_raw"),
                    "documents_urls": tender.get("documents_urls"),
                    "original_url": tender.get("original_url"),
                }
            return None
        except Exception as e:
            logger.error(f"Error updating tender {tender_id}: {e}")
            return None
    
    async def get_tender_filters(self) -> Dict[str, Any]:
        """Get available filter options for tenders."""
        try:
            # Get unique sources
            source_response = self.supabase.table("tenders").select("source_name").execute()
            sources = list(set([tender.get("source_name") for tender in source_response.data if tender.get("source_name")]))
            
            # Get unique provinces
            province_response = self.supabase.table("tenders").select("province").execute()
            provinces = list(set([tender.get("province") for tender in province_response.data if tender.get("province")]))
            
            # Get unique categories
            category_response = self.supabase.table("tenders").select("category").execute()
            categories = list(set([tender.get("category") for tender in category_response.data if tender.get("category")]))
            
            # Get date range
            date_response = self.supabase.table("tenders").select("scraped_at").order("scraped_at", desc=False).execute()
            if date_response.data:
                earliest = date_response.data[0].get("scraped_at")
                latest = date_response.data[-1].get("scraped_at")
                date_range = {"earliest": earliest, "latest": latest}
            else:
                date_range = None
            
            return {
                "sources": sources,
                "provinces": provinces,
                "categories": categories,
                "date_range": date_range
            }
        except Exception as e:
            logger.error(f"Error getting tender filters: {e}")
            return {
                "sources": [],
                "provinces": [],
                "categories": [],
                "date_range": None
            }
    
    async def get_search_suggestions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get search suggestions based on tender titles and organizations."""
        try:
            # Search in titles
            title_response = self.supabase.table("tenders").select("title").ilike("title", f"%{query}%").limit(limit).execute()
            
            # Search in organizations
            org_response = self.supabase.table("tenders").select("organization").ilike("organization", f"%{query}%").limit(limit).execute()
            
            suggestions = []
            
            # Add title suggestions
            for tender in title_response.data:
                title = tender.get("title")
                if title and title not in [s["text"] for s in suggestions]:
                    suggestions.append({
                        "text": title,
                        "type": "title"
                    })
            
            # Add organization suggestions
            for tender in org_response.data:
                org = tender.get("organization")
                if org and org not in [s["text"] for s in suggestions]:
                    suggestions.append({
                        "text": org,
                        "type": "organization"
                    })
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching search suggestions: {e}")
            return []
    
    async def get_related_tenders(self, tender_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get related tenders based on organization, category, or similar criteria."""
        try:
            # Get the original tender
            tender_response = self.supabase.table("tenders").select("*").eq("id", tender_id).execute()
            if not tender_response.data:
                return []
            
            original_tender = tender_response.data[0]
            organization = original_tender.get("organization")
            category = original_tender.get("category")
            
            # Find related tenders by organization first, then category
            related_tenders = []
            
            if organization:
                org_response = self.supabase.table("tenders").select("*").eq("organization", organization).neq("id", tender_id).limit(limit).execute()
                related_tenders.extend(org_response.data)
            
            # If we need more, add by category
            if len(related_tenders) < limit and category:
                cat_response = self.supabase.table("tenders").select("*").eq("category", category).neq("id", tender_id).limit(limit - len(related_tenders)).execute()
                related_tenders.extend(cat_response.data)
            
            # Map to frontend format
            mapped_tenders = []
            for tender in related_tenders[:limit]:
                scraped_at = tender.get("scraped_at")
                mapped_tender = {
                    "id": tender.get("id"),
                    "title": tender.get("title"),
                    "organization": tender.get("organization") or tender.get("buyer"),
                    "source_name": tender.get("source_name") or tender.get("source"),
                    "closing_date": tender.get("closing_date") or tender.get("deadline"),
                    "created_at": scraped_at,
                    "url": tender.get("source_url"),
                }
                mapped_tenders.append(mapped_tender)
            
            return mapped_tenders
            
        except Exception as e:
            logger.error(f"Error fetching related tenders: {e}")
            return []


# Global database service instance
db_service = DatabaseService() 