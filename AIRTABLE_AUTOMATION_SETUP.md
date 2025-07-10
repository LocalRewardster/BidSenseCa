# Airtable Automation Setup Guide for BidSense Enrichment

This guide walks you through setting up the Airtable automation that sends enriched data back to your BidSense system via webhook.

## Prerequisites

1. **Airtable Base Structure**: You should have a base with a "Tasks" table containing your enrichment tasks
2. **Webhook URL**: Your BidSense webhook endpoint (from setup_enrichment.py)
3. **Field Mapping**: Understanding of which Airtable fields map to which BidSense fields

## Step 1: Create the Automation

1. In your Airtable base, click **"Automations"** in the top toolbar
2. Click **"Create automation"**
3. Choose **"When a record matches conditions"** as the trigger

## Step 2: Configure the Trigger

### Trigger Settings:
- **Table**: Tasks
- **Condition**: When `Status` field changes to `Done`
- **Additional filters** (optional): Add any other conditions you need

This ensures the automation only runs when a VA marks a task as complete.

## Step 3: Add the Webhook Action

1. Click **"Add action"**
2. Choose **"Send a webhook"**
3. Configure the webhook settings:

### Webhook Configuration:
- **Method**: POST
- **URL**: `https://your-domain.com/api/v1/enrichment/webhook/airtable`
  - Replace with your actual webhook URL from setup_enrichment.py
  - For local testing: `http://localhost:8000/api/v1/enrichment/webhook/airtable`

## Step 4: Configure Input Variables

In the webhook action, you need to set up the JSON payload. Here's the complete configuration:

### Headers:
```json
{
  "Content-Type": "application/json"
}
```

### Body (JSON):
```json
{
  "opportunity_id": "{{OpportunityID}}",
  "contact_name": "{{ContactName}}",
  "contact_email": "{{ContactEmail}}",
  "closing_date": "{{ClosingDate}}",
  "attachments": "{{Attachments}}",
  "site_meeting": "{{SiteMeeting}}",
  "other_notes": "{{OtherNotes}}"
}
```

## Step 4A: RECOMMENDED - Use Simple Webhook (No JavaScript Needed)

**This is the easiest approach that avoids TypeScript errors entirely:**

Instead of using JavaScript, use Airtable's built-in webhook action with proper field mapping:

### Webhook Body Configuration:
```json
{
  "opportunity_id": "{{OpportunityID}}",
  "contact_name": "{{ContactName}}",
  "contact_email": "{{ContactEmail}}",
  "closing_date": "{{ClosingDate}}",
  "attachments": [
    {{#Attachments}}
    "{{url}}"{{#unless @last}},{{/unless}}
    {{/Attachments}}
  ],
  "site_meeting": "{{SiteMeeting}}",
  "other_notes": "{{OtherNotes}}"
}
```

**Note:** If the above Handlebars syntax doesn't work in your Airtable, use this simpler version:

```json
{
  "opportunity_id": "{{OpportunityID}}",
  "contact_name": "{{ContactName}}",
  "contact_email": "{{ContactEmail}}",
  "closing_date": "{{ClosingDate}}",
  "attachments": "{{Attachments}}",
  "site_meeting": "{{SiteMeeting}}",
  "other_notes": "{{OtherNotes}}"
}
```

Then modify your webhook endpoint to handle the attachment field properly (see Step 4B below).

## Step 4B: ULTIMATE FIX - Minimal JavaScript Version

If you must use JavaScript, here's the **simplest possible version** that works:

```javascript
// Webhook URL
let webhookURL = 'https://your-domain.com/api/v1/enrichment/webhook/airtable';

// Get the triggered record
let record = input.config();

// Simple payload - let the backend handle attachment parsing
let payload = {
    opportunity_id: record.OpportunityID,
    contact_name: record.ContactName,
    contact_email: record.ContactEmail,
    closing_date: record.ClosingDate,
    attachments: record.Attachments, // Send as-is, backend will parse
    site_meeting: record.SiteMeeting,
    other_notes: record.OtherNotes
};

// Send webhook
fetch(webhookURL, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
}).then(response => {
    if (response.ok) {
        console.log('✅ Success:', record.OpportunityID);
    } else {
        console.log('❌ Failed:', response.status);
    }
}).catch(error => {
    console.log('❌ Error:', error);
});
```

