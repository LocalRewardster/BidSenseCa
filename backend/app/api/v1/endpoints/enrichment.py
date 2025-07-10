from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, Dict, Any
import asyncio
import subprocess
import os
from datetime import datetime, timezone

from app.services.database import db_service

router = APIRouter()

# Global status tracking
enrichment_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}

@router.get("/status")
async def get_enrichment_status():
    """Get the current status of the enrichment system."""
    try:
        # Get count of incomplete tenders
        incomplete_count = await get_incomplete_tenders_count()
        
        return {
            "status": "running" if enrichment_status["running"] else "idle",
            "last_run": enrichment_status["last_run"],
            "last_result": enrichment_status["last_result"],
            "error": enrichment_status["error"],
            "incomplete_tenders": incomplete_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting enrichment status: {str(e)}")

@router.get("/incomplete")
async def get_incomplete_tenders(
    limit: int = Query(20, ge=1, le=100),
    include_missing_fields: bool = Query(False, description="Include missing fields information for internal use")
):
    """Get list of tenders that need enrichment."""
    try:
        # Get all tenders that are not enriched (either null or false) - use all possible field names
        response = db_service.supabase.table("tenders").select(
            "id,title,organization,buyer,closing_date,deadline,contact_name,contact_email,contact_phone,description,summary_ai,documents_urls,created_at,enriched,external_id,source_name,source,source_url"
        ).neq("enriched", True).limit(limit * 2).execute()  # Get more to filter
        
        print(f"DEBUG: Found {len(response.data)} tenders with enriched!=true")
        
        incomplete_tenders = []
        
        for tender in response.data:
            if needs_enrichment(tender):
                # Build missing fields list if requested
                missing_fields = []
                if include_missing_fields:
                    # Check what fields are missing
                    contact_name = tender.get("contact_name")
                    contact_email = tender.get("contact_email") 
                    contact_phone = tender.get("contact_phone")
                    
                    has_contact = any([
                        contact_name and str(contact_name).strip() and str(contact_name).strip() not in ['', '(000) 000-0000'],
                        contact_email and str(contact_email).strip() and str(contact_email).strip() not in ['', 'N/A'],
                        contact_phone and str(contact_phone).strip() and str(contact_phone).strip() not in ['', '(000) 000-0000', '101', '5161']
                    ])
                    
                    # Use fallback logic for closing_date
                    closing_date = tender.get("closing_date") or tender.get("deadline")
                    has_closing_date = closing_date is not None and str(closing_date).strip() not in ['', 'null', 'None']
                    
                    documents_urls = tender.get("documents_urls")
                    has_attachments = documents_urls is not None and len(documents_urls) > 0
                    
                    if not has_contact:
                        missing_fields.append("contact_info")
                    if not has_closing_date:
                        missing_fields.append("closing_date")
                    if not has_attachments:
                        missing_fields.append("attachments")
                
                tender_data = {
                    "id": tender["id"],
                    "title": tender["title"],
                    "organization": tender.get("organization") or tender.get("buyer") or "Unknown Organization",  # Use fallback with default
                    "closing_date": tender.get("closing_date") or tender.get("deadline"),  # Use fallback
                    "contact_name": tender.get("contact_name"),
                    "contact_email": tender.get("contact_email"),
                    "contact_phone": tender.get("contact_phone"),
                    "description": tender.get("description") or tender.get("summary_ai"),  # Use fallback
                    "documents_urls": tender.get("documents_urls"),
                    "created_at": tender.get("created_at"),
                    "external_id": tender.get("external_id") or tender["id"],  # Use tender ID if external_id is missing
                    "source_name": tender.get("source_name") or tender.get("source") or "Unknown Source",  # Use fallback with default
                    "source_url": tender.get("source_url") or "",  # Provide empty string default
                }
                
                # Only include missing_fields if requested (for internal use)
                if include_missing_fields:
                    tender_data["missing_fields"] = missing_fields
                
                incomplete_tenders.append(tender_data)
        
        # Limit to requested number
        incomplete_tenders = incomplete_tenders[:limit]
        
        return {
            "tenders": incomplete_tenders,
            "count": len(incomplete_tenders)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching incomplete tenders: {str(e)}")

def needs_enrichment(tender: dict) -> bool:
    """
    Simple boolean check for enrichment needs.
    A tender needs enrichment if it's missing ANY of:
    - Contact info (name, email, or phone)
    - Closing date
    - Attachments (documents_urls)
    """
    # Check contact info - needs at least one contact field
    contact_name = tender.get("contact_name")
    contact_email = tender.get("contact_email") 
    contact_phone = tender.get("contact_phone")
    
    has_contact = any([
        contact_name and str(contact_name).strip() and str(contact_name).strip() not in ['', '(000) 000-0000'],
        contact_email and str(contact_email).strip() and str(contact_email).strip() not in ['', 'N/A'],
        contact_phone and str(contact_phone).strip() and str(contact_phone).strip() not in ['', '(000) 000-0000', '101', '5161']
    ])
    
    # Check closing date - use fallback logic for both old and new field names
    closing_date = tender.get("closing_date") or tender.get("deadline")
    has_closing_date = closing_date is not None and str(closing_date).strip() not in ['', 'null', 'None']
    
    # Check attachments - documents_urls should exist and have items
    documents_urls = tender.get("documents_urls")
    has_attachments = documents_urls is not None and len(documents_urls) > 0
    
    # Return True if missing ANY of the three categories
    return not has_contact or not has_closing_date or not has_attachments

@router.post("/process")
async def process_enrichment(background_tasks: BackgroundTasks, limit: int = Query(4, ge=1, le=20)):
    """Process enrichment for tenders that need it."""
    try:
        # Get tenders that need enrichment - use all possible field names
        response = db_service.supabase.table("tenders").select(
            "id,title,organization,buyer,closing_date,deadline,contact_name,contact_email,contact_phone,description,summary_ai,documents_urls,created_at,enriched,external_id,source_name,source,source_url"
        ).neq("enriched", True).limit(limit * 2).execute()
        
        tenders_to_process = []
        for tender in response.data:
            if needs_enrichment(tender):
                # Prepare tender data for Airtable
                missing_fields = []
                
                # Check what fields are missing
                contact_name = tender.get("contact_name")
                contact_email = tender.get("contact_email") 
                contact_phone = tender.get("contact_phone")
                
                has_contact = any([
                    contact_name and str(contact_name).strip() and str(contact_name).strip() not in ['', '(000) 000-0000'],
                    contact_email and str(contact_email).strip() and str(contact_email).strip() not in ['', 'N/A'],
                    contact_phone and str(contact_phone).strip() and str(contact_phone).strip() not in ['', '(000) 000-0000', '101', '5161']
                ])
                
                # Use fallback logic for closing_date
                closing_date = tender.get("closing_date") or tender.get("deadline")
                has_closing_date = closing_date is not None and str(closing_date).strip() not in ['', 'null', 'None']
                
                documents_urls = tender.get("documents_urls")
                has_attachments = documents_urls is not None and len(documents_urls) > 0
                
                if not has_contact:
                    missing_fields.append("contact_info")
                if not has_closing_date:
                    missing_fields.append("closing_date")
                if not has_attachments:
                    missing_fields.append("attachments")
                
                tender_data = {
                    "id": tender["id"],
                    "title": tender["title"],
                    "organization": tender.get("organization") or tender.get("buyer"),  # Use fallback
                    "external_id": tender.get("external_id") or tender["id"],  # Use tender ID if external_id is missing
                    "source_name": tender.get("source_name") or tender.get("source"),  # Use fallback
                    "source_url": tender.get("source_url"),
                    "missing_fields": missing_fields
                }
                tenders_to_process.append(tender_data)
                
                if len(tenders_to_process) >= limit:
                    break
        
        if not tenders_to_process:
            return {
                "message": "No tenders need enrichment",
                "processed": 0
            }
        
        # Send tenders to Airtable using the gap detector
        try:
            import sys
            import os
            
            # Add the backend directory to the path
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sys.path.append(backend_dir)
            
            from gap_detector import AirtableClient, GapDetector
            from app.config import settings
            
            # Initialize Airtable client
            airtable_token = os.getenv("AIRTABLE_TOKEN")
            airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
            
            if not airtable_token or not airtable_base_id:
                raise Exception("Airtable credentials not configured")
            
            airtable_client = AirtableClient(airtable_token, airtable_base_id)
            gap_detector = GapDetector(airtable_client)
            
            # Get existing tasks to avoid duplicates
            existing_tasks = airtable_client.get_existing_tasks()
            
            # Create Airtable tasks
            tasks_created = gap_detector.create_airtable_tasks(tenders_to_process, existing_tasks)
            
            return {
                "message": f"Enrichment process completed: {tasks_created} tasks created in Airtable",
                "processed": len(tenders_to_process),
                "tasks_created": tasks_created,
                "existing_tasks": len(existing_tasks)
            }
            
        except Exception as e:
            print(f"Error sending to Airtable: {e}")
            return {
                "message": f"Found {len(tenders_to_process)} tenders needing enrichment, but failed to send to Airtable",
                "processed": len(tenders_to_process),
                "error": str(e)
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing enrichment: {str(e)}")

async def get_incomplete_tenders_count() -> int:
    """Get count of tenders that need enrichment using simplified logic."""
    try:
        # Get all tenders that are not enriched
        response = db_service.supabase.table("tenders").select(
            "id,closing_date,contact_name,contact_email,contact_phone,documents_urls,enriched"
        ).neq("enriched", True).execute()
        
        incomplete_count = 0
        for tender in response.data:
            if needs_enrichment(tender):
                incomplete_count += 1
        
        return incomplete_count
    except Exception as e:
        print(f"Error getting incomplete tenders count: {e}")
        return 0

@router.get("/logs")
async def get_enrichment_logs(limit: int = Query(50, ge=1, le=200)):
    """Get recent enrichment logs."""
    try:
        # This could read from log files or database
        # For now, return the last result
        if enrichment_status["last_result"]:
            return {
                "logs": [
                    {
                        "timestamp": enrichment_status["last_run"],
                        "level": "INFO",
                        "message": enrichment_status["last_result"].get("output", "")
                    }
                ]
            }
        else:
            return {"logs": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}") 

@router.get("/debug")
async def debug_enrichment():
    """Debug endpoint to understand enrichment needs."""
    try:
        # Get a few tenders to debug - use all possible field names
        print("Making Supabase query...")
        response = db_service.supabase.table("tenders").select(
            "id,title,organization,buyer,closing_date,deadline,contact_name,contact_email,contact_phone,description,summary_ai,documents_urls,enriched,external_id,source_name,source,source_url"
        ).limit(5).execute()
        
        print(f"Supabase response: data={response.data} count={len(response.data) if response.data else 0}")
        
        debug_info = []
        for tender in response.data:
            print(f"Processing tender: {tender}")
            
            # Check each enrichment category
            contact_name = tender.get("contact_name")
            contact_email = tender.get("contact_email") 
            contact_phone = tender.get("contact_phone")
            
            has_contact = any([
                contact_name and str(contact_name).strip() and str(contact_name).strip() not in ['', '(000) 000-0000'],
                contact_email and str(contact_email).strip() and str(contact_email).strip() not in ['', 'N/A'],
                contact_phone and str(contact_phone).strip() and str(contact_phone).strip() not in ['', '(000) 000-0000', '101', '5161']
            ])
            
            # Use fallback logic for closing_date
            closing_date = tender.get("closing_date") or tender.get("deadline")
            has_closing_date = closing_date is not None and str(closing_date).strip() not in ['', 'null', 'None']
            
            documents_urls = tender.get("documents_urls")
            has_attachments = documents_urls is not None and len(documents_urls) > 0
            
            needs_enrichment_result = needs_enrichment(tender)
            
            # Build missing fields list for debugging (only for debug endpoint)
            missing_fields = []
            if not has_contact:
                missing_fields.append("contact_info")
            if not has_closing_date:
                missing_fields.append("closing_date")
            if not has_attachments:
                missing_fields.append("attachments")
            
            debug_info.append({
                "id": tender["id"],
                "title": tender["title"][:50] + "..." if len(tender["title"]) > 50 else tender["title"],
                "enriched": tender.get("enriched"),
                "needs_enrichment": needs_enrichment_result,
                "missing_fields": missing_fields,  # Only for debug endpoint
                "has_contact": has_contact,
                "has_closing_date": has_closing_date,
                "has_attachments": has_attachments,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "closing_date": closing_date,
                "documents_urls": documents_urls,
                "external_id": tender.get("external_id"),
                "source_name": tender.get("source_name") or tender.get("source"),  # Use fallback
                "source_url": tender.get("source_url"),
                "organization": tender.get("organization") or tender.get("buyer"),  # Use fallback
                "description": tender.get("description") or tender.get("summary_ai")  # Use fallback
            })
        
        return {
            "debug_info": debug_info,
            "total_tenders_checked": len(response.data),
            "needs_enrichment_count": sum(1 for item in debug_info if item["needs_enrichment"])
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "debug_info": [],
            "total_tenders_checked": 0
        } 