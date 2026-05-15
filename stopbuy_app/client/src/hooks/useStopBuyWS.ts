/**
 * StopBuy - WebSocket 훅
 * Design: Analytical Dark — 실시간 분석 상태 관리
 * 백엔드 FastAPI WebSocket과 연결하여 분석 요청/결과 처리
 * 백엔드 미연결 시 데모 모드로 동작
 *
 * 수정 이력:
 * - 연결 타임아웃 3초 → 12초로 증가 (Agent 초기화 시간 고려)
 * - 재연결 로직 강화: 연결 실패 시 최대 2회 재시도
 * - 메시지 전송 전 연결 상태 재확인
 */
import { useCallback, useEffect, useRef, useState } from "react";

export type RegretLevel = "low" | "medium" | "high";
export type AnalysisStatus = "idle" | "connecting" | "analyzing" | "completed" | "error";

export interface RegretCause {
  code: string;
  title: string;
  message: string;
  severity: "low" | "medium" | "high";
  impact_score: number;
}

export interface AlternativeProduct {
  product_id?: number;
  name?: string;
  brand?: string;
  category?: string;
  price?: number;
  rating?: number;
  return_rate?: number;
  regret_score?: number;
  match_score?: number;
  improvement_score?: number;
  final_score?: number;
  recommendation_reason?: string;
  image_url?: string;
}

export interface LLMAnalysis {
  used_llm: boolean;
  summary?: string;
  risk_explanation?: string;
  purchase_advice?: string;
  alternative_strategy?: string;
}

export interface AnalysisResult {
  product_name?: string;
  regret_score?: number;
  regret_level?: RegretLevel;
  model_regret_score?: number;
  cause_score?: number;
  regret_causes?: RegretCause[];
  regret_reasons?: string[];
  alternatives?: AlternativeProduct[];
  llm_analysis?: LLMAnalysis;
  _demo?: boolean;
}

export interface UserProfile {
  budget?: number;
  preferred_brands?: string[];
  important_factors?: string[];
  usage_purpose?: string;
}

export interface ProductInfo {
  name?: string;
  brand?: string;
  category?: string;
  price?: number;
  rating?: number;
  review_count?: number;
  return_rate?: number;
  days_since_release?: number;
  description?: string;
}

interface UseStopBuyWSOptions {
  backendUrl?: string;
}

interface UseStopBuyWSReturn {
  status: AnalysisStatus;
  progress: number;
  progressMessage: string;
  result: AnalysisResult | null;
  error: string | null;
  sessionId: string;
  isConnected: boolean;
  analyze: (params: {
    inputType: "url" | "image" | "manual";
    productUrl?: string;
    imageBase64?: string;
    user?: UserProfile;
    product?: ProductInfo;
  }) => void;
  reset: () => void;
}

function generateSessionId(): string {
  return Math.random().toString(36).substring(2, 18);
}

function getBackendWsUrl(): string {
  // 환경변수로 명시적 지정 시 우선 사용
  const envUrl = import.meta.env.VITE_BACKEND_WS_URL;
  if (envUrl) return envUrl;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

  // 항상 상대 경로 /ws 사용:
  // - 개발 서버(port 3000/5173): Vite proxy가 ws://localhost:8000으로 전달
  // - Docker/프로덕션: Nginx가 http://backend:8000으로 전달
  // 직접 포트 지정 시 CORS 및 프록시 우회 문제 발생하므로 사용하지 않음
  return `${protocol}//${window.location.host}/ws`;
}

