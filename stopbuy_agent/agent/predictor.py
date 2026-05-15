"""
StopBuy AI Agent - 후회 예측 모듈
기존 train_regret_model.py의 RegretPredictor 클래스 기반
LightGBM 모델 + 규칙 기반 원인 분석 + LLM 분석
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "regret_model.pkl")
PRODUCT_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "datas", "product_list.xlsx")

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FEATURES = [
    "budget",
    "price",
    "brand_match",
    "rating",
    "review_count",
    "return_rate",
    "important_factor_match_count",
    "days_since_release",
]


# ─── 유틸리티 함수 ────────────────────────────────────────────────────────────

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return int(value)
    except Exception:
        return default


def clamp_score(value: Any) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return 0.0
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def normalize_specs(specs: Any) -> Dict[str, Any]:
    if isinstance(specs, dict):
        return specs
    if isinstance(specs, str):
        try:
            parsed = json.loads(specs)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def regret_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


# ─── 특징 벡터 생성 ───────────────────────────────────────────────────────────

def build_feature_row(user: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
    budget = safe_float(user.get("budget"))
    price = safe_float(product.get("price"))

    preferred_brands = user.get("preferred_brands", []) or []
    important_factors = user.get("important_factors", []) or []

    product_brand = product.get("brand")
    product_specs = normalize_specs(product.get("specs", {}))
    product_description = str(product.get("description", "") or "")

    important_factor_match_count = sum(
        1
        for factor in important_factors
        if factor in product_specs or factor in product_description
    )

    return {
        "budget": budget,
        "price": price,
        "brand_match": 1 if product_brand in preferred_brands else 0,
        "rating": safe_float(product.get("rating")),
        "review_count": safe_int(product.get("review_count")),
        "return_rate": safe_float(product.get("return_rate")),
        "important_factor_match_count": important_factor_match_count,
        "days_since_release": safe_int(product.get("days_since_release")),
    }


# ─── 후회 원인 분석 ───────────────────────────────────────────────────────────

def make_regret_causes(
    feature: Dict[str, Any],
    user: Dict[str, Any],
    product: Dict[str, Any],
) -> List[Dict[str, Any]]:
    causes = []

    budget = safe_float(feature.get("budget"))
    price = safe_float(feature.get("price"))
    rating = safe_float(feature.get("rating"))
    return_rate = safe_float(feature.get("return_rate"))
    review_count = safe_int(feature.get("review_count"))
    brand_match = safe_int(feature.get("brand_match"))
    factor_match_count = safe_int(feature.get("important_factor_match_count"))
    days_since_release = safe_int(feature.get("days_since_release"))

    if budget > 0 and price > budget:
        over_ratio = (price - budget) / budget
        causes.append({
            "code": "PRICE_OVER_BUDGET",
            "title": "예산 초과",
            "message": (
                f"상품 가격이 예산보다 약 {over_ratio * 100:.1f}% 높아 "
                "구매 후 가격 부담으로 후회할 가능성이 있습니다."
            ),
            "severity": "high" if over_ratio >= 0.3 else "medium",
            "impact_score": round(min(over_ratio, 1.0), 4),
        })

    if rating > 0 and rating < 3.8:
        causes.append({
            "code": "LOW_RATING",
            "title": "낮은 리뷰 평점",
            "message": "리뷰 평점이 낮아 실제 사용 만족도가 떨어질 가능성이 있습니다.",
            "severity": "high" if rating < 3.5 else "medium",
            "impact_score": round((3.8 - rating) / 3.8, 4),
        })

    if return_rate >= 10:
        causes.append({
            "code": "HIGH_RETURN_RATE",
            "title": "높은 반품률",
            "message": "반품률이 높아 실제 구매자들의 불만 가능성이 상대적으로 큽니다.",
            "severity": "high" if return_rate >= 15 else "medium",
            "impact_score": round(min(return_rate / 30, 1.0), 4),
        })

    if review_count < 20:
        causes.append({
            "code": "LOW_REVIEW_COUNT",
            "title": "검증 부족",
            "message": "리뷰 수가 적어 상품 품질이나 만족도가 충분히 검증되지 않았습니다.",
            "severity": "medium",
            "impact_score": 0.35,
        })

    if brand_match == 0 and user.get("preferred_brands"):
        causes.append({
            "code": "BRAND_MISMATCH",
            "title": "선호 브랜드 불일치",
            "message": "사용자가 선호하는 브랜드와 일치하지 않아 만족도가 낮을 수 있습니다.",
            "severity": "low",
            "impact_score": 0.25,
        })

    if factor_match_count == 0 and user.get("important_factors"):
        causes.append({
            "code": "IMPORTANT_FACTOR_MISMATCH",
            "title": "중요 조건 미충족",
            "message": "사용자가 중요하게 생각하는 조건과 상품 특성이 충분히 맞지 않습니다.",
            "severity": "high",
            "impact_score": 0.7,
        })

    if days_since_release > 900:
        causes.append({
            "code": "OLD_PRODUCT",
            "title": "출시 후 장기간 경과",
            "message": "출시된 지 오래되어 최신 대체 상품 대비 경쟁력이 낮을 수 있습니다.",
            "severity": "medium",
            "impact_score": 0.4,
        })

    if not causes:
        causes.append({
            "code": "NO_MAJOR_RISK",
            "title": "주요 후회 원인 없음",
            "message": "현재 입력 기준으로는 뚜렷한 후회 위험 요인이 크지 않습니다.",
            "severity": "low",
            "impact_score": 0.0,
        })

    causes.sort(key=lambda x: x["impact_score"], reverse=True)
    return causes[:5]


def calculate_cause_score(causes: List[Dict[str, Any]]) -> float:
    valid_causes = [c for c in causes if c.get("code") != "NO_MAJOR_RISK"]
    if not valid_causes:
        return 0.0
    impact_scores = [clamp_score(c.get("impact_score", 0.0)) for c in valid_causes]
    max_score = max(impact_scores)
    avg_score = sum(impact_scores) / len(impact_scores)
    return clamp_score(max_score * 0.7 + avg_score * 0.3)


def blend_regret_score(model_score: float, cause_score: float, model_weight: float = 0.75) -> float:
    return clamp_score(
        clamp_score(model_score) * model_weight
        + clamp_score(cause_score) * (1.0 - model_weight)
    )


# ─── LLM 분석 ────────────────────────────────────────────────────────────────

def call_openai_llm(prompt: str) -> Optional[Dict[str, Any]]:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "당신은 구매 후회 예측 결과를 해석하는 AI 분석가입니다. 항상 JSON만 반환하세요."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return None
        parsed = json.loads(content)
        parsed["used_llm"] = True
        return parsed
    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        return None


def generate_llm_analysis(
    user: Dict[str, Any],
    product: Dict[str, Any],
    score_result: Dict[str, Any],
    alternatives: List[Dict[str, Any]],
    use_llm: bool,
) -> Dict[str, Any]:
    regret_score = score_result["regret_score"]
    regret_causes = score_result["regret_causes"]
    level = regret_level(regret_score)

    main_causes = [c.get("title", "") for c in regret_causes if c.get("code") != "NO_MAJOR_RISK"]

    if main_causes:
        summary = f"후회 위험도는 {level} 수준이며, 주요 원인은 {', '.join(main_causes[:3])}입니다."
    else:
        summary = "현재 조건에서는 뚜렷한 후회 위험 요인이 크지 않습니다."

    alt_strategy = (
        f"대체상품은 {alternatives[0].get('name')}을 우선 검토할 수 있습니다."
        if alternatives else "현재 조건에서 적절한 대체상품 후보가 충분하지 않습니다."
    )

    fallback = {
        "used_llm": False,
        "summary": summary,
        "risk_explanation": "규칙 기반 후회 원인과 회귀모델 예측 결과를 기준으로 분석했습니다.",
        "purchase_advice": "예산, 평점, 반품률, 선호 브랜드, 중요 조건 충족 여부를 함께 비교한 뒤 구매를 결정하는 것이 좋습니다.",
        "alternative_strategy": alt_strategy,
    }

    if not use_llm:
        return fallback

    prompt_data = {
        "user": user,
        "target_product": product,
        "score_result": {
            "regret_score": round(regret_score, 4),
            "regret_level": level,
            "regret_causes": regret_causes,
        },
        "alternatives": alternatives[:3],
    }
    prompt = f"""
