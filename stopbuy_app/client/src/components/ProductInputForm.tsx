/*
 * StopBuy - 상품 입력 폼 컴포넌트
 * Design: "Analytical Dual Theme" — CSS 변수(--sb-*) 기반 색상 처리
 * 사용자가 구매 예정 상품 정보를 입력하는 메인 폼
 */
import { useState, useRef, useCallback, type ChangeEvent } from "react";
import { Link, ImagePlus, ClipboardList, Upload, X, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { UserProfile, ProductInfo } from "@/hooks/useStopBuyWS";

type InputTab = "url" | "image" | "manual";

interface ProductInputFormProps {
  onSubmit: (params: {
    inputType: "url" | "image" | "manual";
    productUrl?: string;
    imageBase64?: string;
    user?: UserProfile;
    product?: ProductInfo;
  }) => void;
  isAnalyzing: boolean;
}

const inputStyle = {
  background: "var(--sb-input-bg)",
  border: "1px solid var(--sb-input-border)",
  color: "var(--sb-text-primary)",
};

const labelStyle = { color: "var(--sb-text-secondary)" };

export function ProductInputForm({ onSubmit, isAnalyzing }: ProductInputFormProps) {
  const [activeTab, setActiveTab] = useState<InputTab>("url");
  const [productUrl, setProductUrl] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [budget, setBudget] = useState("");
  const [preferredBrands, setPreferredBrands] = useState("");
  const [importantFactors, setImportantFactors] = useState("");
  const [usagePurpose, setUsagePurpose] = useState("");

  const [productName, setProductName] = useState("");
  const [productBrand, setProductBrand] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [productPrice, setProductPrice] = useState("");
  const [productRating, setProductRating] = useState("");
  const [productReviewCount, setProductReviewCount] = useState("");
  const [productReturnRate, setProductReturnRate] = useState("");

  const handleImageFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setImagePreview(result);
      setImageBase64(result);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImageFile(file);
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleImageFile(file);
    },
    [handleImageFile]
  );

  const buildUserProfile = (): UserProfile => ({
    budget: budget ? parseFloat(budget.replace(/,/g, "")) : undefined,
    preferred_brands: preferredBrands
      ? preferredBrands.split(",").map((s) => s.trim()).filter(Boolean)
      : [],
    important_factors: importantFactors
      ? importantFactors.split(",").map((s) => s.trim()).filter(Boolean)
      : [],
    usage_purpose: usagePurpose || undefined,
  });

  const buildProductInfo = (): ProductInfo => ({
    name: productName || undefined,
    brand: productBrand || undefined,
    category: productCategory || undefined,
    price: productPrice ? parseFloat(productPrice.replace(/,/g, "")) : undefined,
    rating: productRating ? parseFloat(productRating) : undefined,
    review_count: productReviewCount ? parseInt(productReviewCount) : undefined,
    return_rate: productReturnRate ? parseFloat(productReturnRate) : undefined,
  });

  const handleSubmit = () => {
    const user = buildUserProfile();
    if (activeTab === "url") {
      if (!productUrl.trim()) return;
      onSubmit({ inputType: "url", productUrl: productUrl.trim(), user });
    } else if (activeTab === "image") {
      if (!imageBase64) return;
      onSubmit({ inputType: "image", imageBase64, user });
    } else {
      if (!productName.trim()) return;
      onSubmit({ inputType: "manual", user, product: buildProductInfo() });
    }
  };

  const canSubmit =
    !isAnalyzing &&
    ((activeTab === "url" && productUrl.trim()) ||
      (activeTab === "image" && imageBase64) ||
      (activeTab === "manual" && productName.trim()));

  const TABS = [
    { id: "url" as InputTab, icon: Link, label: "URL 입력" },
    { id: "image" as InputTab, icon: ImagePlus, label: "이미지 업로드" },
    { id: "manual" as InputTab, icon: ClipboardList, label: "직접 입력" },
  ];

  return (
    <div className="flex flex-col gap-5">
      {/* 탭 선택 */}
      <div
        className="flex rounded-xl p-1 gap-1 transition-colors duration-300"
        style={{ background: "var(--sb-input-bg)" }}
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium transition-all duration-200"
              style={{
                background: isActive ? "var(--sb-tab-active-bg)" : "transparent",
                color: isActive ? "var(--sb-tab-active-color)" : "var(--sb-tab-inactive-color)",
                border: isActive ? "1px solid var(--sb-tab-active-border)" : "1px solid transparent",
              }}
            >
              <Icon size={15} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* URL 입력 */}
      {activeTab === "url" && (
        <div className="flex flex-col gap-3 animate-fade-in">
          <Label className="text-sm" style={labelStyle}>
            상품 URL을 입력하세요
          </Label>
          <Input
            value={productUrl}
            onChange={(e) => setProductUrl(e.target.value)}
            placeholder="https://www.coupang.com/vp/products/..."
            className="flex-1 text-sm"
            style={inputStyle}
            onKeyDown={(e) => e.key === "Enter" && canSubmit && handleSubmit()}
          />
          <p className="text-xs" style={{ color: "var(--sb-text-dim)" }}>
            쿠팡, G마켓, 11번가, Amazon 등 주요 쇼핑몰 URL을 지원합니다.
          </p>
        </div>
      )}

      {/* 이미지 업로드 */}
      {activeTab === "image" && (
        <div className="flex flex-col gap-3 animate-fade-in">
          <Label className="text-sm" style={labelStyle}>
            상품 이미지를 업로드하세요
          </Label>

          {imagePreview ? (
            <div className="relative rounded-xl overflow-hidden" style={{ height: 200 }}>
              <img
                src={imagePreview}
                alt="업로드된 상품 이미지"
                className="w-full h-full object-contain"
                style={{ background: "var(--sb-input-bg)" }}
              />
              <button
                onClick={() => { setImagePreview(null); setImageBase64(null); }}
                className="absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center transition-colors"
                style={{ background: "rgba(0,0,0,0.6)", color: "#fff" }}
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div
              className="rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-200"
              style={{
                height: 160,
                border: `2px dashed ${isDragOver ? "var(--sb-blue)" : "var(--sb-input-border)"}`,
                background: isDragOver ? "color-mix(in oklch, var(--sb-blue) 6%, transparent)" : "var(--sb-input-bg)",
              }}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
            >
              <Upload size={28} style={{ color: isDragOver ? "var(--sb-blue-light)" : "var(--sb-text-dim)" }} />
              <div className="text-center">
                <p className="text-sm" style={{ color: "var(--sb-text-secondary)" }}>
                  클릭하거나 이미지를 드래그하세요
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--sb-text-dim)" }}>
                  JPG, PNG, WebP 지원 (최대 10MB)
                </p>
              </div>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* 직접 입력 */}
      {activeTab === "manual" && (
        <div className="flex flex-col gap-3 animate-fade-in">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label className="text-xs mb-1.5 block" style={labelStyle}>상품명 *</Label>
              <Input value={productName} onChange={(e) => setProductName(e.target.value)}
                placeholder="예: 삼성 갤럭시 S24" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>브랜드</Label>
              <Input value={productBrand} onChange={(e) => setProductBrand(e.target.value)}
                placeholder="예: Samsung" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>카테고리</Label>
              <Input value={productCategory} onChange={(e) => setProductCategory(e.target.value)}
                placeholder="예: 스마트폰" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>가격 (원)</Label>
              <Input value={productPrice} onChange={(e) => setProductPrice(e.target.value)}
                placeholder="예: 1200000" type="number" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>평점 (0-5)</Label>
              <Input value={productRating} onChange={(e) => setProductRating(e.target.value)}
                placeholder="예: 3.7" type="number" min="0" max="5" step="0.1" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>리뷰 수</Label>
              <Input value={productReviewCount} onChange={(e) => setProductReviewCount(e.target.value)}
                placeholder="예: 150" type="number" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>반품률 (%)</Label>
              <Input value={productReturnRate} onChange={(e) => setProductReturnRate(e.target.value)}
                placeholder="예: 12.5" type="number" min="0" max="100" step="0.1" className="text-sm" style={inputStyle} />
            </div>
          </div>
        </div>
      )}

      {/* 사용자 프로필 (접기/펼치기) */}
      <div>
        <button
          onClick={() => setShowUserProfile(!showUserProfile)}
          className="flex items-center gap-2 text-sm transition-colors w-full text-left"
          style={{ color: "var(--sb-text-muted)" }}
        >
          {showUserProfile ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          <span>내 구매 조건 설정 (선택사항)</span>
        </button>

        {showUserProfile && (
          <div
            className="mt-3 p-4 rounded-xl flex flex-col gap-3 animate-fade-in transition-colors duration-300"
            style={{
              background: "var(--sb-hint-bg)",
              border: "1px solid var(--sb-hint-border)",
            }}
          >
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>예산 (원)</Label>
              <Input value={budget} onChange={(e) => setBudget(e.target.value)}
                placeholder="예: 1500000" type="number" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>선호 브랜드 (쉼표 구분)</Label>
              <Input value={preferredBrands} onChange={(e) => setPreferredBrands(e.target.value)}
                placeholder="예: Samsung, LG, Apple" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>중요 요소 (쉼표 구분)</Label>
              <Input value={importantFactors} onChange={(e) => setImportantFactors(e.target.value)}
                placeholder="예: 성능, 배터리, 휴대성" className="text-sm" style={inputStyle} />
            </div>
            <div>
              <Label className="text-xs mb-1.5 block" style={labelStyle}>사용 목적</Label>
              <Input value={usagePurpose} onChange={(e) => setUsagePurpose(e.target.value)}
                placeholder="예: 영상 편집, 게임, 업무용" className="text-sm" style={inputStyle} />
            </div>
          </div>
        )}
      </div>

      {/* 분석 버튼 */}
      <Button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full h-12 text-base font-semibold transition-all duration-200 active:scale-[0.98]"
        style={{
          background: canSubmit
            ? "linear-gradient(135deg, var(--sb-blue), var(--sb-blue-dark))"
            : "var(--sb-badge-bg)",
          color: canSubmit ? "#FFFFFF" : "var(--sb-text-dim)",
          border: "none",
          boxShadow: canSubmit ? "0 4px 20px color-mix(in oklch, var(--sb-blue) 40%, transparent)" : "none",
        }}
      >
        {isAnalyzing ? "분석 중..." : "구매 후회 예측 시작"}
      </Button>
    </div>
  );
}
