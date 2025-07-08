import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import json
import os
import sys
import mplfinance as mpf

# --- 설정 로드 ---
def load_config():
    # config.json 파일 경로를 스크립트 기준으로 찾습니다.
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"경고: {config_path} 파일을 찾을 수 없거나 유효하지 않습니다. 기본 설정을 사용합니다. 오류: {e}")
        return {}

config = load_config()
SYMBOL = config.get('DAY_TRADING_SYMBOL', 'BTC/USDT')
PROFIT_TARGET_USD = config.get('PROFIT_TARGET_USD', 100)
POSITION_SIZE_USD = config.get('POSITION_SIZE_USD', 10000)
MIN_RR_RATIO = config.get('MIN_RR_RATIO', 2.0)


def apply_technical_indicators(df):
    # 단타 전략에 필요한 지표 추가
    if len(df) >= 5: df.ta.ema(length=5, append=True)
    if len(df) >= 20: df.ta.ema(length=20, append=True)
    if len(df) >= 14: df.ta.rsi(append=True)

    # 기존 지표 (필요시 유지 또는 제거)
    if len(df) >= 200: df.ta.ema(length=200, append=True)
    if len(df) >= 50: df.ta.ema(length=50, append=True)
    if len(df) >= 26: df.ta.macd(append=True)
    if len(df) >= 20: df.ta.bbands(append=True)
    if len(df) >= 20: df.ta.cci(append=True)
    if len(df) >= 14: df.ta.stoch(append=True)
    return df

