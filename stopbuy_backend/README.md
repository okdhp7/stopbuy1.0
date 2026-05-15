# StopBuy — 구매 후회 예측 AI 시스템

> AI가 상품 정보를 분석하여 구매 후회 가능성을 예측하고, 더 나은 대체상품을 추천하는 서비스

---

## 아키텍처 개요

```
[React 프론트엔드]
       │  WebSocket (ws://.../ws/{session_id})
       ▼
[FastAPI 백엔드]  ──── REST API ────► PostgreSQL
       │  WebSocket (ws://localhost:8765)
       ▼
[Python AI Agent]
  ├── RegretPredictor (LightGBM/GradientBoosting)
  ├── 규칙 기반 후회 원인 분석
  ├── 대체상품 추천 엔진
  └── LLM 분석 (OpenAI, 선택사항)
```

### 통신 흐름

1. **사용자** → 상품 URL / 이미지 / 직접 입력 → **React 프론트엔드**
2. **프론트엔드** → WebSocket 연결 → **FastAPI 백엔드** (`/ws/{session_id}`)
3. **백엔드** → WebSocket 연결 → **AI Agent** (`ws://localhost:8765`)
4. **AI Agent** → 상품 정보 추출 → 후회 예측 → 대체상품 추천 → 결과 반환
5. **백엔드** → 결과 중계 + DB 저장 → **프론트엔드**
6. **프론트엔드** → 결과 실시간 표출 (게이지, 원인 목록, 대체상품 카드, AI 분석)

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | React 19, TailwindCSS 4, shadcn/ui, Vite |
| 백엔드 | FastAPI, WebSocket, SQLAlchemy (async), Uvicorn |
| 데이터베이스 | PostgreSQL 15 |
| AI Agent | Python, LightGBM/GradientBoosting, scikit-learn, pandas |
| 통신 | WebSocket (양방향 실시간), REST API |
| 배포 | Docker Compose |

---

## 디렉토리 구조

```
stopbuy_backend/          ← FastAPI 백엔드
├── app/
│   ├── api/
│   │   ├── websocket.py  ← 프론트엔드 ↔ 백엔드 WS 엔드포인트
│   │   └── routes.py     ← REST API (health, history)
│   ├── core/config.py    ← 환경 설정
│   ├── db/database.py    ← DB 연결 (async SQLAlchemy)
│   ├── models/models.py  ← ORM 모델
│   ├── schemas/schemas.py ← Pydantic 스키마
│   ├── services/
│   │   ├── agent_service.py    ← 백엔드 ↔ Agent WS 통신
│   │   └── analysis_service.py ← DB 저장, 이미지 처리
│   └── main.py           ← FastAPI 앱 진입점
├── docker-compose.yml    ← 전체 서비스 통합 실행
├── Dockerfile
├── init.sql              ← DB 초기화 + 샘플 데이터
├── requirements.txt
└── start.sh              ← 실행 스크립트

stopbuy_agent/            ← Python AI Agent
├── agent/
│   ├── predictor.py      ← 후회 예측 + 대체상품 추천 (핵심)
│   ├── product_extractor.py ← URL 크롤링 + 이미지 분석
│   └── server.py         ← WebSocket 서버
├── models/               ← 학습된 모델 저장 위치
├── datas/                ← 상품 데이터 (product_list.xlsx)
├── Dockerfile
├── requirements.txt
└── run_agent.py          ← 에이전트 진입점

stopbuy_app/              ← React 프론트엔드
├── client/src/
│   ├── hooks/useStopBuyWS.ts    ← WebSocket 훅 (데모 모드 포함)
│   ├── components/
│   │   ├── ProductInputForm.tsx  ← URL/이미지/수동 입력 폼
│   │   ├── RegretGauge.tsx       ← SVG 후회 게이지
│   │   ├── AnalysisProgress.tsx  ← 분석 진행 상태
│   │   ├── RegretCauseList.tsx   ← 후회 원인 목록
│   │   ├── AlternativeCard.tsx   ← 대체상품 카드
│   │   └── LLMAnalysisPanel.tsx  ← AI 분석 결과 패널
│   └── pages/Home.tsx            ← 메인 페이지
```

---

## 실행 방법

