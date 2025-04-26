import redis
from .config import Config

redis_client = redis.from_url(Config.REDIS_CACHE_URL, decode_responses=True) # decode_responses=True decodes keys/values to strings

def init_cache():
    """Optional: Basic check if Redis is reachable (can add more robust logic)."""
    try:
        redis_client.ping()
        print("Redis cache connected successfully.")
    except redis.ConnectionError as e:
        print(f"Error connecting to Redis cache: {e}")
