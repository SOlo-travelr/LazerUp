from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"

    # Database
    database_url: str = "postgresql+psycopg://bos:bos@localhost:5432/bos"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = "sk-replace-me"
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 3072
    extraction_model: str = "gpt-4o-mini"
    synthesis_model: str = "gpt-4o"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    jwt_secret: str = "dev-secret-change-me"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
