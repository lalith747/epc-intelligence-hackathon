"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "AI Project Monitoring & Risk Engine"
    app_env: str = "development"
    app_version: str = "1.0.0"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = "sqlite+aiosqlite:///./ai_monitoring.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True

    # OpenAI (kept for optional future use; Gemini is the active provider below)
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000

    # Google Gemini
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"
    google_temperature: float = 0.7
    google_max_tokens: int = 2000

    # Security
    secret_key: str = "your_secret_key_here_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    # File Upload
    max_upload_size: int = 10485760  # 10MB
    upload_dir: str = "./uploads"
    allowed_extensions: str = ".xlsx,.xls,.csv,.json,.pdf,.png,.jpg,.jpeg,.docx,.txt,.mpp,.xml"

    # Email notifications (optional - notifications work on the dashboard
    # regardless; email is only sent if SMTP is configured)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Local app mode
    local_mode: bool = True
    seed_demo_data: bool = True
    frontend_dist_dir: str = "../frontend/dist"

    # LangGraph
    langgraph_checkpoint_ttl: int = 86400  # 24 hours
    langgraph_memory_ttl: int = 604800  # 7 days

    # Vector Database
    vector_dimension: int = 1536
    faiss_index_type: str = "IVFFlat"

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions from string"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def frontend_dist_path(self) -> Path:
        """Absolute path to the built frontend bundle."""
        return (Path(__file__).resolve().parents[2] / self.frontend_dist_dir).resolve()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
