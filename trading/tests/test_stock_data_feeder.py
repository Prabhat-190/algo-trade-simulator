"""
Tests for the stock quote feeder.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stock_data_feeder import StockQuoteFeeder


class TestStockQuoteFeeder(unittest.TestCase):
    def test_build_synthetic_orderbook(self):
        feeder = StockQuoteFeeder.__new__(StockQuoteFeeder)
        feeder.symbol = "AAPL"
        feeder.provider = "finnhub"
        orderbook = feeder.build_synthetic_orderbook({"price": 200.0, "previous_close": 198.0})

        self.assertEqual(orderbook["symbol"], "AAPL")
        self.assertEqual(orderbook["asset_class"], "stock")
        self.assertEqual(len(orderbook["asks"]), 10)
        self.assertEqual(len(orderbook["bids"]), 10)
        self.assertGreater(orderbook["asks"][0][0], 200.0)
        self.assertLess(orderbook["bids"][0][0], 200.0)


if __name__ == '__main__':
    unittest.main()
