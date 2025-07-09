import logging
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

import os
import re
import json
import logging
from datetime import datetime # datetime 임포트

from screener.daily_screener import daily_screener
from screener.altcoin_screener import altcoin_screener
from utils.database import init_db, ScreenerResult, get_db

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, # 기본 로깅 레벨
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"), # app.log 파일에 로그 저장
        logging.StreamHandler() # 콘솔에도 로그 출력
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 데이터베이스 초기화
@app.on_event("startup")
def on_startup():
    init_db()

# Pydantic 모델 정의
class DailyScreenerParams(BaseModel):
    min_daily_volume_krw: Optional[float] = 500_000_000
    min_downtrend_from_ath: Optional[float] = 0.70
    min_volatility_30d: Optional[float] = 45.0
    max_volatility_30d: Optional[float] = 75.0
    min_cci: Optional[float] = -40.0
    max_cci: Optional[float] = 40.0
    cci_period: Optional[int] = 20

class AltcoinScreenerParams(BaseModel):
    min_daily_volume_usd: Optional[float] = 500_000_000
    max_listing_days: Optional[int] = 1648
    min_downtrend_from_ath: Optional[float] = 0.70
    min_volatility: Optional[float] = 40.0
    max_volatility: Optional[float] = 70.0
    min_cci: Optional[float] = -50.0
    max_cci: Optional[float] = 50.0
    cci_period: Optional[int] = 20

class ScreenerResultResponse(BaseModel):
    id: int
    screener_name: str
    timestamp: datetime
    output_text: str
    chart_paths: List[str]
    table_headers: List[str]
    table_rows: List[List[str]]

    class Config:
        orm_mode = True

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
@app.post("/run-screener/{screener_name}")
async def run_screener(
    screener_name: str,
    daily_params: Optional[DailyScreenerParams] = None,
    altcoin_params: Optional[AltcoinScreenerParams] = None,
    db: Session = Depends(get_db)
):
    """
    웹 요청을 받아 해당 스크리너를 별도의 프로세스에서 실행하고 결과를 반환합니다.
    """
    result = {"output": "", "charts": [], "table": {"headers": [], "rows": []}}

    try:
        if screener_name == 'daily':
            logger.info(f"데일리 스크리너 실행 요청: {daily_params.dict() if daily_params else '기본값'}")
            if not daily_params: # 기본값 사용
                daily_params = DailyScreenerParams()
            screener_result = daily_screener(db, **daily_params.dict())
        elif screener_name == 'altcoin':
            logger.info(f"알트코인 스크리너 실행 요청: {altcoin_params.dict() if altcoin_params else '기본값'}")
            if not altcoin_params: # 기본값 사용
                altcoin_params = AltcoinScreenerParams()
            screener_result = altcoin_screener(db, **altcoin_params.dict())
        else:
            logger.warning(f"알 수 없는 스크리너 이름 요청: {screener_name}")
            return {"output": f"알 수 없는 스크리너 이름: {screener_name}", "charts": [], "table": {"headers": [], "rows": []}}

        result["output"] = screener_result["output"]
        result["charts"] = screener_result["charts"]
        result["table"] = screener_result["table_data"]
        logger.info(f"스크리너 {screener_name} 실행 완료.")

    except Exception as e:
        logger.exception(f"스크리너 {screener_name} 실행 중 알 수 없는 오류 발생")
        result["output"] = f"스크리너 실행 중 알 수 없는 오류 발생: {e}"

    return result

# 과거 스크리너 결과 조회 API 엔드포인트
@app.get("/results", response_model=List[ScreenerResultResponse])
async def get_screener_results(db: Session = Depends(get_db)):
    results = db.query(ScreenerResult).order_by(ScreenerResult.timestamp.desc()).all()
    # JSON 문자열로 저장된 필드를 파싱하여 반환
    parsed_results = []
    for res in results:
        parsed_res = {
            "id": res.id,
            "screener_name": res.screener_name,
            "timestamp": res.timestamp,
            "output_text": res.output_text,
            "chart_paths": json.loads(res.chart_paths) if res.chart_paths else [],
            "table_headers": json.loads(res.table_headers) if res.table_headers else [],
            "table_rows": json.loads(res.table_rows) if res.table_rows else []
        }
        parsed_results.append(parsed_res)
    return parsed_results

