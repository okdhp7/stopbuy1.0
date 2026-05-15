"""
StopBuy Backend - SQLAlchemy ORM 모델 정의
분석 이력 및 상품 정보 테이블
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    JSON, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class AnalysisHistory(Base):
    """구매 후회 예측 분석 이력 테이블"""
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)

    # 입력 정보
    input_type = Column(String(10), nullable=False)  # "image" | "url"
    product_url = Column(Text, nullable=True)
    image_path = Column(Text, nullable=True)

    # 상품 정보 (크롤링/분석 결과)
    product_name = Column(String(255), nullable=True)
    product_brand = Column(String(100), nullable=True)
    product_category = Column(String(100), nullable=True)
    product_price = Column(Float, nullable=True)
    product_rating = Column(Float, nullable=True)
    product_review_count = Column(Integer, nullable=True)
    product_return_rate = Column(Float, nullable=True)

    # 사용자 정보
    user_budget = Column(Float, nullable=True)
    user_preferred_brands = Column(JSON, nullable=True)
    user_important_factors = Column(JSON, nullable=True)

    # 예측 결과
    regret_score = Column(Float, nullable=True)
    regret_level = Column(String(10), nullable=True)  # "low" | "medium" | "high"
    regret_causes = Column(JSON, nullable=True)
    regret_reasons = Column(JSON, nullable=True)
    llm_analysis = Column(JSON, nullable=True)
    alternatives = Column(JSON, nullable=True)

    # 상태
    status = Column(String(20), default="pending")  # pending | analyzing | completed | error
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    """상품 정보 테이블 (대체상품 후보 DB)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    return_rate = Column(Float, nullable=True)
    days_since_release = Column(Integer, nullable=True)
    specs = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
