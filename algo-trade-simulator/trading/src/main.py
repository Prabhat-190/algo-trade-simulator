"""
Main application for the trade simulator.
"""
import asyncio
import logging
import argparse
import threading
from typing import Dict, Any

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from src.data.websocket_client import OrderbookWebSocketClient
from src.models.simulator import TradeSimulator
from src.ui.dashboard import Dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Application:
    """
    Main application class for the trade simulator.
    """
    def __init__(self, websocket_uri: str, dashboard_port: int = 8050):
        self.websocket_uri = websocket_uri
        self.dashboard_port = dashboard_port

        # Create simulator
        self.simulator = TradeSimulator()

        # Create WebSocket client
        self.websocket_client = OrderbookWebSocketClient(
            uri=websocket_uri,
            callback=self.handle_orderbook_update
        )

        # Create dashboard
        self.dashboard = Dashboard(self.simulator)
        
        # EXPOSE THE FLASK SERVER FOR GUNICORN (CRITICAL FOR DEPLOYMENT)
        self.server = self.dashboard.app.server 

    def handle_orderbook_update(self, data: Dict[str, Any]):
        try:
            processing_time = self.simulator.update_orderbook(data)
            logger.debug(f"Processed orderbook update in {processing_time:.2f} ms")
        except Exception as e:
            logger.error(f"Error processing orderbook update: {e}")

    async def run_websocket_client(self):
        try:
            await self.websocket_client.connect()
        except Exception as e:
            logger.error(f"WebSocket client error: {e}")

    def run_dashboard_local(self):
        """Only used for local development."""
        try:
            self.dashboard.run_server(debug=False, port=self.dashboard_port, host='0.0.0.0')
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    def start_background_tasks(self):
        """Starts the websocket listener in a background thread."""
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_websocket_client())

        ws_thread = threading.Thread(target=run_async_loop)
        ws_thread.daemon = True
        ws_thread.start()

# --- INSTANTIATE APP GLOBALLY FOR GUNICORN ---
# Create a global instance of the application with default settings
default_uri = os.environ.get('WEBSOCKET_URI', 'wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP')
app_instance = Application(websocket_uri=default_uri)

# Start the background data fetching immediately
app_instance.start_background_tasks()

# Expose the raw Flask server to Gunicorn at the module level
server = app_instance.server 

def main():
    """
    Main entry point for LOCAL execution only.
    """
    parser = argparse.ArgumentParser(description='Trade Simulator')
    parser.add_argument('--websocket-uri', type=str,
                        default='wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP',
                        help='WebSocket URI')
    parser.add_argument('--dashboard-port', type=int, default=8050,
                        help='Dashboard port')
    args = parser.parse_args()

    local_app = Application(
        websocket_uri=args.websocket_uri,
        dashboard_port=args.dashboard_port
    )
    
    logger.info(f"Starting application with WebSocket URI: {args.websocket_uri}")
    logger.info(f"Dashboard available at http://localhost:{args.dashboard_port}")

    # Start the websocket listener
    local_app.start_background_tasks()
    
    # Run the web server in the main thread (blocks execution)
    local_app.run_dashboard_local()

if __name__ == "__main__":
    main()