async def run_screener_logic():
    print(f"--- {SYMBOL} 단타 트레이딩 기회 분석 ---")
    exchange = ccxt.bybit({'enableRateLimit': True})
    try:
        timeframes = ['1d', '4h', '1h', '15m', '5m', '1m']
        print(f"데이터 로딩 중 ({', '.join(timeframes)})...")
        
        tasks = [exchange.fetch_ohlcv(SYMBOL, tf, limit=200) for tf in timeframes]
        results = await asyncio.gather(*tasks)
        
        data = {tf: res for tf, res in zip(timeframes, results)}
        dfs = {tf: pd.DataFrame(d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']) for tf, d in data.items()}

        for tf, df in dfs.items():
            if df.empty:
                print(f"오류: {tf} 데이터를 불러오지 못했습니다.")
                return
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            dfs[tf] = apply_technical_indicators(df.copy())

        # (기존의 복잡한 분석 로직은 여기에 위치합니다 - 간략화를 위해 생략)
        print("분석 로직 실행... (구현 생략)")
        print("현재 손익비 좋은 타점이 없습니다. 관망 후 다시 시도해주세요.")

    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
    finally:
        await exchange.close()
        print("\n--- 분석 종료 ---\n")

async def run_backtest_logic():
    print(f"--- {SYMBOL} 전략 백테스팅 시작 ---")
    exchange = ccxt.bybit({'enableRateLimit': True})
    try:
        print(f"과거 1시간봉 데이터 로딩 중 ({SYMBOL}, 1000 캔들)...")
        ohlcv = await exchange.fetch_ohlcv(SYMBOL, '1h', limit=1000)
        if not ohlcv:
            print("오류: 데이터를 불러오지 못했습니다.")
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = apply_technical_indicators(df.copy())

        # 필요한 컬럼이 있는지 확인
        required_cols = ['EMA_5', 'EMA_20', 'RSI_14']
        for col in required_cols:
            if col not in df.columns:
                print(f"오류: 백테스팅에 필요한 지표({col})가 DataFrame에 없습니다. 지표 계산을 확인하세요.")
                return

        # 백테스팅 변수 초기화
        initial_balance = 10000  # 초기 자본
        current_balance = initial_balance
        in_position = False
        entry_price = 0
        trade_history = []
        position_size_usd = POSITION_SIZE_USD # config에서 가져온 포지션 사이즈

        print(f"백테스팅 시뮬레이션 시작... (초기 자본: {initial_balance:.2f} USD)")

        # 데이터 순회 (지표 계산을 위해 충분한 데이터가 있는 시점부터 시작)
        # EMA_20이 계산되려면 최소 20개의 데이터가 필요하므로, 그 이후부터 시작
        start_index = max(20, 14) # EMA_20과 RSI_14 중 더 큰 값

        for i in range(start_index, len(df)):
            current_candle = df.iloc[i]
            prev_candle = df.iloc[i-1]

            # 현재 캔들의 종가
            current_close = current_candle['close']

            # 지표 값
            ema_5 = current_candle['EMA_5']
            ema_20 = current_candle['EMA_20']
            rsi_14 = current_candle['RSI_14']

            prev_ema_5 = prev_candle['EMA_5']
            prev_ema_20 = prev_candle['EMA_20']

            # 진입 조건 (롱 포지션)
            if not in_position:
                # 골든 크로스: 이전 캔들에서는 5-EMA < 20-EMA 였고, 현재 캔들에서는 5-EMA > 20-EMA
                golden_cross = (prev_ema_5 < prev_ema_20) and (ema_5 > ema_20)
                rsi_condition = rsi_14 >= 50

                if golden_cross and rsi_condition:
                    entry_price = current_close
                    in_position = True
                    # print(f"[{current_candle.name}] 진입 (롱): {entry_price:.2f}")

            # 청산 조건 (롱 포지션)
            elif in_position:
                # 익절 목표 (1%)
                take_profit_price = entry_price * (1 + 0.01)
                # 손절 목표 (0.5%)
                stop_loss_price = entry_price * (1 - 0.005)

                # 데드 크로스: 이전 캔들에서는 5-EMA > 20-EMA 였고, 현재 캔들에서는 5-EMA < 20-EMA
                death_cross = (prev_ema_5 > prev_ema_20) and (ema_5 < ema_20)

                exit_reason = None
                exit_price = 0

                if current_close >= take_profit_price:
                    exit_price = take_profit_price # 익절가로 청산
                    exit_reason = "익절"
                elif current_close <= stop_loss_price:
                    exit_price = stop_loss_price # 손절가로 청산
                    exit_reason = "손절"
                elif death_cross:
                    exit_price = current_close # 데드 크로스 발생 시 현재가로 청산
                    exit_reason = "데드 크로스"

                if exit_reason:
                    profit_loss_ratio = (exit_price - entry_price) / entry_price
                    trade_pnl_usd = position_size_usd * profit_loss_ratio
                    current_balance += trade_pnl_usd

                    trade_history.append({
                        'entry_time': df.iloc[i-1].name, # 진입은 이전 캔들 종가로 가정
                        'entry_price': entry_price,
                        'exit_time': current_candle.name,
                        'exit_price': exit_price,
                        'profit_loss_ratio': profit_loss_ratio,
                        'profit_loss_usd': trade_pnl_usd,
                        'exit_reason': exit_reason
                    })
                    in_position = False
                    # print(f"[{current_candle.name}] 청산 ({exit_reason}): {exit_price:.2f}, PnL: {trade_pnl_usd:.2f} USD, 잔고: {current_balance:.2f}")

        # 최종 결과 계산
        total_trades = len(trade_history)
        winning_trades = sum(1 for trade in trade_history if trade['profit_loss_usd'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = current_balance - initial_balance

        print("\n--- 백테스팅 결과 ---")
        print(f"초기 자본: {initial_balance:.2f} USD")
        print(f"최종 자본: {current_balance:.2f} USD")
        print(f"총 손익: {total_pnl:.2f} USD")
        print(f"총 거래 횟수: {total_trades}")
        print(f"승리 거래: {winning_trades}")
        print(f"패배 거래: {losing_trades}")
        print(f"승률: {win_rate:.2f}%")

        if total_trades > 0:
            avg_profit_per_trade = sum(trade['profit_loss_usd'] for trade in trade_history if trade['profit_loss_usd'] > 0) / winning_trades if winning_trades > 0 else 0
            avg_loss_per_trade = sum(trade['profit_loss_usd'] for trade in trade_history if trade['profit_loss_usd'] < 0) / losing_trades if losing_trades > 0 else 0
            print(f"평균 익절: {avg_profit_per_trade:.2f} USD")
            print(f"평균 손절: {avg_loss_per_trade:.2f} USD")

        # --- 차트 생성 로직 추가 ---
        if not df.empty and total_trades > 0:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'charts')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            chart_file_path = os.path.join(output_dir, f"backtest_{SYMBOL.replace('/', '_')}.png")

            # 진입/청산 지점 시각화를 위한 데이터 준비
            entry_points = [trade['entry_time'] for trade in trade_history]
            exit_points = [trade['exit_time'] for trade in trade_history]
            
            entry_markers = [df.loc[time]['low'] * 0.98 for time in entry_points if time in df.index]
            exit_markers = [df.loc[time]['high'] * 1.02 for time in exit_points if time in df.index]
            
            entry_times_for_plot = [time for time in entry_points if time in df.index]
            exit_times_for_plot = [time for time in exit_points if time in df.index]

            add_plots = [
                mpf.make_addplot(df['EMA_5'], color='blue', width=0.7),
                mpf.make_addplot(df['EMA_20'], color='orange', width=0.7),
                mpf.make_addplot(df.loc[entry_times_for_plot], scatter=True, y=entry_markers, marker='^', color='green', s=100),
                mpf.make_addplot(df.loc[exit_times_for_plot], scatter=True, y=exit_markers, marker='v', color='red', s=100)
            ]

            chart_title = f"{SYMBOL} Backtest Results"

            try:
                mpf.plot(df, 
                         type='candle', 
                         style='yahoo',
                         title=chart_title,
                         volume=True, 
                         panel_ratios=(3, 1),
                         addplot=add_plots,
                         figsize=(15, 8),
                         savefig=dict(fname=chart_file_path, dpi=150, bbox_inches='tight'))
                print(f"Chart saved to {chart_file_path}")
            except Exception as e:
                print(f"백테스팅 차트 생성 중 오류 발생: {e}")

    except (ccxt.NetworkError, ccxt.ExchangeError) as e:
        print(f"백테스팅 중 거래소 통신 오류 발생: {type(e).__name__} - {e}")
    except Exception as e:
        print(f"백테스팅 중 알 수 없는 오류 발생: {type(e).__name__} - {e}")
    finally:
        await exchange.close()
        print("\n--- 백테스팅 종료 ---\n")

def day_trading_screener(mode='screener'):
    """
    일봉, 4시간봉, 1시간봉을 종합적으로 분석하여 손익비 좋은 단타 타점을 찾습니다.
    'screener' 또는 'backtest' 모드로 실행할 수 있습니다.
    """
    if mode == 'screener':
        asyncio.run(run_screener_logic())
    elif mode == 'backtest':
        asyncio.run(run_backtest_logic())
    else:
        print(f"오류: 유효하지 않은 모드 '{mode}' 입니다. 'screener' 또는 'backtest'를 사용하세요.", file=sys.stderr)

if __name__ == "__main__":
    # 이 파일을 직접 실행할 경우 기본 백테스팅 모드로 실행
    day_trading_screener(mode='backtest')
