#!/bin/bash
# StopBuy 전체 시스템 실행 스크립트
#
# 사용법:
#   ./start.sh          → 전체 Docker 통합 실행 (프론트엔드 포함, 기본값)
#   ./start.sh all      → 전체 Docker 통합 실행 (프론트엔드 포함)
#   ./start.sh dev      → 백엔드만 Docker, 프론트엔드는 Vite 개발 서버
#   ./start.sh stop     → 모든 서비스 종료
#   ./start.sh logs     → 전체 로그 출력
#   ./start.sh logs backend  → 특정 서비스 로그

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")/stopbuy_agent"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")/stopbuy_app"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║         StopBuy — 구매 후회 예측 AI            ║"
    echo "║  FastAPI + React + LightGBM + WebSocket      ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    log_info "필수 도구 확인 중..."
    local missing=()
    command -v docker >/dev/null 2>&1 || missing+=("docker")
    if ! docker compose version >/dev/null 2>&1; then
        command -v docker-compose >/dev/null 2>&1 || missing+=("docker-compose")
    fi
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "다음 도구가 필요합니다: ${missing[*]}"
        log_error "Docker 설치: https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker 확인 완료"
}

ensure_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_warn ".env 파일이 없습니다. 기본값으로 생성합니다."
        cat > "$SCRIPT_DIR/.env" << 'EOF'
# StopBuy 환경 설정
# LLM 분석 사용 여부 (true로 설정 시 OpenAI API 키 필요)
USE_LLM=false
OPENAI_API_KEY=
LLM_MODEL_NAME=gpt-4o-mini

# 보안 키 (프로덕션에서는 반드시 변경)
SECRET_KEY=stopbuy-dev-secret-key-change-in-production

# PostgreSQL (기본값 사용 권장)
POSTGRES_USER=stopbuy
POSTGRES_PASSWORD=stopbuy_secret
POSTGRES_DB=stopbuy
EOF
        log_success ".env 파일 생성 완료"
    fi
}

# ── 전체 Docker 통합 실행 (프론트엔드 포함) ──────────────────────────────────
start_all() {
    print_banner
    check_requirements
    ensure_env

    log_info "전체 서비스 빌드 및 시작 중 (DB + Agent + Backend + Frontend)..."
    log_warn "첫 실행 시 Docker 이미지 빌드에 3~10분 소요될 수 있습니다."
    echo ""

    cd "$SCRIPT_DIR"
    docker compose up -d --build

    log_info "서비스 준비 대기 중 (약 20초)..."
    sleep 20

    echo ""
    log_success "StopBuy 시스템 시작 완료!"
    echo ""
    echo -e "  ${GREEN}▶ 프론트엔드:${NC}  http://localhost"
    echo -e "  ${GREEN}▶ 백엔드 API:${NC}  http://localhost:8000"
    echo -e "  ${GREEN}▶ API 문서:${NC}    http://localhost:8000/docs"
    echo -e "  ${GREEN}▶ AI Agent:${NC}    ws://localhost:8765"
    echo -e "  ${GREEN}▶ PostgreSQL:${NC}  localhost:5432"
    echo ""
    echo -e "  상태 확인: ${CYAN}docker compose ps${NC}"
    echo -e "  로그 확인: ${CYAN}./start.sh logs${NC}"
    echo -e "  서비스 종료: ${YELLOW}./start.sh stop${NC}"
}

# ── 개발 모드 (백엔드 Docker + 프론트엔드 Vite 개발 서버) ─────────────────────
start_dev() {
    print_banner
    check_requirements
    ensure_env

    log_info "개발 모드 시작 (백엔드: Docker, 프론트엔드: Vite 개발 서버)..."

    # 백엔드 서비스만 Docker로 시작 (frontend 서비스 제외)
    cd "$SCRIPT_DIR"
    docker compose up -d --build db agent backend

    log_info "백엔드 서비스 준비 대기 중..."
    sleep 10

    # 프론트엔드 개발 서버 시작
    if [ -d "$FRONTEND_DIR" ]; then
        log_info "프론트엔드 개발 서버 시작..."
        cd "$FRONTEND_DIR"
        if command -v pnpm >/dev/null 2>&1; then
            pnpm install --silent 2>/dev/null || true
            pnpm dev &
        elif command -v npm >/dev/null 2>&1; then
            npm install --silent 2>/dev/null || true
            npm run dev &
        else
            log_warn "pnpm/npm을 찾을 수 없습니다. 프론트엔드를 수동으로 실행하세요:"
            log_warn "  cd $FRONTEND_DIR && pnpm install && pnpm dev"
        fi
        FRONTEND_PID=$!
        echo $FRONTEND_PID > /tmp/stopbuy_frontend.pid
    fi

    echo ""
    log_success "개발 환경 시작 완료!"
    echo ""
    echo -e "  ${GREEN}▶ 프론트엔드:${NC}  http://localhost:3000 (Vite 개발 서버)"
    echo -e "  ${GREEN}▶ 백엔드 API:${NC}  http://localhost:8000"
    echo -e "  ${GREEN}▶ API 문서:${NC}    http://localhost:8000/docs"
    echo ""
    echo -e "  종료: ${YELLOW}./start.sh stop${NC}"
}

# ── 서비스 종료 ────────────────────────────────────────────────────────────────
stop_all() {
    log_info "StopBuy 서비스 종료 중..."

    # Vite 개발 서버 종료 (dev 모드에서 실행된 경우)
    if [ -f /tmp/stopbuy_frontend.pid ]; then
        PID=$(cat /tmp/stopbuy_frontend.pid)
        kill "$PID" 2>/dev/null || true
        rm -f /tmp/stopbuy_frontend.pid
        log_success "프론트엔드 개발 서버 종료"
    fi

    # Docker 서비스 종료
    cd "$SCRIPT_DIR"
    docker compose down

    log_success "모든 서비스 종료 완료"
}

# ── 로그 출력 ──────────────────────────────────────────────────────────────────
show_logs() {
    cd "$SCRIPT_DIR"
    docker compose logs -f --tail=100 "$@"
}

# ── 상태 확인 ──────────────────────────────────────────────────────────────────
show_status() {
    cd "$SCRIPT_DIR"
    docker compose ps
    echo ""
    log_info "백엔드 헬스체크:"
    curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  백엔드 미응답"
}

# ── 메인 ───────────────────────────────────────────────────────────────────────
case "${1:-all}" in
    all|prod)  start_all ;;
    dev)       start_dev ;;
    stop)      stop_all ;;
    logs)      show_logs "${@:2}" ;;
    status)    show_status ;;
    *)
        echo "사용법: $0 [all|dev|stop|logs [service]|status]"
        echo ""
        echo "  all    전체 Docker 통합 실행 (프론트엔드 포함, 기본값)"
        echo "  dev    백엔드 Docker + 프론트엔드 Vite 개발 서버"
        echo "  stop   모든 서비스 종료"
        echo "  logs   전체 로그 출력 (logs backend 등 서비스 지정 가능)"
        echo "  status 서비스 상태 확인"
        exit 1
        ;;
esac
