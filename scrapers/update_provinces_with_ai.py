#!/usr/bin/env python3
"""
Script to update existing tender provinces using AI detection.
This will re-analyze all tenders in the database and update their province classifications.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.database import db_service
from app.services.ai_province_service import ai_province_service

async def fetch_all_tenders() -> List[Dict[str, Any]]:
    """Fetch all tenders from the database."""
    try:
        result = db_service.supabase.table('tenders').select('*').execute()
        return result.data
    except Exception as e:
        print(f"Error fetching tenders: {e}")
        return []

async def update_tender_province(tender_id: str, new_province: str, confidence: float, reasoning: str) -> bool:
    """Update a tender's province in the database."""
    try:
        result = db_service.supabase.table('tenders').update({
            'province': new_province,
            'updated_at': 'now()'
        }).eq('id', tender_id).execute()
        
        return len(result.data) > 0
    except Exception as e:
        print(f"Error updating tender {tender_id}: {e}")
        return False

async def update_provinces_with_ai():
    """Update all tender provinces using AI detection."""
    
    print("AI Province Detection Update Script")
    print("=" * 50)
    print("This script will re-analyze all tenders using AI and update their province classifications.")
    
    # Fetch all tenders
    print("\n1. Fetching all tenders from database...")
    tenders = await fetch_all_tenders()
    
    if not tenders:
        print("No tenders found in database.")
        return
    
    print(f"Found {len(tenders)} tenders to analyze.")
    
    # Ask for confirmation
    response = input(f"\nProceed with AI analysis of {len(tenders)} tenders? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Process tenders in batches
    batch_size = 10
    total_updated = 0
    total_errors = 0
    province_changes = {}
    
    print(f"\n2. Processing tenders in batches of {batch_size}...")
    
    for i in range(0, len(tenders), batch_size):
        batch = tenders[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(tenders) + batch_size - 1) // batch_size
        
        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} tenders)...")
        
        for tender in batch:
            try:
                # Prepare tender data for AI analysis
                tender_data = {
                    'title': tender.get('title', ''),
                    'organization': tender.get('buyer', ''),
                    'category': tender.get('category', ''),
                    'summary_raw': tender.get('summary_raw', ''),
                    'url': tender.get('url', ''),
                    'province': tender.get('province', '')  # Current province for context
                }
                
                # Skip if no meaningful data
                if not tender_data['title'] and not tender_data['organization']:
                    print(f"  Skipping tender {tender['id']} - insufficient data")
                    continue
                
                # Detect province using AI
                result = await ai_province_service.detect_province(tender_data)
                
                current_province = tender.get('province', '')
                new_province = result.province
                
                # Log the analysis
                title_preview = tender_data['title'][:50] + "..." if len(tender_data['title']) > 50 else tender_data['title']
                print(f"  {title_preview}")
                print(f"    Current: {current_province} → AI: {new_province} (confidence: {result.confidence:.2f})")
                
                # Track province changes
                if current_province != new_province:
                    change_key = f"{current_province} → {new_province}"
                    province_changes[change_key] = province_changes.get(change_key, 0) + 1
                    print(f"    Reasoning: {result.reasoning}")
                
                # Update the tender in the database
                if await update_tender_province(tender['id'], new_province, result.confidence, result.reasoning):
                    total_updated += 1
                else:
                    total_errors += 1
                    print(f"    ❌ Failed to update database")
                
            except Exception as e:
                total_errors += 1
                print(f"  ❌ Error processing tender {tender.get('id', 'unknown')}: {e}")
        
        # Small delay between batches to avoid overwhelming the API
        if i + batch_size < len(tenders):
            print("  Waiting 2 seconds before next batch...")
            await asyncio.sleep(2)
    
    # Print summary
    print(f"\n{'='*50}")
    print("UPDATE SUMMARY")
    print(f"{'='*50}")
    print(f"Total tenders processed: {len(tenders)}")
    print(f"Successfully updated: {total_updated}")
    print(f"Errors: {total_errors}")
    
    if province_changes:
        print(f"\nProvince Changes:")
        for change, count in sorted(province_changes.items()):
            print(f"  {change}: {count} tenders")
    else:
        print("\nNo province changes detected.")
    
    print(f"\n✅ AI province detection update completed!")

async def test_single_tender():
    """Test AI province detection on a single tender for debugging."""
    
    print("Testing AI Province Detection on Single Tender")
    print("=" * 50)
    
    # Test with the problematic Halifax Regional Municipality tender
    tender_id = "de15c978-1a2d-47ad-9453-65218dc41b8f"
    
    try:
        # Fetch the specific tender
        result = db_service.supabase.table('tenders').select('*').eq('id', tender_id).execute()
        
        if not result.data:
            print(f"Tender {tender_id} not found in database.")
            return
        
        tender = result.data[0]
        
        print(f"Tender ID: {tender['id']}")
        print(f"Title: {tender.get('title', 'N/A')}")
        print(f"Organization: {tender.get('buyer', 'N/A')}")
        print(f"Current Province: {tender.get('province', 'N/A')}")
        
        # Prepare tender data for AI analysis
        tender_data = {
            'title': tender.get('title', ''),
            'organization': tender.get('buyer', ''),
            'category': tender.get('category', ''),
            'summary_raw': tender.get('summary_raw', ''),
            'url': tender.get('url', ''),
            'province': tender.get('province', '')
        }
        
        # Detect province using AI
        ai_result = await ai_province_service.detect_province(tender_data)
        
        print(f"\nAI Analysis:")
        print(f"Detected Province: {ai_result.province}")
        print(f"Confidence: {ai_result.confidence:.2f}")
        print(f"Reasoning: {ai_result.reasoning}")
        
        if ai_result.province == 'NS':
            print("✅ CORRECT - Halifax Regional Municipality correctly identified as Nova Scotia")
        else:
            print(f"❌ UNEXPECTED - Expected NS for Halifax Regional Municipality, got {ai_result.province}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

async def main():
    """Main function to run the update script."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        await test_single_tender()
    else:
        await update_provinces_with_ai()

if __name__ == "__main__":
    asyncio.run(main()) 