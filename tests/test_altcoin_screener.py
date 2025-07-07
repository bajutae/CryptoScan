
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from altcoin_screener import find_potential_altcoins

class TestAltcoinScreener(unittest.TestCase):

    @patch('altcoin_screener.ccxt.upbit')
    def test_find_potential_altcoins(self, mock_upbit):
        # Mock exchange setup
        mock_exchange = MagicMock()
        mock_upbit.return_value = mock_exchange

        # Mock market data
        mock_markets = {
            'BTC/KRW': {'symbol': 'BTC/KRW', 'quote': 'KRW', 'active': True},
            'ETH/KRW': {'symbol': 'ETH/KRW', 'quote': 'KRW', 'active': True},
            'MOVE/KRW': {'symbol': 'MOVE/KRW', 'quote': 'KRW', 'active': True},
        }
        mock_exchange.load_markets.return_value = mock_markets

        # Mock OHLCV data for MOVE/KRW (to meet the criteria)
        move_ohlcv = [
            [pd.Timestamp('2024-01-01').value // 10**6, 100, 120, 90, 110, 1000],
            # ... (add more data points to satisfy indicator calculations)
        ]
        # Create a dataframe with enough data points
        move_df = pd.DataFrame({
            'timestamp': pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=100)),
            'open': 100,
            'high': range(100, 200),
            'low': 90,
            'close': range(100, 200),
            'volume': 5000000
        })
        move_df['close'].iloc[-1] = 30 # ATH 대비 70% 이상 하락
        move_df['high'].iloc[-30:] = range(130, 160) # 변동성
        move_df['low'].iloc[-30:] = range(70, 100)


        # Mock OHLCV data for other coins (not to meet the criteria)
        btc_ohlcv = [[pd.Timestamp('2020-01-01').value // 10**6, 5000, 5100, 4900, 5050, 2000]] * 2000
        eth_ohlcv = [[pd.Timestamp('2022-01-01').value // 10**6, 300, 320, 290, 310, 3000]] * 500

        def mock_fetch_ohlcv(symbol, timeframe, limit):
            if symbol == 'MOVE/KRW':
                # Return a list of lists
                return move_df.values.tolist()
            elif symbol == 'BTC/KRW':
                return btc_ohlcv
            else:
                return eth_ohlcv

        mock_exchange.fetch_ohlcv.side_effect = mock_fetch_ohlcv

        # Run the screener
        with patch('builtins.print') as mock_print:
            find_potential_altcoins()
            # Check if MOVE/KRW was found
            self.assertTrue(any("MOVE/KRW" in call.args[0] for call in mock_print.call_args_list if call.args))


if __name__ == '__main__':
    unittest.main()
