
import mplfinance as mpf
import pandas as pd
import os

def save_chart(
    df,
    symbol,
    chart_days=120,
    output_dir='charts',
    title='',
    add_plots=None,
    vlines=None
):
    """mplfinance를 사용하여 차트를 생성하고 지정된 경로에 저장합니다."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df_chart = df.tail(chart_days).copy()
    df_chart.set_index('timestamp', inplace=True)

    # 파일 경로 설정
    output_path = os.path.join(output_dir, f"{symbol.replace('/', '_')}.png")

    # 차트 생성 및 저장
    try:
        mpf.plot(df_chart, 
                 type='candle', 
                 style='yahoo',
                 title=title,
                 volume=True, 
                 panel_ratios=(3, 1),
                 addplot=add_plots,
                 vlines=dict(vlines=vlines, linewidths=0.5, colors='r', alpha=0.7) if vlines else None,
                 savefig=dict(fname=output_path, dpi=150, bbox_inches='tight'))
        print(f"Chart saved to {output_path}")  # 차트 저장 경로 출력
    except Exception as e:
        print(f"Error creating chart for {symbol}: {e}")
