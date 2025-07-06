# BC Bid Scraper

This module implements a scraper for BC Bid tender opportunities using Playwright for session management and httpx for API calls.

## Architecture

The BC Bid scraper follows a hybrid approach:

1. **Playwright** - Used only for session establishment to obtain `_RequestVerificationToken` and session cookies
2. **httpx** - Used for all API calls (listing and detail fetching) with the obtained session credentials
3. **Concurrency** - 2 async HTTP workers with exponential back-off retries
4. **Database** - Persists rows into `tenders` table and attachments into `documents_urls[]`

## Key Functions

### `get_session()`
- Uses Playwright to navigate to BC Bid main page
- Extracts `_RequestVerificationToken` from the page
- Captures session cookies
- Returns `True` if successful, `False` otherwise

### `fetch_page(page_no)`
- Makes POST request to `/v2/opportunities/search` (TODO: confirm endpoint)
- Uses session token and cookies from `get_session()`
- Returns list of opportunity records or `None` if failed
- Implements exponential back-off retries

### `fetch_detail(opp_id)`
- Makes GET request to `/v2/opportunities/{id}` (TODO: confirm endpoint)
- Uses session token and cookies from `get_session()`
- Returns opportunity details or `None` if failed
- Implements exponential back-off retries

### `save_tender(record)`
- Transforms API record to database format
- Uses base class `save_tender()` method
- Returns `True` if successful, `False` otherwise

## TODO Items

### API Endpoints
- [ ] Confirm correct API endpoint for search (`/v2/opportunities/search`)
- [ ] Confirm correct API endpoint for details (`/v2/opportunities/{id}`)
- [ ] Test alternative endpoints if primary ones don't work

### Field Mappings
The following field mappings need to be confirmed based on actual BC Bid API response:

- [ ] `external_id` - Confirm field name (`id` vs `opportunityId`)
- [ ] `title` - Confirm field name (`title` vs `opportunityTitle`)
- [ ] `organization` - Confirm field name (`organization` vs `buyerName`)
- [ ] `location` - Confirm field name (`location` vs `province`)
- [ ] `naics` - Confirm field name (`naicsCode`)
- [ ] `closing_date` - Confirm field name (`closingDate` vs `deadline`)
- [ ] `description` - Confirm field name (`description` vs `summary`)
- [ ] `summary_raw` - Confirm field name (`rawDescription`)
- [ ] `documents_urls` - Confirm field name (`attachments` vs `documents`)
- [ ] `original_url` - Confirm field name (`url` vs `canonicalUrl`)
- [ ] `category` - Confirm field name (`category` vs `type`)
- [ ] `reference` - Confirm field name (`reference` vs `opportunityNumber`)
- [ ] `contact_name` - Confirm field name (`contactName`)
- [ ] `contact_email` - Confirm field name (`contactEmail`)
- [ ] `contact_phone` - Confirm field name (`contactPhone`)
- [ ] `source_url` - Confirm field name (`sourceUrl`)
- [ ] `contract_value` - Confirm field name (`estimatedValue` vs `budget`)
- [ ] `notice_type` - Confirm field name (`noticeType`)
- [ ] `languages` - Confirm field name (`languages`)
- [ ] `delivery_regions` - Confirm field name (`deliveryRegions`)
- [ ] `opportunity_region` - Confirm field name (`opportunityRegion`)
- [ ] `contract_duration` - Confirm field name (`contractDuration`)
- [ ] `procurement_method` - Confirm field name (`procurementMethod`)
- [ ] `selection_criteria` - Confirm field name (`selectionCriteria`)
- [ ] `commodity_unspsc` - Confirm field name (`commodityCode`)

### Configuration
- [ ] Confirm page size (currently set to 20)
- [ ] Confirm sort field (`closingDate`)
- [ ] Confirm sort order (`asc`)
- [ ] Test different payload structures for search API

### Session Management
- [ ] Test if `_RequestVerificationToken` is in a different location
- [ ] Test if additional headers are required
- [ ] Test if session cookies need specific names

## Usage

### Running the Scraper

```python
from scrapers.scrapers.bc_bid import BCBidScraper

async def main():
    async with BCBidScraper() as scraper:
        tenders = await scraper.scrape_tenders(limit=10)
        print(f"Scraped {len(tenders)} tenders")

if __name__ == "__main__":
    asyncio.run(main())
```

### Running Tests

#### Unit Tests
```bash
cd scrapers
python -m pytest tests/test_bc_bid.py -v
```

#### Integration Tests
```bash
cd scrapers
python -m pytest tests/test_bc_bid_integration.py -v -m integration
```

#### Manual Test Runner
```bash
cd scrapers
python test_bc_bid.py
```

## Testing Strategy

### 1. Unit Tests
- Mock POST `/v2/opportunities/search` responses
- Mock GET `/v2/opportunities/{id}` responses
- Test session establishment with mocked Playwright
- Test error handling and retry logic

### 2. Integration Tests
- Run first page live with Playwright
- Assert ≥ 1 row ingested
- Test API endpoint discovery
- Test page size discovery

### 3. Manual Testing
- Use `test_bc_bid.py` script for step-by-step testing
- Test session establishment
- Test API discovery
- Test first page fetch
- Test detail fetch
- Test full scrape with database ingestion

## Error Handling

The scraper implements comprehensive error handling:

- **Exponential back-off retries** for API calls
- **Session validation** before making requests
- **Graceful degradation** when endpoints fail
- **Detailed logging** for debugging

## Rate Limiting

- **2 concurrent workers** for detail fetching
- **Rate limiting** between requests (configurable)
- **Exponential back-off** for failed requests

## Database Integration

The scraper integrates with the existing database schema:

- Uses `source_name = "bcbid"`
- Maps API fields to database columns
- Handles both new and existing tender updates
- Stores attachments in `documents_urls[]` array

## Next Steps

1. **Run integration tests** to discover actual API endpoints
2. **Update field mappings** based on real API responses
3. **Test with live data** to ensure proper functionality
4. **Optimize performance** based on actual response times
5. **Add monitoring** for production deployment 