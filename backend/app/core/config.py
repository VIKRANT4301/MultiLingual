import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Multilingual Voice-First Revenue Services Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("JWT_SECRET", "super-secret-key-for-poc-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./revenue_services.db")
    
    # AI Config
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")  # 'local' or 'cloud'
    SPEECH_PROVIDER: str = os.getenv("SPEECH_PROVIDER", "local")  # browser/local
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "local")  # mock/local
    PAYMENT_PROVIDER: str = os.getenv("PAYMENT_PROVIDER", "mock")
    
    # Cloud AI credentials (if provided)
    CLOUD_LLM_URL: str = os.getenv("CLOUD_LLM_URL", "")
    CLOUD_LLM_API_KEY: str = os.getenv("CLOUD_LLM_API_KEY", "")

    # Groq & OpenRouter settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    # WhatsApp Cloud API configurations
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
