import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import mplfinance as mpf
import os

# --- 최종 데일리 분석 기준 ---
EXCHANGE = 'upbit'
BASE_CURRENCY = 'KRW'
MIN_DAILY_VOLUME_KRW = 500_000_000
OUTPUT_DIR = 'charts'  # 차트 이미지 저장 폴더

# 1. 차트 패턴 기준
MIN_DOWNTREND_FROM_ATH = 0.70
MIN_VOLATILITY_30D = 45.0
MAX_VOLATILITY_30D = 75.0
MIN_CCI = -40.0
MAX_CCI = 40.0
CCI_PERIOD = 20

# 2. 과거 거래량 분석 기준
VOLUME_LOOKBACK_DAYS = 30
CHART_DAYS = 120  # 차트에 표시할 기간 (일)
# ----------------------------------------------------

def create_chart(df, coin_info, output_path):
    """mplfinance를 사용하여 차트를 생성하고 저장합니다."""
    df_chart = df.tail(CHART_DAYS).copy()
    df_chart.set_index('timestamp', inplace=True)

    # CCI 패널 추가
    cci_panel = mpf.make_addplot(df_chart[f'CCI_{CCI_PERIOD}_0.015'], panel=2, color='purple', ylabel='CCI')
    
    # 거래량 급증일 표시
    spike_date = pd.to_datetime(coin_info['max_spike_date_full'])
    volume_overlays = [spike_date]
    
    # 차트 제목
    title = (f"{coin_info['symbol']} | ATH 대비 {coin_info['downtrend']:.1f}% 하락\n"
             f"30일 변동성: {coin_info['volatility']:.1f}% | 현재 CCI: {coin_info['cci']:.1f}\n"
             f"과거 거래량 급증: {coin_info['max_volume_spike']:.1f}배 ({coin_info['max_spike_date']})")

    # 차트 생성 및 저장
    mpf.plot(df_chart, type='candle', style='yahoo',
             title=title,
             volume=True, panel_ratios=(3, 1),
             addplot=[cci_panel],
             vlines=dict(vlines=volume_overlays, linewidths=0.5, colors='r', alpha=0.7),
             savefig=dict(fname=output_path, dpi=150, bbox_inches='tight'))

def daily_screener():
    """
    매일 실행하여 관심 코인을 찾아내고, 결과를 watchlist.txt와 차트 이미지로 저장합니다.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    header = f"--- {datetime.now().strftime('%Y-%m-%d')} 데일리 관심 코인 스크리너 ---\n"
    print(header.strip())
    
    try:
        exchange = getattr(ccxt, EXCHANGE)()
        markets = exchange.load_markets()
    except Exception as e:
        print(f"오류: 거래소 연결 실패 - {e}")
        return

    symbols = [m['symbol'] for m in markets.values() if m['quote'] == BASE_CURRENCY and m.get('active', True)]
    print(f"총 {len(symbols)}개의 {BASE_CURRENCY} 마켓 코인 분석 시작...")
    print("-" * 70)

    found_coins = []
    
    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] 분석 중: {symbol}...", end='\r')
        
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=2000)
            if len(ohlcv) < CCI_PERIOD + 30: continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            df.ta.cci(length=CCI_PERIOD, append=True)
            ath = df['high'].max()
            latest = df.iloc[-1]
            
            downtrend_from_ath = (1 - latest['close'] / ath)
            if downtrend_from_ath < MIN_DOWNTREND_FROM_ATH: continue
            
            recent_high = df['high'].tail(30).max()
            recent_low = df['low'].tail(30).min()
            volatility_metric = ((recent_high - recent_low) / latest['close']) * 100 if latest['close'] > 0 else 0
            if not (MIN_VOLATILITY_30D <= volatility_metric <= MAX_VOLATILITY_30D): continue
            
            current_cci = latest[f'CCI_{CCI_PERIOD}_0.015']
            if not (MIN_CCI <= current_cci <= MAX_CCI): continue

            if (latest['close'] * latest['volume']) < MIN_DAILY_VOLUME_KRW: continue

            df['volume_sma_30'] = df['volume'].rolling(window=30).mean()
            recent_volume_df = df.iloc[-VOLUME_LOOKBACK_DAYS:].copy()
            recent_volume_df['spike_ratio'] = recent_volume_df['volume'] / recent_volume_df['volume_sma_30']
            max_spike_day = recent_volume_df.loc[recent_volume_df['spike_ratio'].idxmax()]
            
            coin_data = {
                "symbol": symbol,
                "downtrend": downtrend_from_ath * 100,
                "volatility": volatility_metric,
                "cci": current_cci,
                "max_volume_spike": max_spike_day['spike_ratio'],
                "max_spike_date": max_spike_day['timestamp'].strftime('%m-%d'),
                "max_spike_date_full": max_spike_day['timestamp']
            }
            found_coins.append(coin_data)
            
            # 차트 생성
            chart_path = os.path.join(OUTPUT_DIR, f"{symbol.replace('/', '_')}.png")
            create_chart(df, coin_data, chart_path)

        except Exception:
            continue
            
    # 결과 요약 및 파일 저장
    output_content = header
    print("\n\n--- 분석 완료 ---")
    if found_coins:
        sorted_coins = sorted(found_coins, key=lambda x: x['max_volume_spike'], reverse=True)
        
        result_header = f"총 {len(sorted_coins)}개의 관심 코인을 발견했습니다. (결과는 'charts' 폴더에 저장됨)\n\n"
        result_table_header = f"{'종목명':<12} | {'ATH대비':>8} | {'변동성(30일)':>12} | {'현재CCI':>8} | {'과거 거래량 급증':>15}\n"
        result_separator = "-" * 70 + "\n"
        
        output_content += result_header + result_table_header + result_separator
        print(result_header.strip())
        print(result_table_header.strip())
        print(result_separator.strip())

        for coin in sorted_coins:
            ath_str = f"-{coin['downtrend']:.1f}%"
            vol_str = f"{coin['volatility']:.1f}%"
            cci_str = f"{coin['cci']:.1f}"
            vol_spike_str = f"{coin['max_volume_spike']:.1f}배 ({coin['max_spike_date']})"
            
            line = f"{coin['symbol']:<12} | {ath_str:>8} | {vol_str:>12} | {cci_str:>8} | {vol_spike_str:>15}\n"
            output_content += line
            print(line.strip())
    else:
        result_none = "오늘의 기준에 맞는 관심 코인을 찾지 못했습니다.\n"
        output_content += result_none
        print(result_none.strip())

    output_content += "-" * 70 + "\n"
    
    with open('watchlist.txt', 'w', encoding='utf-8') as f:
        f.write(output_content)
    print(f"\n분석 요약이 'watchlist.txt' 파일에 저장되었습니다.")

if __name__ == '__main__':
    daily_screener()