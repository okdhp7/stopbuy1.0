#!/bin/bash
# StopBuy AI Agent 로컬 실행 스크립트
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== StopBuy AI Agent 로컬 실행 ==="

# 가상환경 생성 및 활성화
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "[1/3] 가상환경 생성..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

source "$SCRIPT_DIR/venv/bin/activate"

# 의존성 설치
echo "[2/3] 의존성 설치..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# 환경변수 설정
export AGENT_HOST="${AGENT_HOST:-0.0.0.0}"
export AGENT_PORT="${AGENT_PORT:-8765}"
export USE_LLM="${USE_LLM:-false}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

echo "[3/3] AI Agent 서버 시작..."
echo "  WebSocket: ws://localhost:$AGENT_PORT"
echo "  LLM 사용: $USE_LLM"

cd "$SCRIPT_DIR"
python3 run_agent.py
