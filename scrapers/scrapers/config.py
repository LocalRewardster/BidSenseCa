from typing import Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class ScraperSettings(BaseSettings):
    """Configuration for scrapers."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    
    # Apify Configuration (for proxy pool)
    apify_api_token: Optional[str] = Field(default=None, description="Apify API token for proxy pool")
    
    # Scraping Configuration
    scraper_timeout_seconds: int = Field(default=30, description="Scraper timeout in seconds")
    scraper_max_retries: int = Field(default=3, description="Maximum scraper retries")
    scraper_delay_seconds: float = Field(default=1.0, description="Delay between requests")
    
    # Browser Configuration
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_type: str = Field(default="chromium", description="Browser type (chromium, firefox, webkit)")
    
    # Rate Limiting
    requests_per_minute: int = Field(default=60, description="Maximum requests per minute")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Allow extra fields from the full environment file
    )


# Global settings instance
settings = ScraperSettings() 