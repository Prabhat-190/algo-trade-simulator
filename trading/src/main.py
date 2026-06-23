"""
main.py
Unified High-Concurrency Main Entrypoint for the Real-Time Trading Simulator Dashboard.
Integrates Redis Pub/Sub streams, project stores, container health checks, and a premium 
cyber obsidian glassmorphic theme featuring advanced frosted blur layers and high-contrast neon telemetry.
"""
import json
import threading
import logging
import os
import sys
import time
from typing import Dict, Any

import redis

# Resilient path resolution to ensure module visibility across isolated runtimes
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..')))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, 'trading')))

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
import plotly.graph_objects as go

from src.ui.dashboard import Dashboard
from src.models.simulator import TradeSimulator
from src.models.trading_project import TradingProjectStore

# Configure production-ready log stream matrix
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ProductionDashApplication")

# Global mutex to secure the shared simulator data frames from concurrent race conditions
state_lock = threading.Lock()

class Application:
    """
    Core application wrapper coordinating state storage engines, trading simulations,
    live container diagnostic probes, and the premium blurred dark dashboard cockpit.
    """
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        logger.info(f"Establishing high-speed channel link to Redis broker at {redis_host}:{redis_port}")
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Pull optional environment configuration for ML model weight contexts
        models_dir = os.environ.get('MODELS_DIR', None)
        
        # Instantiate thread-safe quant calculation engine
        self.simulator = TradeSimulator(models_dir=models_dir)

        # Initialize internal storage layer infrastructure
        self.project_store = TradingProjectStore(redis_client=self.redis_client)
        
        # Instantiate Dash UI components using a dark baseline stylesheet template
        self.dashboard = Dashboard(self.simulator, project_store=self.project_store)

        # 🎨 STEP 1: Inject Premium Obsidian Glassmorphism Themes and Heavy Blur CSS Animations
        self._inject_glassmorphic_visual_architecture()

        # 🩺 STEP 2: Establish container status tracking paths
        self._register_health_monitor_route(redis_host, redis_port)
        
        # Expose active Flask engine reference securely upstream for Gunicorn multi-process bounds
        self.server = self.dashboard.app.server 

    def _inject_glassmorphic_visual_architecture(self):
        """
        Overrides the underlying template compiler to inject deep frosted glass styles,
        saturated blur cards, clean neon telemetry guides, and micro-motion vectors.
        """
        self.dashboard.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>Institutional Algorithmic Trading Cockpit</title>
                {%favicon%}
                {%css%}
                <style>
                    :root {
                        --bg-deep-obsidian: #04060a;
                        --bg-blur-card: rgba(13, 20, 34, 0.65);
                        --bg-input-focus: rgba(24, 38, 58, 0.85);
                        --border-slate-glass: rgba(255, 255, 255, 0.08);
                        --border-slate-glow: rgba(0, 229, 255, 0.5);
                        
                        /* High-Definition Cyber Theme Accents */
                        --cyber-cyan: #00e5ff;
                        --neon-green: #00e676;
                        --neon-red: #ff1744;
                        --neon-gold: #ffd600;
                        --text-premium-white: #ffffff;
                        --text-silver-gray: #b0c4de;
                        --text-muted-dim: #64748b;
                    }
                    
                    body {
                        background: fixed radial-gradient(circle at 50% 15%, #0a1626 0%, var(--bg-deep-obsidian) 85%) !important;
                        color: var(--text-premium-white) !important;
                        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
                        margin: 0;
                        padding: 0;
                        overflow-x: hidden;
                        letter-spacing: 0.3px;
                    }
                    
                    /* Custom Scrollbar Optimization for Live Streams */
                    ::-webkit-scrollbar {
                        width: 6px;
                        height: 6px;
                    }
                    ::-webkit-scrollbar-track {
                        background: var(--bg-deep-obsidian);
                    }
                    ::-webkit-scrollbar-thumb {
                        background: rgba(255, 255, 255, 0.15);
                        border-radius: 3px;
                    }
                    ::-webkit-scrollbar-thumb:hover {
                        background: var(--cyber-cyan);
                    }
                    
                    /* ==========================================================================
                       FROSTED GLASSMORPHISM CARD DESIGN WITH SATURATED BLUR & HIGH CONTRAST FIXES
                       ========================================================================== */
                    .card {
                        background: var(--bg-blur-card) !important;
                        backdrop-filter: blur(25px) saturate(190%) !important;
                        -webkit-backdrop-filter: blur(25px) saturate(190%) !important;
                        border: 1px solid var(--border-slate-glass) !important;
                        border-radius: 14px !important;
                        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.65) !important;
                        margin-bottom: 24px;
                        opacity: 0;
                        
                        /* Entry Keyframe Initialization */
                        animation: smoothSlideUp 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), 
                                    box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1), 
                                    border-color 0.3s ease !important;
                    }
                    
                    /* Card Hover Transformation Matrix */
                    .card:hover {
                        transform: translateY(-4px);
                        box-shadow: 0 20px 50px 0 rgba(0, 229, 255, 0.2) !important;
                        border-color: var(--border-slate-glow) !important;
                    }
                    
                    .card-header {
                        background: linear-gradient(90deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.00) 100%) !important;
                        border-bottom: 1px solid var(--border-slate-glass) !important;
                        color: var(--cyber-cyan) !important;
                        font-size: 13px !important;
                        font-weight: 700 !important;
                        text-transform: uppercase;
                        letter-spacing: 1.5px;
                        padding: 16px 20px !important;
                        border-top-left-radius: 14px !important;
                        border-top-right-radius: 14px !important;
                    }

                    /* CRITICAL HIGH-CONTRAST READABILITY OVERRIDES FOR SIMULATION RESULTS */
                    .card-body, .card-body p, .card-body div, .card-body span {
                        color: var(--text-premium-white) !important;
                    }

                    .card-body h5, .card-body h4 {
                        color: var(--text-silver-gray) !important;
                        font-weight: 600 !important;
                        font-size: 13px !important;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-top: 16px;
                        margin-bottom: 6px;
                    }

                    /* Advanced Financial Metric Display Boxes */
                    #slippage-output, #fees-output, #market-impact-output, 
                    #net-cost-output, #maker-taker-output, #latency-output,
                    #connection-status, #last-update-time {
                        font-family: 'SF Mono', Consolas, Menlo, monospace !important;
                        font-size: 15px !important;
                        font-weight: 700 !important;
                        padding: 10px 14px;
                        background: rgba(4, 6, 10, 0.6) !important;
                        border-radius: 8px;
                        border-left: 4px solid var(--cyber-cyan);
                        margin-bottom: 14px;
                        display: block;
                        box-shadow: inset 0 1px 2px rgba(0,0,0,0.4);
                    }

                    #slippage-output { border-left-color: var(--cyber-cyan); color: var(--cyber-cyan) !important; }
                    #fees-output { border-left-color: var(--neon-gold); color: var(--neon-gold) !important; }
                    #market-impact-output { border-left-color: var(--neon-red); color: var(--neon-red) !important; }
                    #net-cost-output { 
                        border-left-color: #e040fb; 
                        color: #ff33ff !important; 
                        font-size: 18px !important; 
                        background: rgba(224, 64, 251, 0.08) !important;
                        box-shadow: 0 0 15px rgba(224, 64, 251, 0.15);
                    }
                    #maker-taker-output { border-left-color: var(--text-silver-gray); color: var(--text-premium-white) !important; }
                    #latency-output { border-left-color: var(--neon-green); color: var(--neon-green) !important; }
                    
                    /* ==========================================================================
                       KEYFRAME MICRO-ANIMATIONS
                       ========================================================================== */
                    @keyframes smoothSlideUp {
                        0% { opacity: 0; transform: translateY(22px) scale(0.97); }
                        100% { opacity: 1; transform: translateY(0) scale(1); }
                    }
                    
                    @keyframes telemetryPulseRadar {
                        0% { box-shadow: 0 0 0 0 rgba(0, 230, 114, 0.6); }
                        70% { box-shadow: 0 0 0 12px rgba(0, 230, 114, 0); }
                        100% { box-shadow: 0 0 0 0 rgba(0, 230, 114, 0); }
                    }
                    
                    /* ==========================================================================
                       COMPONENTS, INPUTS, AND REACTION TREATMENTS
                       ========================================================================== */
                    .live-status-dot {
                        width: 8px;
                        height: 8px;
                        background-color: var(--neon-green);
                        border-radius: 50%;
                        display: inline-block;
                        margin-right: 12px;
                        animation: telemetryPulseRadar 2.4s infinite;
                    }
                    
                    /* Frosted Input Fields and Dropdown selection layers overrides */
                    input, .Select-control, .form-control {
                        background-color: rgba(4, 6, 10, 0.8) !important;
                        backdrop-filter: blur(4px);
                        border: 1px solid var(--border-slate-glass) !important;
                        color: var(--text-premium-white) !important;
                        border-radius: 6px !important;
                        height: 40px !important;
                        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
                    }
                    
                    input:focus, .Select-control:hover, .form-control:focus {
                        border-color: var(--cyber-cyan) !important;
                        background-color: var(--bg-input-focus) !important;
                        box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.18) !important;
                        outline: none;
                        color: #ffffff !important;
                    }

                    label {
                        color: var(--text-silver-gray) !important;
                        font-weight: 600;
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.6px;
                        margin-bottom: 6px;
                    }
                    
                    .bid-row-update { color: var(--neon-green) !important; font-family: 'SF Mono', monospace; font-weight: 600; }
                    .ask-row-update { color: var(--neon-red) !important; font-family: 'SF Mono', monospace; font-weight: 600; }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''

    def _register_health_monitor_route(self, redis_host: str, redis_port: int):
        """ Binds system metric check validations to core server routes """
        @self.dashboard.app.server.get('/healthz')
        def healthz():
            with state_lock:
                last_update = self.simulator.last_update_time
            return {
                'status': 'ok',
                'redis_host': redis_host,
                'redis_port': redis_port,
                'last_orderbook_update': last_update,
                'timestamp': time.time()
            }, 200

    def listen_to_redis_feed(self):
        """
        Background subscriber queue mapping real-time data ticks forwarded 
        by the decoupled feeder microservice service layers.
        """
        pubsub = self.redis_client.pubsub()
        pubsub.psubscribe("orderbook:*:stream")
        logger.info("Dash server engine connected to Redis synchronization backbone.")

        for message in pubsub.listen():
            if message['type'] == 'pmessage':
                try:
                    orderbook_data = json.loads(message['data'])
                    # Block state access using strict locks during calculation sync ticks
                    with state_lock:
                        self.simulator.update_orderbook(orderbook_data)
                except Exception as e:
                    logger.error(f"Error updating synchronized runtime metrics: {e}")

    def start_background_tasks(self):
        """ Spawns daemon infrastructure processing threads dedicated entirely to stream handling """
        sync_thread = threading.Thread(target=self.listen_to_redis_feed)
        sync_thread.daemon = True
        sync_thread.start()
        logger.info("Asynchronous Redis monitoring matrix initialized successfully.")

    def run_dashboard_local(self, port: int = 8050):
        """ Local system fallback bootstrap framework entrypoint """
        try:
            self.dashboard.run_server(debug=False, port=port, host='0.0.0.0')
        except Exception as e:
            logger.error(f"UI visualization crashed on startup loops: {e}")

# --- GLOBAL ARCHITECTURE BOUNDARY FOR UPSTREAM WORKERS / LOAD BALANCERS ---
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

app_instance = Application(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
app_instance.start_background_tasks()

# Expose WSGI context boundaries to container management tools (Gunicorn)
server = app_instance.server 

def main():
    """
    Main entry point for local execution parameters.
    """
    import argparse
    parser = argparse.ArgumentParser(description='Production Algo Trade Simulator Interface')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8050)), help='Dashboard port')
    args = parser.parse_args()

    logger.info(f"Launching production interface on port allocation: {args.port}")
    app_instance.run_dashboard_local(port=args.port)

if __name__ == "__main__":
    main()