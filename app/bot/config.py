from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    bot_token: str
    admin_ids: list[int]
    provider_token: str = ""
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str

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
    provider_token: str = ""
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""


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
            admin_ids=settings.admin_ids,
            provider_token=settings.provider_token,
            yookassa_shop_id=settings.yookassa_shop_id,
            yookassa_secret_key=settings.yookassa_secret_key,
        ),
        db=DatabaseConfig(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            name=settings.db_name,
        ),
        redis=RedisConfig(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
        )
    )