// ─── 데모 모드: 백엔드 미연결 시 사용 ───────────────────────────────────
function generateDemoResult(params: {
  inputType: string;
  productUrl?: string;
  product?: ProductInfo;
}): AnalysisResult {
  const name =
    params.product?.name ||
    (params.productUrl ? "URL 입력 상품" : "이미지 입력 상품");
  const price = params.product?.price ?? 150000;
  const rating = params.product?.rating ?? 3.5;
  const returnRate = params.product?.return_rate ?? 15;

  let score = 0.45;
  if (rating < 3.5) score += 0.15;
  if (returnRate > 10) score += 0.12;
  if (price > 500000) score += 0.08;
  score = Math.min(0.95, Math.max(0.05, score + (Math.random() - 0.5) * 0.1));

  const level: RegretLevel = score >= 0.65 ? "high" : score >= 0.4 ? "medium" : "low";

  const causes: RegretCause[] = [];
  if (returnRate > 10) {
    causes.push({
      code: "HIGH_RETURN_RATE",
      title: "높은 반품률",
      message: `반품률 ${returnRate}%는 동일 카테고리 평균보다 높습니다. 실제 구매 후 불만족 가능성이 있습니다.`,
      severity: "high",
      impact_score: 0.35,
    });
  }
  if (rating < 3.5) {
    causes.push({
      code: "LOW_RATING",
      title: "낮은 평점",
      message: `평점 ${rating}점은 기준치(3.5점)보다 낮습니다. 품질 또는 기대치 불일치 가능성이 있습니다.`,
      severity: "medium",
      impact_score: 0.28,
    });
  }
  if (price > 500000) {
    causes.push({
      code: "HIGH_PRICE_RISK",
      title: "고가 구매 위험",
      message: `${price.toLocaleString()}원의 고가 상품입니다. 충분한 비교 검토 후 구매를 권장합니다.`,
      severity: "medium",
      impact_score: 0.22,
    });
  }
  if (causes.length === 0) {
    causes.push({
      code: "NO_MAJOR_RISK",
      title: "뚜렷한 위험 없음",
      message: "현재 입력 기준으로는 주요 후회 위험 요인이 크지 않습니다.",
      severity: "low",
      impact_score: 0.05,
    });
  }

  const alternatives: AlternativeProduct[] =
    level !== "low"
      ? [
          {
            product_id: 1,
            name: "갤럭시 S24 FE",
            brand: "Samsung",
            category: params.product?.category || "스마트폰",
            price: 699000,
            rating: 4.3,
            return_rate: 3.2,
            regret_score: 0.22,
            recommendation_reason: "높은 평점과 낮은 반품률로 만족도가 검증된 상품입니다.",
          },
          {
            product_id: 2,
            name: "아이폰 15",
            brand: "Apple",
            category: params.product?.category || "스마트폰",
            price: 1250000,
            rating: 4.6,
            return_rate: 2.1,
            regret_score: 0.15,
            recommendation_reason: "업계 최고 수준의 사용자 만족도를 보유한 프리미엄 선택지입니다.",
          },
          {
            product_id: 3,
            name: "픽셀 8a",
            brand: "Google",
            category: params.product?.category || "스마트폰",
            price: 649000,
            rating: 4.4,
            return_rate: 2.8,
            regret_score: 0.19,
            recommendation_reason: "합리적인 가격에 순수 안드로이드 경험을 제공합니다.",
          },
        ]
      : [];

  return {
    product_name: name,
    regret_score: score,
    regret_level: level,
    model_regret_score: score * 0.9,
    cause_score: score * 0.8,
    regret_causes: causes,
    alternatives,
    llm_analysis: {
      used_llm: false,
      summary: `${name}의 구매 후회 가능성은 ${Math.round(score * 100)}점으로 평가됩니다. ${level === "high" ? "신중한 검토가 필요합니다." : level === "medium" ? "몇 가지 주의사항이 있습니다." : "비교적 안전한 구매입니다."}`,
      risk_explanation:
        causes
          .filter((c) => c.code !== "NO_MAJOR_RISK")
          .map((c) => c.message)
          .join(" ") || "현재 입력 기준으로는 주요 위험 요인이 없습니다.",
      purchase_advice:
        level === "high"
          ? "구매를 잠시 보류하고 대체상품을 검토해보세요. 특히 반품률과 평점을 중심으로 비교해보시길 권장합니다."
          : level === "medium"
          ? "구매 전 리뷰를 충분히 확인하고, 반품/교환 정책을 미리 파악해두세요."
          : "현재 조건에서는 구매를 진행해도 좋습니다. 단, 개인 사용 목적에 맞는지 최종 확인하세요.",
      alternative_strategy:
        alternatives.length > 0
          ? `${alternatives.length}개의 대체상품을 확인해보세요. 특히 ${alternatives[0]?.name}은 후회 점수가 ${Math.round((alternatives[0]?.regret_score ?? 0) * 100)}점으로 현재 상품보다 낮습니다.`
          : "현재 상품이 해당 카테고리에서 좋은 선택입니다.",
    },
    _demo: true,
  };
}

