"""
WebSocket client for connecting to cryptocurrency exchange L2 orderbook data.
"""
import asyncio
import json
import logging
import signal
import time
from collections.abc import Callable

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    Client for connecting to WebSocket endpoints and processing L2 orderbook data.
    """
    def __init__(
        self,
        uri: str,
        callback: Callable[[dict], None],
        reconnect_interval: int = 5,
        max_reconnect_interval: int = 60,
        max_connection_attempts: int = 0  # 0 = infinite retries
    ):
        """
        Initialize the WebSocket client.

        Args:
            uri: WebSocket endpoint URI
            callback: Function to call with received data
            reconnect_interval: Initial time in seconds to wait before reconnecting
            max_reconnect_interval: Maximum time in seconds to wait before reconnecting
            max_connection_attempts: Maximum connection attempts (0 = infinite)
        """
        self.uri = uri
        self.callback = callback
        self.base_reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval
        self.max_connection_attempts = max_connection_attempts
        self.websocket = None
        self.running = False
        self.last_message_time = 0
        self.connection_attempts = 0
        self.current_reconnect_interval = reconnect_interval
        self._shutdown_event = asyncio.Event()

    async def connect(self):
        """
        Connect to the WebSocket endpoint and start processing messages.
        """
        self.running = True
        self.connection_attempts = 0
        self.current_reconnect_interval = self.base_reconnect_interval

        # Set up signal handlers for graceful shutdown
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._shutdown_event.set)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

        while self.running and (self.max_connection_attempts == 0 or self.connection_attempts < self.max_connection_attempts):
            try:
                self.connection_attempts += 1
                logger.info(f"Connecting to {self.uri} (attempt {self.connection_attempts})")

                async with websockets.connect(
                    self.uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as websocket:
                    self.websocket = websocket
                    self.connection_attempts = 0  # Reset counter on successful connection
                    self.current_reconnect_interval = self.base_reconnect_interval  # Reset backoff
                    logger.info(f"Connected to {self.uri}")

                    # Process messages
                    async for message in websocket:
                        if not self.running:
                            break
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
            except asyncio.CancelledError:
                logger.info("WebSocket client cancelled")
                break
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")

            if self.running and not self._shutdown_event.is_set():
                logger.info(f"Reconnecting in {self.current_reconnect_interval} seconds...")
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.current_reconnect_interval)
                    # If we get here, shutdown was requested
                    break
                except TimeoutError:
                    # Timeout is expected - continue to reconnect
                    pass

                # Exponential backoff with jitter
                self.current_reconnect_interval = min(
                    self.current_reconnect_interval * 2,
                    self.max_reconnect_interval
                )
            else:
                break

        if self.max_connection_attempts > 0 and self.connection_attempts >= self.max_connection_attempts:
            logger.error(f"Max connection attempts ({self.max_connection_attempts}) reached. Stopping reconnection.")
        self.running = False

    def disconnect(self):
        """
        Disconnect from the WebSocket endpoint gracefully.
        """
        logger.info("Disconnecting WebSocket client...")
        self.running = False
        self._shutdown_event.set()
        if self.websocket:
            try:
                # Schedule the close on the event loop
                asyncio.create_task(self.websocket.close())
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
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

    def get_connection_attempts(self) -> int:
        """
        Get the number of connection attempts.

        Returns:
            int: Number of connection attempts
        """
        return self.connection_attempts

    def get_current_reconnect_interval(self) -> float:
        """
        Get the current reconnect interval.

        Returns:
            float: Current reconnect interval in seconds
        """
        return self.current_reconnect_interval


class OrderbookWebSocketClient(WebSocketClient):
    """
    Specialized WebSocket client for L2 orderbook data.
    """
    def __init__(
        self,
        uri: str,
        callback: Callable[[dict], None],
        reconnect_interval: int = 5,
        max_reconnect_interval: int = 60,
        max_connection_attempts: int = 0
    ):
        """
        Initialize the orderbook WebSocket client.

        Args:
            uri: WebSocket endpoint URI
            callback: Function to call with processed orderbook data
            reconnect_interval: Initial time in seconds to wait before reconnecting
            max_reconnect_interval: Maximum time in seconds to wait before reconnecting
            max_connection_attempts: Maximum connection attempts (0 = infinite)
        """
        super().__init__(
            uri,
            self._process_orderbook,
            reconnect_interval,
            max_reconnect_interval,
            max_connection_attempts
        )
        self.user_callback = callback

    def _process_orderbook(self, data: dict):
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
