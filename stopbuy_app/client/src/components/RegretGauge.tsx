/*
 * StopBuy - 후회 게이지 컴포넌트
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반 색상 처리
 * 색상: high=red, medium=amber, low=green (테마 변수 사용)
 */
import { useEffect, useRef, useState } from "react";
import type { RegretLevel } from "@/hooks/useStopBuyWS";

interface RegretGaugeProps {
  score: number; // 0.0 ~ 1.0
  level: RegretLevel;
  size?: number;
  animated?: boolean;
}

// CSS 변수는 SVG 내부에서 직접 사용 불가 → JS로 해결
const LEVEL_CONFIG = {
  high:   { colorVar: "--sb-red",   label: "높음" },
  medium: { colorVar: "--sb-amber", label: "보통" },
  low:    { colorVar: "--sb-green", label: "낮음" },
};

function getCSSVar(name: string): string {
  if (typeof window === "undefined") return "#888";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function RegretGauge({ score, level, size = 200, animated = true }: RegretGaugeProps) {
  const [displayScore, setDisplayScore] = useState(0);
  const animFrameRef = useRef<number | null>(null);
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.medium;

  // 테마 변경 시 색상 재계산
  const [resolvedColor, setResolvedColor] = useState("#888");
  useEffect(() => {
    setResolvedColor(getCSSVar(config.colorVar));
  }, [config.colorVar, level]);

  const radius = (size / 2) * 0.75;
  const circumference = 2 * Math.PI * radius;
  const strokeWidth = size * 0.055;
  const center = size / 2;
  const arcLength = circumference * 0.75;
  const targetOffset = arcLength - arcLength * score;
  const [strokeDashoffset, setStrokeDashoffset] = useState(arcLength);
  const rotation = 135;

  useEffect(() => {
    if (!animated) {
      setStrokeDashoffset(targetOffset);
      setDisplayScore(Math.round(score * 100));
      return;
    }

    const duration = 1200;
    const startTime = performance.now();
    const startOffset = arcLength;
    const startScore = 0;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);

      setStrokeDashoffset(startOffset + (targetOffset - startOffset) * eased);
      setDisplayScore(Math.round((startScore + (score - startScore) * eased) * 100));

      if (progress < 1) {
        animFrameRef.current = requestAnimationFrame(animate);
      }
    };

    animFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [score, arcLength, targetOffset, animated]);

  const c = resolvedColor || "#888";

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <defs>
            <filter id={`glow-${level}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 트랙 (배경 원호) */}
          <circle
            cx={center} cy={center} r={radius}
            fill="none"
            stroke="currentColor"
            className="text-border"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform={`rotate(${rotation} ${center} ${center})`}
            style={{ opacity: 0.25 }}
          />

          {/* 진행 원호 */}
          <circle
            cx={center} cy={center} r={radius}
            fill="none"
            stroke={c}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform={`rotate(${rotation} ${center} ${center})`}
            filter={`url(#glow-${level})`}
            style={{ transition: "none" }}
          />

          {/* 내부 원 배경 */}
          <circle
            cx={center} cy={center} r={radius * 0.72}
            fill={c}
            fillOpacity={0.08}
          />
        </svg>

        {/* 중앙 텍스트 */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ fontFamily: "'Space Grotesk', monospace" }}
        >
          <span
            className="font-bold leading-none"
            style={{
              fontSize: size * 0.22,
              color: c,
              textShadow: `0 0 20px ${c}80`,
            }}
          >
            {displayScore}
          </span>
          <span
            className="font-medium mt-1"
            style={{ fontSize: size * 0.075, color: "var(--sb-text-muted)" }}
          >
            후회 점수
          </span>
        </div>
      </div>

      {/* 레벨 배지 */}
      <div
        className="px-4 py-1.5 rounded-full text-sm font-semibold border transition-colors duration-300"
        style={{
          color: c,
          background: `${c}14`,
          borderColor: `${c}40`,
          fontFamily: "'Space Grotesk', monospace",
          letterSpacing: "0.05em",
        }}
      >
        후회 가능성 {config.label}
      </div>
    </div>
  );
}
