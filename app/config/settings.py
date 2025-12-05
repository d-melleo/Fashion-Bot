"""
Налаштування додатку
Завантажує конфігурацію з .env файлу
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


# Базова директорія проєкту
BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    """Налаштування додатку"""
    
    # ========================================
    # TELEGRAM BOT
    # ========================================
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    BOT_USERNAME: str = Field(..., description="Bot Username")
    OWNER_TELEGRAM_ID: int = Field(..., description="Owner Telegram ID")
    
    # ========================================
    # MONGODB
    # ========================================
    MONGO_ROOT_USERNAME: str = Field(default="admin")
    MONGO_ROOT_PASSWORD: str = Field(...)
    MONGO_DATABASE: str = Field(default="FashionBot")
    MONGO_HOST: str = Field(default="cluster0.qh8t139.mongodb.net")
    MONGO_PORT: int = Field(default=27017)
    
    @property
    def MONGODB_URL(self) -> str:
        """Формує URL для підключення до MongoDB"""
        return (
            f"mongodb+srv://{self.MONGO_ROOT_USERNAME}:{self.MONGO_ROOT_PASSWORD}"
            f"@{self.MONGO_HOST}"
            f"/{self.MONGO_DATABASE}"  # Add database name
            f"?retryWrites=true&w=majority"  # Add recommended options
        )
    
    # ========================================
    # RABBITMQ
    # ========================================
    RABBITMQ_USER: str = Field(default="fashion_bot")
    RABBITMQ_PASSWORD: str = Field(...)
    RABBITMQ_HOST: str = Field(default="rabbitmq")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_QUEUE_NAME: str = Field(default="ai_generation_queue")
    
    @property
    def RABBITMQ_URL(self) -> str:
        """Формує URL для підключення до RabbitMQ"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
        )
    
    # ========================================
    # AI PROVIDERS
    # ========================================
    GEMINI_API_KEY: str = Field(...)
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")
    GEMINI_TEMPERATURE: float = Field(default=0.7)
    GEMINI_MAX_TOKENS: int = Field(default=2048)
    
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4")
    OPENAI_TEMPERATURE: float = Field(default=0.7)
    OPENAI_MAX_TOKENS: int = Field(default=2048)
    
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-opus-20240229")
    ANTHROPIC_TEMPERATURE: float = Field(default=0.7)
    ANTHROPIC_MAX_TOKENS: int = Field(default=2048)
    
    ACTIVE_AI_PROVIDER: str = Field(default="gemini")
    
    # ========================================
    # LIQPAY
    # ========================================
    LIQPAY_PUBLIC_KEY: str = Field(...)
    LIQPAY_PRIVATE_KEY: str = Field(...)
    LIQPAY_TEST_MODE: bool = Field(default=True)
    
    SUBSCRIPTION_PRICE: float = Field(default=10.00)
    SUBSCRIPTION_CURRENCY: str = Field(default="USD")
    
    CURRENCY_CONVERSION_KEY: str = Field(...)
    
    # ========================================
    # WEB APP
    # ========================================
    WEBAPP_URL: str = Field(default="https://your-webapp-domain.com")
    FAKE_STORE_API_URL: str = Field(default="https://fakestoreapi.com")
    
    # ========================================
    # LOGGING
    # ========================================
    LOG_LEVEL: str = Field(default="DEBUG")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE_PATH: str = Field(default=str(BASE_DIR / "logs" / "bot.log"))
    LOG_MAX_BYTES: int = Field(default=10485760)  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5)
    
    # ========================================
    # RATE LIMITING
    # ========================================
    RATE_LIMIT_REQUESTS: int = Field(default=10)
    RATE_LIMIT_PERIOD: int = Field(default=60)  # seconds
    
    # ========================================
    # SECURITY
    # ========================================
    SECRET_KEY: str = Field(...)
    
    # ========================================
    # FEATURE FLAGS
    # ========================================
    ENABLE_TRIAL_REQUEST: bool = Field(default=True)
    ENABLE_WEBAPP: bool = Field(default=True)
    ENABLE_STYLIST_REQUESTS: bool = Field(default=True)
    
    # ========================================
    # APPLICATION
    # ========================================
    ENVIRONMENT: str = Field(default="development")
    TIMEZONE: str = Field(default="Europe/Kiev")
    DEFAULT_LANGUAGE: str = Field(default="uk")
    
    # ========================================
    # DOCKER SETTINGS
    # ========================================
    COMPOSE_PROJECT_NAME: str = Field(default="fashion_bot")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()


# Валідація критичних налаштувань
def validate_settings():
    """Валідація критичних налаштувань"""
    required_fields = [
        'BOT_TOKEN',
        'MONGO_ROOT_PASSWORD',
        'RABBITMQ_PASSWORD',
        'GEMINI_API_KEY',
        'LIQPAY_PUBLIC_KEY',
        'LIQPAY_PRIVATE_KEY',
        'SECRET_KEY',
    ]
    
    missing_fields = []
    for field in required_fields:
        value = getattr(settings, field, None)
        if not value or value == "your_" + field.lower() + "_here":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_fields)}\n"
            f"Please check your .env file"
        )


# Автоматична валідація при імпорті
if settings.ENVIRONMENT != "development":
    validate_settings()