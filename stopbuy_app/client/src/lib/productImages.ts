import type { AlternativeProduct } from "@/hooks/useStopBuyWS";

export const PRODUCT_PLACEHOLDER_IMAGE =
  "https://d2xsxph8kpxj0f.cloudfront.net/310519663632451254/8SbY3RBNCHrKBA7jPh2CJe/stopbuy_product_placeholder-ZSAsS7GCJQb9MZnQ4RoFR7.webp";

type ProductImageRule = {
  keywords: string[];
  imageUrl: string;
};

const PRODUCT_IMAGE_RULES: ProductImageRule[] = [
  {
    keywords: ["macbook", "맥북", "galaxybook", "갤럭시북", "그램", "xps", "spectre", "ideapad", "노트북", "laptop"],
    imageUrl: "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["rog", "게이밍 노트북", "gaming laptop"],
    imageUrl: "https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["iphone", "아이폰", "galaxy s", "갤럭시 s", "pixel", "픽셀", "xiaomi", "스마트폰", "phone"],
    imageUrl: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["airpods", "에어팟", "buds", "버즈", "earbuds", "이어폰"],
    imageUrl: "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["sony wh", "bose", "jbl", "헤드폰", "headphone", "노이즈캔슬링"],
    imageUrl: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["tv", "qled", "oled", "티비", "텔레비전"],
    imageUrl: "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["monitor", "모니터", "ultragear", "오디세이"],
    imageUrl: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["냉장고", "refrigerator", "비스포크"],
    imageUrl: "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["세탁기", "washer", "washing machine"],
    imageUrl: "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["공기청정기", "air purifier", "청정기"],
    imageUrl: "https://images.unsplash.com/photo-1585771724684-38269d6639fd?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["커피", "coffee", "머신", "캡슐"],
    imageUrl: "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["tablet", "태블릿", "ipad", "아이패드", "pencil", "펜슬", "스타일러스"],
    imageUrl: "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["만년필", "문구", "pen", "stationery"],
    imageUrl: "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["사료", "강아지", "고양이", "반려동물", "pet food", "dog food", "cat food"],
    imageUrl: "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["패션", "의류", "옷", "fashion", "clothing"],
    imageUrl: "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["신발", "운동화", "shoes", "sneakers"],
    imageUrl: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["화장품", "cosmetic", "skincare", "스킨케어"],
    imageUrl: "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=900&q=80",
  },
  {
    keywords: ["가구", "의자", "책상", "furniture", "chair", "desk"],
    imageUrl: "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=900&q=80",
  },
];

const CATEGORY_IMAGE_MAP: Record<string, string> = {
  전자제품: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80",
  가전제품: "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=900&q=80",
  "도서/문구": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=900&q=80",
  반려동물: "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?auto=format&fit=crop&w=900&q=80",
  패션: "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80",
};

function normalize(value?: string | number | null): string {
  return String(value ?? "").toLowerCase().replace(/\s+/g, " ").trim();
}

export function getAlternativeProductImage(product: AlternativeProduct): string {
  if (product.image_url?.trim()) {
    return product.image_url;
  }

  const searchableText = normalize(
    [product.name, product.brand, product.category].filter(Boolean).join(" "),
  );

  const matchedRule = PRODUCT_IMAGE_RULES.find((rule) =>
    rule.keywords.some((keyword) => searchableText.includes(keyword.toLowerCase())),
  );

  if (matchedRule) {
    return matchedRule.imageUrl;
  }

  const category = product.category?.trim();
  if (category && CATEGORY_IMAGE_MAP[category]) {
    return CATEGORY_IMAGE_MAP[category];
  }

  return PRODUCT_PLACEHOLDER_IMAGE;
}
