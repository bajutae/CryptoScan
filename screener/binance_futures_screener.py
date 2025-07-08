import asyncio
from datetime import datetime
import ccxt.async_support as ccxt
import pandas as pd

# --- 설정 ---
# 스크리닝 기준
MIN_OI_CHANGE_24H = 0.0  # 24시간 미결제약정 증가율 (%)
MIN_OI_CHANGE_4H = 0.0   # 4시간 미결제약정 증가율 (%)
MAX_PRICE_CHANGE_24H = 1000.0  # 24시간 가격 상승률 제한 (%)
MIN_OI_USD_24H = 0 # 최소 24시간 미결제약정 (1천만 USD)
MIN_VOLUME_USD_24H = 0 # 최소 24시간 거래량 (5천만 USD)

async def fetch_symbol_data(exchange, symbol):
    """단일 심볼에 대한 모든 필요 데이터를 비동기적으로 가져옵니다."""
    try:
        now = exchange.milliseconds()
        since_24h = now - 24 * 60 * 60 * 1000
        
        # 1. Ticker 정보 (가격 변동, 거래량)
        ticker = await exchange.fetch_ticker(symbol)
        price_change_24h = ticker.get('percentage')
        volume_24h_usd = ticker.get('quoteVolume')

        if price_change_24h is None or volume_24h_usd is None:
            print(f"  - {symbol}: Ticker 데이터 부족 (price_change_24h: {price_change_24h}, volume_24h_usd: {volume_24h_usd})")
            return None

        # 2. 미결제 약정 (Open Interest)
        oi_history = await exchange.fetch_open_interest_history(symbol, '1h', since=since_24h, limit=25)
        if len(oi_history) < 24:
            print(f"  - {symbol}: OI 히스토리 부족 ({len(oi_history)}개)")
            return None

        current_oi_usd = oi_history[-1]['openInterestValue']
        oi_24h_ago = oi_history[0]['openInterestValue']
        # oi_4h_ago 계산 시 인덱스 오류 방지
        oi_4h_ago_index = -4 if len(oi_history) >= 4 else 0
        oi_4h_ago = oi_history[oi_4h_ago_index]['openInterestValue']

        oi_change_24h = ((current_oi_usd - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago else 0
        oi_change_4h = ((current_oi_usd - oi_4h_ago) / oi_4h_ago) * 100 if oi_4h_ago else 0

        # 기본 필터링: 거래량 및 OI 최소 기준
        if current_oi_usd < MIN_OI_USD_24H:
            print(f"  - {symbol}: OI 부족 ({current_oi_usd:.0f} < {MIN_OI_USD_24H})")
            return None
        if volume_24h_usd < MIN_VOLUME_USD_24H:
            print(f"  - {symbol}: Volume 부족 ({volume_24h_usd:.0f} < {MIN_VOLUME_USD_24H})")
            return None

        return {
            'symbol': symbol,
            'price_change_24h': price_change_24h,
            'volume_24h_usd': volume_24h_usd,
            'current_oi_usd': current_oi_usd,
            'oi_change_24h': oi_change_24h,
            'oi_change_4h': oi_change_4h,
        }
    except Exception as e:
        print(f"  - {symbol}: 데이터 수집 중 예외 발생: {e}")
        return None

async def get_binance_futures_data():
    """모든 선물 시장의 데이터를 병렬로 가져옵니다."""
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    all_coin_data = []
    try:
        markets = await exchange.load_markets()
        symbols = [m['symbol'] for m in markets.values() if m.get('type') == 'future' and m.get('active') and m['symbol'].endswith(':USDT')]
        print(f"총 {len(symbols)}개의 USDT 기반 선물 심볼 분석 시작...")

        tasks = [fetch_symbol_data(exchange, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        all_coin_data = [res for res in results if res is not None]

    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")
    finally:
        await exchange.close()
        print(f"\n총 {len(all_coin_data)}개의 유효한 심볼 데이터 수집 완료.")
        return all_coin_data

def screen_coins(data):
    """수집된 데이터를 기준으로 코인을 스크리닝합니다."""
    print(f"\n=== 코인 스크리닝 시작 (총 {len(data)}개 심볼) ===")
    
    # 1차 필터링: OI 및 Volume 최소 기준 (fetch_symbol_data에서 이미 처리됨)
    # 여기서는 추가적인 필터링만 수행
    
    # 2차 필터링: 24H OI Change
    filtered_by_oi_24h = [coin for coin in data if coin['oi_change_24h'] > MIN_OI_CHANGE_24H]
    print(f"  - 24H OI Change ({MIN_OI_CHANGE_24H}%) 통과: {len(filtered_by_oi_24h)}개")

    # 3차 필터링: 4H OI Change
    filtered_by_oi_4h = [coin for coin in filtered_by_oi_24h if coin['oi_change_4h'] > MIN_OI_CHANGE_4H]
    print(f"  - 4H OI Change ({MIN_OI_CHANGE_4H}%) 통과: {len(filtered_by_oi_4h)}개")

    # 4차 필터링: Price Change 24H
    final_filtered_coins = [coin for coin in filtered_by_oi_4h if coin['price_change_24h'] < MAX_PRICE_CHANGE_24H]
    print(f"  - 24H Price Change (< {MAX_PRICE_CHANGE_24H}%) 통과: {len(final_filtered_coins)}개")

    return final_filtered_coins

def print_results(found_coins):
    """스크리닝 결과를 표 형식으로 출력합니다."""
    print("\n--- 스크리닝 결과 ---")
    if found_coins:
        sorted_coins = sorted(found_coins, key=lambda x: x['oi_change_24h'], reverse=True)
        print(f"총 {len(sorted_coins)}개의 코인이 기준을 만족합니다:")
        print(f"{'Symbol':<15} | {'Price Chg 24H':>15} | {'OI Chg 24H':>13} | {'OI Chg 4H':>12} | {'OI (USD)':>15} | {'Volume 24H (USD)':>20}")
        print("-" * 105)
        for coin in sorted_coins:
            oi_usd_str = f"{coin['current_oi_usd']/1_000_000:.1f}M"
            vol_usd_str = f"{coin['volume_24h_usd']/1_000_000:.1f}M"
            print(f"{coin['symbol']:<15} | {coin['price_change_24h']:>14.2f}% | {coin['oi_change_24h']:>12.2f}% | {coin['oi_change_4h']:>11.2f}% | {oi_usd_str:>15} | {vol_usd_str:>20}")
    else:
        print("기준에 맞는 코인을 찾지 못했습니다.")
    print("\n스크리닝 완료.")

async def futures_screener_async():
    """비동기 로직을 실행하는 메인 함수"""
    print(f"--- 바이낸스 선물 OI 기반 스크리너 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"기준:")
    print(f"  - 24H OI Change > {MIN_OI_CHANGE_24H}%")
    print(f"  - 4H OI Change > {MIN_OI_CHANGE_4H}%")
    print(f"  - 24H Price Change < {MAX_PRICE_CHANGE_24H}%")
    print(f"  - 24H Min OI > ${MIN_OI_USD_24H/1_000_000:.0f}M")
    print(f"  - 24H Min Volume > ${MIN_VOLUME_USD_24H/1_000_000:.0f}M")
    print("-" * 70)

    data = await get_binance_futures_data()
    if data:
        filtered_coins = screen_coins(data)
        print_results(filtered_coins)
    else:
        print("데이터를 가져오는 데 실패하여 스크리닝을 진행할 수 없습니다.")

def futures_screener():
    """스크리너를 동기적으로 실행하기 위한 래퍼 함수"""
    asyncio.run(futures_screener_async())

if __name__ == '__main__':
    futures_screener()
