from app.core.config import settings
from rag_packages.shared.redis.client import RedisClient


r = RedisClient(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
)
redis_client = r.get_client()
cache_key_prefix = settings.REDIS_CACHE_KEY_PREFIX


def generate_cache_key(identifier: str) -> str:
    return RedisClient.generate_key(cache_key_prefix, identifier)
