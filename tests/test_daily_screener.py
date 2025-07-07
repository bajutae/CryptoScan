
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from daily_screener import daily_screener

class TestDailyScreener(unittest.TestCase):

    @patch('daily_screener.ccxt.upbit')
    @patch('daily_screener.mpf.plot')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_daily_screener_finds_coin(self, mock_makedirs, mock_exists, mock_open, mock_plot, mock_upbit):
        # Mock exchange setup
        mock_exchange = MagicMock()
        mock_upbit.return_value = mock_exchange
        mock_exchange.load_markets.return_value = {
            'MOVE/KRW': {'symbol': 'MOVE/KRW', 'quote': 'KRW', 'active': True}
        }

        # Simplified and robust test data
        now = pd.Timestamp.now()
        ohlcv_list = []
        for i in range(200):
            # Base data that does not meet criteria on its own
            ohlcv_list.append([int((now - pd.Timedelta(days=199-i)).timestamp() * 1000), 200, 210, 190, 205, 1_000_000])

        # Set a clear ATH well in the past
        ohlcv_list[50][2] = 600 

        # Set the last 30 days to precisely meet the volatility and CCI criteria
        for i in range(1, 31):
            ts = int((now - pd.Timedelta(days=30-i)).timestamp() * 1000)
            # This creates a sideways market, which results in a CCI around 0
            ohlcv_list[-i] = [ts, 105, 120, 95, 100, 600_000_000]
        
        # Set the final day's data to pass all checks
        ohlcv_list[-1][4] = 100 # close = 100
        ohlcv_list[-1][2] = 125 # high
        ohlcv_list[-1][3] = 75  # low
        
        # Ensure recent high/low for volatility are met
        ohlcv_list[-2][2] = 130 # This will be the recent_high
        ohlcv_list[-3][3] = 70  # This will be the recent_low

        # Add a volume spike
        ohlcv_list[-5][5] = 9_000_000_000
        
        mock_exchange.fetch_ohlcv.return_value = ohlcv_list

        # Run the screener
        daily_screener()

        # Assertions
        mock_makedirs.assert_called_once_with('charts')
        mock_plot.assert_called_once()
        mock_open.assert_called_with('watchlist.txt', 'w', encoding='utf-8')
        
        handle = mock_open()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("MOVE/KRW", written_content)

if __name__ == '__main__':
    unittest.main()
