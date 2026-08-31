from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量或项目根目录的 .env 文件加载运行配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Agent Task Platform"
    app_env: str = "dev"
    debug: bool = True
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/agent_task_db"
    )
    jwt_secret_key: str = Field(default="please-change-this-secret", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, gt=0)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次依赖注入都重复解析环境变量。"""
    return Settings()
