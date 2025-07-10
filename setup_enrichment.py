#!/usr/bin/env python3
"""
BidSense Enrichment Setup Helper

This script helps you set up the human-in-the-loop enrichment system.
"""

import os
import sys
from pathlib import Path

def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num: int, title: str, description: str):
    """Print a formatted step."""
    print(f"\n{step_num}. {title}")
    print("-" * (len(title) + 3))
    print(description)

def main():
    """Main setup function."""
    print_header("BidSense Enrichment Setup Guide")
    
    print("""
This guide will help you set up the human-in-the-loop enrichment system
for BidSense. The system uses Airtable for task management and webhooks
to sync enriched data back to your database.
    """)
    
    print_step(
        1,
        "Database Migration",
        """
Run the database migration to add enrichment tracking fields:

From your backend directory:
cd backend
# Apply the migration to add enrichment fields
# This adds 'enriched' and 'enriched_at' columns to the tenders table
        """
    )
    
    print_step(
        2,
        "Webhook URL for Airtable",
        f"""
Your webhook URL for the Airtable automation is:

🔗 {os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/enrichment/webhook/airtable

This endpoint receives enriched data from Airtable when VAs complete tasks.

For production, replace localhost with your actual domain:
https://your-domain.com/api/v1/enrichment/webhook/airtable
        """
    )
    
    print_step(
        3,
        "Environment Variables",
        """
Add these environment variables to your backend/.env file:

# Airtable Configuration
AIRTABLE_TOKEN=your_airtable_personal_access_token
AIRTABLE_BASE_ID=your_base_id_from_airtable_url

# API Base URL (for gap detector)
API_BASE_URL=http://localhost:8000  # or your production URL

To get your Airtable credentials:
1. Go to https://airtable.com/developers/web/api/introduction
2. Create a Personal Access Token with read/write permissions
3. Copy your base ID from the Airtable URL (starts with 'app')
        """
    )
    
    print_step(
        4,
        "Test the Webhook Endpoint",
        """
Test that your webhook endpoint is working:

curl -X POST http://localhost:8000/api/v1/enrichment/webhook/airtable \\
  -H "Content-Type: application/json" \\
  -d '{
    "opportunity_id": "test-123",
    "contact_name": "John Doe",
    "contact_email": "john@example.com"
  }'

Expected response: {"success": false, ...} (tender not found is expected for test data)
        """
    )
    
    print_step(
        5,
        "Run the Gap Detector",
        """
Test the gap detector to see which tenders need enrichment:

# Dry run (doesn't create tasks)
python backend/gap_detector.py --dry-run --max-tasks 10

# Create actual tasks in Airtable
python backend/gap_detector.py --max-tasks 25 --completeness-threshold 0.8

The gap detector will:
- Find tenders with completeness scores ≤ 0.8
- Check for existing tasks in Airtable
- Create new tasks for incomplete tenders
        """
    )
    
    print_step(
        6,
        "Airtable Automation JavaScript",
        """
Use this JavaScript code in your Airtable automation:

let webhookURL = 'YOUR_WEBHOOK_URL_FROM_STEP_2';
let record = input.config();

// Extract attachment URLs from Airtable
let attachmentUrls = [];
if (record.Attachments) {
    attachmentUrls = record.Attachments.map(att => att.url);
}

let payload = {
    opportunity_id: record.OpportunityID,
    contact_name: record.ContactName || null,
    contact_email: record.ContactEmail || null,
    closing_date: record.ClosingDate || null,
    attachments: attachmentUrls.length > 0 ? attachmentUrls : null,
    site_meeting: record.SiteMeeting || null,
    other_notes: record.OtherNotes || null
};

await fetch(webhookURL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
});

console.log('Webhook sent for:', record.OpportunityID);
        """
    )
    
    print_step(
        7,
        "Test the Complete Flow",
        """
Test the complete enrichment flow:

1. Run gap detector to create tasks
2. Complete a task in Airtable with enriched data
3. Verify the webhook updates your database
4. Check the enrichment status endpoint:

curl http://localhost:8000/api/v1/enrichment/status/OPPORTUNITY_ID
        """
    )
    
    print_step(
        8,
        "Monitor and Scale",
        """
Monitor your enrichment pipeline:

# Check incomplete tenders
curl http://localhost:8000/api/v1/enrichment/incomplete

# Run gap detector daily with cron
0 9 * * * cd /path/to/bidsense && python backend/gap_detector.py --max-tasks 50

# Scale VAs based on task volume
- 1 VA can handle ~100 tasks/day (3 min/task)
- Monitor Airtable metrics for throughput
- Adjust completeness threshold based on quality needs
        """
    )
    
    print_header("Setup Complete!")
    
    print("""
Your enrichment system is now configured! 

🎯 Next Steps:
1. Apply the database migration
2. Update your environment variables  
3. Set up the Airtable automation
4. Run a test with the gap detector
5. Train your VAs using the Airtable interface

📊 Key URLs:
- Webhook: /api/v1/enrichment/webhook/airtable
- Status: /api/v1/enrichment/status/{opportunity_id}
- Incomplete: /api/v1/enrichment/incomplete

💡 Pro Tips:
- Start with a completeness threshold of 0.8
- Monitor VA performance with Airtable metrics
- Use dry-run mode to test before creating tasks
- Set up daily cron jobs for automated gap detection
    """)

if __name__ == "__main__":
    main() 