"""
StopBuy AI Agent - WebSocket 서버
백엔드로부터 분석 요청을 수신하고 결과를 반환하는 WebSocket 서버

수정 이력:
- websockets 13.x asyncio 신규 API 사용: websockets.asyncio.server.serve
  (legacy websockets.serve 대신 명시적으로 asyncio API 사용)
- 서버 시작 시 실제 바인딩 IP 주소 목록 표시
- 연결 안정성 강화: 예외 처리 세분화
- 동시 요청 처리: asyncio.create_task로 블로킹 없이 처리
- 상품 정보 기본값 보완 강화
- 로그 포맷에 파일명(%(filename)s) 및 행번호(%(lineno)d) 추가
- 수신 메시지 전체 내용 DEBUG 로그로 출력
"""
import asyncio
import json
import logging
import os
import socket
from typing import Any, Dict, Optional

from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosed

# ── 로거 설정 ─────────────────────────────────────────────────────────────────
# 포맷: 시각 [레벨] 파일명:행번호 로거명 - 메시지
_LOG_FORMAT = (
    "%(asctime)s [%(levelname)-8s] %(filename)s:%(lineno)d %(name)s - %(message)s"
)
_LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.DEBUG),
    format=_LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# websockets 내부 로거도 동일 포맷 적용
for _ws_logger_name in ("websockets.server", "websockets.client", "websockets"):
    _ws_logger = logging.getLogger(_ws_logger_name)
    if not _ws_logger.handlers:
        _ws_logger.setLevel(logging.WARNING)  # websockets 내부 노이즈 억제

# ── 환경 설정 ─────────────────────────────────────────────────────────────────
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8765"))
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# 수신 데이터 출력 시 최대 길이 (너무 길면 잘라서 표시)
_MAX_LOG_LEN = int(os.getenv("LOG_MAX_DATA_LEN", "2000"))

# ── 예측기 초기화 (서버 시작 시 한 번만) ─────────────────────────────────────
from agent.predictor import RegretPredictor
from agent.product_extractor import extract_product_info

predictor: Optional[RegretPredictor] = None


def get_predictor() -> RegretPredictor:
    global predictor
    if predictor is None:
        logger.info("RegretPredictor 초기화 중...")
        predictor = RegretPredictor(use_llm=USE_LLM)
    return predictor


def get_local_ips() -> list:
    """현재 머신의 실제 IP 주소 목록 반환 (루프백 제외)"""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    # UDP 소켓으로 외부 연결 시 사용하는 IP 확인 (가장 신뢰도 높음)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            if primary_ip not in ips:
                ips.insert(0, primary_ip)
    except Exception:
        pass
    return ips if ips else ["127.0.0.1"]


