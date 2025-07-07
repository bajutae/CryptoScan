

import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import ccxt.async_support as ccxt

async def get_market_data(exchange):
    """Fetches required market data from the exchange."""
    btc_usdt = await exchange.fetch_ticker('BTC/USDT')
    eth_usdt = await exchange.fetch_ticker('ETH/USDT')
    eth_btc = await exchange.fetch_ticker('ETH/BTC')
    
    # We will use a proxy by looking at the 24h volume of BTC, ETH, and a few top stablecoins against a common quote currency like USD or USDT.
    # This is a rough estimation. For accurate dominance, a dedicated data source like CoinMarketCap API is needed.
    async def safe_fetch_ticker(exchange, symbol):
        try:
            return await exchange.fetch_ticker(symbol)
        except Exception:
            return None

    usdt_ticker = await safe_fetch_ticker(exchange, 'USDT/USD') or await safe_fetch_ticker(exchange, 'USDT/USDC')
    usdc_ticker = await safe_fetch_ticker(exchange, 'USDC/USD') or await safe_fetch_ticker(exchange, 'USDC/USDT')

    return {
        "btc_price_usd": btc_usdt['last'],
        "eth_price_usd": eth_usdt['last'],
        "eth_btc_price": eth_btc['last'],
        "btc_volume_24h": btc_usdt['quoteVolume'],
        "eth_volume_24h": eth_usdt['quoteVolume'],
        "usdt_volume_24h": usdt_ticker['quoteVolume'] if usdt_ticker else 0,
        "usdc_volume_24h": usdc_ticker['quoteVolume'] if usdc_ticker else 0,
    }

async def analyze_market_with_gemini():
    """
    Analyzes the crypto market using data from an exchange and the Gemini API.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("오류: GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        print("시장 데이터 수집 중...")
        market_data = await get_market_data(exchange)
        
        print("Gemini API로 시장 분석 요청 중...")
        
        prompt = f"""
        다음 암호화폐 시장 데이터를 기반으로 오늘의 시장 상황을 상세히 분석해줘.
        결과는 마크다운 형식으로, 각 항목을 명확하게 구분해서 설명해줘.

        **제공된 데이터:**
        - 비트코인(BTC) 가격 (USD): ${market_data['btc_price_usd']:,.2f}
        - 이더리움(ETH) 가격 (USD): ${market_data['eth_price_usd']:,.2f}
        - ETH/BTC 비율: {market_data['eth_btc_price']:.6f}
        - BTC 24시간 거래량 (USD): ${market_data['btc_volume_24h']:,.2f}
        - ETH 24시간 거래량 (USD): ${market_data['eth_volume_24h']:,.2f}
        - USDT 24시간 거래량 (USD): ${market_data['usdt_volume_24h']:,.2f}
        - USDC 24시간 거래량 (USD): ${market_data['usdc_volume_24h']:,.2f}

        **분석 항목:**
        1.  **비트코인 도미넌스 시황:** 현재 비트코인 가격과 거래량을 바탕으로 시장에서의 지배력을 분석해줘.
        2.  **BTC/ETH 가격 차트 분석:** ETH/BTC 비율의 의미를 설명하고, 현재 수치가 이더리움의 상대적 강세 또는 약세를 어떻게 나타내는지 분석해줘.
        3.  **테더(USDT) 도미넌스 시황:** USDT와 USDC의 거래량을 통해 스테이블코인의 시장 점유율과 자금 흐름에 대해 추론하고, 이것이 시장에 미치는 영향을 설명해줘.
        4.  **종합적인 시장 전망:** 위의 분석들을 종합하여 현재 시장 상황에 대한 단기적인 전망을 제시해줘.
        """

        response = await model.generate_content_async(prompt)
        
        print("\n--- Gemini 시장 분석 결과 ---")
        print(response.text)
        print("---------------------------\n")

    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(analyze_market_with_gemini())

