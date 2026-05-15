"""
StopBuy Backend - Core Configuration
FastAPI 애플리케이션 전역 설정 관리

연결 경로:
  [로컬 개발]
    Frontend(3000) → Vite proxy /ws → Backend(8000) → Agent(8765 on localhost)
    AGENT_WS_URL = ws://localhost:8765

  [Docker Compose]
    Frontend(80/Nginx) → /ws → Backend(8000) → Agent(8765 on 'agent' 컨테이너)
    AGENT_WS_URL = ws://agent:8765  ← docker-compose.yml 환경변수로 주입
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 앱 기본 설정
    APP_NAME: str = "StopBuy API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql+asyncpg://stopbuy:stopbuy123@localhost:5432/stopbuy_db"
    DATABASE_SYNC_URL: str = "postgresql://stopbuy:stopbuy123@localhost:5432/stopbuy_db"

    # AI Agent WebSocket 설정
    # - 로컬 개발: ws://localhost:8765
    # - Docker Compose: ws://agent:8765  (docker-compose.yml의 AGENT_WS_URL 환경변수로 자동 주입)
    AGENT_WS_HOST: str = "localhost"
    AGENT_WS_PORT: int = 8765
    AGENT_WS_URL: str = "ws://localhost:8765"

    # CORS 설정
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 파일 업로드 설정
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "/tmp/stopbuy_uploads"

    # 후회 임계값 (이 값 이상이면 대체상품 추천)
    REGRET_THRESHOLD: float = 0.4

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
