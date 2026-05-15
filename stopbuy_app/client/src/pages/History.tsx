/**
 * StopBuy - 분석 이력 페이지
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반
 * Layout: 헤더 + 이력 목록 카드 그리드 + 상세 모달
 */
import { useState, useEffect, useCallback } from "react";
import { Link } from "wouter";
import {
  ShoppingCart, ArrowLeft, RefreshCw, Clock, TrendingUp,
  TrendingDown, AlertTriangle, CheckCircle, XCircle,
  ChevronRight, Sun, Moon, BarChart2, Package, Search
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/contexts/ThemeContext";

// ── 타입 정의 ──────────────────────────────────────────────────────────────
interface HistoryItem {
  id: number;
  session_id: string;
  input_type: "url" | "image" | "manual";
  product_name: string | null;
  regret_score: number | null;
  regret_level: "low" | "medium" | "high" | null;
  status: "pending" | "analyzing" | "completed" | "failed";
  created_at: string;
}

interface HistoryDetail {
  id: number;
  session_id: string;
  input_type: string;
  product_url: string | null;
  product_name: string | null;
  product_brand: string | null;
  product_category: string | null;
  product_price: number | null;
  product_rating: number | null;
  regret_score: number | null;
  regret_level: string | null;
  regret_causes: string[] | null;
  regret_reasons: string[] | null;
  alternatives: Array<{
    name: string;
    brand: string;
    price: number;
    rating: number;
    reason: string;
    match_score: number;
  }> | null;
  llm_analysis: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

// ── 유틸 함수 ──────────────────────────────────────────────────────────────
function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function getRegretColor(level: string | null) {
  if (level === "high") return "var(--sb-red)";
  if (level === "medium") return "var(--sb-amber)";
  return "var(--sb-green)";
}

function getRegretLabel(level: string | null) {
  if (level === "high") return "후회 가능성 높음";
  if (level === "medium") return "후회 가능성 중간";
  if (level === "low") return "후회 가능성 낮음";
  return "분석 중";
}

function getInputTypeLabel(type: string) {
  if (type === "url") return "URL";
  if (type === "image") return "이미지";
  return "직접 입력";
}

function getStatusIcon(status: string) {
  if (status === "completed") return <CheckCircle size={14} style={{ color: "var(--sb-green)" }} />;
  if (status === "failed") return <XCircle size={14} style={{ color: "var(--sb-red)" }} />;
  if (status === "analyzing") return <RefreshCw size={14} className="animate-spin" style={{ color: "var(--sb-blue)" }} />;
  return <Clock size={14} style={{ color: "var(--sb-text-dim)" }} />;
}

// ── 상세 모달 컴포넌트 ──────────────────────────────────────────────────────
function DetailModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await fetch(`/api/history/${sessionId}`);
        if (!res.ok) throw new Error("상세 정보를 불러올 수 없습니다.");
        const data = await res.json();
        setDetail(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [sessionId]);

  const regretPct = detail?.regret_score != null ? Math.round(detail.regret_score * 100) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl"
        style={{ background: "var(--sb-card-bg)", border: "1px solid var(--sb-border)" }}
        onClick={e => e.stopPropagation()}
      >
        {/* 모달 헤더 */}
        <div
          className="sticky top-0 flex items-center justify-between px-6 py-4 rounded-t-2xl"
          style={{ background: "var(--sb-card-bg)", borderBottom: "1px solid var(--sb-border)" }}
        >
          <h2 className="font-bold text-lg" style={{ color: "var(--sb-text-primary)" }}>
            분석 상세 결과
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
            style={{ color: "var(--sb-text-muted)", background: "var(--sb-input-bg)" }}
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-5">
          {loading && (
            <div className="flex flex-col items-center py-12 gap-3">
              <RefreshCw size={28} className="animate-spin" style={{ color: "var(--sb-blue)" }} />
              <p style={{ color: "var(--sb-text-muted)" }}>불러오는 중...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center py-12 gap-3">
              <AlertTriangle size={28} style={{ color: "var(--sb-red)" }} />
              <p style={{ color: "var(--sb-red)" }}>{error}</p>
            </div>
          )}

          {detail && !loading && (
            <>
              {/* 상품 정보 */}
              <div
                className="rounded-xl p-4 space-y-2"
                style={{ background: "var(--sb-input-bg)", border: "1px solid var(--sb-border)" }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-base" style={{ color: "var(--sb-text-primary)" }}>
                      {detail.product_name || "상품명 미확인"}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      {detail.product_brand && (
                        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--sb-blue-dim)", color: "var(--sb-blue)" }}>
                          {detail.product_brand}
                        </span>
                      )}
                      {detail.product_category && (
                        <span className="text-xs" style={{ color: "var(--sb-text-muted)" }}>
                          {detail.product_category}
                        </span>
                      )}
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--sb-border)", color: "var(--sb-text-dim)" }}>
                        {getInputTypeLabel(detail.input_type)}
                      </span>
                    </div>
                  </div>
                  {detail.product_price != null && (
                    <div className="text-right shrink-0">
                      <div className="font-bold text-lg" style={{ color: "var(--sb-text-primary)" }}>
                        {detail.product_price.toLocaleString()}원
                      </div>
                      {detail.product_rating != null && (
                        <div className="text-xs" style={{ color: "var(--sb-amber)" }}>
                          ★ {detail.product_rating.toFixed(1)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {detail.product_url && (
                  <a
                    href={detail.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs truncate block"
                    style={{ color: "var(--sb-blue)" }}
                  >
                    {detail.product_url}
                  </a>
                )}
              </div>

              {/* 후회 점수 */}
              {regretPct != null && (
                <div
                  className="rounded-xl p-4"
                  style={{ background: "var(--sb-input-bg)", border: "1px solid var(--sb-border)" }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium" style={{ color: "var(--sb-text-secondary)" }}>
                      후회 예측 점수
                    </span>
                    <span className="font-bold text-2xl" style={{ color: getRegretColor(detail.regret_level), fontFamily: "'Space Grotesk', monospace" }}>
                      {regretPct}%
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "var(--sb-border)" }}>
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${regretPct}%`, background: getRegretColor(detail.regret_level) }}
                    />
                  </div>
                  <div className="mt-2 text-xs font-medium" style={{ color: getRegretColor(detail.regret_level) }}>
                    {getRegretLabel(detail.regret_level)}
                  </div>
                </div>
              )}

              {/* 후회 원인 */}
              {detail.regret_reasons && detail.regret_reasons.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-2" style={{ color: "var(--sb-text-secondary)" }}>
                    후회 예측 원인
                  </h4>
                  <ul className="space-y-1.5">
                    {detail.regret_reasons.map((reason, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm" style={{ color: "var(--sb-text-muted)" }}>
                        <span className="mt-0.5 shrink-0" style={{ color: "var(--sb-amber)" }}>▸</span>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 대체상품 */}
              {detail.alternatives && detail.alternatives.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-2" style={{ color: "var(--sb-text-secondary)" }}>
                    추천 대체상품 ({detail.alternatives.length}개)
                  </h4>
                  <div className="space-y-2">
                    {detail.alternatives.slice(0, 3).map((alt, i) => (
                      <div
                        key={i}
                        className="rounded-lg p-3 flex items-start justify-between gap-3"
                        style={{ background: "var(--sb-input-bg)", border: "1px solid var(--sb-border)" }}
                      >
                        <div className="min-w-0">
                          <div className="font-medium text-sm truncate" style={{ color: "var(--sb-text-primary)" }}>
                            {alt.name}
                          </div>
                          <div className="text-xs mt-0.5" style={{ color: "var(--sb-text-muted)" }}>
                            {alt.brand} · ★ {alt.rating?.toFixed(1)}
                          </div>
                          <div className="text-xs mt-1" style={{ color: "var(--sb-text-dim)" }}>
                            {alt.reason}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="font-bold text-sm" style={{ color: "var(--sb-blue)" }}>
                            {alt.price?.toLocaleString()}원
                          </div>
                          <div className="text-xs mt-0.5" style={{ color: "var(--sb-green)" }}>
                            {Math.round((alt.match_score || 0) * 100)}% 매칭
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI 분석 */}
              {detail.llm_analysis && (
                <div>
                  <h4 className="text-sm font-semibold mb-2" style={{ color: "var(--sb-text-secondary)" }}>
                    AI 심층 분석
                  </h4>
                  <div
                    className="rounded-xl p-4 text-sm leading-relaxed"
                    style={{ background: "var(--sb-input-bg)", border: "1px solid var(--sb-border)", color: "var(--sb-text-muted)" }}
                  >
                    {detail.llm_analysis}
                  </div>
                </div>
              )}

              {/* 오류 메시지 */}
              {detail.error_message && (
                <div
                  className="rounded-xl p-4 text-sm"
                  style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--sb-red)" }}
                >
                  {detail.error_message}
                </div>
              )}

              <div className="text-xs text-right" style={{ color: "var(--sb-text-dim)" }}>
                분석 일시: {formatDate(detail.created_at)}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 메인 이력 페이지 ──────────────────────────────────────────────────────
export default function History() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLevel, setFilterLevel] = useState<"all" | "high" | "medium" | "low">("all");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/history?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`);
      if (!res.ok) throw new Error("이력을 불러올 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.");
      const data: HistoryItem[] = await res.json();
      setItems(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const filtered = items.filter(item => {
    const matchSearch = !searchQuery ||
      (item.product_name?.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchLevel = filterLevel === "all" || item.regret_level === filterLevel;
    return matchSearch && matchLevel;
  });

  // 통계
  const completedItems = items.filter(i => i.status === "completed");
  const avgScore = completedItems.length > 0
    ? completedItems.reduce((s, i) => s + (i.regret_score ?? 0), 0) / completedItems.length
    : 0;
  const highRiskCount = completedItems.filter(i => i.regret_level === "high").length;

  return (
    <div
      className="min-h-screen flex flex-col transition-colors duration-300"
      style={{ background: "var(--sb-page-bg)" }}
    >
      {/* ── 헤더 ── */}
      <header
        className="sticky top-0 z-50 flex items-center justify-between px-4 sm:px-6 h-14 transition-colors duration-300"
        style={{
          background: "var(--sb-header-bg)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--sb-header-border)",
        }}
      >
        <div className="flex items-center gap-3">
          <Link href="/">
            <button
              className="flex items-center gap-1.5 text-sm transition-colors"
              style={{ color: "var(--sb-text-muted)" }}
            >
              <ArrowLeft size={16} />
              <span className="hidden sm:inline">홈으로</span>
            </button>
          </Link>
          <div
            className="w-px h-5"
            style={{ background: "var(--sb-border)" }}
          />
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, var(--sb-blue), var(--sb-blue-dark))" }}
            >
              <ShoppingCart size={13} style={{ color: isDark ? "#0A0E1A" : "#fff" }} />
            </div>
            <span
              className="font-bold text-base"
              style={{ fontFamily: "'Space Grotesk', monospace", color: "var(--sb-text-primary)" }}
            >
              분석 이력
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchHistory}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
            style={{ color: "var(--sb-text-muted)", background: "var(--sb-input-bg)" }}
            title="새로고침"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={toggleTheme}
            title={isDark ? "화이트 테마로 전환" : "블랙 테마로 전환"}
            className="w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200"
            style={{
              background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
              border: `1px solid ${isDark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.10)"}`,
              color: "var(--sb-text-secondary)",
            }}
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </header>

      <main className="flex-1 container py-6 max-w-5xl mx-auto px-4">
        {/* ── 통계 카드 ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            {
              icon: <BarChart2 size={18} />,
              label: "총 분석 수",
              value: items.length,
              unit: "건",
              color: "var(--sb-blue)",
            },
            {
              icon: <CheckCircle size={18} />,
              label: "완료된 분석",
              value: completedItems.length,
              unit: "건",
              color: "var(--sb-green)",
            },
            {
              icon: <TrendingUp size={18} />,
              label: "평균 후회 점수",
              value: Math.round(avgScore * 100),
              unit: "%",
              color: "var(--sb-amber)",
            },
            {
              icon: <AlertTriangle size={18} />,
              label: "고위험 상품",
              value: highRiskCount,
              unit: "건",
              color: "var(--sb-red)",
            },
          ].map((stat, i) => (
            <div
              key={i}
              className="rounded-xl p-4"
              style={{ background: "var(--sb-card-bg)", border: "1px solid var(--sb-border)" }}
            >
              <div className="flex items-center gap-2 mb-2" style={{ color: stat.color }}>
                {stat.icon}
                <span className="text-xs" style={{ color: "var(--sb-text-muted)" }}>{stat.label}</span>
              </div>
              <div
                className="text-2xl font-bold"
                style={{ fontFamily: "'Space Grotesk', monospace", color: "var(--sb-text-primary)" }}
              >
                {stat.value}
                <span className="text-sm font-normal ml-0.5" style={{ color: "var(--sb-text-muted)" }}>
                  {stat.unit}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* ── 검색/필터 ── */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div
            className="flex items-center gap-2 flex-1 rounded-xl px-3 h-10"
            style={{ background: "var(--sb-input-bg)", border: "1px solid var(--sb-border)" }}
          >
            <Search size={14} style={{ color: "var(--sb-text-dim)" }} />
            <input
              type="text"
              placeholder="상품명으로 검색..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="flex-1 bg-transparent text-sm outline-none"
              style={{ color: "var(--sb-text-primary)" }}
            />
          </div>
          <div className="flex gap-1.5">
            {(["all", "high", "medium", "low"] as const).map(level => (
              <button
                key={level}
                onClick={() => setFilterLevel(level)}
                className="px-3 h-10 rounded-xl text-xs font-medium transition-all duration-150"
                style={{
                  background: filterLevel === level
                    ? (level === "all" ? "var(--sb-blue)" : level === "high" ? "var(--sb-red)" : level === "medium" ? "var(--sb-amber)" : "var(--sb-green)")
                    : "var(--sb-input-bg)",
                  color: filterLevel === level ? "#fff" : "var(--sb-text-muted)",
                  border: `1px solid ${filterLevel === level ? "transparent" : "var(--sb-border)"}`,
                }}
              >
                {level === "all" ? "전체" : level === "high" ? "고위험" : level === "medium" ? "중위험" : "저위험"}
              </button>
            ))}
          </div>
        </div>

        {/* ── 이력 목록 ── */}
        {loading && (
          <div className="flex flex-col items-center py-20 gap-4">
            <RefreshCw size={32} className="animate-spin" style={{ color: "var(--sb-blue)" }} />
            <p style={{ color: "var(--sb-text-muted)" }}>분석 이력을 불러오는 중...</p>
          </div>
        )}

        {error && (
          <div
            className="rounded-2xl p-8 flex flex-col items-center gap-4 text-center"
            style={{ background: "var(--sb-card-bg)", border: "1px solid var(--sb-border)" }}
          >
            <AlertTriangle size={40} style={{ color: "var(--sb-red)" }} />
            <div>
              <p className="font-semibold" style={{ color: "var(--sb-text-primary)" }}>
                이력을 불러올 수 없습니다
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--sb-text-muted)" }}>{error}</p>
            </div>
            <Button onClick={fetchHistory} size="sm">
              다시 시도
            </Button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div
            className="rounded-2xl p-12 flex flex-col items-center gap-4 text-center"
            style={{ background: "var(--sb-card-bg)", border: "1px solid var(--sb-border)" }}
          >
            <Package size={48} style={{ color: "var(--sb-text-dim)" }} />
            <div>
              <p className="font-semibold text-lg" style={{ color: "var(--sb-text-primary)" }}>
                {searchQuery || filterLevel !== "all" ? "검색 결과가 없습니다" : "분석 이력이 없습니다"}
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--sb-text-muted)" }}>
                {searchQuery || filterLevel !== "all"
                  ? "검색 조건을 변경해 보세요"
                  : "홈으로 돌아가서 상품을 분석해 보세요"}
              </p>
            </div>
            {!(searchQuery || filterLevel !== "all") && (
              <Link href="/">
                <Button size="sm">홈으로 이동</Button>
              </Link>
            )}
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-2">
            {filtered.map(item => {
              const regretPct = item.regret_score != null ? Math.round(item.regret_score * 100) : null;
              return (
                <div
                  key={item.id}
                  className="rounded-xl p-4 flex items-center gap-4 cursor-pointer transition-all duration-150 group"
                  style={{
                    background: "var(--sb-card-bg)",
                    border: "1px solid var(--sb-border)",
                  }}
                  onClick={() => item.status === "completed" && setSelectedSession(item.session_id)}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = "var(--sb-blue)";
                    (e.currentTarget as HTMLDivElement).style.background = "var(--sb-card-hover)";
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = "var(--sb-border)";
                    (e.currentTarget as HTMLDivElement).style.background = "var(--sb-card-bg)";
                  }}
                >
                  {/* 상태 아이콘 */}
                  <div className="shrink-0">
                    {getStatusIcon(item.status)}
                  </div>

                  {/* 상품 정보 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="font-medium text-sm truncate"
                        style={{ color: "var(--sb-text-primary)" }}
                      >
                        {item.product_name || "상품명 미확인"}
                      </span>
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "var(--sb-border)", color: "var(--sb-text-dim)" }}
                      >
                        {getInputTypeLabel(item.input_type)}
                      </span>
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: "var(--sb-text-dim)" }}>
                      {formatDate(item.created_at)}
                    </div>
                  </div>

                  {/* 후회 점수 */}
                  {regretPct != null && (
                    <div className="shrink-0 flex items-center gap-3">
                      {/* 미니 바 */}
                      <div className="hidden sm:flex flex-col items-end gap-1">
                        <div
                          className="w-20 h-1.5 rounded-full overflow-hidden"
                          style={{ background: "var(--sb-border)" }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${regretPct}%`,
                              background: getRegretColor(item.regret_level),
                            }}
                          />
                        </div>
                        <span
                          className="text-xs font-medium"
                          style={{ color: getRegretColor(item.regret_level), fontFamily: "'Space Grotesk', monospace" }}
                        >
                          {regretPct}%
                        </span>
                      </div>

                      {/* 레벨 뱃지 */}
                      <div
                        className="text-xs px-2 py-1 rounded-lg font-medium"
                        style={{
                          background: `${getRegretColor(item.regret_level)}18`,
                          color: getRegretColor(item.regret_level),
                        }}
                      >
                        {item.regret_level === "high" ? (
                          <span className="flex items-center gap-1"><TrendingUp size={11} /> 고위험</span>
                        ) : item.regret_level === "medium" ? (
                          <span className="flex items-center gap-1"><AlertTriangle size={11} /> 중위험</span>
                        ) : (
                          <span className="flex items-center gap-1"><TrendingDown size={11} /> 저위험</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 상세 보기 화살표 */}
                  {item.status === "completed" && (
                    <ChevronRight
                      size={16}
                      className="shrink-0 transition-transform group-hover:translate-x-0.5"
                      style={{ color: "var(--sb-text-dim)" }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 페이지네이션 */}
        {!loading && !error && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
              style={{ borderColor: "var(--sb-border)", color: "var(--sb-text-muted)" }}
            >
              이전
            </Button>
            <span className="text-sm" style={{ color: "var(--sb-text-muted)" }}>
              {page + 1} 페이지
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={items.length < PAGE_SIZE}
              onClick={() => setPage(p => p + 1)}
              style={{ borderColor: "var(--sb-border)", color: "var(--sb-text-muted)" }}
            >
              다음
            </Button>
          </div>
        )}
      </main>

      {/* 상세 모달 */}
      {selectedSession && (
        <DetailModal
          sessionId={selectedSession}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}
