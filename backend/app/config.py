from typing import List
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=1000, description="Maximum tokens for OpenAI requests")
    
    # SendGrid Configuration
    sendgrid_api_key: str = Field(..., description="SendGrid API key")
    sendgrid_from_email: str = Field(default="noreply@bidsense.ca", description="From email address")
    sendgrid_from_name: str = Field(default="BidSense", description="From name")
    
    # Railway Configuration
    railway_token: str = Field(default="", description="Railway API token")
    railway_project_id: str = Field(default="", description="Railway project ID")
    
    # Apify Configuration
    apify_api_token: str = Field(default="", description="Apify API token for proxy pool")
    
    # PostHog Analytics
    posthog_api_key: str = Field(default="", description="PostHog API key")
    posthog_host: str = Field(default="https://app.posthog.com", description="PostHog host URL")
    
    # Application Configuration
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=True, description="Debug mode")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Allowed CORS origins (comma-separated)"
    )
    api_base_url: str = Field(default="http://localhost:8000", description="API base URL")
    
    # Database Configuration
    database_url: str = Field(..., description="Database connection URL")
    
    # Email Configuration
    email_digest_frequency: str = Field(default="daily", description="Email digest frequency")
    email_digest_time: str = Field(default="07:00", description="Email digest time (HH:MM)")
    
    # Scraping Configuration
    scraper_interval_hours: int = Field(default=1, description="Scraper interval in hours")
    scraper_timeout_seconds: int = Field(default=30, description="Scraper timeout in seconds")
    scraper_max_retries: int = Field(default=3, description="Maximum scraper retries")
    
    # Security
    secret_key: str = Field(..., description="Application secret key")
    jwt_secret: str = Field(..., description="JWT secret key")
    
    # Feature Flags
    enable_ai_summaries: bool = Field(default=True, description="Enable AI summaries")
    enable_vector_search: bool = Field(default=True, description="Enable vector search")
    enable_email_digest: bool = Field(default=True, description="Enable email digest")
    alpha_mode: bool = Field(default=True, description="Alpha mode enabled")
    
    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 