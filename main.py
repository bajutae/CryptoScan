
import argparse
import sys
import uvicorn
from screener import daily_screener, altcoin_screener, binance_futures_screener, day_trading_screener

# --- CLI 스크리너 설정 ---
SCREENER_MAP = {
    'daily': daily_screener.daily_screener,
    'altcoin': altcoin_screener.altcoin_screener,
    'futures': binance_futures_screener.futures_screener,
    'daytrade': lambda mode: day_trading_screener.day_trading_screener(mode=mode),
}

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
    parser_run.add_argument(
        'screener',
        choices=SCREENER_MAP.keys(),
        help=(
            '실행할 스크리너를 선택합니다.\n'
            '  - daily: 일봉 기준 관심 코인 분석\n'
            '  - altcoin: 특정 패턴의 알트코인 탐색\n'
            '  - futures: 바이낸스 선물 시장 데이터 분석\n'
            '  - daytrade: 특정 코인 단타 전략 분석 및 백테스트'
        )
    )
    parser_run.add_argument(
        '--mode',
        choices=['screener', 'backtest'],
        default='screener',
        help='daytrade 스크리너의 실행 모드를 선택합니다. (기본값: screener)'
    )

    args = parser.parse_args()

    if args.command == 'web':
        print(f"웹 서버를 시작합니다. http://{args.host}:{args.port} 에서 접속하세요.")
        uvicorn.run("webapp:app", host=args.host, port=args.port, reload=True)
    
    elif args.command == 'run':
        screener_to_run = SCREENER_MAP.get(args.screener)
        if screener_to_run:
            if args.screener == 'daytrade':
                screener_to_run(args.mode)
            else:
                screener_to_run()
        else:
            print(f"오류: '{args.screener}'는 유효한 스크리너가 아닙니다.", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()

