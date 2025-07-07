from binance.client import Client
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 설정 ---
# 바이낸스 API 키와 시크릿은 필요하지 않습니다. (공개 데이터만 사용)
# 만약 개인 계정 데이터가 필요하다면 여기에 API_KEY와 API_SECRET을 추가하세요.
# API_KEY = "YOUR_API_KEY"
# API_SECRET = "YOUR_API_SECRET"

# 스크리닝 기준
OI_CHANGE_24H_MIN = 2.0  # Open Interest Change % 24H > 2%
OI_CHANGE_4H_MIN = 1.0   # Open Interest Change % 4H > 1%
LONG_ACCOUNTS_1H_MIN = 45.0 # Long Accounts % (1H) > 45%
LONG_ACCOUNTS_1H_MAX = 70.0 # Long Accounts % (1H) < 70%
PRICE_CHANGE_24H_MAX = 6.0  # Price Change % 24H < 6%
OI_VOLUME_24H_MIN = 0.4     # Open Interest / Volume 24H > 0.4
FUNDING_RATE_AVG_MIN = 0.00006 # Funding Rate Average > 0.006% (0.006%는 0.00006)

# --- 함수 정의 ---
def get_binance_futures_data():
    client = Client()
    
    print("바이��스 선물 시장 데이터 로딩 중...")
    try:
        exchange_info = client.get_exchange_info()
        symbols = [s['symbol'] for s in exchange_info['symbols'] if s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING']
        print(f"총 {len(symbols)}개의 선물 심볼 발견.")
    except Exception as e:
        print(f"거래소 정보 로딩 실패: {e}")
        return []

    all_coin_data = []

    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] 데이터 수집 중: {symbol}...", end='\r')
        try:
            # 24시간 통계 (가격 변동, 거래량)
            # Fetch all 24hr tickers and find the specific symbol
            all_tickers_24h = client.ticker_24hr_all_tickers()
            ticker_24h = next((t for t in all_tickers_24h if t['symbol'] == symbol), None)
            if not ticker_24h: continue
            price_change_24h = float(ticker_24h['priceChangePercent'])
            volume_24h = float(ticker_24h['quoteVolume']) # USDT volume

            # 미결제 약정 (Open Interest)
            # 24시간 전 OI
            oi_history_24h = client.open_interest_hist(symbol=symbol, period='1h', limit=24)
            if not oi_history_24h: continue
            oi_24h_ago = float(oi_history_24h[0]['sumOpenInterest']) # 가장 오래된 데이터 (24시간 전)
            current_oi = float(oi_history_24h[-1]['sumOpenInterest']) # 가장 최신 데이터

            oi_change_24h = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago != 0 else 0

            # 4시간 전 OI
            oi_history_4h = client.get_open_interest_hist(symbol=symbol, period='1h', limit=4)
            if not oi_history_4h: continue
            oi_4h_ago = float(oi_history_4h[0]['sumOpenInterest'])
            oi_change_4h = ((current_oi - oi_4h_ago) / oi_4h_ago) * 100 if oi_4h_ago != 0 else 0

            # 롱/숏 계정 비율 (1시간)
            long_short_ratio_1h = client.long_short_account_ratio(symbol=symbol, period='1h', limit=1)
            if not long_short_ratio_1h: continue
            long_accounts_percent_1h = float(long_short_ratio_1h[0]['longAccount']) * 100 # longAccount는 비율로 제공됨

            # 펀딩 비율 (최근 펀딩 비율 및 평균)
            funding_rate_data = client.futures_funding_rate(symbol=symbol, limit=10) # 최근 10개 펀딩 비율
            if not funding_rate_data: continue
            avg_funding_rate = sum([float(f['fundingRate']) for f in funding_rate_data]) / len(funding_rate_data)

            # OI / Volume 24H
            oi_volume_ratio_24h = current_oi / volume_24h if volume_24h != 0 else 0

            coin_data = {
                'symbol': symbol,
                'oi_change_24h': oi_change_24h,
                'oi_change_4h': oi_change_4h,
                'long_accounts_1h': long_accounts_percent_1h,
                'price_change_24h': price_change_24h,
                'oi_volume_24h': oi_volume_ratio_24h,
                'funding_rate_avg': avg_funding_rate
            }
            all_coin_data.append(coin_data)
            time.sleep(0.1) # Rate limit 방지를 위한 딜레이

        except Exception as e:
            print(f"오류 발생 ({symbol}): {e}")
            continue
    print("\n데이터 수집 완료.")
    return all_coin_data

def screen_coins(data):
    print("\n=== 코인 스크리닝 시작 ===")
    found_coins = []
    for coin in data:
        if (coin['oi_change_24h'] > OI_CHANGE_24H_MIN and
            coin['oi_change_4h'] > OI_CHANGE_4H_MIN and
            coin['long_accounts_1h'] > LONG_ACCOUNTS_1H_MIN and
            coin['long_accounts_1h'] < LONG_ACCOUNTS_1H_MAX and
            coin['price_change_24h'] < PRICE_CHANGE_24H_MAX and
            coin['oi_volume_24h'] > OI_VOLUME_24H_MIN and
            coin['funding_rate_avg'] > FUNDING_RATE_AVG_MIN):
            found_coins.append(coin)
    return found_coins

def print_results(found_coins):
    print("\n--- 스크리닝 결과 ---")
    if found_coins:
        print(f"총 {len(found_coins)}개의 코인이 기준을 만족합니다:")
        print(f"{'Symbol':<12} | {'OI Chg 24H':>12} | {'OI Chg 4H':>11} | {'Long Acc 1H':>12} | {'Price Chg 24H':>13} | {'OI/Vol 24H':>11} | {'Funding Rate':>12}")
        print("-" * 95)
        for coin in found_coins:
            print(f"{coin['symbol']:<12} | {coin['oi_change_24h']:>11.2f}% | {coin['oi_change_4h']:>10.2f}% | {coin['long_accounts_1h']:>11.2f}% | {coin['price_change_24h']:>12.2f}% | {coin['oi_volume_24h']:>10.2f} | {coin['funding_rate_avg']*100:>11.4f}%")
    else:
        print("기준에 맞는 코인을 찾지 못했습니다.")
    print("\n스크리닝 완료.")

if __name__ == '__main__':
    print(f"--- 바이낸스 선물 코인 스크리너 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"기준:")
    print(f"  - Open Interest Change % 24H > {OI_CHANGE_24H_MIN}%")
    print(f"  - Open Interest Change % 4H > {OI_CHANGE_4H_MIN}%")
    print(f"  - Long Accounts % (1H) > {LONG_ACCOUNTS_1H_MIN}% and < {LONG_ACCOUNTS_1H_MAX}%")
    print(f"  - Price Change % 24H < {PRICE_CHANGE_24H_MAX}%")
    print(f"  - Open Interest / Volume 24H > {OI_VOLUME_24H_MIN}")
    print(f"  - Funding Rate Average > {FUNDING_RATE_AVG_MIN*100:.4f}%")
    print("-" * 70)

    data = get_binance_futures_data()
    if data:
        filtered_coins = screen_coins(data)
        print_results(filtered_coins)
    else:
        print("데이터를 가져오는 데 실패하여 스크리닝을 진행할 수 없습니다.")
