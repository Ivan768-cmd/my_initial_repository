from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.config import Config


def get_redis_storage(config: Config) -> RedisStorage:
    redis = Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
    )
    return RedisStorage(redis=redis)
