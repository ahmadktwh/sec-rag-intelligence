import json
import logging
import os
import hashlib
from typing import Optional, Any
import redis
from dotenv import load_dotenv

# Setup Logging
logger = logging.getLogger(__name__)

class CacheManager:
    """
    Handles API response caching using Redis.
    Implements TTL and query hashing for efficiency.
    """
    
    def __init__(self):
        load_dotenv()
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.enabled = False
        
        try:
            self.client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.client.ping()
            self.enabled = True
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Caching will be disabled.")

    def _generate_key(self, ticker: str, query: str, top_k: int) -> str:
        """Generates a unique MD5 hash for the request."""
        raw_key = f"{ticker.upper()}:{query.lower()}:{top_k}"
        return hashlib.md5(raw_key.encode()).hexdigest()

    def get_cached_response(self, ticker: str, query: str, top_k: int) -> Optional[Any]:
        """Retrieves a cached response if it exists."""
        if not self.enabled:
            return None
        
        key = self._generate_key(ticker, query, top_k)
        cached_data = self.client.get(key)
        
        if cached_data:
            logger.info(f"Cache Hit for {ticker}: {query}")
            return json.loads(cached_data)
        
        return None

    def set_cached_response(self, ticker: str, query: str, top_k: int, response_data: Any, ttl: int = 3600):
        """Saves a response to cache with a Time-To-Live (TTL)."""
        if not self.enabled:
            return
        
        key = self._generate_key(ticker, query, top_k)
        self.client.setex(
            name=key,
            time=ttl,
            value=json.dumps(response_data)
        )
        logger.info(f"Cached new results for {ticker} (TTL: {ttl}s)")