def _truncate(text: str, max_len: int = _MAX_LOG_LEN) -> str:
    """긴 문자열을 max_len 글자로 잘라 표시"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... (총 {len(text)}자, {len(text) - max_len}자 생략)"


def _pretty_json(data: Any, max_len: int = _MAX_LOG_LEN) -> str:
    """dict/list를 보기 좋은 JSON 문자열로 변환 후 길이 제한"""
    try:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        text = str(data)
    return _truncate(text, max_len)


async def send_message(websocket: ServerConnection, data: dict):
    """JSON 메시지 전송"""
    try:
        payload = json.dumps(data, ensure_ascii=False)
        logger.debug(
            "▶ 송신 | type=%s | session=%s | payload=%s",
            data.get("type"),
            data.get("session_id", "-"),
            _truncate(payload),
        )
        await websocket.send(payload)
    except Exception as e:
        logger.error("메시지 전송 오류: %s", e)
        raise


async def send_progress(websocket: ServerConnection, session_id: str, progress: int, message: str):
    """진행 상황 전송"""
    await send_message(websocket, {
        "type": "progress",
        "session_id": session_id,
        "progress": progress,
        "message": message,
    })


async def handle_analysis_request(websocket: ServerConnection, session_id: str, data: Dict[str, Any]):
    """분석 요청 처리"""
    try:
        logger.debug(
            "◆ handle_analysis_request 시작 | session=%s | data=\n%s",
            session_id,
            _pretty_json(data),
        )
        await send_progress(websocket, session_id, 30, "상품 정보 추출 중...")

        # 상품 정보 추출 (URL 크롤링 또는 이미지 분석)
        product_info = None
        try:
            product_info = await extract_product_info(data)
            logger.debug(
                "extract_product_info 결과 | session=%s | product_info=\n%s",
                session_id,
                _pretty_json(product_info),
            )
        except Exception as e:
            logger.warning("상품 정보 추출 실패, 직접 입력 사용: %s", e)

        # 추출 실패 시 직접 입력 데이터 사용
        if not product_info:
            product_info = data.get("product") or {}

        # 사용자 정보
        user_info = data.get("user") or {}

        # ── 기본값 보완 ──────────────────────────────────────
        if not product_info.get("name"):
            product_info["name"] = (
                data.get("product_name")
                or (data.get("product_url") and "URL 입력 상품")
                or (data.get("image_path") and "이미지 입력 상품")
                or "분석 상품"
            )

        cat = product_info.get("category")
        if not cat or cat in ("기타", ""):
            product_info["category"] = None

        if not product_info.get("rating"):
            product_info["rating"] = 3.5

        if not product_info.get("review_count"):
            product_info["review_count"] = 0

        if product_info.get("return_rate") is None:
            product_info["return_rate"] = 5.0

        if not product_info.get("price"):
            product_info["price"] = 0

        logger.info(
            "분석 시작 | session=%s | product=%s | price=%s | category=%s | rating=%s",
            session_id,
            product_info.get("name"),
            product_info.get("price"),
            product_info.get("category"),
            product_info.get("rating"),
        )
        logger.debug(
            "분석 입력 상세 | session=%s\n  user_info=%s\n  product_info=%s",
            session_id,
            _pretty_json(user_info),
            _pretty_json(product_info),
        )

        await send_progress(websocket, session_id, 55, "후회 가능성 예측 중...")

        loop = asyncio.get_event_loop()
        pred = get_predictor()
        result = await loop.run_in_executor(
            None,
            lambda: pred.predict_regret(user=user_info, product=product_info)
        )

        logger.debug(
            "predict_regret 결과 | session=%s | result=\n%s",
            session_id,
            _pretty_json(result),
        )

        await send_progress(websocket, session_id, 85, "대체상품 검색 완료. 결과 정리 중...")

        alt_count = len(result.get("alternatives", []))
        logger.info(
            "분석 완료 | session=%s | regret_score=%s | level=%s | alternatives=%d",
            session_id,
            result.get("regret_score"),
            result.get("regret_level"),
            alt_count,
        )

        await send_message(websocket, {
            "type": "result",
            "session_id": session_id,
            "data": result,
        })

    except ConnectionClosed:
        logger.warning("분석 중 연결 종료: session=%s", session_id)
    except Exception as e:
        logger.error("분석 오류 | session=%s: %s", session_id, e, exc_info=True)
        try:
            await send_message(websocket, {
                "type": "error",
                "session_id": session_id,
                "message": f"분석 중 오류가 발생했습니다: {str(e)}",
            })
        except Exception:
            pass


async def handle_client(websocket: ServerConnection):
    """클라이언트(백엔드) 연결 처리 — websockets 13.x asyncio API"""
    try:
        client_addr = websocket.remote_address
    except Exception:
        client_addr = "unknown"
    logger.info("백엔드 연결: %s", client_addr)

    try:
        async for raw_message in websocket:
            # ── 수신 원문 로그 (DEBUG) ─────────────────────────
            logger.debug(
                "◀ 수신 원문 | from=%s | len=%d bytes | raw=%s",
                client_addr,
                len(raw_message) if isinstance(raw_message, (str, bytes)) else 0,
                _truncate(raw_message if isinstance(raw_message, str) else raw_message.decode("utf-8", errors="replace")),
            )

            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError as e:
                logger.error("메시지 파싱 오류: %s | raw=%s", e, _truncate(str(raw_message)))
                try:
                    await send_message(websocket, {
                        "type": "error",
                        "message": "잘못된 메시지 형식입니다.",
                    })
                except Exception:
                    pass
                continue

            msg_type = message.get("type")
            session_id = message.get("session_id", "unknown")

            # ── 수신 파싱 결과 로그 (INFO) ─────────────────────
            logger.info(
                "◀ 수신 | type=%s | session=%s | from=%s",
                msg_type,
                session_id,
                client_addr,
            )
            # 수신 데이터 전체를 DEBUG 레벨로 출력
            logger.debug(
                "◀ 수신 데이터 상세 | type=%s | session=%s |\n%s",
                msg_type,
                session_id,
                _pretty_json(message),
            )

            if msg_type == "ping":
                logger.debug("ping 수신 → pong 응답 | session=%s", session_id)
                try:
                    await send_message(websocket, {
                        "type": "pong",
                        "session_id": session_id,
                    })
                except Exception:
                    pass

            elif msg_type == "request":
                data = message.get("data", {})
                logger.info(
                    "분석 요청 접수 | session=%s | data_keys=%s",
                    session_id,
                    list(data.keys()) if isinstance(data, dict) else type(data).__name__,
                )
                asyncio.create_task(
                    handle_analysis_request(websocket, session_id, data)
                )

            else:
                logger.warning(
                    "알 수 없는 메시지 타입: %s | session=%s | message=\n%s",
                    msg_type,
                    session_id,
                    _pretty_json(message),
                )

    except ConnectionClosed as e:
        logger.info("백엔드 연결 종료: %s (code=%s)", client_addr, getattr(e, "rcvd", None))
    except Exception as e:
        logger.error("클라이언트 처리 오류: %s", e, exc_info=True)


async def main():
    """WebSocket 서버 시작"""
    logger.info("RegretPredictor 사전 로드 중...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_predictor)

    local_ips = get_local_ips()

    logger.info("=" * 60)
    logger.info("AI Agent WebSocket 서버 시작")
    logger.info("  바인딩 주소 : %s:%d", AGENT_HOST, AGENT_PORT)
    logger.info("  LLM 사용   : %s", USE_LLM)
    logger.info("  로그 레벨  : %s", _LOG_LEVEL)
    logger.info("  API        : websockets 13.x asyncio (websockets.asyncio.server.serve)")
    logger.info("  접속 가능 URL:")
    logger.info("    ws://127.0.0.1:%d  (로컬루프백)", AGENT_PORT)
    for ip in local_ips:
        logger.info("    ws://%s:%d  (실제 IP)", ip, AGENT_PORT)
    logger.info("  백엔드 연결 설정: AGENT_WS_URL=ws://agent:%d  (Docker)", AGENT_PORT)
    logger.info("  백엔드 연결 설정: AGENT_WS_URL=ws://localhost:%d  (로컬)", AGENT_PORT)
    logger.info("=" * 60)

    # websockets 13.x asyncio API 사용
    async with serve(
        handle_client,
        AGENT_HOST,
        AGENT_PORT,
        ping_interval=20,
        ping_timeout=10,
    ):
        logger.info(
            "서버 준비 완료 — ws://%s:%d 에서 백엔드 연결 대기 중...",
            AGENT_HOST,
            AGENT_PORT,
        )
        await asyncio.Future()  # 무한 대기


if __name__ == "__main__":
    asyncio.run(main())
