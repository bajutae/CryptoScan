from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

# SQLite 데이터베이스 파일 경로
DATABASE_URL = "sqlite:///./screener_results.db"

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Base 클래스 생성 (모델 정의에 사용)
Base = declarative_base()

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 데이터베이스 모델 정의
class ScreenerResult(Base):
    __tablename__ = "screener_results"

    id = Column(Integer, primary_key=True, index=True)
    screener_name = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    output_text = Column(Text)
    chart_paths = Column(Text) # JSON string of list of paths
    table_headers = Column(Text) # JSON string of list of headers
    table_rows = Column(Text) # JSON string of list of lists of rows

    def __repr__(self):
        return f"<ScreenerResult(id={self.id}, screener_name='{self.screener_name}', timestamp='{self.timestamp}')>"

# 데이터베이스 테이블 생성
def init_db():
    Base.metadata.create_all(bind=engine)

# 의존성 주입을 위한 함수 (FastAPI에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()