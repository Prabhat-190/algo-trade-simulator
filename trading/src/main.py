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
        """
        Initialize the application.

        Args:
            websocket_uri: URI for the WebSocket connection
            dashboard_port: Port for the dashboard
        """
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

    def handle_orderbook_update(self, data: Dict[str, Any]):
        """
        Handle orderbook updates from the WebSocket.

        Args:
            data: Orderbook data
        """
        try:
            # Update the simulator with the new data
            processing_time = self.simulator.update_orderbook(data)
            logger.debug(f"Processed orderbook update in {processing_time:.2f} ms")
        except Exception as e:
            logger.error(f"Error processing orderbook update: {e}")

    async def run_websocket_client(self):
        """
        Run the WebSocket client.
        """
        try:
            await self.websocket_client.connect()
        except Exception as e:
            logger.error(f"WebSocket client error: {e}")

    def run_dashboard(self):
        """
        Run the dashboard.
        """
        try:
            self.dashboard.run_server(debug=False, port=self.dashboard_port)
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    def run(self):
        """
        Run the application.
        """
        # Start the dashboard in a separate thread
        dashboard_thread = threading.Thread(target=self.run_dashboard)
        dashboard_thread.daemon = True
        dashboard_thread.start()

        # Create a sample orderbook for testing
        sample_data = {
            'timestamp': '2023-05-04T10:39:13Z',
            'exchange': 'OKX',
            'symbol': 'BTC-USDT-SWAP',
            'asks': [
                ['45000.5', '1.5'],
                ['45001.0', '2.0'],
                ['45002.0', '3.0'],
                ['45003.0', '4.0'],
                ['45004.0', '5.0']
            ],
            'bids': [
                ['44999.5', '1.0'],
                ['44999.0', '2.0'],
                ['44998.0', '3.0'],
                ['44997.0', '4.0'],
                ['44996.0', '5.0']
            ]
        }

        # Update the simulator with sample data
        self.simulator.update_orderbook(sample_data)

        # Run the WebSocket client in the main thread
        try:
            asyncio.run(self.run_websocket_client())
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"WebSocket client error: {e}")

def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description='Trade Simulator')
    parser.add_argument('--websocket-uri', type=str,
                        default='wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP',
                        help='WebSocket URI')
    parser.add_argument('--dashboard-port', type=int, default=8050,
                        help='Dashboard port')
    args = parser.parse_args()

    # Create and run the application
    app = Application(
        websocket_uri=args.websocket_uri,
        dashboard_port=args.dashboard_port
    )

    logger.info(f"Starting application with WebSocket URI: {args.websocket_uri}")
    logger.info(f"Dashboard available at http://localhost:{args.dashboard_port}")

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    main()
