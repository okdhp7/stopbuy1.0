/*
 * StopBuy - 분석 진행 상태 컴포넌트
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반 색상 처리
 */
import { Brain, Search, Sparkles, CheckCircle2 } from "lucide-react";

interface AnalysisProgressProps {
  progress: number;
  message: string;
}

const STEPS = [
  { icon: Search,        label: "상품 정보 수집",   threshold: 25 },
  { icon: Brain,         label: "후회 가능성 예측", threshold: 60 },
  { icon: Sparkles,      label: "대체상품 검색",    threshold: 85 },
  { icon: CheckCircle2,  label: "결과 정리",        threshold: 100 },
];

export function AnalysisProgress({ progress, message }: AnalysisProgressProps) {
  return (
    <div className="flex flex-col items-center gap-8 py-8 px-4">
      {/* 메인 진행 바 */}
      <div className="w-full max-w-md">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm" style={{ color: "var(--sb-text-secondary)" }}>{message}</span>
          <span
            className="text-sm font-semibold"
            style={{ fontFamily: "'Space Grotesk', monospace", color: "var(--sb-blue-light)" }}
          >
            {progress}%
          </span>
        </div>
        <div
          className="h-2 rounded-full overflow-hidden transition-colors duration-300"
          style={{ background: "var(--sb-input-border)" }}
        >
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg, var(--sb-blue), var(--sb-blue-dark))",
              boxShadow: "0 0 12px color-mix(in oklch, var(--sb-blue) 50%, transparent)",
            }}
          />
        </div>
      </div>

      {/* 단계 표시 */}
      <div className="flex gap-6 flex-wrap justify-center">
        {STEPS.map((step, idx) => {
          const isCompleted = progress >= step.threshold;
          const isActive =
            progress >= (STEPS[idx - 1]?.threshold ?? 0) && progress < step.threshold;

          return (
            <div
              key={step.label}
              className="flex flex-col items-center gap-2"
              style={{ opacity: isCompleted || isActive ? 1 : 0.3 }}
            >
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300"
                style={{
                  background: isCompleted
                    ? "color-mix(in oklch, var(--sb-green) 15%, transparent)"
                    : isActive
                    ? "color-mix(in oklch, var(--sb-blue) 15%, transparent)"
                    : "var(--sb-input-bg)",
                  border: `1px solid ${
                    isCompleted
                      ? "color-mix(in oklch, var(--sb-green) 40%, transparent)"
                      : isActive
                      ? "color-mix(in oklch, var(--sb-blue) 40%, transparent)"
                      : "var(--sb-input-border)"
                  }`,
                  boxShadow: isActive
                    ? "0 0 12px color-mix(in oklch, var(--sb-blue) 30%, transparent)"
                    : "none",
                }}
              >
                <step.icon
                  size={18}
                  style={{
                    color: isCompleted
                      ? "var(--sb-green)"
                      : isActive
                      ? "var(--sb-blue-light)"
                      : "var(--sb-text-dim)",
                    animation: isActive ? "sb-pulse 1.5s ease-in-out infinite" : "none",
                  }}
                />
              </div>
              <span
                className="text-xs text-center"
                style={{
                  color: isCompleted
                    ? "var(--sb-green)"
                    : isActive
                    ? "var(--sb-blue-light)"
                    : "var(--sb-text-dim)",
                }}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* 분석 중 텍스트 */}
      <div className="text-center">
        <p className="text-sm" style={{ color: "var(--sb-text-secondary)" }}>
          AI가 구매 후회 가능성을 분석하고 있습니다
        </p>
        <div className="flex justify-center gap-1 mt-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background: "var(--sb-blue-light)",
                animation: `sb-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes sb-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
        @keyframes sb-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
