import logging
import redis
import pickle
from functools import lru_cache, wraps
from src import app

logger = logging.getLogger(__name__)

# Подключение к Redis
try:
    redis_client = redis.StrictRedis(
        host=app.config.REDIS.HOST, port=app.config.REDIS.PORT, db=app.config.REDIS.DB
    )
    redis_client.ping()  # Проверяем соединение с Redis
    redis_available = True
except redis.ConnectionError:
    logger.warning("Redis is not available, using local cache.")
    redis_available = False


# Декоратор для работы с Redis или lru_cache в зависимости от доступности
def cache(expiration_seconds):
    def decorator(func):
        if redis_available:
            return redis_cache(func, expiration_seconds)
        else:
            return lru_cache_cache(func)

    return decorator


# Реализация Redis-кеша с указанием времени жизни 1 l день по-умолчанию
def redis_cache(func, expiration_seconds=24 * 60 * 60):
    @wraps(func)
    def wrapper(*args):
        cache_key = str(args)
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return pickle.loads(cached_result)  # Возвращаем результат из Redis-кеша
        except redis.ConnectionError:
            logger.warning("Redis connection failed, switching to local cache.")
            return lru_cache_cache(func)(
                *args
            )  # В случае ошибки Redis используем lru_cache

        result = func(*args)
        try:
            redis_client.set(
                cache_key, pickle.dumps(result), ex=expiration_seconds
            )  # Устанавливаем срок действия ключа
        except redis.ConnectionError:
            logger.error("Failed to cache result in Redis, using local cache.")

        return result

    return wrapper


# Реализация lru_cache для локального кеширования
def lru_cache_cache(func):
    return lru_cache(maxsize=1024)(func)
