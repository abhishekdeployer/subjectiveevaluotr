import os
from dotenv import load_dotenv
from models import AIModels

# Load environment variables
load_dotenv()

class Config:
    """
    Main configuration class for the Lokasewa Evaluator
    """
    
    # API Keys
    GOOGLE_AI_STUDIO_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    # API URLs
    GOOGLE_AI_STUDIO_BASE_URL = "https://generativelanguage.googleapis.com/v1"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Rate Limiting
    GEMINI_RATE_LIMIT_MAX = int(os.getenv("GEMINI_RATE_LIMIT_MAX", "1500"))
    GEMINI_RATE_LIMIT_WINDOW = int(os.getenv("GEMINI_RATE_LIMIT_WINDOW", "86400"))  # 24 hours
    
    # File Processing
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "3"))
    IMAGE_DPI = int(os.getenv("IMAGE_DPI", "300"))
    
    # Session Management
    MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "1000"))
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Timeouts (seconds)
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    
    # Currency conversion
    USD_TO_NPR_RATE = float(os.getenv("USD_TO_NPR_RATE", "142.0"))  # 1 USD = 142 NPR (as of Oct 3, 2025)
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        errors = []
        
        if not cls.GOOGLE_AI_STUDIO_API_KEY:
            errors.append("GOOGLE_AI_STUDIO_API_KEY is required")
            
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required")
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def get_model_config(cls, model_name):
        """Get configuration for a specific AI model"""
        from models import ModelSettings
        return ModelSettings.get_config(model_name)