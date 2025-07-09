import logging
import pandas as pd
import os
import sys
import argparse
from sqlalchemy.orm import Session # Session 임포트

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.market_data import get_active_symbols, get_ohlcv, calculate_indicators
from utils.config_loader import CONFIG
from utils.database import ScreenerResult # ScreenerResult 모델 임포트
import json # json 임포트
from .daily_screener import EXCHANGE, BASE_CURRENCY

def altcoin_screener(
    db: Session, # db 세션 인자 추가
    min_daily_volume_usd: float = CONFIG.get("altcoin_screener", {}).get("min_daily_volume_usd", 500_000_000),
    max_listing_days: int = CONFIG.get("altcoin_screener", {}).get("max_listing_days", 1648),
    min_downtrend_from_ath: float = CONFIG.get("altcoin_screener", {}).get("min_downtrend_from_ath", 0.70),
    min_volatility: float = CONFIG.get("altcoin_screener", {}).get("min_volatility", 40.0),
    max_volatility: float = CONFIG.get("altcoin_screener", {}).get("max_volatility", 70.0),
    min_cci: float = CONFIG.get("altcoin_screener", {}).get("min_cci", -50.0),
    max_cci: float = CONFIG.get("altcoin_screener", {}).get("max_cci", 50.0),
    cci_period: int = CONFIG.get("altcoin_screener", {}).get("cci_period", 20)
):
    """
    MOVE/KRW, IMX/KRW와 유사한 특징을 가진 알트코인을 탐색합니다.
    """
    header = "=== MOVE/IMX 유사 코인 탐색 스크립트 ===\n"
    header += f"거래소: {EXCHANGE.upper()}, 기준 통화: {BASE_CURRENCY}\n"
    header += "-" * 40 + "\n"
    logger.info(f"알트코인 스크리너 시작. 파라미터: {{min_daily_volume_usd=min_daily_volume_usd, max_listing_days=max_listing_days, min_downtrend_from_ath=min_downtrend_from_ath, min_volatility=min_volatility, max_volatility=max_volatility, min_cci=min_cci, max_cci=max_cci, cci_period=cci_period}}")

    symbols = get_active_symbols(EXCHANGE, BASE_CURRENCY)
    if not symbols:
        logger.error(f"{EXCHANGE}에서 {BASE_CURRENCY} 마켓 정보를 가져오는 데 실패했습니다.")
        return {"output": f"{EXCHANGE}에서 {BASE_CURRENCY} 마켓 정보를 가져오는 데 실패했습니다.", "charts": [], "table_data": {"headers": [], "rows": []}}

    logger.info(f"총 {len(symbols)}개의 {BASE_CURRENCY} 마켓 코인을 대상으로 분석을 시작합니다.")

    found_coins = []
    chart_paths = [] # altcoin 스크리너는 현재 차트를 생성하지 않지만, 구조를 맞춤
    
    max_indicator_period = cci_period
    if USE_RSI_FILTER:
        max_indicator_period = max(max_indicator_period, RSI_PERIOD)
    if USE_VOLUME_INCREASE_FILTER:
        max_indicator_period = max(max_indicator_period, VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD)

    required_days = max_listing_days + max_indicator_period + 5

    for i, symbol in enumerate(symbols):
        logger.debug(f"[{i+1}/{len(symbols)}] 분석 중: {symbol}...")
        
        try:
            df = get_ohlcv(EXCHANGE, symbol, '1d', limit=required_days)
            if df is None or len(df) < max_indicator_period:
                logger.debug(f"{symbol}: OHLCV 데이터 부족 또는 로드 실패.")
                continue

            if len(df) > max_listing_days:
                logger.debug(f"{symbol}: 상장일 ({len(df)}일) 기준 미달.")
                continue

            df = calculate_indicators(df, cci_period=cci_period, rsi_period=RSI_PERIOD)
            
            ath = df['high'].max()
            latest = df.iloc[-1]
            
            recent_high = df['high'].tail(30).max()
            recent_low = df['low'].tail(30).min()
            volatility_metric = ((recent_high - recent_low) / latest['close']) * 100 if latest['close'] > 0 else 0

            daily_volume_usd = latest['close'] * latest['volume']
            if daily_volume_usd < min_daily_volume_usd:
                logger.debug(f"{symbol}: 일일 거래량 ({daily_volume_usd:.0f} USD) 기준 미달.")
                continue

            downtrend_from_ath = (1 - latest['close'] / ath)
            if downtrend_from_ath < min_downtrend_from_ath:
                logger.debug(f"{symbol}: ATH 대비 하락률 ({downtrend_from_ath:.2f}) 기준 미달.")
                continue

            if not (min_volatility <= volatility_metric <= max_volatility):
                logger.debug(f"{symbol}: 변동성 ({volatility_metric:.2f}%) 기준 미달.")
                continue
            
            current_cci = latest[f'CCI_{cci_period}_0.015']
            if not (min_cci <= current_cci <= max_cci):
                logger.debug(f"{symbol}: CCI ({current_cci:.2f}) 기준 미달.")
                continue

            if USE_RSI_FILTER:
                current_rsi = latest[f'RSI_{RSI_PERIOD}']
                if current_rsi < MIN_RSI:
                    logger.debug(f"{symbol}: RSI ({current_rsi:.2f}) 기준 미달.")
                    continue

            if USE_VOLUME_INCREASE_FILTER:
                if len(df) < VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD:
                    logger.debug(f"{symbol}: 거래량 증가 분석을 위한 데이터 부족.")
                    continue
                recent_avg_volume = df['volume'].tail(VOLUME_INCREASE_PERIOD).mean()
                compare_avg_volume = df['volume'].iloc[-(VOLUME_COMPARE_PERIOD + VOLUME_INCREASE_PERIOD):-VOLUME_INCREASE_PERIOD].mean()
                
                if compare_avg_volume > 0:
                    volume_increase_percentage = ((recent_avg_volume - compare_avg_volume) / compare_avg_volume) * 100
                    if volume_increase_percentage < MIN_VOLUME_INCREASE_PERCENTAGE:
                        logger.debug(f"{symbol}: 거래량 증가율 ({volume_increase_percentage:.2f}%) 기준 미달.")
                        continue
                else:
                    logger.debug(f"{symbol}: 비교 거래량 0으로 거래량 증가 분석 불가.")
                    continue

            coin_data = {
                "symbol": symbol,
                "downtrend": downtrend_from_ath * 100,
                "volatility": volatility_metric,
                "cci": current_cci,
            }
            if USE_RSI_FILTER:
                coin_data["rsi"] = latest.get(f'RSI_{RSI_PERIOD}')
            if USE_VOLUME_INCREASE_FILTER:
                coin_data["volume_increase_percentage"] = volume_increase_percentage
            found_coins.append(coin_data)
            logger.info(f"[발견!] {symbol} 이(가) 알트코인 스크리너 기준에 부합합니다.")

        except Exception as e:
            logger.error(f"코인 {symbol} 분석 중 오류 발생: {e}")
            continue
            
    output_content = header
    table_headers = ['종목명', 'ATH대비', '변동성(30일)', '현재CCI']
    if USE_RSI_FILTER: table_headers.append('현재RSI')
    if USE_VOLUME_INCREASE_FILTER: table_headers.append('거래량증가율')
    table_rows = []

    output_content += "\n=== 분석 완료 ===\n"
    if found_coins:
        output_content += f"총 {len(found_coins)}개의 잠재적 코인을 발견했습니다:\n"
        output_content += ", ".join([coin['symbol'] for coin in found_coins]) + "\n\n"

        # 테이블 형식으로 결과 구성
        result_table_header = " | ".join([f'{h:<12}' for h in table_headers]) + "\n"

        result_separator = "-" * (len(result_table_header) - 1) + "\n"

        output_content += result_table_header + result_separator

        for coin in found_coins:
            row = [coin['symbol']] 
            row.append(f"-{coin['downtrend']:.1f}%")
            row.append(f"{coin['volatility']:.1f}%")
            row.append(f"{coin['cci']:.1f}")
            if USE_RSI_FILTER and "rsi" in coin: row.append(f"{coin['rsi']:.1f}")
            if USE_VOLUME_INCREASE_FILTER and "volume_increase_percentage" in coin: row.append(f"{coin['volume_increase_percentage']:.1f}%")
            table_rows.append(row)
            output_content += " | ".join([f'{item:<12}' for item in row]) + "\n"

    else:
        output_content += "기준에 맞는 코인을 찾지 못했습니다. 설정을 변경하여 다시 시도해보세요.\n"

    logger.info("알트코인 스크리너 분석 완료.")

    # 데이터베이스에 결과 저장
    screener_result_db = ScreenerResult(
        screener_name="altcoin",
        output_text=output_content,
        chart_paths=json.dumps(chart_paths),
        table_headers=json.dumps(table_headers),
        table_rows=json.dumps(table_rows)
    )
    db.add(screener_result_db)
    db.commit()
    db.refresh(screener_result_db)
    logger.info(f"알트코인 스크리너 결과 DB에 저장됨: ID {screener_result_db.id}")

    return {
        "output": output_content,
        "charts": chart_paths,
        "table_data": {
            "headers": table_headers,
            "rows": table_rows
        }
    }