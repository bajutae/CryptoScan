from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional

import os
import re
import json
import sys
import subprocess

app = FastAPI()

# 정적 파일 및 템플릿 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/charts", StaticFiles(directory=os.path.join(BASE_DIR, "charts")), name="charts")

# 메인 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def parse_screener_output(output: str):
    table_data = {
        "headers": [],
        "rows": []
    }
    
    # 정규 표현식을 사용하여 테이블 헤더와 구분선을 찾습니다.
    header_match = re.search(r"(Symbol|종목명) *\|.*\n-", output, re.MULTILINE)
    
    if not header_match:
        return table_data

    table_start_index = header_match.end()
    table_lines = output[table_start_index:].split('\n')

    # 헤더 파싱
    header_line = header_match.group(0).split('\n')[0]
    headers = [h.strip() for h in header_line.split('|')]
    table_data["headers"] = headers

    # 데이터 행 파싱
    for line in table_lines:
        if '---' in line or not line.strip():
            break # 테이블 끝
        
        row_values = [v.strip() for v in line.split('|')]
        if len(row_values) == len(headers):
            table_data["rows"].append(row_values)
            
    return table_data

# 스크리너 실행 API 엔드포인트
@app.get("/run-screener/{screener_name}")
async def run_screener(
    screener_name: str,
    min_daily_volume_krw: Optional[float] = None,
    min_downtrend_from_ath: Optional[float] = None,
    min_volatility_30d: Optional[float] = None,
    max_volatility_30d: Optional[float] = None,
    min_cci: Optional[float] = None,
    max_cci: Optional[float] = None,
    cci_period: Optional[int] = None,
    min_daily_volume_usd: Optional[float] = None,
    max_listing_days: Optional[int] = None,
    min_volatility: Optional[float] = None,
    max_volatility: Optional[float] = None,
):
    """
    웹 요청을 받아 해당 스크리너를 별도의 프로세스에서 실행하고 결과를 반환합니다.
    """
    command = [
        sys.executable,
        "main.py",
        "run",
        screener_name
    ]

    # 파라미터 추가
    if screener_name == 'daily':
        if min_daily_volume_krw is not None: command.extend(["--min-daily-volume-krw", str(min_daily_volume_krw)])
        if min_downtrend_from_ath is not None: command.extend(["--min-downtrend-from-ath", str(min_downtrend_from_ath)])
        if min_volatility_30d is not None: command.extend(["--min-volatility-30d", str(min_volatility_30d)])
        if max_volatility_30d is not None: command.extend(["--max-volatility-30d", str(max_volatility_30d)])
        if min_cci is not None: command.extend(["--min-cci", str(min_cci)])
        if max_cci is not None: command.extend(["--max-cci", str(max_cci)])
        if cci_period is not None: command.extend(["--cci-period", str(cci_period)])
    elif screener_name == 'altcoin':
        if min_daily_volume_usd is not None: command.extend(["--min-daily-volume-usd", str(min_daily_volume_usd)])
        if max_listing_days is not None: command.extend(["--max-listing-days", str(max_listing_days)])
        if min_downtrend_from_ath is not None: command.extend(["--min-downtrend-from-ath", str(min_downtrend_from_ath)])
        if min_volatility is not None: command.extend(["--min-volatility", str(min_volatility)])
        if max_volatility is not None: command.extend(["--max-volatility", str(max_volatility)])
        if min_cci is not None: command.extend(["--min-cci", str(min_cci)])
        if max_cci is not None: command.extend(["--max-cci", str(max_cci)])
        if cci_period is not None: command.extend(["--cci-period", str(cci_period)])

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd(),
            encoding='utf-8'
        )
        output = process.stdout
        error_output = process.stderr
        
        # 스크리너 스크립트에서 오류가 발생했는지 확인
        if process.returncode != 0:
            full_error_message = f"스크리너 실행 중 오류 발생 (Exit Code: {process.returncode}):\n{output}\n{error_output}"
            return {"output": full_error_message, "charts": [], "table": {"headers": [], "rows": []}}

        chart_paths = re.findall(r"Chart saved to (charts/.*?.png)", output)
        table_data = parse_screener_output(output)
        
        return {"output": output, "charts": chart_paths, "table": table_data}
    except subprocess.CalledProcessError as e:
        # 이 블록은 check=True 때문에 거의 실행되지 않음
        error_message = f"오류 발생 (Exit Code: {e.returncode}):\n"
        error_message += e.stdout
        error_message += e.stderr
        return {"output": error_message, "charts": [], "table": {"headers": [], "rows": []}}
    except Exception as e:
        return {"output": f"알 수 없는 오류 발생: {e}", "charts": [], "table": {"headers": [], "rows": []}}

