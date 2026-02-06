from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from decimal import Decimal


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_URL: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    MAX_ACTIVE_LOANS: int
    LOAN_DURATION_DAYS: int
    DAILY_FINE: Decimal
    MAX_PAGE_SIZE: int
    RATE_LIMIT_TIMES: int
    RATE_LIMIT_SECONDS: int
    NOTIFICATION_DUE_SOON_DAYS: int
    NOTIFICATION_MAX_PER_RUN: int
    NOTIFICATION_SCHEDULER_SECONDS: int

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()  # type: ignore
