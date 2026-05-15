#!/bin/bash
# StopBuy 백엔드 로컬 실행 스크립트 (Docker 없이)
# 사전 조건: PostgreSQL 실행 중, Python 3.11+

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== StopBuy 백엔드 로컬 실행 ==="

# 가상환경 생성 및 활성화
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "[1/4] 가상환경 생성..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

source "$SCRIPT_DIR/venv/bin/activate"

# 의존성 설치
echo "[2/4] 의존성 설치..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# 환경변수 설정
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://stopbuy:stopbuy_secret@localhost:5432/stopbuy}"
export AGENT_WS_URL="${AGENT_WS_URL:-ws://localhost:8765}"
export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "[3/4] 환경변수 설정 완료"
echo "  DATABASE_URL: $DATABASE_URL"
echo "  AGENT_WS_URL: $AGENT_WS_URL"

# FastAPI 서버 실행
echo "[4/4] FastAPI 서버 시작..."
echo "  API 문서: http://localhost:8000/docs"
cd "$SCRIPT_DIR"
uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
