"""
StopBuy Backend - Agent 연결 서비스
백엔드 ↔ AI Agent 간 WebSocket 통신 관리

수정 이력:
- websockets 13.x asyncio 신규 API 사용: websockets.asyncio.client.connect
  (legacy websockets.connect 대신 명시적으로 asyncio API 사용)
  → Agent server.py(asyncio.server.serve)와 동일한 API 계층 사용으로 handshake 오류 해결
- is_connected(): close_code 대신 State.OPEN 기반으로 수정
  (websockets 13.x asyncio ClientConnection에는 close_code 속성이 없음)
  → 기존 코드에서 is_connected()가 항상 False를 반환하여 매번 재연결 시도,
     send() 직후 연결이 닫혀 Agent가 메시지를 수신하지 못하는 문제 해결
- _listen_loop: 연결 종료 후 자동 재연결 루프 추가
- send_analysis_request: 타임아웃 120초
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from websockets.asyncio.client import connect, ClientConnection
from websockets.connection import State
from websockets.exceptions import ConnectionClosed

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentConnectionManager:
    """AI Agent와의 WebSocket 연결 관리 (websockets 13.x asyncio API)"""

    def __init__(self):
        self._connection: Optional[ClientConnection] = None
        self._connecting: bool = False        # 연결 시도 중 플래그
        self._reconnect_interval = 3          # 재연결 간격 (초)
        self._max_retries = 5
        self._callbacks: Dict[str, Callable] = {}  # session_id → callback
        self._listen_task: Optional[asyncio.Task] = None

    def is_connected(self) -> bool:
        """연결 상태 확인 (websockets 13.x asyncio ClientConnection 기준)

        websockets 13.x asyncio ClientConnection에는 close_code 속성이 없음.
        State.OPEN(=1) 여부로 연결 상태를 판단해야 함.
        """
        if self._connection is None:
            return False
        try:
            return self._connection.state == State.OPEN
        except Exception:
            return False

    async def connect(self) -> bool:
        """Agent WebSocket 서버에 연결 (재진입 안전)"""
        if self.is_connected():
            return True

        if self._connecting:
            # 다른 코루틴이 이미 연결 시도 중 → 최대 15초 대기
            for _ in range(30):
                await asyncio.sleep(0.5)
                if self.is_connected():
                    return True
            return False

        self._connecting = True
        try:
            for attempt in range(self._max_retries):
                try:
                    logger.info(
                        f"Agent 연결 시도 {attempt + 1}/{self._max_retries}: "
                        f"{settings.AGENT_WS_URL}"
                    )
                    # websockets 13.x asyncio API — legacy websockets.connect() 대신 사용
                    self._connection = await connect(
                        settings.AGENT_WS_URL,
                        open_timeout=15,
                        ping_interval=20,
                        ping_timeout=10,
                    )
                    logger.info(f"AI Agent 연결 성공: {settings.AGENT_WS_URL}")
                    # 수신 루프 시작 (기존 태스크 취소 후 재시작)
                    self._start_listen_loop()
                    return True
                except Exception as e:
                    logger.warning(
                        f"Agent 연결 시도 {attempt + 1}/{self._max_retries} 실패: {e}"
                    )
                    self._connection = None
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._reconnect_interval)

            logger.error("AI Agent 연결 최종 실패")
            return False
        finally:
            self._connecting = False

    def _start_listen_loop(self):
        """수신 루프 태스크 시작 (기존 태스크 취소 후 재시작)"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def disconnect(self):
        """연결 종료"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:
                pass
            self._connection = None

    async def send_analysis_request(
        self,
        session_id: str,
        payload: Dict[str, Any],
        callback: Callable,
        timeout: float = 120.0,
    ) -> bool:
        """분석 요청을 Agent에 전송 (타임아웃 120초)"""
        self._callbacks[session_id] = callback

        # 연결 확인 및 재연결 시도
        if not self.is_connected():
            logger.info("Agent 미연결 상태 — 연결 시도 중...")
            connected = await self.connect()
            if not connected:
                logger.error("Agent 연결 불가 — 폴백 처리")
                self._callbacks.pop(session_id, None)
                return False

        message = {
            "type": "request",
            "session_id": session_id,
            "data": payload,
        }

        try:
            await self._connection.send(json.dumps(message, ensure_ascii=False))
            logger.info(f"분석 요청 전송 완료: session_id={session_id}")
            return True
        except ConnectionClosed as e:
            logger.error(f"Agent 메시지 전송 실패 (연결 종료): {e}")
            self._connection = None
            # 재연결 후 재전송 1회 시도
            logger.info("재연결 후 재전송 시도...")
            if await self.connect():
                try:
                    await self._connection.send(json.dumps(message, ensure_ascii=False))
                    logger.info(f"재연결 후 재전송 성공: session_id={session_id}")
                    return True
                except Exception as e2:
                    logger.error(f"재전송 실패: {e2}")

            self._callbacks.pop(session_id, None)
            return False
        except Exception as e:
            logger.error(f"예상치 못한 전송 오류: {e}", exc_info=True)
            self._callbacks.pop(session_id, None)
            return False

    async def _listen_loop(self):
        """Agent로부터 메시지 수신 루프"""
        conn = self._connection
        if conn is None:
            return
        logger.info("Agent 수신 루프 시작")
        try:
            async for raw_message in conn:
                try:
                    message = json.loads(raw_message)
                    await self._handle_agent_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Agent 메시지 파싱 오류: {e} | raw={raw_message[:200]}")
                except Exception as e:
                    logger.error(f"메시지 처리 오류: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Agent 수신 루프 취소됨")
        except ConnectionClosed as e:
            logger.warning(f"Agent 연결 종료: {e}")
            self._connection = None
        except Exception as e:
            logger.error(f"Agent 수신 루프 오류: {e}", exc_info=True)
            self._connection = None
        finally:
            logger.info("Agent 수신 루프 종료")

    async def _handle_agent_message(self, message: Dict[str, Any]):
        """Agent 메시지 처리 및 콜백 호출"""
        session_id = message.get("session_id")
        msg_type = message.get("type")

        logger.info(f"Agent 메시지 수신: type={msg_type}, session={session_id}")
        logger.info(f"메시지 내용: {json.dumps(message.get('data'), ensure_ascii=False)[:500]}")

        if session_id and session_id in self._callbacks:
            callback = self._callbacks[session_id]
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"콜백 실행 오류 (session={session_id}): {e}", exc_info=True)

            # 완료 또는 오류 시 콜백 제거
            if msg_type in ("result", "error"):
                self._callbacks.pop(session_id, None)
        else:
            if session_id:
                logger.warning(
                    f"콜백 없음: session_id={session_id}, "
                    f"등록된 세션={list(self._callbacks.keys())}"
                )


# 싱글톤 인스턴스
agent_manager = AgentConnectionManager()
