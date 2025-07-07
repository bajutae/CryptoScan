import subprocess
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# 정적 파일 및 템플릿 설정
# 현재 파일의 위치를 기준으로 절대 경로를 만듭니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 메인 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 스크리너 실행 API 엔드포인트
@app.get("/run-screener/{screener_name}")
async def run_screener(screener_name: str, mode: str = 'screener'):
    """
    웹 요청을 받아 해당 스크리너를 별도의 프로세스에서 실행하고 결과를 반환합니다.
    """
    command = [
        sys.executable, # 현재 파이썬 인터프리터
        "main.py",
        "run",         # 'run' 커맨드 추가
        screener_name
    ]

    if screener_name == 'daytrade':
        command.extend(["--mode", mode])

    try:
        # subprocess를 사용하여 main.py를 실행하고 출력을 캡처합니다.
        # os.getcwd()를 사용하여 현재 작업 디렉토리에서 실행하도록 합니다.
        process = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True, 
            cwd=os.getcwd(),
            encoding='utf-8'
        )
        output = process.stdout
        if process.stderr:
            output += "\n--- Stderr ---\n" + process.stderr
        return {"output": output}
    except subprocess.CalledProcessError as e:
        error_message = f"오류 발생 (Exit Code: {e.returncode}):\n"
        error_message += e.stdout
        error_message += e.stderr
        return {"output": error_message}
    except Exception as e:
        return {"output": f"알 수 없는 오류 발생: {e}"}