## Step 4C: Debug What Airtable Actually Sends

Add this debug script to see exactly what Airtable is sending:

```javascript
// Debug script - use this first to understand your data structure
let record = input.config();

console.log('=== DEBUGGING AIRTABLE FIELDS ===');
console.log('OpportunityID:', record.OpportunityID);
console.log('Attachments type:', typeof record.Attachments);
console.log('Attachments value:', record.Attachments);
console.log('Attachments JSON:', JSON.stringify(record.Attachments, null, 2));

// Try different ways to access attachments
if (record.Attachments) {
    console.log('Attachments exists');
    console.log('Is array?', Array.isArray(record.Attachments));
    console.log('Length:', record.Attachments.length);
    
    // Try to access first attachment
    if (record.Attachments[0]) {
        console.log('First attachment:', record.Attachments[0]);
        console.log('First attachment keys:', Object.keys(record.Attachments[0]));
    }
}

console.log('=== END DEBUG ===');
```

**Run this debug script first**, then look at the console output to see exactly how Airtable structures your attachment field.

## Step 4D: Backend Fix (Recommended Approach)

The best approach is to handle attachment parsing in your backend. Update your webhook endpoint to properly parse Airtable's attachment format:

```python
# Add this to your enrichment.py webhook handler
def parse_airtable_attachments(attachments_field):
    """Parse Airtable attachments field into URLs."""
    if not attachments_field:
        return None
    
    # Handle different formats Airtable might send
    if isinstance(attachments_field, str):
        # If it's already a URL string
        return [attachments_field]
    
    if isinstance(attachments_field, list):
        urls = []
        for attachment in attachments_field:
            if isinstance(attachment, dict) and 'url' in attachment:
                urls.append(attachment['url'])
            elif isinstance(attachment, str):
                urls.append(attachment)
        return urls if urls else None
    
    if isinstance(attachments_field, dict) and 'url' in attachments_field:
        return [attachments_field['url']]
    
    return None

# Update your webhook handler
@router.post("/webhook/airtable", response_model=EnrichmentStatus)
async def handle_airtable_webhook(payload: AirtableWebhookPayload):
    # ... existing code ...
    
    # Parse attachments properly
    if payload.attachments:
        parsed_attachments = parse_airtable_attachments(payload.attachments)
        if parsed_attachments:
            update_data["documents_urls"] = parsed_attachments
            updated_fields["documents_urls"] = parsed_attachments
    
    # ... rest of existing code ...
```

## Step 5: Field Mapping Reference

Make sure your Airtable "Tasks" table has these fields:

| Airtable Field Name | Field Type | Description | Required |
|-------------------|------------|-------------|----------|
| `OpportunityID` | Single line text | The unique identifier for the tender | ✅ Yes |
| `ContactName` | Single line text | Contact person name | No |
| `ContactEmail` | Email | Contact email address | No |
| `ClosingDate` | Date | Tender closing/deadline date | No |
| `Attachments` | Attachment | Documents/files related to tender | No |
| `SiteMeeting` | Long text | Site meeting or selection criteria info | No |
| `OtherNotes` | Long text | Additional notes from manual research | No |
| `Status` | Single select | Task status (Unassigned, In Progress, Done) | ✅ Yes |
| `SourceURL` | URL | Original tender URL | No |
| `Portal` | Single select | Source portal (CanadaBuys, MERX, etc.) | No |

## Step 6: Advanced JavaScript Configuration (FIXED VERSION)

If you need more control over the data transformation, you can use a "Run a script" action instead of the webhook action. Here's the **corrected JavaScript** that fixes the TypeScript error:

