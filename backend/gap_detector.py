#!/usr/bin/env python3
"""
Gap Detector for BidSense Enrichment Pipeline

This script identifies tenders that need manual enrichment and creates
tasks in Airtable for virtual assistants to complete.

Usage:
    python gap_detector.py --max-tasks 50 --completeness-threshold 0.8
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the app directory to the path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.services.database import db_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AirtableClient:
    """Client for interacting with Airtable API."""
    
    def __init__(self, token: str, base_id: str, table_name: str = "Tasks"):
        self.token = token
        self.base_id = base_id
        self.table_name = table_name
        self.base_url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        self.portals_url = f"https://api.airtable.com/v0/{base_id}/Portals"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # Cache for portal name to record ID mapping
        self._portal_cache = {}
    
    def get_portal_record_id(self, portal_name: str, portal_field_name: str = "Portal Name") -> Optional[str]:
        """Get the record ID for a portal name from the Portals table."""
        # Check cache first
        cache_key = f"{portal_name}_{portal_field_name}"
        if cache_key in self._portal_cache:
            return self._portal_cache[cache_key]
        
        try:
            # Search for the portal by name
            params = {
                "fields[]": [portal_field_name],
                "filterByFormula": f"{{{portal_field_name}}} = '{portal_name}'"
            }
            
            logger.info(f"Looking up Portal record for '{portal_name}' in field '{portal_field_name}'")
            
            response = requests.get(
                self.portals_url,
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                if records:
                    record_id = records[0]["id"]
                    # Cache the result
                    self._portal_cache[cache_key] = record_id
                    logger.info(f"Found Portal record ID for '{portal_name}': {record_id}")
                    return record_id
                else:
                    logger.warning(f"No Portal record found for '{portal_name}' in field '{portal_field_name}'")
                    return None
            else:
                logger.error(f"Failed to get Portal record: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Portal record ID for '{portal_name}': {e}")
            return None
    
    def create_task(self, task_data: Dict[str, Any]) -> bool:
        """Create a new task in Airtable."""
        try:
            payload = {"fields": task_data}
            
            # Debug: Log each field individually to identify the problem
            logger.info(f"Creating Airtable task with fields:")
            for field_name, field_value in task_data.items():
                logger.info(f"  {field_name}: {field_value} (type: {type(field_value).__name__})")
            
            # Debug: Log the exact payload being sent
            logger.info(f"Full payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Created Airtable task for {task_data.get('OpportunityID')}")
                return True
            else:
                logger.error(f"❌ Failed to create Airtable task: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Airtable task: {e}")
            return False
    
    def get_existing_tasks(self) -> List[str]:
        """Get list of existing opportunity IDs in Airtable to avoid duplicates."""
        try:
            # Get all records with just the OpportunityID field
            params = {
                "fields[]": ["OpportunityID"],
                "maxRecords": 1000
            }
            
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                existing_ids = []
                for record in data.get("records", []):
                    opportunity_id = record.get("fields", {}).get("OpportunityID")
                    if opportunity_id:
                        existing_ids.append(opportunity_id)
                
                logger.info(f"Found {len(existing_ids)} existing tasks in Airtable")
                return existing_ids
            else:
                logger.error(f"Failed to get existing tasks: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting existing tasks: {e}")
            return []


class GapDetector:
    """Main class for detecting and creating enrichment tasks."""
    
    def __init__(self, airtable_client: AirtableClient):
        self.airtable = airtable_client
    
    async def detect_incomplete_tenders(
        self,
        max_tasks: int = 50,
        completeness_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Detect tenders that need manual enrichment.
        
        Args:
            max_tasks: Maximum number of tasks to create
            completeness_threshold: Completeness score threshold (0.0 to 1.0) - deprecated
            
        Returns:
            List of incomplete tender dictionaries
        """
        try:
            logger.info(f"Detecting incomplete tenders")
            
            # Get incomplete tenders from the API endpoint (new format)
            response = await self._call_api_endpoint(
                "/api/v1/enrichment/incomplete",
                params={
                    "limit": max_tasks * 2,  # Get more than needed to filter
                    # Note: max_completeness parameter is no longer used
                }
            )
            
            if not response:
                logger.error("Failed to get incomplete tenders from API")
                return []
            
            # New API returns "tenders" instead of "incomplete_tenders"
            incomplete_tenders = response.get("tenders", [])
            logger.info(f"Found {len(incomplete_tenders)} incomplete tenders")
            
            return incomplete_tenders[:max_tasks]  # Limit to max_tasks
            
        except Exception as e:
            logger.error(f"Error detecting incomplete tenders: {e}")
            return []
    
    async def _call_api_endpoint(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Call a local API endpoint."""
        try:
            import httpx
            
            base_url = settings.api_base_url
            url = f"{base_url}{endpoint}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"API call failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling API endpoint {endpoint}: {e}")
            return None
    
    def map_portal_from_source(self, source_name: str) -> str:
        """Map source name to portal name for Airtable."""
        portal_mapping = {
            "canadabuys": "CanadaBuys",
            "bcbid": "BC Bid",
            "merx": "MERX",
            "bids_and_tenders": "bids&tenders",
            "sask_tenders": "SaskTenders",
            "apc": "APC",
            "manitoba": "Manitoba Tenders",
            "quebec": "SEAO"
        }
        return portal_mapping.get(source_name, source_name)
    
    def create_airtable_tasks(
        self,
        incomplete_tenders: List[Dict[str, Any]],
        existing_tasks: List[str]
    ) -> int:
        """
        Create Airtable tasks for incomplete tenders.
        
        Args:
            incomplete_tenders: List of tender dictionaries
            existing_tasks: List of existing opportunity IDs in Airtable
            
        Returns:
            Number of tasks successfully created
        """
        created_count = 0
        
        for tender in incomplete_tenders:
            try:
                opportunity_id = tender.get("external_id") or tender.get("id")  # Use tender ID if external_id is missing
                if not opportunity_id:
                    logger.warning(f"Skipping tender without external_id or id: {tender.get('title')}")
                    continue
                
                # Skip if task already exists
                if opportunity_id in existing_tasks:
                    logger.info(f"Task already exists for {opportunity_id}, skipping")
                    continue
                
                # Calculate missing fields if not provided by API
                missing_fields = tender.get("missing_fields", [])
                if not missing_fields:
                    # Calculate missing fields directly
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
                        missing_fields.append("Contact")
                    if not has_closing_date:
                        missing_fields.append("ClosingDate")
                    if not has_attachments:
                        missing_fields.append("Attachments")
                
                # Choose ONE of the following based on your Airtable field configuration:
                # Option 1: Multiple Select field (send as array)
                missing_fields_value = missing_fields  # Multiple Select needs array with correct options
                # Option 2: Long Text field (send as string) - uncomment next line if needed
                # missing_fields_value = ", ".join(missing_fields) if missing_fields else ""
                
                # Get Portal record ID from Portals table
                portal_name = self.map_portal_from_source(tender.get("source_name", ""))
                
                # Handle empty or unknown source names
                if not portal_name or portal_name == "Unknown Source" or portal_name == "":
                    portal_name = "CanadaBuys"  # Default portal
                
                # Use only PortalName field since that's what exists in Airtable
                portal_record_id = self.airtable.get_portal_record_id(portal_name, "PortalName")
                
                if not portal_record_id:
                    logger.error(f"Could not find Portal record for '{portal_name}' in PortalName field, skipping task")
                    continue
                
                # Prepare Airtable task data
                task_data = {
                    "OpportunityID": opportunity_id,
                    "SourceURL": tender.get("source_url", ""),
                    "Portal": [portal_record_id],  # Send as array of record IDs for linked field
                    "MissingFields": missing_fields_value,  # Format depends on Airtable field type
                    "Status": "Unassigned"  # Single Select field
                }
                
                # Create the task
                if self.airtable.create_task(task_data):
                    created_count += 1
                    logger.info(f"Created task {created_count}: {tender.get('title', 'Unknown')[:50]}...")
                else:
                    logger.error(f"Failed to create task for {opportunity_id}")
                    
            except Exception as e:
                logger.error(f"Error creating task for tender {tender.get('id')}: {e}")
                continue
        
        return created_count
    
    async def run_gap_detection(
        self,
        max_tasks: int = 50,
        completeness_threshold: float = 0.8,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete gap detection and task creation process.
        
        Args:
            max_tasks: Maximum number of tasks to create
            completeness_threshold: Completeness score threshold
            dry_run: If True, don't actually create tasks
            
        Returns:
            Summary of the gap detection run
        """
        logger.info("Starting gap detection process")
        
        # Get existing tasks to avoid duplicates
        existing_tasks = [] if dry_run else self.airtable.get_existing_tasks()
        
        # Detect incomplete tenders
        incomplete_tenders = await self.detect_incomplete_tenders(
            max_tasks=max_tasks,
            completeness_threshold=completeness_threshold
        )
        
        if not incomplete_tenders:
            logger.info("No incomplete tenders found")
            return {
                "status": "completed",
                "incomplete_tenders_found": 0,
                "tasks_created": 0,
                "existing_tasks": len(existing_tasks),
                "would_create": 0  # Add this for dry run consistency
            }
        
        # Filter out tenders that already have tasks
        new_tenders = [
            tender for tender in incomplete_tenders
            if tender.get("external_id") not in existing_tasks
        ]
        
        logger.info(f"Found {len(new_tenders)} new tenders needing enrichment")
        
        if dry_run:
            logger.info("DRY RUN: Would create tasks for the following tenders:")
            for tender in new_tenders:
                logger.info(f"  - {tender.get('title', 'Unknown')[:50]}... (Score: {tender.get('completeness_score', 0):.2f})")
            
            return {
                "status": "dry_run_completed",
                "incomplete_tenders_found": len(incomplete_tenders),
                "new_tenders": len(new_tenders),
                "existing_tasks": len(existing_tasks),
                "would_create": len(new_tenders)
            }
        
        # Create Airtable tasks
        tasks_created = self.create_airtable_tasks(new_tenders, existing_tasks)
        
        logger.info(f"Gap detection completed: {tasks_created} tasks created")
        
        return {
            "status": "completed",
            "incomplete_tenders_found": len(incomplete_tenders),
            "new_tenders": len(new_tenders),
            "existing_tasks": len(existing_tasks),
            "tasks_created": tasks_created
        }


async def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="BidSense Gap Detector")
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=50,
        help="Maximum number of tasks to create (default: 50)"
    )
    parser.add_argument(
        "--completeness-threshold",
        type=float,
        default=0.8,
        help="Completeness score threshold 0.0-1.0 (default: 0.8)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually creating tasks"
    )
    parser.add_argument(
        "--airtable-token",
        type=str,
        help="Airtable API token (or set AIRTABLE_TOKEN env var)"
    )
    parser.add_argument(
        "--airtable-base-id",
        type=str,
        help="Airtable base ID (or set AIRTABLE_BASE_ID env var)"
    )
    
    args = parser.parse_args()
    
    # Get Airtable credentials
    airtable_token = args.airtable_token or os.getenv("AIRTABLE_TOKEN")
    airtable_base_id = args.airtable_base_id or os.getenv("AIRTABLE_BASE_ID")
    
    if not airtable_token or not airtable_base_id:
        logger.error("Airtable token and base ID are required")
        logger.error("Set AIRTABLE_TOKEN and AIRTABLE_BASE_ID environment variables")
        logger.error("Or use --airtable-token and --airtable-base-id arguments")
        sys.exit(1)
    
    # Validate arguments
    if not 0.0 <= args.completeness_threshold <= 1.0:
        logger.error("Completeness threshold must be between 0.0 and 1.0")
        sys.exit(1)
    
    if args.max_tasks <= 0:
        logger.error("Max tasks must be greater than 0")
        sys.exit(1)
    
    try:
        # Initialize Airtable client
        airtable_client = AirtableClient(airtable_token, airtable_base_id)
        
        # Initialize gap detector
        gap_detector = GapDetector(airtable_client)
        
        # Run gap detection
        result = await gap_detector.run_gap_detection(
            max_tasks=args.max_tasks,
            completeness_threshold=args.completeness_threshold,
            dry_run=args.dry_run
        )
        
        # Print summary
        logger.info("Gap Detection Summary:")
        logger.info(f"  Status: {result['status']}")
        logger.info(f"  Incomplete tenders found: {result['incomplete_tenders_found']}")
        logger.info(f"  Existing tasks in Airtable: {result['existing_tasks']}")
        
        if args.dry_run:
            logger.info(f"  Would create: {result['would_create']} tasks")
        else:
            logger.info(f"  Tasks created: {result['tasks_created']}")
        
    except KeyboardInterrupt:
        logger.info("Gap detection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 