// ─── 메인 훅 ─────────────────────────────────────────────────────────────
export function useStopBuyWS(options: UseStopBuyWSOptions = {}): UseStopBuyWSReturn {
  const [status, setStatus] = useState<AnalysisStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId] = useState(() => generateSessionId());

  const wsRef = useRef<WebSocket | null>(null);
  const pendingRequestRef = useRef<{ type: string; session_id: string; data: object } | null>(null);
  const demoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);

  const backendWsUrl = options.backendUrl || getBackendWsUrl();
  const wsUrl = `${backendWsUrl}/${sessionId}`;

  const handleMessage = useCallback((message: {
    type: string;
    data?: AnalysisResult;
    progress?: number;
    message?: string;
    error?: string;
  }) => {
    const { type } = message;
    if (type === "progress") {
      setProgress(message.progress || 0);
      setProgressMessage(message.message || "분석 중...");
    } else if (type === "result") {
      setResult(message.data || null);
      setProgress(100);
      setProgressMessage("분석 완료!");
      setStatus("completed");
    } else if (type === "error") {
      setError(message.message || "알 수 없는 오류가 발생했습니다.");
      setStatus("error");
    }
  }, []);

  const runDemoMode = useCallback(
    (params: {
      inputType: "url" | "image" | "manual";
      productUrl?: string;
      imageBase64?: string;
      user?: UserProfile;
      product?: ProductInfo;
    }) => {
      const steps = [
        { progress: 15, message: "상품 정보 수집 중...", delay: 400 },
        { progress: 35, message: "후회 패턴 분석 중...", delay: 900 },
        { progress: 60, message: "머신러닝 모델 예측 중...", delay: 1600 },
        { progress: 80, message: "대체상품 검색 중...", delay: 2400 },
        { progress: 95, message: "결과 정리 중...", delay: 3000 },
      ];

      steps.forEach(({ progress, message, delay }) => {
        demoTimerRef.current = setTimeout(() => {
          setProgress(progress);
          setProgressMessage(message);
        }, delay);
      });

      demoTimerRef.current = setTimeout(() => {
        const demoResult = generateDemoResult(params);
        setResult(demoResult);
        setProgress(100);
        setProgressMessage("분석 완료! (데모 모드)");
        setStatus("completed");
      }, 3600);
    },
    []
  );

  const fallbackToDemo = useCallback(
    (pending: { type: string; session_id: string; data: object }) => {
      const data = pending.data as {
        input_type: "url" | "image" | "manual";
        product_url?: string;
        image_base64?: string;
        user?: UserProfile;
        product?: ProductInfo;
      };
      setStatus("analyzing");
      runDemoMode({
        inputType: data.input_type,
        productUrl: data.product_url,
        imageBase64: data.image_base64,
        user: data.user,
        product: data.product,
      });
    },
    [runDemoMode]
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // 타임아웃 12초 (Agent 초기화 시간 고려)
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          wsRef.current = null;
          // 재시도 또는 데모 모드 전환
          if (pendingRequestRef.current) {
            if (retryCountRef.current < 2) {
              retryCountRef.current += 1;
              setTimeout(() => connect(), 2000);
            } else {
              const pending = pendingRequestRef.current;
              pendingRequestRef.current = null;
              retryCountRef.current = 0;
              fallbackToDemo(pending);
            }
          }
        }
      }, 12000);

      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        setIsConnected(true);
        retryCountRef.current = 0;
        setStatus("analyzing");
        if (pendingRequestRef.current) {
          ws.send(JSON.stringify(pendingRequestRef.current));
          pendingRequestRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleMessage(message);
        } catch (e) {
          console.error("WebSocket 메시지 파싱 오류:", e);
        }
      };

      ws.onclose = () => {
        clearTimeout(connectionTimeout);
        setIsConnected(false);
        wsRef.current = null;
      };

      ws.onerror = (err) => {
        clearTimeout(connectionTimeout);
        console.error("WebSocket 연결 오류:", err);
        setIsConnected(false);
        wsRef.current = null;
        if (pendingRequestRef.current) {
          if (retryCountRef.current < 2) {
            retryCountRef.current += 1;
            setTimeout(() => connect(), 2000);
          } else {
            const pending = pendingRequestRef.current;
            pendingRequestRef.current = null;
            retryCountRef.current = 0;
            fallbackToDemo(pending);
          }
        }
      };
    } catch (err) {
      console.error("WebSocket 생성 실패:", err);
      if (pendingRequestRef.current) {
        const pending = pendingRequestRef.current;
        pendingRequestRef.current = null;
        retryCountRef.current = 0;
        fallbackToDemo(pending);
      }
    }
  }, [wsUrl, handleMessage, fallbackToDemo]);

  const analyze = useCallback(
    (params: {
      inputType: "url" | "image" | "manual";
      productUrl?: string;
      imageBase64?: string;
      user?: UserProfile;
      product?: ProductInfo;
    }) => {
      setStatus("connecting");
      setProgress(5);
      setProgressMessage("서버에 연결 중...");
      setResult(null);
      setError(null);
      retryCountRef.current = 0;

      const requestMessage = {
        type: "request",
        session_id: sessionId,
        data: {
          input_type: params.inputType,
          product_url: params.productUrl,
          image_base64: params.imageBase64,
          user: params.user || {},
          product: params.product || null,
        },
      };

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(requestMessage));
        setStatus("analyzing");
        setProgress(10);
        setProgressMessage("분석 요청 전송 완료...");
      } else {
        pendingRequestRef.current = requestMessage;
        connect();
      }
    },
    [sessionId, connect]
  );

  const reset = useCallback(() => {
    if (demoTimerRef.current) clearTimeout(demoTimerRef.current);
    setStatus("idle");
    setProgress(0);
    setProgressMessage("");
    setResult(null);
    setError(null);
    retryCountRef.current = 0;
  }, []);

  useEffect(() => {
    return () => {
      if (demoTimerRef.current) clearTimeout(demoTimerRef.current);
      wsRef.current?.close();
    };
  }, []);

  return {
    status,
    progress,
    progressMessage,
    result,
    error,
    sessionId,
    isConnected,
    analyze,
    reset,
  };
}