### 방법 1: Docker Compose (권장)

```bash
cd stopbuy_backend

# 선택사항: LLM 사용 시 .env 파일 편집
cp .env.example .env
# OPENAI_API_KEY=sk-... 추가

# 전체 서비스 시작 (DB + Agent + 백엔드)
./start.sh dev

# 프론트엔드는 별도 실행
cd ../stopbuy_app
pnpm dev
```

### 방법 2: 로컬 직접 실행

```bash
# 1. PostgreSQL 실행 후 DB 생성
createdb stopbuy
psql stopbuy < stopbuy_backend/init.sql

# 2. AI Agent 실행
cd stopbuy_agent
./run_local.sh

# 3. FastAPI 백엔드 실행
cd stopbuy_backend
./run_local.sh

# 4. React 프론트엔드 실행
cd stopbuy_app
pnpm dev
```

### 접속 URL

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000 |
| API 문서 (Swagger) | http://localhost:8000/docs |
| AI Agent WS | ws://localhost:8765 |
| PostgreSQL | localhost:5432 |

---

## 환경 변수

### 백엔드 (`stopbuy_backend/.env`)

```env
DATABASE_URL=postgresql+asyncpg://stopbuy:stopbuy_secret@localhost:5432/stopbuy
AGENT_WS_URL=ws://localhost:8765
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
SECRET_KEY=your-secret-key
```

### AI Agent (`stopbuy_agent/.env`)

```env
AGENT_HOST=0.0.0.0
AGENT_PORT=8765
USE_LLM=false              # true로 설정 시 OpenAI LLM 사용
OPENAI_API_KEY=sk-...      # USE_LLM=true 시 필요
LLM_MODEL_NAME=gpt-4o-mini
```

---

## 주요 기능

### 후회 예측 모델
- **ML 모델**: GradientBoostingRegressor (학습 데이터 없을 시 자동 더미 모델 생성)
- **입력 특징**: 예산, 가격, 브랜드 일치, 평점, 리뷰 수, 반품률, 중요 조건 충족, 출시 경과일
- **출력**: 후회 점수 (0~1), 후회 수준 (low/medium/high)

### 후회 원인 분석
- 예산 초과, 낮은 평점, 높은 반품률, 리뷰 부족, 브랜드 불일치, 중요 조건 미충족, 구형 상품

### 대체상품 추천
- 동일 카테고리 상품 중 후회 점수가 낮은 상품 필터링
- 매칭 점수(예산, 브랜드, 평점, 반품률) + 개선 점수 + 가격 우위 종합 평가

### LLM 분석 (선택)
- OpenAI GPT를 통한 자연어 분석 요약, 위험 설명, 구매 조언, 대체 전략 제공

### 데모 모드
- 백엔드 미연결 시 프론트엔드에서 자동으로 데모 결과 생성 (개발/테스트용)

---

## API 엔드포인트

### WebSocket
- `ws://localhost:8000/ws/{session_id}` — 실시간 분석 요청/결과

### REST
- `GET /health` — 서버 상태 및 Agent 연결 확인
- `GET /api/history` — 분석 이력 조회 (페이지네이션)
- `GET /api/history/{session_id}` — 특정 세션 분석 결과 조회

### WebSocket 메시지 형식

**요청 (프론트엔드 → 백엔드)**
```json
{
  "type": "request",
  "session_id": "abc123",
  "data": {
    "input_type": "url|image|manual",
    "product_url": "https://...",
    "image_base64": "data:image/...",
    "user": { "budget": 1000000, "preferred_brands": ["Samsung"] },
    "product": { "name": "...", "price": 900000, "rating": 3.5 }
  }
}
```

**응답 — 진행 상황 (백엔드 → 프론트엔드)**
```json
{ "type": "progress", "session_id": "abc123", "progress": 55, "message": "후회 가능성 예측 중..." }
```

**응답 — 결과 (백엔드 → 프론트엔드)**
```json
{
  "type": "result",
  "session_id": "abc123",
  "data": {
    "product_name": "...",
    "regret_score": 0.72,
    "regret_level": "high",
    "regret_causes": [...],
    "alternatives": [...],
    "llm_analysis": {...}
  }
}
```
