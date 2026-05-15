-- StopBuy 데이터베이스 초기화 스크립트
-- PostgreSQL 15+

-- UUID 확장
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 분석 이력 테이블
CREATE TABLE IF NOT EXISTS analysis_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  VARCHAR(64) NOT NULL,
    input_type  VARCHAR(20) NOT NULL DEFAULT 'manual',
    product_url TEXT,
    product_name VARCHAR(500),
    product_brand VARCHAR(200),
    product_category VARCHAR(200),
    product_price NUMERIC(15, 2),
    product_rating NUMERIC(3, 2),
    product_review_count INTEGER,
    product_return_rate NUMERIC(5, 2),
    regret_score NUMERIC(5, 4),
    regret_level VARCHAR(20),
    model_regret_score NUMERIC(5, 4),
    cause_score NUMERIC(5, 4),
    regret_causes JSONB,
    alternatives JSONB,
    llm_analysis JSONB,
    user_profile JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_analysis_session ON analysis_history(session_id);
CREATE INDEX IF NOT EXISTS idx_analysis_created ON analysis_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_level ON analysis_history(regret_level);

-- 샘플 상품 데이터 (대체상품 DB 역할)
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(500) NOT NULL,
    brand       VARCHAR(200),
    category    VARCHAR(200),
    price       NUMERIC(15, 2),
    rating      NUMERIC(3, 2),
    review_count INTEGER DEFAULT 0,
    return_rate NUMERIC(5, 2) DEFAULT 5.0,
    days_since_release INTEGER DEFAULT 180,
    image_url   TEXT,
    product_url TEXT,
    description TEXT,
    specs       JSONB,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC);

-- 샘플 상품 데이터 삽입
INSERT INTO products (name, brand, category, price, rating, review_count, return_rate, days_since_release, description) VALUES
('갤럭시 S24 FE', 'Samsung', '스마트폰', 699000, 4.3, 1250, 3.2, 90, '삼성 갤럭시 S24 FE - 합리적인 가격의 플래그십 경험'),
('아이폰 15', 'Apple', '스마트폰', 1250000, 4.6, 3200, 2.1, 180, '애플 아이폰 15 - 강력한 성능과 카메라'),
('픽셀 8a', 'Google', '스마트폰', 649000, 4.4, 890, 2.8, 120, '구글 픽셀 8a - 순수 안드로이드 경험'),
('갤럭시 북4 프로', 'Samsung', '노트북', 1890000, 4.5, 560, 4.1, 150, '삼성 갤럭시 북4 프로 - 얇고 가벼운 프리미엄 노트북'),
('LG 그램 16', 'LG', '노트북', 1650000, 4.4, 780, 3.5, 200, 'LG 그램 16 - 초경량 고성능 노트북'),
('맥북 에어 M3', 'Apple', '노트북', 1590000, 4.7, 2100, 1.8, 240, '애플 맥북 에어 M3 - 놀라운 배터리와 성능'),
('소니 WH-1000XM5', 'Sony', '이어폰/헤드폰', 379000, 4.7, 4500, 2.3, 365, '소니 WH-1000XM5 - 최고의 노이즈 캔슬링'),
('에어팟 프로 2세대', 'Apple', '이어폰/헤드폰', 329000, 4.5, 6700, 2.0, 400, '애플 에어팟 프로 2세대 - 탁월한 ANC와 음질'),
('갤럭시 버즈3 프로', 'Samsung', '이어폰/헤드폰', 259000, 4.2, 1890, 3.8, 60, '삼성 갤럭시 버즈3 프로 - 안드로이드 최적화 이어폰'),
('LG 올레드 C4 55인치', 'LG', 'TV', 1490000, 4.8, 2300, 1.5, 180, 'LG 올레드 C4 - 완벽한 블랙과 색재현'),
('삼성 네오 QLED 8K', 'Samsung', 'TV', 2890000, 4.4, 450, 2.9, 120, '삼성 네오 QLED 8K - 미래형 화질'),
('다이슨 V15 디텍트', 'Dyson', '청소기', 899000, 4.6, 1200, 3.1, 300, '다이슨 V15 디텍트 - 레이저로 먼지 감지'),
('샤오미 로봇청소기 S10+', 'Xiaomi', '청소기', 459000, 4.3, 2100, 4.2, 180, '샤오미 로봇청소기 S10+ - 자동 먼지통 비움'),
('나이키 에어맥스 270', 'Nike', '신발', 159000, 4.2, 3400, 8.5, 730, '나이키 에어맥스 270 - 편안한 일상화'),
('아디다스 울트라부스트 23', 'Adidas', '신발', 189000, 4.5, 2800, 5.2, 365, '아디다스 울트라부스트 23 - 최고의 러닝화')
ON CONFLICT DO NOTHING;

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_analysis_history_updated_at
    BEFORE UPDATE ON analysis_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
