/*
 * StopBuy - LLM 분석 결과 패널 컴포넌트
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반 색상 처리
 */
import { Sparkles, ShieldAlert, Lightbulb, ArrowRightLeft } from "lucide-react";
import type { LLMAnalysis } from "@/hooks/useStopBuyWS";

interface LLMAnalysisPanelProps {
  analysis: LLMAnalysis;
}

const SECTIONS = [
  {
    key: "summary" as keyof LLMAnalysis,
    icon: Sparkles,
    title: "종합 요약",
    colorVar: "var(--sb-amber)",
  },
  {
    key: "risk_explanation" as keyof LLMAnalysis,
    icon: ShieldAlert,
    title: "위험 설명",
    colorVar: "var(--sb-red)",
  },
  {
    key: "purchase_advice" as keyof LLMAnalysis,
    icon: Lightbulb,
    title: "구매 조언",
    colorVar: "var(--sb-blue-light)",
  },
  {
    key: "alternative_strategy" as keyof LLMAnalysis,
    icon: ArrowRightLeft,
    title: "대체상품 전략",
    colorVar: "var(--sb-green)",
  },
];

export function LLMAnalysisPanel({ analysis }: LLMAnalysisPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* AI 분석 헤더 */}
      <div className="flex items-center gap-2 mb-1">
        <Sparkles size={16} style={{ color: "var(--sb-amber)" }} />
        <span className="text-sm font-semibold" style={{ color: "var(--sb-text-primary)" }}>
          AI 분석 결과
        </span>
        {analysis.used_llm ? (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "color-mix(in oklch, var(--sb-amber) 12%, transparent)",
              color: "var(--sb-amber)",
              border: "1px solid color-mix(in oklch, var(--sb-amber) 30%, transparent)",
              fontFamily: "'Space Grotesk', monospace",
            }}
          >
            GPT 분석
          </span>
        ) : (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "var(--sb-badge-bg)",
              color: "var(--sb-text-muted)",
              border: "1px solid var(--sb-input-border)",
            }}
          >
            규칙 기반
          </span>
        )}
      </div>

      {SECTIONS.map((section, idx) => {
        const value = analysis[section.key];
        if (!value || typeof value !== "string") return null;
        const Icon = section.icon;
        const c = section.colorVar;

        return (
          <div
            key={section.key}
            className="rounded-xl p-4 animate-slide-up transition-colors duration-300"
            style={{
              background: `color-mix(in oklch, ${c} 6%, transparent)`,
              border: `1px solid color-mix(in oklch, ${c} 20%, transparent)`,
              animationDelay: `${idx * 60}ms`,
              animationFillMode: "both",
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon size={14} style={{ color: c }} />
              <span
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: c }}
              >
                {section.title}
              </span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: "var(--sb-text-secondary)" }}>
              {value}
            </p>
          </div>
        );
      })}
    </div>
  );
}
