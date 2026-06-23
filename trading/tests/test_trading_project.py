"""
Tests for trading project persistence.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.trading_project import TradingProject, TradingProjectStore


class TestTradingProjectStore(unittest.TestCase):
    def test_save_and_load_project_from_memory(self):
        store = TradingProjectStore(redis_client=None)
        project = TradingProject.from_dict({
            'name': 'ETH Swing Plan',
            'strategy': 'swing',
            'exchange': 'OKX',
            'market_type': 'spot',
            'symbol': 'ETH-USDT',
            'side': 'sell',
            'quantity_usd': 2500,
            'volatility': 0.02,
            'fee_tier': 'VIP1',
        })

        store.save(project)
        loaded = store.get('ETH Swing Plan')

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.symbol, 'ETH-USDT')
        self.assertEqual(loaded.strategy, 'swing')
        self.assertEqual(loaded.quantity_usd, 2500)

    def test_project_options_are_dropdown_ready(self):
        store = TradingProjectStore(redis_client=None)
        options = store.list_projects()

        self.assertGreaterEqual(len(options), 1)
        self.assertIn('label', options[0])
        self.assertIn('value', options[0])


if __name__ == '__main__':
    unittest.main()
