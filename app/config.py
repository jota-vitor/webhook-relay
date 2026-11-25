from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Webhook Relay"
    database_url: str = "sqlite:///./relay.db"
    redis_url: str = "redis://localhost:6379/0"
    max_attempts: int = 8
    signature_tolerance_seconds: int = 300


settings = Settings()
