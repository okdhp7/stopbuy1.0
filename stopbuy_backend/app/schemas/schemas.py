"""
StopBuy Backend - Pydantic 스키마 정의
API 요청/응답 데이터 검증 모델
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


# ─── 사용자 정보 ───────────────────────────────────────────────────────────────
class UserProfile(BaseModel):
    budget: Optional[float] = Field(None, description="예산 (원)", ge=0)
    preferred_brands: Optional[List[str]] = Field(default_factory=list, description="선호 브랜드 목록")
    important_factors: Optional[List[str]] = Field(default_factory=list, description="중요 고려 요소")
    usage_purpose: Optional[str] = Field(None, description="사용 목적")
    experience_level: Optional[str] = Field("beginner", description="경험 수준")


# ─── 상품 정보 ───────────────────────────────────────────────────────────────
class ProductInfo(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    return_rate: Optional[float] = None
    days_since_release: Optional[int] = None
    specs: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


# ─── 분석 요청 ───────────────────────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    input_type: str = Field(..., description="입력 유형: image | url")
    product_url: Optional[str] = Field(None, description="상품 URL")
    image_base64: Optional[str] = Field(None, description="이미지 Base64 데이터")
    user: Optional[UserProfile] = Field(default_factory=UserProfile, description="사용자 프로필")
    product: Optional[ProductInfo] = Field(None, description="수동 입력 상품 정보")


# ─── 후회 원인 ───────────────────────────────────────────────────────────────
class RegretCause(BaseModel):
    code: str
    title: str
    message: str
    severity: str  # low | medium | high
    impact_score: float


# ─── 대체상품 ────────────────────────────────────────────────────────────────
class AlternativeProduct(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    return_rate: Optional[float] = None
    regret_score: Optional[float] = None
    match_score: Optional[float] = None
    improvement_score: Optional[float] = None
    final_score: Optional[float] = None
    recommendation_reason: Optional[str] = None
    image_url: Optional[str] = None


# ─── LLM 분석 결과 ───────────────────────────────────────────────────────────
class LLMAnalysis(BaseModel):
    used_llm: bool = False
    summary: Optional[str] = None
    risk_explanation: Optional[str] = None
    purchase_advice: Optional[str] = None
    alternative_strategy: Optional[str] = None


# ─── 분석 결과 ───────────────────────────────────────────────────────────────
class AnalysisResult(BaseModel):
    session_id: str
    status: str  # pending | analyzing | completed | error

    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_info: Optional[ProductInfo] = None

    regret_score: Optional[float] = None
    regret_level: Optional[str] = None  # low | medium | high
    model_regret_score: Optional[float] = None
    cause_score: Optional[float] = None

    regret_causes: Optional[List[RegretCause]] = None
    regret_reasons: Optional[List[str]] = None

    alternatives: Optional[List[AlternativeProduct]] = None
    llm_analysis: Optional[LLMAnalysis] = None

    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


# ─── WebSocket 메시지 ────────────────────────────────────────────────────────
class WSMessage(BaseModel):
    type: str  # request | result | error | progress | ping | pong
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    progress: Optional[int] = None  # 0-100


# ─── 이력 조회 응답 ──────────────────────────────────────────────────────────
class HistoryResponse(BaseModel):
    id: int
    session_id: str
    input_type: str
    product_name: Optional[str]
    regret_score: Optional[float]
    regret_level: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
