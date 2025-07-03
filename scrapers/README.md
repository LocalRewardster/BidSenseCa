# BidSense Scrapers

Playwright-based scraping scripts for Canadian tender portals.

## Supported Sources

- **CanadaBuys** (canadabuys.canada.ca) - Federal government procurement
- **Ontario Portal** (ontariotenders.com) - Ontario tenders
- **Alberta Purchasing Connection** (alberta.bidsandtenders.ca) - Alberta tenders

## Setup

```bash
# Install dependencies
poetry install

# Install Playwright browsers
poetry run install-browsers

# Copy environment variables
cp ../.env.example .env
# Fill in your Supabase credentials
```

## Usage

```bash
# Run all scrapers
poetry run scrape-all

# Run with specific options
python -m scrapers.runner --limit 100
```

## Configuration

Set these environment variables in your `.env` file:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
APIFY_API_TOKEN=your_apify_token  # Optional, for proxy pool
```

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run flake8 .
``` 