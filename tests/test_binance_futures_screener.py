
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from binance_futures_screener import get_binance_futures_data, screen_coins

class TestBinanceFuturesScreener(unittest.TestCase):

    @patch('binance_futures_screener.ccxt.binanceusdm')
    def test_get_and_screen_coins(self, mock_binanceusdm):
        # Mock exchange instance and its async methods
        mock_exchange = AsyncMock()
        mock_binanceusdm.return_value = mock_exchange

        # Mock API responses
        mock_exchange.load_markets.return_value = {
            'BTC/USDT': {'symbol': 'BTC/USDT', 'type': 'future', 'active': True}
        }
        mock_exchange.fetch_tickers.return_value = {
            'BTC/USDT': {'symbol': 'BTC/USDT', 'change': 5.0, 'quoteVolume': 2500}
        }
        
        now = MagicMock()
        now.milliseconds.return_value = 1720396800000 # A fixed timestamp
        mock_exchange.milliseconds = now.milliseconds

        mock_exchange.fetch_open_interest_history.return_value = [
            {'openInterestValue': 1000, 'timestamp': 1720310400000}, # 24h ago
            {'openInterestValue': 1015, 'timestamp': 1720382400000}, # 4h ago
            {'openInterestValue': 1030, 'timestamp': 1720396800000}  # now
        ]
        mock_exchange.fapiPublicGet.return_value = [{'longAccount': '0.6'}]
        mock_exchange.fetch_funding_rate_history.return_value = [{'fundingRate': 0.0001}]

        # --- Run the async data fetching ---
        data = asyncio.run(get_binance_futures_data())

        # --- Run the screening ---
        found_coins = screen_coins(data)

        # --- Assertions ---
        self.assertEqual(len(found_coins), 1)
        self.assertEqual(found_coins[0]['symbol'], 'BTC/USDT')
        self.assertGreater(found_coins[0]['oi_change_24h'], 2.0)
        self.assertGreater(found_coins[0]['oi_change_4h'], 1.0)
        self.assertGreater(found_coins[0]['long_accounts_1h'], 45.0)
        self.assertLess(found_coins[0]['price_change_24h'], 6.0)
        
        # Ensure the exchange is closed
        mock_exchange.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
