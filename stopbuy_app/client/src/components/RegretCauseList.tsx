/*
 * StopBuy - 후회 원인 목록 컴포넌트
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반 색상 처리
 */
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import type { RegretCause } from "@/hooks/useStopBuyWS";

interface RegretCauseListProps {
  causes: RegretCause[];
}

const SEVERITY_CONFIG = {
  high: {
    icon: AlertTriangle,
    colorVar: "var(--sb-red)",
    label: "높음",
  },
  medium: {
    icon: AlertCircle,
    colorVar: "var(--sb-amber)",
    label: "보통",
  },
  low: {
    icon: Info,
    colorVar: "var(--sb-green)",
    label: "낮음",
  },
};

export function RegretCauseList({ causes }: RegretCauseListProps) {
  const validCauses = causes.filter((c) => c.code !== "NO_MAJOR_RISK");

  if (validCauses.length === 0) {
    return (
      <div
        className="flex items-center gap-3 p-4 rounded-xl transition-colors duration-300"
        style={{
          background: "color-mix(in oklch, var(--sb-green) 8%, transparent)",
          border: "1px solid color-mix(in oklch, var(--sb-green) 25%, transparent)",
        }}
      >
        <Info size={20} style={{ color: "var(--sb-green)", flexShrink: 0 }} />
        <p className="text-sm" style={{ color: "var(--sb-text-secondary)" }}>
          현재 입력 기준으로는 뚜렷한 후회 위험 요인이 크지 않습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {validCauses.map((cause, idx) => {
        const config = SEVERITY_CONFIG[cause.severity] || SEVERITY_CONFIG.low;
        const Icon = config.icon;
        const impactPercent = Math.round(cause.impact_score * 100);
        const c = config.colorVar;

        return (
          <div
            key={cause.code}
            className="rounded-xl p-4 animate-slide-up transition-colors duration-300"
            style={{
              background: `color-mix(in oklch, ${c} 8%, transparent)`,
              border: `1px solid color-mix(in oklch, ${c} 25%, transparent)`,
              animationDelay: `${idx * 80}ms`,
              animationFillMode: "both",
            }}
          >
            <div className="flex items-start gap-3">
              <Icon size={18} style={{ color: c, flexShrink: 0, marginTop: 2 }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-sm font-semibold" style={{ color: c }}>
                    {cause.title}
                  </span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
                    style={{
                      background: `color-mix(in oklch, ${c} 15%, transparent)`,
                      color: c,
                      fontFamily: "'Space Grotesk', monospace",
                    }}
                  >
                    영향도 {impactPercent}%
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--sb-text-secondary)" }}>
                  {cause.message}
                </p>

                {/* 임팩트 바 */}
                <div
                  className="mt-2 h-1 rounded-full overflow-hidden transition-colors duration-300"
                  style={{ background: "var(--sb-input-border)" }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{
                      width: `${impactPercent}%`,
                      background: c,
                      boxShadow: `0 0 6px color-mix(in oklch, ${c} 50%, transparent)`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