### Script Configuration (Fixed):
```javascript
// Get the webhook URL from your environment
let webhookURL = 'https://your-domain.com/api/v1/enrichment/webhook/airtable';

// Get the record that triggered the automation
let record = input.config();

// Extract attachment URLs from Airtable attachment field (FIXED)
let attachmentUrls = [];
if (record.Attachments) {
    // Handle both array and single attachment cases
    if (Array.isArray(record.Attachments)) {
        attachmentUrls = record.Attachments.map(attachment => {
            // Check if attachment is an object with url property
            if (typeof attachment === 'object' && attachment.url) {
                return attachment.url;
            }
            // If it's already a string URL, return it
            return attachment;
        }).filter(url => url); // Remove any null/undefined values
    } else if (typeof record.Attachments === 'string') {
        // If it's a single string URL
        attachmentUrls = [record.Attachments];
    } else if (typeof record.Attachments === 'object' && record.Attachments.url) {
        // If it's a single attachment object
        attachmentUrls = [record.Attachments.url];
    }
}

// Prepare the payload
let payload = {
    opportunity_id: record.OpportunityID,
    contact_name: record.ContactName || null,
    contact_email: record.ContactEmail || null,
    closing_date: record.ClosingDate || null,
    attachments: attachmentUrls.length > 0 ? attachmentUrls : null,
    site_meeting: record.SiteMeeting || null,
    other_notes: record.OtherNotes || null
};

// Send the webhook
try {
    let response = await fetch(webhookURL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });
    
    if (response.ok) {
        console.log('✅ Webhook sent successfully for:', record.OpportunityID);
        console.log('📎 Attachments found:', attachmentUrls.length);
    } else {
        console.error('❌ Webhook failed:', response.status, response.statusText);
    }
} catch (error) {
    console.error('❌ Error sending webhook:', error);
}
```

## Alternative: Simpler JavaScript Version (Recommended)

If you're still getting TypeScript errors, try this simpler version:

```javascript
// Get the webhook URL
let webhookURL = 'https://your-domain.com/api/v1/enrichment/webhook/airtable';

// Get the record that triggered the automation
let record = input.config();

// Handle attachments more safely
let attachmentUrls = [];
try {
    if (record.Attachments) {
        // Convert to string and parse if needed
        let attachments = record.Attachments;
        if (typeof attachments === 'string') {
            // If it's already a string (URL), use it
            attachmentUrls = [attachments];
        } else if (attachments.length) {
            // If it's an array, extract URLs
            for (let i = 0; i < attachments.length; i++) {
                let attachment = attachments[i];
                if (attachment && attachment.url) {
                    attachmentUrls.push(attachment.url);
                }
            }
        }
    }
} catch (e) {
    console.log('Note: Could not process attachments:', e);
}

// Prepare the payload
let payload = {
    opportunity_id: record.OpportunityID,
    contact_name: record.ContactName || null,
    contact_email: record.ContactEmail || null,
    closing_date: record.ClosingDate || null,
    attachments: attachmentUrls.length > 0 ? attachmentUrls : null,
    site_meeting: record.SiteMeeting || null,
    other_notes: record.OtherNotes || null
};

// Send the webhook
try {
    let response = await fetch(webhookURL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });
    
    if (response.ok) {
        console.log('✅ Webhook sent successfully for:', record.OpportunityID);
    } else {
        console.error('❌ Webhook failed:', response.status, response.statusText);
    }
} catch (error) {
    console.error('❌ Error sending webhook:', error);
}
```

## Step 7: Input Variable Setup for Script Action

If using the script action, configure these input variables:

1. **Record**: Select "Record (from trigger)"
2. **Fields to include**: Select all the fields you need:
   - OpportunityID
   - ContactName
   - ContactEmail
   - ClosingDate
   - Attachments
   - SiteMeeting
   - OtherNotes

## Step 8: Troubleshooting TypeScript Errors

### Common TypeScript Issues in Airtable:

1. **Property 'url' does not exist on type 'string'**
   - **Cause**: Airtable's TypeScript is strict about attachment field types
   - **Solution**: Use the safer JavaScript versions above

2. **Cannot read property 'map' of undefined**
   - **Cause**: Attachments field might be empty or null
   - **Solution**: Always check if the field exists before processing

