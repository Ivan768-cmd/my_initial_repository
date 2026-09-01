from dataclasses import dataclass
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    bot_token: str
    admin_ids: list[int]

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]


@dataclass
class Config:
    bot: TgBot
    db: DatabaseConfig
    redis: RedisConfig


def load_config() -> Config:
    settings = Settings()

    return Config(
        bot=TgBot(
            token=settings.bot_token,
            admin_ids=settings.admin_ids
        ),
        db=DatabaseConfig(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            name=settings.db_name
        ),
        redis=RedisConfig(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
    )
