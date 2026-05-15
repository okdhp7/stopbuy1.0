"""
StopBuy Backend - FastAPI 메인 애플리케이션
구매 후회 예측 및 대체상품 추천 서비스 백엔드

수정 이력:
- 서버 시작 시 Agent 사전 연결 시도 추가 (첫 요청 지연 제거)
- DB 초기화 재시도 로직 유지 (최대 10회, 3초 간격)
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import create_tables
from app.api.websocket import router as ws_router
from app.api.routes import router as api_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    logger.info("StopBuy 백엔드 서버 시작 중...")

    # 업로드 디렉토리 생성
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # DB 테이블 생성 시도 (최대 10회 재시도 - DB 준비 대기)
    for attempt in range(10):
        try:
            await create_tables()
            logger.info("데이터베이스 테이블 초기화 완료")
            break
        except Exception as e:
            if attempt < 9:
                logger.warning(f"DB 초기화 대기 중 ({attempt+1}/10): {e}")
                await asyncio.sleep(3)
            else:
                logger.warning(f"DB 초기화 실패 (DB 없이 실행): {e}")

    # Agent 사전 연결 시도 (백그라운드, 실패해도 서버 시작)
    from app.services.agent_service import agent_manager

    async def _try_connect_agent():
        await asyncio.sleep(2)  # Agent 컨테이너 준비 대기
        connected = await agent_manager.connect()
        if connected:
            logger.info("AI Agent 사전 연결 성공")
        else:
            logger.warning("AI Agent 사전 연결 실패 — 요청 시 재시도합니다")

    asyncio.create_task(_try_connect_agent())

    logger.info(f"서버 준비 완료 - Agent URL: {settings.AGENT_WS_URL}")
    yield

    logger.info("StopBuy 백엔드 서버 종료 중...")
    await agent_manager.disconnect()


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="구매 후회 예측 및 대체상품 추천 API",
    lifespan=lifespan,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(ws_router, tags=["WebSocket"])
app.include_router(api_router, prefix="/api", tags=["API"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "websocket": "/ws/{session_id}",
    }


@app.get("/health")
async def health_check():
    """Docker 헬스체크 및 상태 확인 엔드포인트"""
    from app.services.agent_service import agent_manager
    return {
        "status": "ok",
        "agent_connected": agent_manager.is_connected(),
        "version": settings.APP_VERSION,
    }
