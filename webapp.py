import subprocess
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import re

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
    header_match = re.search(r"(Symbol|종목명) *\|.*\n-+", output, re.MULTILINE)
    
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
async def run_screener(screener_name: str, mode: str = 'screener'):
    """
    웹 요청을 받아 해당 스크리너를 별도의 프로세스에서 실행하고 결과를 반환합니다.
    """
    command = [
        sys.executable,
        "main.py",
        "run",
        screener_name
    ]

    if screener_name == 'daytrade':
        command.extend(["--mode", mode])

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
        
        chart_paths = re.findall(r"Chart saved to (charts/.*?.png)", output)
        table_data = parse_screener_output(output)
        
        return {"output": output, "charts": chart_paths, "table": table_data}
    except subprocess.CalledProcessError as e:
        error_message = f"오류 발생 (Exit Code: {e.returncode}):\n"
        error_message += e.stdout
        error_message += e.stderr
        return {"output": error_message, "charts": [], "table": {"headers": [], "rows": []}}
    except Exception as e:
        return {"output": f"알 수 없는 오류 발생: {e}", "charts": [], "table": {"headers": [], "rows": []}}
