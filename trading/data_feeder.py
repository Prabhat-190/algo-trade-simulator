"""
data_feeder.py
Data Feeder Service - Connects to OKX WebSocket and streams data to Redis.
"""
import asyncio
import json
import logging
import os
import sys
import time
import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from data.websocket_client import OrderbookWebSocketClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataFeeder")


class RedisDataFeeder:
    def __init__(self, websocket_uri: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.websocket_uri = websocket_uri
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client: redis.Redis | None = None
        self._redis_connected = False
        
        self.websocket_client = OrderbookWebSocketClient(
            uri=websocket_uri,
            callback=self.handle_orderbook_update
        )
        
        # Initialize Redis connection
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection with retry logic."""
        max_retries = 5
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Redis at {self.redis_host}:{self.redis_port} (attempt {attempt + 1}/{max_retries})")
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                # Test the connection
                self.redis_client.ping()
                self._redis_connected = True
                logger.info("Successfully connected to Redis")
                return
            except (RedisConnectionError, RedisError, TimeoutError) as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to Redis after {max_retries} attempts. Running without Redis.")
                    self.redis_client = None
                    self._redis_connected = False

    def handle_orderbook_update(self, data: dict):
        if not self._redis_connected or not self.redis_client:
            logger.warning("Redis not connected, skipping orderbook update")
            return
            
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            payload = json.dumps(data)
            
            # Publish to pub/sub channel for Dash dashboard
            self.redis_client.publish(f"orderbook:{symbol}:stream", payload)
            
            # Cache the latest state
            self.redis_client.set(f"orderbook:{symbol}:latest", payload)
        except (RedisConnectionError, RedisError, TimeoutError) as e:
            logger.error(f"Redis error forwarding data: {e}. Attempting to reconnect...")
            self._init_redis()
        except Exception as e:
            logger.error(f"Error forwarding data to Redis: {e}")

    async def start(self):
        logger.info("Starting Redis Data Feeder service...")
        try:
            await self.websocket_client.connect()
        except KeyboardInterrupt:
            logger.info("Feeder service stopped manually.")
        except Exception as e:
            logger.error(f"Feeder service error: {e}")


if __name__ == "__main__":
    WS_URI = os.environ.get('WEBSOCKET_URI', 'wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    
    feeder = RedisDataFeeder(websocket_uri=WS_URI, redis_host=REDIS_HOST, redis_port=REDIS_PORT)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(feeder.start())
    except KeyboardInterrupt:
        logger.info("Feeder service stopped manually.")