import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Configure logging to provide rich output for debugging and monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Settings(BaseSettings):
    """
    Manages application settings and secrets using pydantic-settings.
    It automatically reads from a .env file.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    # API Version
    API_V1_STR: str = "/api/v1"

    # LLM Provider
    GOOGLE_API_KEY: str

    # Tool APIs
    SERP_API_KEY: str
    AMADEUS_CLIENT_ID: Optional[str] = None
    AMADEUS_CLIENT_SECRET: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    SENDER_EMAIL: Optional[str] = None
    
    # Project Info
    PROJECT_NAME: str = "AI Trip Planner"

# Instantiate the settings
settings = Settings()
logger = logging.getLogger(__name__)

# Perform validation checks on startup to ensure the application is configured correctly
if not settings.GOOGLE_API_KEY:
    logger.error("FATAL: GOOGLE_API_KEY is not set. The application cannot function.")
    raise ValueError("GOOGLE_API_KEY is not set. Please check your .env file.")
if not settings.SERP_API_KEY:
    logger.error("FATAL: SERP_API_KEY is not set. Search tools will fail.")
    raise ValueError("SERP_API_KEY is not set. Please check your .env file.")

logger.info("Application settings loaded and validated successfully.")