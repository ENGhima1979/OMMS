from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "OMMS"
    APP_NAME_AR: str = "نظام إدارة التشغيل والصيانة"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./omms.db"

    # Security
    SECRET_KEY: str = "omms-super-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "*"]

    # File Upload
    MAX_FILE_SIZE: int = 52428800  # 50MB
    UPLOAD_DIR: str = "uploads"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"


settings = Settings()
