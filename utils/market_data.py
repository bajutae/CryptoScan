
import ccxt
import pandas as pd
import pandas_ta as ta

def get_active_symbols(exchange_name, base_currency):
    """거래소에서 지정된 기준 통화의 모든 활성 심볼 목록을 가져옵니다."""
    try:
        exchange = getattr(ccxt, exchange_name)()
        markets = exchange.load_markets()
        return [
            m['symbol'] for m in markets.values() 
            if m['quote'] == base_currency and m.get('active', True)
        ]
    except Exception as e:
        print(f"Error loading symbols from {exchange_name}: {e}")
        return []

def get_ohlcv(exchange_name, symbol, timeframe='1d', limit=2000):
    """지정된 심볼의 OHLCV 데이터를 가져옵니다."""
    try:
        exchange = getattr(ccxt, exchange_name)()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching OHLCV for {symbol}: {e}")
        return None

def calculate_indicators(df, cci_period=20, rsi_period=14):
    """데이터프레임에 기술적 분석 지표를 추가합니다."""
    if df is None:
        return None
    
    df.ta.cci(length=cci_period, append=True)
    df.ta.rsi(length=rsi_period, append=True)
    # 추후 다른 지표들도 이곳에 추가할 수 있습니다.
    return df