3. **Type 'unknown' is not assignable to type 'string'**
   - **Cause**: Airtable doesn't know the exact type of your fields
   - **Solution**: Use type checking (`typeof`) before operations

### Debug Your Attachments:

Add this debug code to see what your attachments field contains:

```javascript
// Debug: Log the attachments field structure
console.log('Attachments field type:', typeof record.Attachments);
console.log('Attachments field value:', record.Attachments);

if (record.Attachments) {
    console.log('Is array:', Array.isArray(record.Attachments));
    if (Array.isArray(record.Attachments)) {
        console.log('Array length:', record.Attachments.length);
        if (record.Attachments.length > 0) {
            console.log('First attachment:', record.Attachments[0]);
            console.log('First attachment type:', typeof record.Attachments[0]);
        }
    }
}
```

## Step 9: Test the Automation

### Testing Steps:
1. **Create a test record** in your Tasks table
2. **Fill in some enrichment data** (contact info, etc.)
3. **Add a test attachment** to verify URL extraction
4. **Change the Status to "Done"**
5. **Check the automation run log** in Airtable
6. **Verify the webhook was received** in your BidSense logs

### Testing Checklist:
- [ ] Automation triggers when Status changes to "Done"
- [ ] No TypeScript errors in automation log
- [ ] Webhook payload contains correct data
- [ ] Attachment URLs are properly extracted
- [ ] BidSense receives and processes the webhook
- [ ] Tender is marked as enriched in database

## Step 10: Common Issues and Solutions

### Issue: Automation doesn't trigger
- **Solution**: Check that the trigger condition matches exactly
- **Check**: Ensure the Status field value is exactly "Done" (case-sensitive)

### Issue: TypeScript errors in automation
- **Solution**: Use the safer JavaScript versions provided above
- **Check**: Add debug logging to understand your field types

### Issue: Webhook returns 404 error
- **Solution**: Verify the webhook URL is correct
- **Check**: Ensure your BidSense backend is running and accessible

### Issue: Attachment URLs not working
- **Solution**: Airtable attachment URLs expire after 2 hours
- **Check**: Process attachments immediately or store them permanently

### Issue: Date format errors
- **Solution**: Ensure dates are in ISO format (YYYY-MM-DD)
- **Check**: Use Airtable's date formatting options

## Step 11: Production Considerations

### Security:
- Use HTTPS URLs for webhooks
- Consider adding authentication headers if needed
- Validate webhook signatures if implementing

### Monitoring:
- Set up logging in your BidSense system
- Monitor automation run history in Airtable
- Track success/failure rates

### Scaling:
- Consider rate limiting for high-volume operations
- Implement retry logic for failed webhooks
- Monitor API usage limits

## Example Airtable Table Structure

Here's what your Tasks table should look like:

| OpportunityID | SourceURL | Portal | Status | ContactName | ContactEmail | ClosingDate | Attachments | SiteMeeting | OtherNotes |
|---------------|-----------|---------|---------|-------------|--------------|-------------|-------------|-------------|------------|
| RFP-2024-001 | https://... | CanadaBuys | Done | John Smith | john@gov.ca | 2024-02-15 | [file1.pdf] | Site visit required | Updated requirements |
| RFP-2024-002 | https://... | MERX | In Progress | | | | | | |

## Webhook Payload Example

When the automation runs, it will send this JSON to your webhook:

```json
{
  "opportunity_id": "RFP-2024-001",
  "contact_name": "John Smith",
  "contact_email": "john@gov.ca",
  "closing_date": "2024-02-15",
  "attachments": ["https://dl.airtable.com/.attachments/file1.pdf"],
  "site_meeting": "Site visit required",
  "other_notes": "Updated requirements"
}
```

## Support

If you encounter issues:
1. Check the Airtable automation logs
2. Verify your webhook URL is accessible
3. Test with a simple payload first
4. Check your BidSense backend logs for errors
5. Use the debug JavaScript code to understand field types

Remember to replace `https://your-domain.com` with your actual domain in all webhook URLs! 