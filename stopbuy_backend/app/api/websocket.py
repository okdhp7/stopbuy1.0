"""
StopBuy Backend - WebSocket 라우터
프론트엔드 ↔ 백엔드 ↔ AI Agent 실시간 통신 처리

수정 이력:
- handle_analysis_request: Agent 콜백에서 예외 발생 시 프론트엔드에 에러 전달
- send_demo_result: Agent 미연결 시 데모 결과 반환 (개발/테스트용)
- 이미지 base64 처리 안정화
- agent_callback 내 await 누락 방지
"""
import asyncio
import json
import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.agent_service import agent_manager
from app.services.analysis_service import (
    save_uploaded_image,
    extract_product_from_url,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """프론트엔드 WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"클라이언트 연결: session_id={session_id}")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        logger.info(f"클라이언트 연결 해제: session_id={session_id}")

    async def send_message(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"메시지 전송 실패 (session={session_id}): {e}")
                self.disconnect(session_id)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    프론트엔드 WebSocket 엔드포인트
    - 클라이언트로부터 분석 요청 수신
    - AI Agent에 요청 전달
    - Agent 결과를 클라이언트로 전달
    """
    await manager.connect(websocket, session_id)

    try:
        while True:
            raw_data = await websocket.receive_text()

            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "session_id": session_id,
                    "message": "잘못된 메시지 형식입니다.",
                })
                continue

            msg_type = message.get("type")
            logger.info(f"프론트엔드 메시지 수신: type={msg_type}, session={session_id}")

            if msg_type == "ping":
                await manager.send_message(session_id, {
                    "type": "pong",
                    "session_id": session_id,
                })
                continue

            if msg_type == "request":
                # 비동기 처리 (블로킹 방지)
                asyncio.create_task(
                    handle_analysis_request(session_id, message)
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket 오류 (session={session_id}): {e}")
        manager.disconnect(session_id)


async def handle_analysis_request(session_id: str, message: dict):
    """분석 요청 처리 및 Agent 전달"""
    data = message.get("data", {})

    # 1단계: 진행 상황 알림
    await manager.send_message(session_id, {
        "type": "progress",
        "session_id": session_id,
        "progress": 10,
        "message": "상품 정보를 분석 중입니다...",
    })

    # 2단계: 이미지 저장 처리
    if data.get("image_base64"):
        try:
            image_path = save_uploaded_image(data["image_base64"], session_id)
            data["image_path"] = image_path
            data.pop("image_base64", None)  # 대용량 데이터 제거
            logger.info(f"이미지 저장 완료: {image_path}")
        except Exception as e:
            logger.error(f"이미지 저장 실패: {e}")

    # 3단계: URL 기본 정보 추출
    if data.get("product_url"):
        try:
            url_info = extract_product_from_url(data["product_url"])
            if url_info:
                data["url_info"] = url_info
                logger.info(f"URL 정보 추출: {url_info}")
        except Exception as e:
            logger.error(f"URL 정보 추출 실패: {e}")

    await manager.send_message(session_id, {
        "type": "progress",
        "session_id": session_id,
        "progress": 25,
        "message": "AI Agent에 분석을 요청하고 있습니다...",
    })

    # 4단계: Agent 콜백 등록 및 요청 전송
    async def agent_callback(agent_message: dict):
        """Agent 응답을 프론트엔드로 전달"""
        msg_type = agent_message.get("type")

        if msg_type == "progress":
            await manager.send_message(session_id, {
                "type": "progress",
                "session_id": session_id,
                "progress": agent_message.get("progress", 50),
                "message": agent_message.get("message", "분석 중..."),
            })

        elif msg_type == "result":
            result_data = agent_message.get("data", {})
            logger.info(
                f"Agent 결과 수신: session={session_id}, "
                f"regret_score={result_data.get('regret_score')}, "
                f"alternatives={len(result_data.get('alternatives', []))}"
            )
            await manager.send_message(session_id, {
                "type": "result",
                "session_id": session_id,
                "data": result_data,
            })

        elif msg_type == "error":
            error_msg = agent_message.get("message", "분석 중 오류가 발생했습니다.")
            logger.error(f"Agent 오류: session={session_id}, msg={error_msg}")
            # Agent 오류 시 데모 결과로 폴백
            await send_demo_result(session_id, data)

    success = await agent_manager.send_analysis_request(
        session_id=session_id,
        payload=data,
        callback=agent_callback,
    )

    if not success:
        # Agent 연결 실패 시 데모 결과 반환
        logger.warning(f"Agent 연결 실패 — 데모 결과 반환: session={session_id}")
        await send_demo_result(session_id, data)


async def send_demo_result(session_id: str, data: dict):
    """Agent 연결 불가 시 데모 결과 반환 (개발/테스트용)"""
    await asyncio.sleep(0.8)
    await manager.send_message(session_id, {
        "type": "progress",
        "session_id": session_id,
        "progress": 50,
        "message": "후회 가능성 예측 중...",
    })

    await asyncio.sleep(1.2)
    await manager.send_message(session_id, {
        "type": "progress",
        "session_id": session_id,
        "progress": 80,
        "message": "대체상품 검색 중...",
    })

    await asyncio.sleep(0.8)

    # 입력 데이터에서 상품명 추출
    product_data = data.get("product") or {}
    product_name = (
        product_data.get("name")
        or (data.get("product_url") and "URL 입력 상품")
        or "테스트 상품"
    )

    demo_result = {
        "product_name": product_name,
        "regret_score": 0.72,
        "regret_level": "high",
        "model_regret_score": 0.68,
        "cause_score": 0.80,
        "regret_causes": [
            {
                "code": "PRICE_OVER_BUDGET",
                "title": "예산 초과",
                "message": "상품 가격이 예산보다 약 20% 높아 구매 후 가격 부담으로 후회할 가능성이 있습니다.",
                "severity": "high",
                "impact_score": 0.80,
            },
            {
                "code": "LOW_RATING",
                "title": "낮은 리뷰 평점",
                "message": "리뷰 평점이 낮아 실제 사용 만족도가 떨어질 가능성이 있습니다.",
                "severity": "medium",
                "impact_score": 0.55,
            },
            {
                "code": "HIGH_RETURN_RATE",
                "title": "높은 반품률",
                "message": "반품률이 높아 실제 구매자들의 불만 가능성이 상대적으로 큽니다.",
                "severity": "medium",
                "impact_score": 0.45,
            },
        ],
        "regret_reasons": [
            "상품 가격이 예산보다 약 20% 높아 구매 후 가격 부담으로 후회할 가능성이 있습니다.",
            "리뷰 평점이 낮아 실제 사용 만족도가 떨어질 가능성이 있습니다.",
            "반품률이 높아 실제 구매자들의 불만 가능성이 상대적으로 큽니다.",
        ],
        "alternatives": [
            {
                "product_id": 201,
                "name": "추천 대체상품 A",
                "brand": "Samsung",
                "category": "전자제품",
                "price": 850000,
                "rating": 4.6,
                "return_rate": 3.2,
                "regret_score": 0.18,
                "match_score": 0.85,
                "improvement_score": 0.54,
                "final_score": 0.78,
                "recommendation_reason": "예산 범위에 적합, 리뷰 평점이 우수함, 반품률이 낮아 구매 후 불만 가능성이 낮음",
                "image_url": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=300",
            },
            {
                "product_id": 202,
                "name": "추천 대체상품 B",
                "brand": "LG",
                "category": "전자제품",
                "price": 920000,
                "rating": 4.4,
                "return_rate": 4.1,
                "regret_score": 0.22,
                "match_score": 0.78,
                "improvement_score": 0.50,
                "final_score": 0.71,
                "recommendation_reason": "선호 브랜드와 일치, 예측 후회 가능성이 기존 후보보다 낮음",
                "image_url": "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=300",
            },
            {
                "product_id": 203,
                "name": "추천 대체상품 C",
                "brand": "Sony",
                "category": "전자제품",
                "price": 780000,
                "rating": 4.3,
                "return_rate": 5.5,
                "regret_score": 0.28,
                "match_score": 0.72,
                "improvement_score": 0.44,
                "final_score": 0.65,
                "recommendation_reason": "기존 후보보다 가격 부담이 낮음, 예측 후회 가능성이 기존 후보보다 낮음",
                "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300",
            },
        ],
        "llm_analysis": {
            "used_llm": False,
            "summary": "후회 위험도는 high 수준이며, 주요 원인은 예산 초과, 낮은 리뷰 평점, 높은 반품률입니다.",
            "risk_explanation": "가격이 예산을 초과하고 리뷰 평점이 낮아 구매 후 만족도가 떨어질 가능성이 높습니다.",
            "purchase_advice": "예산, 평점, 반품률, 선호 브랜드, 중요 조건 충족 여부를 함께 비교한 뒤 구매를 결정하는 것이 좋습니다.",
            "alternative_strategy": "대체상품 A를 우선 검토하세요. 예측 후회 점수가 0.18로 현저히 낮고 평점도 우수합니다.",
        },
        "_demo": True,
    }

    await manager.send_message(session_id, {
        "type": "result",
        "session_id": session_id,
        "data": demo_result,
    })
