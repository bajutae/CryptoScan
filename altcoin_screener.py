import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# --- 설정 (MOVE/KRW, IMX/KRW 특징 기반) ---
EXCHANGE = 'upbit'
BASE_CURRENCY = 'KRW'
MIN_DAILY_VOLUME_USD = 500000000  # 5억 KRW

# 1. 신규 상장 코인 기준 (2021년 1월 1일 이후 상장)
MAX_LISTING_DAYS = 1648

# 2. 상장 후 고점 대비 하락 기준
MIN_DOWNTREND_FROM_ATH = 0.70  # 최소 70% 이상 하락

# 3. 최근 변동성 기준 (바닥 다지기)
MIN_VOLATILITY = 40.0  # 최소 40%
MAX_VOLATILITY = 70.0  # 최대 70%

# 4. CCI 기준 (과매도 탈출 시도)
MIN_CCI = -50.0
MAX_CCI = 50.0
CCI_PERIOD = 20

# --- 추가 선택적 기준 ---
# 5. RSI 기준 (상승 모멘텀)
USE_RSI_FILTER = False # True로 설정 시 적용
MIN_RSI = 40.0 # RSI 최소값
RSI_PERIOD = 14

# 6. 거래량 증가 기준
USE_VOLUME_INCREASE_FILTER = False # True로 설정 시 적용
VOLUME_INCREASE_PERIOD = 7 # 최근 며칠간의 평균 거래량
VOLUME_COMPARE_PERIOD = 30 # 비교할 이전 기간의 평균 거래량
MIN_VOLUME_INCREASE_PERCENTAGE = 20.0 # 최소 거래량 증가율 (%)
# ----------------------------------------------------

def find_potential_altcoins():
    """
    MOVE/KRW, IMX/KRW와 유사한 특징을 가진 알트코인을 탐색합니다.
    기본 조건:
    1. 2021년 1월 1일 이후 상장 (MAX_LISTING_DAYS 설정)
    2. ATH 대비 70% 이상 하락
    3. 최근 30일 변동성이 40% ~ 70% 사이
    4. CCI(-50 ~ +50) 과매도 탈출 시도
    선택적 조건 (USE_RSI_FILTER, USE_VOLUME_INCREASE_FILTER 설정에 따라 적용):
    5. RSI 기준 (MIN_RSI 이상)
    6. 거래량 증가 기준 (MIN_VOLUME_INCREASE_PERCENTAGE 이상)
    """
    print("=== MOVE/IMX 유사 ��인 탐색 스크립트 ===")
    print(f"거래소: {EXCHANGE.upper()}, 기준 통화: {BASE_CURRENCY}")
    print("-" * 40)

    try:
        exchange = getattr(ccxt, EXCHANGE)()
        markets = exchange.load_markets()
    except Exception as e:
        print(f"오류: 거래소 '{EXCHANGE}'에 연결할 수 없습니다. {e}")
        return

    symbols = [m['symbol'] for m in markets.values() if m['quote'] == BASE_CURRENCY and m.get('active', True)]
    print(f"총 {len(symbols)}개의 {BASE_CURRENCY} 마켓 코인을 대상으로 분석을 시작합니다.")

    found_coins = []
    
    # Calculate minimum required days for all indicators
    max_indicator_period = CCI_PERIOD
    if USE_RSI_FILTER:
        max_indicator_period = max(max_indicator_period, RSI_PERIOD)
    if USE_VOLUME_INCREASE_FILTER:
        max_indicator_period = max(max_indicator_period, VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD)

    required_days = MAX_LISTING_DAYS + max_indicator_period + 5 # Add a buffer for safety

    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] 분석 중: {symbol}...", end='\r')
        
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=required_days)
            
            # Ensure enough data for all active indicators
            if len(ohlcv) < max_indicator_period:
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # --- 조건 1: 신규 상장 코인 ---
            if len(df) > MAX_LISTING_DAYS:
                continue

            # --- 지표 계산 ---
            df.ta.cci(length=CCI_PERIOD, append=True)
            if USE_RSI_FILTER:
                df.ta.rsi(length=RSI_PERIOD, append=True)
            
            ath = df['high'].max()
            latest = df.iloc[-1]
            
            recent_high = df['high'].tail(30).max()
            recent_low = df['low'].tail(30).min()
            volatility_metric = ((recent_high - recent_low) / latest['close']) * 100 if latest['close'] > 0 else 0

            # --- 조건 검증 ---
            # 최소 거래대금
            daily_volume_usd = latest['close'] * latest['volume']
            if daily_volume_usd < MIN_DAILY_VOLUME_USD:
                continue

            # 조건 2: ATH 대비 하락률
            downtrend_from_ath = (1 - latest['close'] / ath)
            if downtrend_from_ath < MIN_DOWNTREND_FROM_ATH:
                continue

            # 조건 3: 최근 변동성
            if not (MIN_VOLATILITY <= volatility_metric <= MAX_VOLATILITY):
                continue
            
            # 조건 4: CCI 범위
            current_cci = latest[f'CCI_{CCI_PERIOD}_0.015']
            if not (MIN_CCI <= current_cci <= MAX_CCI):
                continue

            # 조건 5: RSI 범위 (선택적)
            if USE_RSI_FILTER:
                current_rsi = latest[f'RSI_{RSI_PERIOD}']
                if current_rsi < MIN_RSI:
                    continue

            # 조건 6: 거래량 증가 (선택적)
            if USE_VOLUME_INCREASE_FILTER:
                # Ensure enough data for volume comparison
                if len(df) < VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD:
                    continue
                recent_avg_volume = df['volume'].tail(VOLUME_INCREASE_PERIOD).mean()
                compare_avg_volume = df['volume'].iloc[-(VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD):-VOLUME_INCREASE_PERIOD].mean()
                
                if compare_avg_volume > 0:
                    volume_increase_percentage = ((recent_avg_volume - compare_avg_volume) / compare_avg_volume) * 100
                    if volume_increase_percentage < MIN_VOLUME_INCREASE_PERCENTAGE:
                        continue
                else: # Avoid division by zero if compare_avg_volume is 0
                    continue

            # 모든 조건 만족 시 발견
            print(f"\n[발견!] {symbol} 이(가) MOVE/IMX와 유사합니다.")
            print(f"  - 상장 후 고점 대비: -{downtrend_from_ath*100:.2f}% 하락")
            print(f"  - 최근 30일 변동성: {volatility_metric:.2f}%")
            print(f"  - 현재 CCI({CCI_PERIOD}): {current_cci:.2f}")
            if USE_RSI_FILTER:
                print(f"  - 현재 RSI({RSI_PERIOD}): {current_rsi:.2f}")
            if USE_VOLUME_INCREASE_FILTER:
                print(f"  - 최근 {VOLUME_INCREASE_PERIOD}일 평균 거래량 증가율: {volume_increase_percentage:.2f}%")
            print("-" * 20)
            found_coins.append(symbol)

        except Exception as e:
            # print(f"Error processing {symbol}: {e}") # For debugging
            continue
            
    print("\n=== 분석 완료 ===")
    if found_coins:
        print(f"총 {len(found_coins)}개의 잠재적 코인을 발견했습니다:")
        print(", ".join(found_coins))
    else:
        print("기준��� 맞는 코인을 찾지 못했습니다. 설정을 변경하여 다시 시도해보세요.")

if __name__ == '__main__':
    find_potential_altcoins()