당신은 구매 후회 예측과 대체상품 추천을 지원하는 AI 쇼핑 컨설턴트입니다.
아래 JSON 데이터를 근거로 사용자에게 제공할 분석 결과를 작성하세요.
요구사항:
1. 반드시 JSON 형식으로만 답변하세요.
2. 없는 사실을 만들어내지 마세요.
3. 한국어로 작성하세요.
4. 결과 JSON 구조: {{"summary": "...", "risk_explanation": "...", "purchase_advice": "...", "alternative_strategy": "..."}}

분석 데이터:
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}
""".strip()

    llm_result = call_openai_llm(prompt)
    if not llm_result:
        return fallback

    return {
        "used_llm": True,
        "summary": llm_result.get("summary", fallback["summary"]),
        "risk_explanation": llm_result.get("risk_explanation", fallback["risk_explanation"]),
        "purchase_advice": llm_result.get("purchase_advice", fallback["purchase_advice"]),
        "alternative_strategy": llm_result.get("alternative_strategy", fallback["alternative_strategy"]),
    }


# ─── 더미 모델 생성 (학습 데이터 없을 때) ────────────────────────────────────

def create_dummy_model():
    """학습 데이터 없을 때 사용할 더미 모델 생성"""
    os.makedirs(MODEL_DIR, exist_ok=True)

    # 간단한 규칙 기반 더미 데이터로 모델 학습
    np.random.seed(42)
    n = 500
    budget = np.random.uniform(100000, 5000000, n)
    price = np.random.uniform(50000, 6000000, n)
    brand_match = np.random.randint(0, 2, n)
    rating = np.random.uniform(1.0, 5.0, n)
    review_count = np.random.randint(0, 1000, n)
    return_rate = np.random.uniform(0, 30, n)
    factor_match = np.random.randint(0, 5, n)
    days = np.random.randint(0, 1500, n)

    X = np.column_stack([budget, price, brand_match, rating, review_count, return_rate, factor_match, days])

    # 규칙 기반 레이블 생성
    y = np.zeros(n)
    y += np.clip((price - budget) / np.maximum(budget, 1), 0, 1) * 0.3
    y += np.clip((3.8 - rating) / 3.8, 0, 1) * 0.25
    y += np.clip(return_rate / 30, 0, 1) * 0.2
    y += (1 - brand_match) * 0.1
    y += (1 - np.clip(factor_match / 3, 0, 1)) * 0.1
    y += np.clip((days - 900) / 600, 0, 1) * 0.05
    y = np.clip(y + np.random.normal(0, 0.05, n), 0, 1)

    from sklearn.ensemble import GradientBoostingRegressor
    model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
    model.fit(X, y)  # X is already numpy array, no feature names

    joblib.dump(model, MODEL_PATH)
    logger.info(f"더미 모델 생성 완료: {MODEL_PATH}")
    return model


# ─── RegretPredictor 클래스 ───────────────────────────────────────────────────

class RegretPredictor:
    """구매 후회 예측 및 대체상품 추천 메인 클래스"""

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        product_data_path: str = PRODUCT_DATA_PATH,
        use_llm: bool = False,
    ):
        self.use_llm = use_llm

        # 모델 로드 (없으면 더미 모델 생성)
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            logger.info(f"모델 로드 완료: {model_path}")
        else:
            logger.warning(f"모델 파일 없음. 더미 모델 생성: {model_path}")
            self.model = create_dummy_model()

        # 상품 데이터 로드
        self.products_df = self._load_products(product_data_path)
        logger.info(
            f"RegretPredictor 초기화 완료 | "
            f"상품 수: {len(self.products_df)} | "
            f"LLM: {self.use_llm}"
        )

    def _load_products(self, path: str) -> pd.DataFrame:
        if os.path.exists(path):
            try:
                if path.endswith(".xlsx"):
                    return pd.read_excel(path)
                return pd.read_csv(path)
            except Exception as e:
                logger.error(f"상품 데이터 로드 실패: {e}")

        # 데이터 파일 없을 때 샘플 데이터 반환
        return self._get_sample_products()

    def _get_sample_products(self) -> pd.DataFrame:
        """샘플 상품 데이터 (데이터 파일 없을 때 사용) - 다양한 카테고리 60개 이상"""
        data = [
            # ── 노트북 ──────────────────────────────────────────────────────────
            {"product_id": 101, "name": "삼성 갤럭시북 Pro 360", "category": "전자제품", "brand": "Samsung",
             "price": 1590000, "rating": 4.6, "review_count": 320, "return_rate": 2.5,
             "days_since_release": 180, "specs": {"성능": "high", "휴대성": "high", "배터리": "high"},
             "description": "고성능 2-in-1 업무용 노트북"},
            {"product_id": 102, "name": "LG 그램 16", "category": "전자제품", "brand": "LG",
             "price": 1490000, "rating": 4.7, "review_count": 510, "return_rate": 2.1,
             "days_since_release": 150, "specs": {"성능": "high", "휴대성": "high", "배터리": "high"},
             "description": "초경량 프리미엄 노트북"},
            {"product_id": 103, "name": "ASUS ROG 게이밍 노트북", "category": "전자제품", "brand": "ASUS",
             "price": 1990000, "rating": 4.5, "review_count": 280, "return_rate": 3.8,
             "days_since_release": 120, "specs": {"성능": "high", "휴대성": "low", "배터리": "medium"},
             "description": "고성능 게이밍 노트북"},
            {"product_id": 104, "name": "레노버 IdeaPad 5", "category": "전자제품", "brand": "Lenovo",
             "price": 790000, "rating": 4.2, "review_count": 620, "return_rate": 5.0,
             "days_since_release": 300, "specs": {"성능": "medium", "휴대성": "medium", "배터리": "medium"},
             "description": "가성비 업무용 노트북"},
            {"product_id": 105, "name": "Dell XPS 15", "category": "전자제품", "brand": "Dell",
             "price": 1850000, "rating": 4.7, "review_count": 390, "return_rate": 2.0,
             "days_since_release": 90, "specs": {"성능": "high", "휴대성": "high", "배터리": "high"},
             "description": "프리미엄 비즈니스 노트북"},
            {"product_id": 106, "name": "Apple MacBook Air M3", "category": "전자제품", "brand": "Apple",
             "price": 1590000, "rating": 4.9, "review_count": 980, "return_rate": 1.2,
             "days_since_release": 60, "specs": {"성능": "high", "휴대성": "high", "배터리": "high"},
             "description": "M3 칩 탑재 초경량 맥북"},
            {"product_id": 107, "name": "HP Spectre x360", "category": "전자제품", "brand": "HP",
             "price": 1750000, "rating": 4.5, "review_count": 240, "return_rate": 2.8,
             "days_since_release": 200, "specs": {"성능": "high", "휴대성": "high", "배터리": "high"},
             "description": "2-in-1 프리미엄 노트북"},
            # ── 스마트폰 ────────────────────────────────────────────────────────
            {"product_id": 201, "name": "삼성 갤럭시 S24 Ultra", "category": "전자제품", "brand": "Samsung",
             "price": 1550000, "rating": 4.7, "review_count": 1200, "return_rate": 2.0,
             "days_since_release": 60, "specs": {"카메라": "high", "배터리": "high", "성능": "high"},
             "description": "S펜 탑재 플래그십 스마트폰"},
            {"product_id": 202, "name": "Apple iPhone 15 Pro", "category": "전자제품", "brand": "Apple",
             "price": 1550000, "rating": 4.8, "review_count": 2100, "return_rate": 1.5,
             "days_since_release": 45, "specs": {"카메라": "high", "배터리": "medium", "성능": "high"},
             "description": "티타늄 프레임 프리미엄 아이폰"},
            {"product_id": 203, "name": "Google Pixel 8", "category": "전자제품", "brand": "Google",
             "price": 990000, "rating": 4.5, "review_count": 480, "return_rate": 3.0,
             "days_since_release": 90, "specs": {"카메라": "high", "배터리": "medium", "성능": "high"},
             "description": "AI 카메라 특화 안드로이드"},
            {"product_id": 204, "name": "삼성 갤럭시 A55", "category": "전자제품", "brand": "Samsung",
             "price": 580000, "rating": 4.3, "review_count": 760, "return_rate": 3.5,
             "days_since_release": 120, "specs": {"카메라": "medium", "배터리": "high", "성능": "medium"},
             "description": "가성비 중급형 스마트폰"},
            {"product_id": 205, "name": "Xiaomi 14 Pro", "category": "전자제품", "brand": "Xiaomi",
             "price": 890000, "rating": 4.4, "review_count": 350, "return_rate": 4.2,
             "days_since_release": 80, "specs": {"카메라": "high", "배터리": "high", "성능": "high"},
             "description": "라이카 카메라 탑재 플래그십"},
            # ── 이어폰/헤드폰 ────────────────────────────────────────────────────
            {"product_id": 301, "name": "Sony WH-1000XM5", "category": "전자제품", "brand": "Sony",
             "price": 380000, "rating": 4.8, "review_count": 1500, "return_rate": 2.0,
             "days_since_release": 200, "specs": {"음질": "high", "노이즈캔슬링": "high", "배터리": "high"},
             "description": "최강 노이즈캔슬링 헤드폰"},
            {"product_id": 302, "name": "Apple AirPods Pro 2", "category": "전자제품", "brand": "Apple",
             "price": 329000, "rating": 4.7, "review_count": 2800, "return_rate": 1.8,
             "days_since_release": 150, "specs": {"음질": "high", "노이즈캔슬링": "high", "배터리": "medium"},
             "description": "애플 생태계 최적화 이어폰"},
            {"product_id": 303, "name": "삼성 갤럭시 버즈 2 Pro", "category": "전자제품", "brand": "Samsung",
             "price": 219000, "rating": 4.4, "review_count": 680, "return_rate": 3.2,
             "days_since_release": 180, "specs": {"음질": "high", "노이즈캔슬링": "medium", "배터리": "medium"},
             "description": "갤럭시 생태계 최적화 이어폰"},
            {"product_id": 304, "name": "JBL Tune 770NC", "category": "전자제품", "brand": "JBL",
             "price": 129000, "rating": 4.2, "review_count": 420, "return_rate": 4.0,
             "days_since_release": 240, "specs": {"음질": "medium", "노이즈캔슬링": "medium", "배터리": "high"},
             "description": "가성비 노이즈캔슬링 헤드폰"},
            {"product_id": 305, "name": "Bose QuietComfort 45", "category": "전자제품", "brand": "Bose",
             "price": 420000, "rating": 4.6, "review_count": 890, "return_rate": 2.5,
             "days_since_release": 300, "specs": {"음질": "high", "노이즈캔슬링": "high", "배터리": "high"},
             "description": "프리미엄 노이즈캔슬링 헤드폰"},
            # ── TV/모니터 ────────────────────────────────────────────────────────
            {"product_id": 401, "name": "삼성 QLED 65인치 TV", "category": "전자제품", "brand": "Samsung",
             "price": 1890000, "rating": 4.6, "review_count": 560, "return_rate": 3.0,
             "days_since_release": 120, "specs": {"화질": "high", "크기": "65인치", "HDR": "high"},
             "description": "QLED 4K 스마트 TV"},
            {"product_id": 402, "name": "LG OLED 55인치 TV", "category": "전자제품", "brand": "LG",
             "price": 1690000, "rating": 4.8, "review_count": 780, "return_rate": 2.2,
             "days_since_release": 90, "specs": {"화질": "high", "크기": "55인치", "HDR": "high"},
             "description": "OLED 4K 프리미엄 TV"},
            {"product_id": 403, "name": "LG 울트라기어 27인치 모니터", "category": "전자제품", "brand": "LG",
             "price": 490000, "rating": 4.5, "review_count": 340, "return_rate": 2.8,
             "days_since_release": 180, "specs": {"해상도": "QHD", "주사율": "165Hz", "패널": "IPS"},
             "description": "게이밍 QHD 모니터"},
            {"product_id": 404, "name": "삼성 오디세이 32인치 모니터", "category": "전자제품", "brand": "Samsung",
             "price": 650000, "rating": 4.4, "review_count": 210, "return_rate": 3.5,
             "days_since_release": 150, "specs": {"해상도": "4K", "주사율": "144Hz", "패널": "VA"},
             "description": "4K 게이밍 모니터"},
            # ── 가전제품 ─────────────────────────────────────────────────────────
            {"product_id": 501, "name": "삼성 비스포크 냉장고 4도어", "category": "전자제품", "brand": "Samsung",
             "price": 2490000, "rating": 4.7, "review_count": 420, "return_rate": 1.8,
             "days_since_release": 180, "specs": {"용량": "870L", "에너지등급": "1등급", "냉각": "메탈쿨링"},
             "description": "커스텀 패널 프리미엄 냉장고"},
            {"product_id": 502, "name": "LG 트롬 세탁기 25kg", "category": "전자제품", "brand": "LG",
             "price": 1390000, "rating": 4.6, "review_count": 580, "return_rate": 2.0,
             "days_since_release": 120, "specs": {"용량": "25kg", "에너지등급": "1등급", "세탁방식": "드럼"},
             "description": "AI DD 모터 대용량 세탁기"},
            {"product_id": 503, "name": "다이슨 V15 청소기", "category": "전자제품", "brand": "Dyson",
             "price": 890000, "rating": 4.7, "review_count": 1200, "return_rate": 2.5,
             "days_since_release": 200, "specs": {"흡입력": "high", "배터리": "60분", "필터": "HEPA"},
             "description": "레이저 감지 무선 청소기"},
            {"product_id": 504, "name": "삼성 비스포크 에어컨 6평", "category": "전자제품", "brand": "Samsung",
             "price": 890000, "rating": 4.5, "review_count": 310, "return_rate": 2.8,
             "days_since_release": 150, "specs": {"냉방면적": "6평", "에너지등급": "1등급", "소음": "low"},
             "description": "인버터 벽걸이 에어컨"},
            {"product_id": 505, "name": "LG 퓨리케어 공기청정기", "category": "전자제품", "brand": "LG",
             "price": 490000, "rating": 4.6, "review_count": 890, "return_rate": 2.2,
             "days_since_release": 90, "specs": {"적용면적": "49평", "필터": "HEPA", "소음": "low"},
             "description": "360도 청정 공기청정기"},
            # ── 패션/의류 ─────────────────────────────────────────────────────────
            {"product_id": 601, "name": "나이키 에어포스 1 로우", "category": "패션/의류", "brand": "Nike",
             "price": 119000, "rating": 4.6, "review_count": 3200, "return_rate": 6.5,
             "days_since_release": 500, "specs": {"소재": "가죽", "착화감": "high", "내구성": "high"},
             "description": "클래식 레더 스니커즈"},
            {"product_id": 602, "name": "아디다스 스탠스미스", "category": "패션/의류", "brand": "Adidas",
             "price": 109000, "rating": 4.5, "review_count": 2800, "return_rate": 5.8,
             "days_since_release": 600, "specs": {"소재": "가죽", "착화감": "medium", "내구성": "high"},
             "description": "클래식 테니스 스니커즈"},
            {"product_id": 603, "name": "노스페이스 눕시 패딩", "category": "패션/의류", "brand": "NorthFace",
             "price": 298000, "rating": 4.7, "review_count": 1500, "return_rate": 4.0,
             "days_since_release": 180, "specs": {"보온성": "high", "방수": "medium", "무게": "light"},
             "description": "구스다운 경량 패딩"},
            {"product_id": 604, "name": "유니클로 울트라라이트 다운", "category": "패션/의류", "brand": "Uniqlo",
             "price": 89900, "rating": 4.4, "review_count": 4200, "return_rate": 5.5,
             "days_since_release": 120, "specs": {"보온성": "medium", "방수": "low", "무게": "ultralight"},
             "description": "초경량 다운 재킷"},
            {"product_id": 605, "name": "나이키 드라이핏 러닝화", "category": "패션/의류", "brand": "Nike",
             "price": 139000, "rating": 4.5, "review_count": 980, "return_rate": 7.0,
             "days_since_release": 90, "specs": {"쿠셔닝": "high", "통기성": "high", "내구성": "medium"},
             "description": "반응형 쿠셔닝 러닝화"},
            {"product_id": 606, "name": "리바이스 511 슬림 청바지", "category": "패션/의류", "brand": "Levis",
             "price": 89000, "rating": 4.3, "review_count": 1800, "return_rate": 8.5,
             "days_since_release": 365, "specs": {"핏": "슬림", "소재": "데님", "신축성": "medium"},
             "description": "클래식 슬림핏 청바지"},
            # ── 스포츠/레저 ───────────────────────────────────────────────────────
            {"product_id": 701, "name": "가민 포러너 265 스마트워치", "category": "스포츠/레저", "brand": "Garmin",
             "price": 590000, "rating": 4.7, "review_count": 680, "return_rate": 2.5,
             "days_since_release": 150, "specs": {"GPS": "high", "배터리": "13일", "방수": "5ATM"},
             "description": "러닝 전용 GPS 스마트워치"},
            {"product_id": 702, "name": "Apple Watch Series 9", "category": "스포츠/레저", "brand": "Apple",
             "price": 599000, "rating": 4.6, "review_count": 1500, "return_rate": 2.8,
             "days_since_release": 90, "specs": {"GPS": "high", "배터리": "18시간", "방수": "50m"},
             "description": "애플 생태계 스마트워치"},
            {"product_id": 703, "name": "삼성 갤럭시 워치 6", "category": "스포츠/레저", "brand": "Samsung",
             "price": 349000, "rating": 4.4, "review_count": 890, "return_rate": 3.2,
             "days_since_release": 120, "specs": {"GPS": "high", "배터리": "40시간", "방수": "5ATM"},
             "description": "갤럭시 생태계 스마트워치"},
            {"product_id": 704, "name": "요넥스 배드민턴 라켓 Astrox", "category": "스포츠/레저", "brand": "Yonex",
             "price": 189000, "rating": 4.6, "review_count": 420, "return_rate": 3.0,
             "days_since_release": 200, "specs": {"무게": "83g", "강도": "high", "밸런스": "헤드헤비"},
             "description": "공격형 배드민턴 라켓"},
            {"product_id": 705, "name": "나이키 줌 페가수스 40", "category": "스포츠/레저", "brand": "Nike",
             "price": 149000, "rating": 4.5, "review_count": 760, "return_rate": 6.0,
             "days_since_release": 120, "specs": {"쿠셔닝": "high", "통기성": "high", "무게": "light"},
             "description": "데일리 트레이닝 러닝화"},
            {"product_id": 706, "name": "코멧 캠핑 텐트 4인용", "category": "스포츠/레저", "brand": "Comet",
             "price": 189000, "rating": 4.3, "review_count": 280, "return_rate": 5.5,
             "days_since_release": 240, "specs": {"수용인원": "4인", "방수": "3000mm", "무게": "3.2kg"},
             "description": "패밀리 돔 텐트"},
            # ── 뷰티/화장품 ───────────────────────────────────────────────────────
            {"product_id": 801, "name": "설화수 윤조에센스 6세대", "category": "뷰티/화장품", "brand": "Sulwhasoo",
             "price": 120000, "rating": 4.7, "review_count": 2100, "return_rate": 3.5,
             "days_since_release": 180, "specs": {"용량": "150ml", "피부타입": "all", "기능": "보습/탄력"},
             "description": "한방 성분 프리미엄 에센스"},
            {"product_id": 802, "name": "이니스프리 그린티 세럼", "category": "뷰티/화장품", "brand": "Innisfree",
             "price": 28000, "rating": 4.4, "review_count": 3500, "return_rate": 4.0,
             "days_since_release": 120, "specs": {"용량": "80ml", "피부타입": "all", "기능": "보습/진정"},
             "description": "제주 녹차 성분 세럼"},
            {"product_id": 803, "name": "라네즈 워터슬리핑 마스크", "category": "뷰티/화장품", "brand": "Laneige",
             "price": 35000, "rating": 4.6, "review_count": 4200, "return_rate": 3.2,
             "days_since_release": 200, "specs": {"용량": "70ml", "피부타입": "건성/복합", "기능": "보습"},
             "description": "수면 중 집중 보습 마스크"},
            {"product_id": 804, "name": "헤라 블랙 쿠션 파운데이션", "category": "뷰티/화장품", "brand": "Hera",
             "price": 58000, "rating": 4.5, "review_count": 1800, "return_rate": 5.0,
             "days_since_release": 150, "specs": {"커버력": "medium", "지속력": "high", "마감감": "세미매트"},
             "description": "세미매트 쿠션 파운데이션"},
            # ── 가구/인테리어 ─────────────────────────────────────────────────────
            {"product_id": 901, "name": "허먼밀러 에어론 의자", "category": "가구/인테리어", "brand": "HermanMiller",
             "price": 1890000, "rating": 4.9, "review_count": 680, "return_rate": 1.5,
             "days_since_release": 365, "specs": {"소재": "메쉬", "조절기능": "high", "내구성": "high"},
             "description": "프리미엄 인체공학 의자"},
            {"product_id": 902, "name": "시디즈 T50 의자", "category": "가구/인테리어", "brand": "Sidiz",
             "price": 490000, "rating": 4.6, "review_count": 1200, "return_rate": 3.0,
             "days_since_release": 200, "specs": {"소재": "메쉬", "조절기능": "high", "내구성": "high"},
             "description": "국내 인체공학 의자"},
            {"product_id": 903, "name": "이케아 BEKANT 책상", "category": "가구/인테리어", "brand": "IKEA",
             "price": 189000, "rating": 4.2, "review_count": 890, "return_rate": 6.0,
             "days_since_release": 500, "specs": {"크기": "160x80cm", "소재": "MDF", "하중": "50kg"},
             "description": "심플 디자인 사무용 책상"},
            {"product_id": 904, "name": "플렉시스팟 전동 스탠딩 책상", "category": "가구/인테리어", "brand": "Flexispot",
             "price": 390000, "rating": 4.5, "review_count": 560, "return_rate": 4.5,
             "days_since_release": 180, "specs": {"크기": "140x70cm", "높이조절": "전동", "하중": "100kg"},
             "description": "전동 높이조절 스탠딩 책상"},
            # ── 식품/건강 ─────────────────────────────────────────────────────────
            {"product_id": 1001, "name": "마이프로틴 임팩트 웨이 단백질", "category": "식품/건강", "brand": "MyProtein",
             "price": 89000, "rating": 4.5, "review_count": 2800, "return_rate": 3.5,
             "days_since_release": 120, "specs": {"단백질": "25g/서빙", "칼로리": "130kcal", "맛": "다양"},
             "description": "고품질 웨이 프로틴"},
            {"product_id": 1002, "name": "뉴트리코어 종합비타민", "category": "식품/건강", "brand": "Nutricore",
             "price": 35000, "rating": 4.4, "review_count": 1500, "return_rate": 4.0,
             "days_since_release": 200, "specs": {"성분": "23종 비타민미네랄", "용량": "90정", "복용법": "1일 1정"},
             "description": "23종 비타민 미네랄 복합제"},
            {"product_id": 1003, "name": "네스프레소 버츄오 플러스", "category": "식품/건강", "brand": "Nespresso",
             "price": 219000, "rating": 4.6, "review_count": 980, "return_rate": 3.0,
             "days_since_release": 180, "specs": {"용량": "1.2L", "압력": "19bar", "예열시간": "25초"},
             "description": "캡슐 커피 머신"},
            # ── 도서/문구 ─────────────────────────────────────────────────────────
            {"product_id": 1101, "name": "애플 Apple Pencil 2세대", "category": "전자제품", "brand": "Apple",
             "price": 179000, "rating": 4.8, "review_count": 1800, "return_rate": 2.0,
             "days_since_release": 300, "specs": {"호환성": "iPad Pro/Air", "충전": "무선", "감압": "4096단계"},
             "description": "iPad 전용 스타일러스 펜"},
            {"product_id": 1102, "name": "파이롯트 만년필 카쿠노", "category": "도서/문구", "brand": "Pilot",
             "price": 25000, "rating": 4.5, "review_count": 680, "return_rate": 3.5,
             "days_since_release": 400, "specs": {"촉크기": "F", "소재": "플라스틱", "잉크방식": "카트리지"},
             "description": "입문용 만년필"},
            # ── 반려동물 ─────────────────────────────────────────────────────────
            {"product_id": 1201, "name": "로얄캐닌 강아지 사료 미니 어덜트", "category": "반려동물", "brand": "RoyalCanin",
             "price": 65000, "rating": 4.6, "review_count": 2100, "return_rate": 3.0,
             "days_since_release": 200, "specs": {"용량": "4kg", "대상": "소형견 성견", "주성분": "닭고기"},
             "description": "소형견 전용 프리미엄 사료"},
            {"product_id": 1202, "name": "힐스 사이언스 다이어트 고양이", "category": "반려동물", "brand": "Hills",
             "price": 55000, "rating": 4.5, "review_count": 1400, "return_rate": 3.5,
             "days_since_release": 180, "specs": {"용량": "3.2kg", "대상": "성묘", "기능": "체중관리"},
             "description": "수의사 추천 고양이 사료"},
        ]
        return pd.DataFrame(data)

    def _predict_final_score(self, user: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        feature = build_feature_row(user, product)
        X = np.array([[feature.get(f, 0.0) or 0.0 for f in FEATURES]], dtype=np.float64)

        model_regret_score = clamp_score(self.model.predict(X)[0])
        regret_causes = make_regret_causes(feature=feature, user=user, product=product)
        cause_score = calculate_cause_score(regret_causes)
        regret_score = blend_regret_score(model_score=model_regret_score, cause_score=cause_score)

        return {
            "feature": feature,
            "model_regret_score": model_regret_score,
            "cause_score": cause_score,
            "regret_score": regret_score,
            "regret_causes": regret_causes,
        }

    def predict_regret(self, user: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """메인 예측 함수"""
        score_result = self._predict_final_score(user=user, product=product)
        regret_score = score_result["regret_score"]
        regret_causes = score_result["regret_causes"]

        # 후회 임계값 이상이면 대체상품 추천
        alternatives = []
        if regret_score >= 0.4:
            alternatives = self.recommend_alternatives(
                user=user,
                target_product=product,
                target_regret_score=regret_score,
                top_k=5,
            )

        llm_analysis = generate_llm_analysis(
            user=user,
            product=product,
            score_result=score_result,
            alternatives=alternatives,
            use_llm=self.use_llm,
        )

        return {
            "product_id": product.get("product_id") or product.get("id"),
            "product_name": product.get("name"),
            "regret_score": round(regret_score, 4),
            "regret_level": regret_level(regret_score),
            "model_regret_score": round(score_result["model_regret_score"], 4),
            "cause_score": round(score_result["cause_score"], 4),
            "regret_causes": regret_causes,
            "regret_reasons": [c["message"] for c in regret_causes],
            "alternatives": alternatives,
            "llm_analysis": llm_analysis,
        }

    def recommend_alternatives(
        self,
        user: Dict[str, Any],
        target_product: Dict[str, Any],
        target_regret_score: float,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """대체상품 추천"""
        if self.products_df.empty:
            return []

        target_product_id = target_product.get("product_id") or target_product.get("id")
        target_category = target_product.get("category")
        target_price = safe_float(target_product.get("price"))
        budget = safe_float(user.get("budget"))

        candidates = self.products_df.copy()

        # 카테고리 필터링: None/빈문자열/'기타'이면 전체 상품 대상으로 추천
        skip_category_filter = (
            not target_category
            or target_category.strip() == ""
            or target_category == "기타"
        )
        if not skip_category_filter and "category" in candidates.columns:
            same_cat = candidates[candidates["category"] == target_category]
            # 같은 카테고리 후보가 충분하지 않으면 전체 후보 사용
            candidates = same_cat if len(same_cat) >= 2 else candidates

        if target_product_id is not None and "product_id" in candidates.columns:
            candidates = candidates[candidates["product_id"] != target_product_id]

        results = []
        for _, row in candidates.iterrows():
            candidate = row.to_dict()
            candidate_score_result = self._predict_final_score(user=user, product=candidate)
            candidate_regret_score = candidate_score_result["regret_score"]

            match_score = self._calculate_match_score(user, candidate, target_price)
            improvement_score = target_regret_score - candidate_regret_score
            final_score = (
                match_score * 0.55
                + max(improvement_score, 0) * 0.35
                + self._price_advantage_score(candidate, target_price, budget) * 0.10
            )

            if candidate_regret_score <= target_regret_score:
                results.append({
                    "product_id": candidate.get("product_id"),
                    "name": candidate.get("name"),
                    "brand": candidate.get("brand"),
                    "category": candidate.get("category"),
                    "price": safe_float(candidate.get("price")),
                    "rating": safe_float(candidate.get("rating")),
                    "return_rate": safe_float(candidate.get("return_rate")),
                    "regret_score": round(candidate_regret_score, 4),
                    "match_score": round(match_score, 4),
                    "improvement_score": round(improvement_score, 4),
                    "final_score": round(final_score, 4),
                    "recommendation_reason": self._make_alternative_reason(
                        user=user,
                        candidate=candidate,
                        target_price=target_price,
                        candidate_regret_score=candidate_regret_score,
                        target_regret_score=target_regret_score,
                    ),
                })

        results.sort(key=lambda x: (-x["final_score"], x["regret_score"], x["price"]))
        return results[:top_k]

    def _calculate_match_score(self, user, product, target_price) -> float:
        score = 0.0
        budget = safe_float(user.get("budget"))
        price = safe_float(product.get("price"))
        rating = safe_float(product.get("rating"))
        return_rate = safe_float(product.get("return_rate"))
        preferred_brands = user.get("preferred_brands", []) or []

        if budget > 0 and price <= budget:
            score += 0.30
        if preferred_brands and product.get("brand") in preferred_brands:
            score += 0.20
        if rating >= 4.3:
            score += 0.20
        elif rating >= 4.0:
            score += 0.10
        if return_rate <= 5:
            score += 0.15
        elif return_rate <= 10:
            score += 0.08
        if target_price > 0 and price < target_price:
            score += 0.15
        return min(score, 1.0)

    def _price_advantage_score(self, product, target_price, budget) -> float:
        price = safe_float(product.get("price"))
        score = 0.0
        if budget > 0 and price <= budget:
            score += 0.5
        if target_price > 0 and price < target_price:
            discount_ratio = (target_price - price) / target_price
            score += min(discount_ratio, 0.5)
        return min(score, 1.0)

    def _make_alternative_reason(self, user, candidate, target_price, candidate_regret_score, target_regret_score) -> str:
        reasons = []
        budget = safe_float(user.get("budget"))
        price = safe_float(candidate.get("price"))
        rating = safe_float(candidate.get("rating"))
        return_rate = safe_float(candidate.get("return_rate"))

        if budget > 0 and price <= budget:
            reasons.append("예산 범위에 적합")
        if target_price > 0 and price < target_price:
            reasons.append("기존 후보보다 가격 부담이 낮음")
        if rating >= 4.3:
            reasons.append("리뷰 평점이 우수함")
        if return_rate <= 5:
            reasons.append("반품률이 낮아 구매 후 불만 가능성이 낮음")
        if candidate_regret_score < target_regret_score:
            reasons.append("예측 후회 가능성이 기존 후보보다 낮음")
        if candidate.get("brand") in (user.get("preferred_brands", []) or []):
            reasons.append("선호 브랜드와 일치")

        return ", ".join(reasons) if reasons else "현재 후보 대비 전반적인 적합도가 높음"
