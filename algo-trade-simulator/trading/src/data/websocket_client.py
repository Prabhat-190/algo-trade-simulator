"""
WebSocket client for connecting to cryptocurrency exchange L2 orderbook data.
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Callable, Optional, Any

import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketClient:
    """
    Client for connecting to WebSocket endpoints and processing L2 orderbook data.
    """
    def __init__(self, uri: str, callback: Callable[[Dict], None], reconnect_interval: int = 5):
        """
        Initialize the WebSocket client.
        
        Args:
            uri: WebSocket endpoint URI
            callback: Function to call with received data
            reconnect_interval: Time in seconds to wait before reconnecting
        """
        self.uri = uri
        self.callback = callback
        self.reconnect_interval = reconnect_interval
        self.websocket = None
        self.running = False
        self.last_message_time = 0
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        
    async def connect(self):
        """
        Connect to the WebSocket endpoint and start processing messages.
        """
        self.running = True
        self.connection_attempts = 0
        
        while self.running and self.connection_attempts < self.max_connection_attempts:
            try:
                self.connection_attempts += 1
                logger.info(f"Connecting to {self.uri} (attempt {self.connection_attempts})")
                
                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    self.connection_attempts = 0  # Reset counter on successful connection
                    logger.info(f"Connected to {self.uri}")
                    
                    # Process messages
                    async for message in websocket:
                        self.last_message_time = time.time()
                        try:
                            data = json.loads(message)
                            self.callback(data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse message: {message}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                
            if self.running:
                logger.info(f"Reconnecting in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)
                
        if self.connection_attempts >= self.max_connection_attempts:
            logger.error(f"Max connection attempts ({self.max_connection_attempts}) reached. Stopping reconnection.")
            self.running = False
    
    def disconnect(self):
        """
        Disconnect from the WebSocket endpoint.
        """
        self.running = False
        logger.info("WebSocket client disconnected")
        
    def is_connected(self) -> bool:
        """
        Check if the client is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.websocket is not None and not self.websocket.closed
    
    def get_last_message_time(self) -> float:
        """
        Get the timestamp of the last received message.
        
        Returns:
            float: Timestamp of the last message
        """
        return self.last_message_time


class OrderbookWebSocketClient(WebSocketClient):
    """
    Specialized WebSocket client for L2 orderbook data.
    """
    def __init__(self, uri: str, callback: Callable[[Dict], None], reconnect_interval: int = 5):
        """
        Initialize the orderbook WebSocket client.
        
        Args:
            uri: WebSocket endpoint URI
            callback: Function to call with processed orderbook data
            reconnect_interval: Time in seconds to wait before reconnecting
        """
        super().__init__(uri, self._process_orderbook, reconnect_interval)
        self.user_callback = callback
        
    def _process_orderbook(self, data: Dict):
        """
        Process the raw orderbook data and pass it to the user callback.
        
        Args:
            data: Raw orderbook data from the WebSocket
        """
        try:
            # Ensure the data has the expected format
            if not all(key in data for key in ['timestamp', 'exchange', 'symbol', 'asks', 'bids']):
                logger.warning(f"Received data missing required fields: {data}")
                return
                
            # Convert string prices and quantities to float
            processed_data = {
                'timestamp': data['timestamp'],
                'exchange': data['exchange'],
                'symbol': data['symbol'],
                'asks': [[float(price), float(qty)] for price, qty in data['asks']],
                'bids': [[float(price), float(qty)] for price, qty in data['bids']]
            }
            
            # Call the user callback with the processed data
            self.user_callback(processed_data)
            
        except Exception as e:
            logger.error(f"Error processing orderbook data: {e}")
