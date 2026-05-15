"""
StopBuy Backend - REST API 라우터
분석 이력 조회, 상태 확인 등 REST 엔드포인트
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.analysis_service import (
    get_analysis_history,
    get_analysis_by_session,
)
from app.services.agent_service import agent_manager
from app.schemas.schemas import HistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "ok",
        "agent_connected": agent_manager.is_connected(),
    }


@router.get("/agent/status")
async def agent_status():
    """AI Agent 연결 상태 확인"""
    connected = agent_manager.is_connected()
    return {
        "connected": connected,
        "message": "AI Agent가 연결되어 있습니다." if connected else "AI Agent가 연결되어 있지 않습니다.",
    }


@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """분석 이력 목록 조회"""
    records = await get_analysis_history(db, limit=limit, offset=offset)
    return records


@router.get("/history/{session_id}")
async def get_history_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 세션의 분석 결과 조회"""
    record = await get_analysis_by_session(db, session_id)
    if not record:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    return {
        "id": record.id,
        "session_id": record.session_id,
        "input_type": record.input_type,
        "product_url": record.product_url,
        "product_name": record.product_name,
        "product_brand": record.product_brand,
        "product_category": record.product_category,
        "product_price": record.product_price,
        "product_rating": record.product_rating,
        "regret_score": record.regret_score,
        "regret_level": record.regret_level,
        "regret_causes": record.regret_causes,
        "regret_reasons": record.regret_reasons,
        "alternatives": record.alternatives,
        "llm_analysis": record.llm_analysis,
        "status": record.status,
        "error_message": record.error_message,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
