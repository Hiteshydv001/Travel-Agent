import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Settings(BaseSettings):
    """
    Application settings.
    """
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Trip Planner API"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # LLM Settings
    GOOGLE_API_KEY: str = ""
    
    # Email Settings
    GMAIL_SENDER_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    SENDGRID_API_KEY: str = ""
    SENDER_EMAIL: str = ""
    
    # Amadeus API Settings
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    
    # SerpAPI Settings
    SERP_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("Starting up AI Trip Planner API...")

# Validation checks for required settings
if not settings.GOOGLE_API_KEY:
    logger.error("FATAL: GOOGLE_API_KEY is not set.")
    raise ValueError("GOOGLE_API_KEY is not set.")
if not settings.SERP_API_KEY:
    logger.error("FATAL: SERP_API_KEY is not set.")
    raise ValueError("SERP_API_KEY is not set.")

logger.info("Application settings loaded and validated successfully.")