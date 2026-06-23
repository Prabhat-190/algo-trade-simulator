"""
Tests for the trade simulator.
"""
import unittest
import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.simulator import TradeSimulator
from src.data.orderbook import Orderbook
from src.models.slippage_model import SlippageModel
from src.models.market_impact import AlmgrenChrissModel
from src.models.maker_taker import MakerTakerModel
from src.models.fee_model import FeeModel

class TestSimulator(unittest.TestCase):
    """
    Tests for the trade simulator.
    """
    def setUp(self):
        """
        Set up the test.
        """
        self.simulator = TradeSimulator()
        
        # Create sample orderbook data
        self.sample_data = {
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
        
    def test_update_orderbook(self):
        """
        Test updating the orderbook.
        """
        # Update the orderbook
        processing_time = self.simulator.update_orderbook(self.sample_data)
        
        # Check that the orderbook was updated
        self.assertEqual(self.simulator.orderbook.exchange, 'OKX')
        self.assertEqual(self.simulator.orderbook.symbol, 'BTC-USDT-SWAP')
        self.assertEqual(len(self.simulator.orderbook.asks), 5)
        self.assertEqual(len(self.simulator.orderbook.bids), 5)
        
        # Check that the processing time is reasonable
        self.assertGreater(processing_time, 0)
        
    def test_simulate_market_order(self):
        """
        Test simulating a market order.
        """
        # Update the orderbook first
        self.simulator.update_orderbook(self.sample_data)
        
        # Simulate a market order
        result = self.simulator.simulate_market_order(
            side='buy',
            quantity=0.1,  # 0.1 BTC
            exchange='OKX',
            market_type='spot',
            fee_tier='VIP0',
            volatility=0.01
        )
        
        # Check that the result contains the expected keys
        expected_keys = [
            'timestamp', 'exchange', 'symbol', 'side', 'quantity',
            'mid_price', 'execution_price', 'order_value',
            'maker_proportion', 'fees', 'slippage', 'slippage_percentage',
            'market_impact', 'market_impact_percentage',
            'net_cost', 'net_cost_percentage', 'processing_time'
        ]
        
        for key in expected_keys:
            self.assertIn(key, result)
            
        # Check that the values are reasonable
        self.assertEqual(result['side'], 'buy')
        self.assertEqual(result['quantity'], 0.1)
        self.assertEqual(result['exchange'], 'OKX')
        
        # Mid price should be the average of best bid and best ask
        expected_mid_price = (45000.5 + 44999.5) / 2
        self.assertAlmostEqual(result['mid_price'], expected_mid_price)
        
        # Order value should be quantity * mid price
        expected_order_value = 0.1 * expected_mid_price
        self.assertAlmostEqual(result['order_value'], expected_order_value)
        
        # Fees should be positive
        self.assertGreater(result['fees']['total_fee'], 0)
        
        # Slippage should be non-negative for a buy order
        self.assertGreaterEqual(result['slippage'], 0)
        
        # Market impact should be positive
        self.assertGreater(result['market_impact']['total_impact'], 0)
        
        # Net cost should be the sum of fees, slippage, and market impact
        expected_net_cost = (
            result['fees']['total_fee'] + 
            result['slippage'] + 
            result['market_impact']['total_impact']
        )
        self.assertAlmostEqual(result['net_cost'], expected_net_cost)
        
        # Processing time should be reasonable
        self.assertGreater(result['processing_time'], 0)
        
    def test_orderbook_methods(self):
        """
        Test orderbook methods.
        """
        # Update the orderbook
        self.simulator.update_orderbook(self.sample_data)
        
        # Test mid price
        expected_mid_price = (45000.5 + 44999.5) / 2
        self.assertAlmostEqual(self.simulator.orderbook.get_mid_price(), expected_mid_price)
        
        # Test spread
        expected_spread = 45000.5 - 44999.5
        self.assertAlmostEqual(self.simulator.orderbook.get_spread(), expected_spread)
        
        # Test spread percentage
        expected_spread_percentage = (expected_spread / expected_mid_price) * 100
        self.assertAlmostEqual(self.simulator.orderbook.get_spread_percentage(), expected_spread_percentage)
        
        # Test volume at price
        self.assertAlmostEqual(self.simulator.orderbook.get_volume_at_price('ask', 45000.5), 1.5)
        self.assertAlmostEqual(self.simulator.orderbook.get_volume_at_price('bid', 44999.5), 1.0)
        
        # Test volume up to price
        self.assertAlmostEqual(self.simulator.orderbook.get_volume_up_to_price('ask', 45002.0), 1.5 + 2.0 + 3.0)
        self.assertAlmostEqual(self.simulator.orderbook.get_volume_up_to_price('bid', 44998.0), 1.0 + 2.0 + 3.0)
        
        # Test price for volume
        self.assertAlmostEqual(self.simulator.orderbook.get_price_for_volume('ask', 2.0), 45001.0)
        self.assertAlmostEqual(self.simulator.orderbook.get_price_for_volume('bid', 2.0), 44999.0)
        
        # Test orderbook imbalance
        total_bid_volume = 1.0 + 2.0 + 3.0 + 4.0 + 5.0
        total_ask_volume = 1.5 + 2.0 + 3.0 + 4.0 + 5.0
        expected_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        self.assertAlmostEqual(self.simulator.orderbook.get_orderbook_imbalance(), expected_imbalance)
        
if __name__ == '__main__':
    unittest.main()
