import os

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
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
