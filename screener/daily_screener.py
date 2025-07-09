import logging
import pandas as pd
from datetime import datetime
import os
import sys
import mplfinance as mpf
from sqlalchemy.orm import Session # Session 임포트

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.market_data import get_active_symbols, get_ohlcv, calculate_indicators
from utils.charting import save_chart
from utils.config_loader import CONFIG
from utils.database import ScreenerResult, get_db # ScreenerResult 모델 및 get_db 임포트
import json # json 임포트

from celery_app import celery_app # celery_app 임포트

logger = logging.getLogger(__name__)

# --- 최종 데일리 분석 기준 ---
EXCHANGE = 'upbit'
BASE_CURRENCY = 'KRW'
OUTPUT_DIR = 'charts'

# 2. 과거 거래량 분석 기준
VOLUME_LOOKBACK_DAYS = 30
CHART_DAYS = 120
# ----------------------------------------------------

def daily_screener(
    db: Session, # db 세션 인자 추가
    min_daily_volume_krw: float = CONFIG.get("daily_screener", {}).get("min_daily_volume_krw", 500_000_000),
    min_downtrend_from_ath: float = CONFIG.get("daily_screener", {}).get("min_downtrend_from_ath", 0.70),
    min_volatility_30d: float = CONFIG.get("daily_screener", {}).get("min_volatility_30d", 45.0),
    max_volatility_30d: float = CONFIG.get("daily_screener", {}).get("max_volatility_30d", 75.0),
    min_cci: float = CONFIG.get("daily_screener", {}).get("min_cci", -40.0),
    max_cci: float = CONFIG.get("daily_screener", {}).get("max_cci", 40.0),
    cci_period: int = CONFIG.get("daily_screener", {}).get("cci_period", 20)
):
    """
    매일 실행하여 관심 코인을 찾아내고, 결과를 watchlist.txt와 차트 이미지로 저장합니다.
    """
    header = f"--- {datetime.now().strftime('%Y-%m-%d')} 데일리 관심 코인 스크리너 ---\n"
    logger.info(f"데일리 스크리너 시작. 파라미터: {{min_daily_volume_krw=min_daily_volume_krw, min_downtrend_from_ath=min_downtrend_from_ath, min_volatility_30d=min_volatility_30d, max_volatility_30d=max_volatility_30d, min_cci=min_cci, max_cci=max_cci, cci_period=cci_period}}")

    symbols = get_active_symbols(EXCHANGE, BASE_CURRENCY)
    if not symbols:
        logger.error(f"{EXCHANGE}에서 {BASE_CURRENCY} 마켓 정보를 가져오는 데 실패했습니다.")
        return {"output": f"{EXCHANGE}에서 {BASE_CURRENCY} 마켓 정보를 가져오는 데 실패했습니다.", "charts": [], "table_data": {"headers": [], "rows": []}}
        
    logger.info(f"총 {len(symbols)}개의 {BASE_CURRENCY} 마켓 코인 분석 시작...")

    found_coins = []
    chart_paths = []
    
    for i, symbol in enumerate(symbols):
        logger.debug(f"[{i+1}/{len(symbols)}] 분석 중: {symbol}...")
        
        try:
            df = get_ohlcv(EXCHANGE, symbol, '1d', limit=2000)
            if df is None or len(df) < cci_period + 30:
                logger.debug(f"{symbol}: OHLCV 데이터 부족 또는 로드 실패.")
                continue

            df = calculate_indicators(df, cci_period=cci_period)
            ath = df['high'].max()
            latest = df.iloc[-1]
            
            downtrend_from_ath = (1 - latest['close'] / ath)
            if downtrend_from_ath < min_downtrend_from_ath:
                logger.debug(f"{symbol}: ATH 대비 하락률 ({downtrend_from_ath:.2f}) 기준 미달.")
                continue
            
            recent_high = df['high'].tail(30).max()
            recent_low = df['low'].tail(30).min()
            volatility_metric = ((recent_high - recent_low) / latest['close']) * 100 if latest['close'] > 0 else 0
            if not (min_volatility_30d <= volatility_metric <= max_volatility_30d):
                logger.debug(f"{symbol}: 30일 변동성 ({volatility_metric:.2f}%) 기준 미달.")
                continue
            
            current_cci = latest[f'CCI_{cci_period}_0.015']
            if not (min_cci <= current_cci <= max_cci):
                logger.debug(f"{symbol}: CCI ({current_cci:.2f}) 기준 미달.")
                continue

            if (latest['close'] * latest['volume']) < min_daily_volume_krw:
                logger.debug(f"{symbol}: 일일 거래량 ({latest['close'] * latest['volume']:.0f} KRW) 기준 미달.")
                continue

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
            logger.info(f"[발견!] {symbol} 이(가) 데일리 스크리너 기준에 부합합니다.")
            
            # 차트 생성 정보 준비
            cci_panel = mpf.make_addplot(df.tail(CHART_DAYS)[f'CCI_{cci_period}_0.015'], panel=2, color='purple', ylabel='CCI')
            spike_date = pd.to_datetime(coin_data['max_spike_date_full'])
            
            chart_title = coin_data['symbol']

            chart_path = save_chart(
                df,
                symbol,
                chart_days=CHART_DAYS,
                output_dir=OUTPUT_DIR,
                title=chart_title,
                add_plots=[cci_panel],
                vlines=[spike_date]
            )
            if chart_path:
                chart_paths.append(chart_path)

        except Exception as e:
            logger.error(f"코인 {symbol} 분석 중 오류 발생: {e}")
            continue
            
    # 결과 요약
    output_content = header
    table_headers = ['종목명', 'ATH대비', '변동성(30일)', '현재CCI', '과거 거래량 급증']
    table_rows = []

    if found_coins:
        sorted_coins = sorted(found_coins, key=lambda x: x['max_volume_spike'], reverse=True)
        
        result_header = f"총 {len(sorted_coins)}개의 관심 코인을 발견했습니다. (결과는 '{os.path.join(os.getcwd(), OUTPUT_DIR)}' 폴더에 저장됨)\n\n"
        result_table_header = f"{'종목명':<12} | {'ATH대비':>8} | {'변동성(30일)':>12} | {'현재CCI':>8} | {'과거 거래량 급증':>15}\n"
        result_separator = "-" * 70 + "\n"

        output_content += result_header + result_table_header + result_separator

        for coin in sorted_coins:
            ath_str = f"-{coin['downtrend']:.1f}%"
            vol_str = f"{coin['volatility']:.1f}%"
            cci_str = f"{coin['cci']:.1f}"
            vol_spike_str = f"{coin['max_volume_spike']:.1f}배 ({coin['max_spike_date']})"
            
            line = f"{coin['symbol']:<12} | {ath_str:>8} | {vol_str:>12} | {cci_str:>8} | {vol_spike_str:>15}\n"
            output_content += line
            table_rows.append([coin['symbol'], ath_str, vol_str, cci_str, vol_spike_str])
    else:
        result_none = "오늘의 기준에 맞는 관심 코인을 찾지 못했습니다.\n"
        output_content += result_none

    output_content += "-" * 70 + "\n"
    
    logger.info("데일리 스크리너 분석 완료.")

    # 데이터베이스에 결과 저장
    screener_result_db = ScreenerResult(
        screener_name="daily",
        output_text=output_content,
        chart_paths=json.dumps(chart_paths),
        table_headers=json.dumps(table_headers),
        table_rows=json.dumps(table_rows)
    )
    db.add(screener_result_db)
    db.commit()
    db.refresh(screener_result_db)
    logger.info(f"데일리 스크리너 결과 DB에 저장됨: ID {screener_result_db.id}")

    # 데이터베이스에 결과 저장
    screener_result_db = ScreenerResult(
        screener_name="daily",
        output_text=output_content,
        chart_paths=json.dumps(chart_paths),
        table_headers=json.dumps(table_headers),
        table_rows=json.dumps(table_rows)
    )
    db.add(screener_result_db)
    db.commit()
    db.refresh(screener_result_db)
    logger.info(f"데일리 스크리너 결과 DB에 저장됨: ID {screener_result_db.id}")

    return {
        "output": output_content,
        "charts": chart_paths,
        "table_data": {
            "headers": table_headers,
            "rows": table_rows
        }
    }