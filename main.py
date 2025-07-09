import argparse
import sys
import uvicorn
from screener import daily_screener, altcoin_screener

# --- 메인 실행 로직 ---
def main():
    # 최상위 파서
    parser = argparse.ArgumentParser(
        description='암호화폐 스크리너 및 웹 UI 실행기',
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='실행할 명령')

    # 'web' 커맨드 파서
    parser_web = subparsers.add_parser('web', help='웹 UI를 실행합니다.')
    parser_web.add_argument('--host', default='127.0.0.1', help='호스트 주소')
    parser_web.add_argument('--port', type=int, default=8000, help='포트 번호')

    # 'run' 커맨드 파서 (기존 CLI 기능)
    parser_run = subparsers.add_parser('run', help='CLI에서 스크리너를 직접 실행합니다.')
    # Add a subparser for each screener under 'run'
    screener_subparsers = parser_run.add_subparsers(dest='screener_name', required=True, help='실행할 스크리너')

    # Daily Screener Subparser
    daily_parser = screener_subparsers.add_parser('daily', help='데일리 관심 코인 스크리너')
    daily_parser.add_argument('--min-daily-volume-krw', type=float, default=500_000_000, help='최소 일일 거래량 (KRW)')
    daily_parser.add_argument('--min-downtrend-from-ath', type=float, default=0.70, help='ATH 대비 최소 하락률 (0.0 ~ 1.0)')
    daily_parser.add_argument('--min-volatility-30d', type=float, default=45.0, help='최소 30일 변동성 (%)')
    daily_parser.add_argument('--max-volatility-30d', type=float, default=75.0, help='최대 30일 변동성 (%)')
    daily_parser.add_argument('--min-cci', type=float, default=-40.0, help='최소 CCI 값')
    daily_parser.add_argument('--max-cci', type=float, default=40.0, help='최대 CCI 값')
    daily_parser.add_argument('--cci-period', type=int, default=20, help='CCI 계산 기간')

    # Altcoin Screener Subparser
    altcoin_parser = screener_subparsers.add_parser('altcoin', help='신규 상장 후 하락한 알트코인 탐색')
    altcoin_parser.add_argument('--min-daily-volume-usd', type=float, default=500_000_000, help='최소 일일 거래량 (USD)')
    altcoin_parser.add_argument('--max-listing-days', type=int, default=1648, help='최대 상장일 (일)')
    altcoin_parser.add_argument('--min-downtrend-from-ath', type=float, default=0.70, help='ATH 대비 최소 하락률 (0.0 ~ 1.0)')
    altcoin_parser.add_argument('--min-volatility', type=float, default=40.0, help='최소 30일 변동성 (%)')
    altcoin_parser.add_argument('--max-volatility', type=float, default=70.0, help='최대 30일 변동성 (%)')
    altcoin_parser.add_argument('--min-cci', type=float, default=-50.0, help='최소 CCI 값')
    altcoin_parser.add_argument('--max-cci', type=float, default=50.0, help='최대 CCI 값')
    altcoin_parser.add_argument('--cci-period', type=int, default=20, help='CCI 계산 기간')

    args = parser.parse_args()

    if args.command == 'web':
        print(f"웹 서버를 시작합니다. http://{args.host}:{args.port} 에서 접속하세요.")
        uvicorn.run("webapp:app", host=args.host, port=args.port, reload=True)
    
    elif args.command == 'run':
        if args.screener_name == 'daily':
            daily_screener.daily_screener(
                min_daily_volume_krw=args.min_daily_volume_krw,
                min_downtrend_from_ath=args.min_downtrend_from_ath,
                min_volatility_30d=args.min_volatility_30d,
                max_volatility_30d=args.max_volatility_30d,
                min_cci=args.min_cci,
                max_cci=args.max_cci,
                cci_period=args.cci_period
            )
        elif args.screener_name == 'altcoin':
            altcoin_screener.altcoin_screener(
                min_daily_volume_usd=args.min_daily_volume_usd,
                max_listing_days=args.max_listing_days,
                min_downtrend_from_ath=args.min_downtrend_from_ath,
                min_volatility=args.min_volatility,
                max_volatility=args.max_volatility,
                min_cci=args.min_cci,
                max_cci=args.max_cci,
                cci_period=args.cci_period
            )

if __name__ == '__main__':
    main()