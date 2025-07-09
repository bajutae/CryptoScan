from celery import Celery
from celery.signals import worker_process_init
from sqlalchemy.orm import Session
from utils.database import SessionLocal, init_db

# Celery 애플리케이션 설정
celery_app = Celery(
    "screener_tasks",
    broker="redis://localhost:6379/0",  # Redis 브로커 URL
    backend="redis://localhost:6379/1"   # Redis 백엔드 URL (결과 저장)
)

# Celery 태스크가 실행될 때마다 DB 세션을 초기화
def configure_worker_for_sqlalchemy(*args, **kwargs):
    init_db() # DB 테이블이 없으면 생성

worker_process_init.connect(configure_worker_for_sqlalchemy)

# 스크리너 함수들을 Celery 태스크로 임포트 (나중에 추가)
# from screener.daily_screener import daily_screener
# from screener.altcoin_screener import altcoin_screener