"""
StopBuy Backend - 분석 서비스
분석 이력 DB 저장 및 상품 정보 추출 처리
"""
import base64
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.models import AnalysisHistory
from app.schemas.schemas import AnalysisRequest, AnalysisResult, ProductInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """고유 세션 ID 생성"""
    return str(uuid.uuid4()).replace("-", "")[:16]


async def save_analysis_start(
    db: AsyncSession,
    session_id: str,
    request: AnalysisRequest,
) -> AnalysisHistory:
    """분석 시작 시 DB에 레코드 생성"""
    record = AnalysisHistory(
        session_id=session_id,
        input_type=request.input_type,
        product_url=request.product_url,
        user_budget=request.user.budget if request.user else None,
        user_preferred_brands=request.user.preferred_brands if request.user else None,
        user_important_factors=request.user.important_factors if request.user else None,
        status="analyzing",
        created_at=datetime.utcnow(),
    )

    if request.product:
        record.product_name = request.product.name
        record.product_brand = request.product.brand
        record.product_category = request.product.category
        record.product_price = request.product.price
        record.product_rating = request.product.rating
        record.product_review_count = request.product.review_count
        record.product_return_rate = request.product.return_rate

    db.add(record)
    await db.flush()
    return record


async def update_analysis_result(
    db: AsyncSession,
    session_id: str,
    result: Dict[str, Any],
    status: str = "completed",
):
    """분석 완료 시 DB 업데이트"""
    stmt = select(AnalysisHistory).where(AnalysisHistory.session_id == session_id)
    row = (await db.execute(stmt)).scalar_one_or_none()

    if not row:
        logger.warning(f"session_id={session_id} 레코드를 찾을 수 없습니다.")
        return

    row.status = status
    row.regret_score = result.get("regret_score")
    row.regret_level = result.get("regret_level")
    row.regret_causes = result.get("regret_causes")
    row.regret_reasons = result.get("regret_reasons")
    row.alternatives = result.get("alternatives")
    row.llm_analysis = result.get("llm_analysis")
    row.product_name = result.get("product_name") or row.product_name
    row.updated_at = datetime.utcnow()

    if status == "error":
        row.error_message = result.get("message", "알 수 없는 오류")

    await db.flush()


async def get_analysis_history(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
):
    """분석 이력 조회"""
    stmt = (
        select(AnalysisHistory)
        .order_by(desc(AnalysisHistory.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_analysis_by_session(
    db: AsyncSession,
    session_id: str,
) -> Optional[AnalysisHistory]:
    """세션 ID로 분석 결과 조회"""
    stmt = select(AnalysisHistory).where(AnalysisHistory.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def save_uploaded_image(image_base64: str, session_id: str) -> str:
    """Base64 이미지를 파일로 저장하고 경로 반환"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Base64 헤더 제거
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    image_data = base64.b64decode(image_base64)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{session_id}.jpg")

    with open(file_path, "wb") as f:
        f.write(image_data)

    return file_path


def extract_product_from_url(url: str) -> Dict[str, Any]:
    """URL에서 기본 상품 정보 추출 (실제 크롤링은 Agent에서 수행)"""
    info = {"source_url": url}

    # 쇼핑몰 도메인 감지
    domain_map = {
        "coupang.com": "쿠팡",
        "gmarket.co.kr": "G마켓",
        "auction.co.kr": "옥션",
        "11st.co.kr": "11번가",
        "amazon.com": "Amazon",
        "amazon.co.kr": "Amazon Korea",
        "naver.com": "네이버 쇼핑",
        "kakao.com": "카카오쇼핑",
        "ssg.com": "SSG",
        "lotte.com": "롯데온",
    }

    for domain, name in domain_map.items():
        if domain in url:
            info["platform"] = name
            break
    else:
        info["platform"] = "기타"

    return info
