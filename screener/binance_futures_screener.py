import asyncio
from datetime import datetime
import ccxt.async_support as ccxt

# --- 설정 ---
# 스크리닝 기준
OI_CHANGE_24H_MIN = 2.0  # Open Interest Change % 24H > 2%
OI_CHANGE_4H_MIN = 1.0   # Open Interest Change % 4H > 1%
LONG_ACCOUNTS_1H_MIN = 45.0 # Long Accounts % (1H) > 45%
LONG_ACCOUNTS_1H_MAX = 70.0 # Long Accounts % (1H) < 70%
PRICE_CHANGE_24H_MAX = 6.0  # Price Change % 24H < 6%
OI_VOLUME_24H_MIN = 0.4     # Open Interest / Volume 24H > 0.4
FUNDING_RATE_AVG_MIN = 0.00006 # Funding Rate Average > 0.006% (0.006%는 0.00006)

# --- 함수 정의 ---
async def get_binance_futures_data():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    
    print("바이낸스 선물 시장 데이터 로딩 중...")
    try:
        markets = await exchange.load_markets()
        symbols = [m['symbol'] for m in markets.values() if m.get('type') == 'future' and m.get('active')]
        print(f"총 {len(symbols)}개의 선물 심볼 발견.")
    except Exception as e:
        print(f"거래소 정보 로딩 실패: {e}")
        await exchange.close()
        return []

    all_coin_data = []
    
    try:
        tickers = await exchange.fetch_tickers(symbols)
    except Exception as e:
        print(f"티커 정보 로딩 실패: {e}")
        await exchange.close()
        return []

    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] 데이터 수집 중: {symbol}...", end='\r')
        try:
            ticker = tickers.get(symbol)
            if not ticker: continue

            price_change_24h = ticker['change']
            volume_24h = ticker['quoteVolume']

            now = exchange.milliseconds()
            since_24h = now - 24 * 60 * 60 * 1000
            since_4h = now - 4 * 60 * 60 * 1000

            oi_history_24h = await exchange.fetch_open_interest_history(symbol, '1h', since=since_24h, limit=24)
            if not oi_history_24h: continue
            oi_24h_ago = oi_history_24h[0]['openInterestValue']
            current_oi = oi_history_24h[-1]['openInterestValue']
            oi_change_24h = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago != 0 else 0

            oi_history_4h = [oi for oi in oi_history_24h if oi['timestamp'] >= since_4h]
            if not oi_history_4h: continue
            oi_4h_ago = oi_history_4h[0]['openInterestValue']
            oi_change_4h = ((current_oi - oi_4h_ago) / oi_4h_ago) * 100 if oi_4h_ago != 0 else 0

            long_short_ratio_1h = await exchange.fapiPublicGet('globalLongShortAccountRatio', {'symbol': symbol, 'period': '1h', 'limit': 1})
            if not long_short_ratio_1h: continue
            long_accounts_percent_1h = float(long_short_ratio_1h[0]['longAccount']) * 100

            funding_rate_data = await exchange.fetch_funding_rate_history(symbol, limit=10)
            if not funding_rate_data: continue
            avg_funding_rate = sum(f['fundingRate'] for f in funding_rate_data) / len(funding_rate_data)

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

        except Exception as e:
            continue
            
    await exchange.close()
    print("\n데이터 수집 완료.")
    return all_coin_data

def screen_coins(data):
    print("\n=== 코인 스크리닝 시작 ===")
    found_coins = []
    for coin in data:
        if (
            coin['oi_change_24h'] > OI_CHANGE_24H_MIN and
            coin['oi_change_4h'] > OI_CHANGE_4H_MIN and
            LONG_ACCOUNTS_1H_MIN < coin['long_accounts_1h'] < LONG_ACCOUNTS_1H_MAX and
            coin['price_change_24h'] < PRICE_CHANGE_24H_MAX and
            coin['oi_volume_24h'] > OI_VOLUME_24H_MIN and
            coin['funding_rate_avg'] > FUNDING_RATE_AVG_MIN
        ):
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

async def futures_screener_async():
    print(f"--- 바이낸스 선물 코인 스크리너 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"기준:")
    print(f"  - Open Interest Change % 24H > {OI_CHANGE_24H_MIN}%")
    print(f"  - Open Interest Change % 4H > {OI_CHANGE_4H_MIN}%")
    print(f"  - Long Accounts % (1H) > {LONG_ACCOUNTS_1H_MIN}% and < {LONG_ACCOUNTS_1H_MAX}%")
    print(f"  - Price Change % 24H < {PRICE_CHANGE_24H_MAX}%")
    print(f"  - Open Interest / Volume 24H > {OI_VOLUME_24H_MIN}")
    print(f"  - Funding Rate Average > {FUNDING_RATE_AVG_MIN*100:.4f}%")
    print("-" * 70)

    data = await get_binance_futures_data()
    if data:
        filtered_coins = screen_coins(data)
        print_results(filtered_coins)
    else:
        print("데이터를 가져오는 데 실패하여 스크리닝을 진행할 수 없습니다.")

def futures_screener():
    asyncio.run(futures_screener_async())

if __name__ == '__main__':
    futures_screener()