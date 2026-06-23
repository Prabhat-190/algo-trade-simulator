"""
data_feeder.py
Data Feeder Service - Connects to OKX WebSocket and streams data to Redis.
"""
import asyncio
import json
import logging
import os
import redis
from src.data.websocket_client import OrderbookWebSocketClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataFeeder")

class RedisDataFeeder:
    def __init__(self, websocket_uri: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.websocket_client = OrderbookWebSocketClient(
            uri=websocket_uri,
            callback=self.handle_orderbook_update
        )

    def handle_orderbook_update(self, data: dict):
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            payload = json.dumps(data)
            
            # Publish to pub/sub channel for Dash dashboard
            self.redis_client.publish(f"orderbook:{symbol}:stream", payload)
            
            # Cache the latest state
            self.redis_client.set(f"orderbook:{symbol}:latest", payload)
        except Exception as e:
            logger.error(f"Error forwarding data to Redis: {e}")

    async def start(self):
        logger.info("Starting Redis Data Feeder service...")
        await self.websocket_client.connect()

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