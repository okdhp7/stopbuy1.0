"""
StopBuy AI Agent - 상품 정보 추출 모듈
쿠팡, 네이버쇼핑, 11번가, G마켓, 옥션 URL 파싱 지원 (전용 CSS 셀렉터)
이미지 분석 기반 상품 정보 추출 지원 (Vision LLM)
"""
import asyncio
import base64
import json
import logging
import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

# ── 카테고리 키워드 매핑 ──────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "전자제품": [
        "노트북", "laptop", "컴퓨터", "pc", "태블릿", "ipad", "갤럭시탭",
        "스마트폰", "아이폰", "iphone", "galaxy", "갤럭시", "핸드폰", "휴대폰",
        "tv", "텔레비전", "모니터", "프린터", "카메라", "dslr", "미러리스",
        "냉장고", "세탁기", "에어컨", "청소기", "전자레인지", "오븐",
        "공기청정기", "가습기", "제습기", "선풍기", "전기밥솥",
        "이어폰", "헤드폰", "스피커", "블루투스", "airpods",
        "충전기", "배터리", "보조배터리", "키보드", "마우스",
        "게임기", "닌텐도", "플레이스테이션", "xbox",
    ],
    "패션/의류": [
        "티셔츠", "셔츠", "바지", "청바지", "원피스", "스커트",
        "재킷", "코트", "패딩", "점퍼", "후드", "맨투맨", "니트",
        "운동화", "구두", "슬리퍼", "샌들", "가방", "백팩", "핸드백",
        "지갑", "모자", "벨트", "시계", "반지", "목걸이", "귀걸이",
    ],
    "식품/건강": [
        "식품", "음식", "과자", "음료", "커피", "차", "건강식품",
        "비타민", "단백질", "다이어트", "유기농", "쌀", "라면",
        "냉동식품", "즉석식품", "과일", "채소",
    ],
    "뷰티/화장품": [
        "화장품", "스킨케어", "로션", "크림", "세럼", "에센스",
        "마스크팩", "선크림", "파운데이션", "립스틱", "마스카라",
        "샴푸", "컨디셔너", "헤어", "향수", "바디워시",
    ],
    "스포츠/레저": [
        "스포츠", "운동", "헬스", "요가", "필라테스", "자전거",
        "킥보드", "등산", "캠핑", "텐트", "수영", "골프", "테니스",
        "축구", "농구", "낚시",
    ],
    "가구/인테리어": [
        "가구", "소파", "침대", "매트리스", "책상", "의자", "테이블",
        "옷장", "서랍", "선반", "조명", "커튼", "카펫", "인테리어",
    ],
    "도서/문구": [
        "책", "도서", "소설", "만화", "교재", "참고서",
        "문구", "펜", "노트", "다이어리", "플래너",
    ],
    "유아/아동": [
        "유아", "아기", "어린이", "장난감", "블록", "레고",
        "유모차", "카시트", "기저귀", "분유",
    ],
    "반려동물": [
        "강아지", "고양이", "반려동물", "사료", "간식",
        "하네스", "목줄", "케이지", "모래",
    ],
}


def detect_shop(url: str) -> Optional[str]:
    """URL에서 쇼핑몰 종류 감지"""
    try:
        domain = urlparse(url).netloc.lower()
        if "coupang.com" in domain:
            return "coupang"
        if "smartstore.naver.com" in domain or "shopping.naver.com" in domain or "brand.naver.com" in domain:
            return "naver"
        if "11st.co.kr" in domain:
            return "11st"
        if "gmarket.co.kr" in domain:
            return "gmarket"
        if "auction.co.kr" in domain:
            return "auction"
        if "wemakeprice.com" in domain:
            return "wemakeprice"
        if "tmon.co.kr" in domain:
            return "tmon"
        if "interpark.com" in domain:
            return "interpark"
    except Exception:
        pass
    return "generic"


def detect_category_from_text(text: str) -> Optional[str]:
    """텍스트에서 카테고리 감지"""
    if not text:
        return None
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else None


def _extract_price(text: str) -> Optional[float]:
    """텍스트에서 가격 추출"""
    for pattern in [r'(\d{1,3}(?:,\d{3})+)원', r'₩\s*(\d{1,3}(?:,\d{3})*)', r'"price":\s*"?(\d+)"?']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1).replace(",", ""))
                if 100 <= v <= 100_000_000:
                    return v
            except ValueError:
                pass
    return None


def _extract_rating(text: str) -> Optional[float]:
    """텍스트에서 평점 추출"""
    for pattern in [r'"ratingValue":\s*"?([\d.]+)"?', r'평점[:\s]*([\d.]+)', r'rating["\s:]+([0-9.]+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                if 0 <= v <= 5:
                    return v
                if 0 <= v <= 10:
                    return v / 2
            except ValueError:
                pass
    return None


def _extract_review_count(text: str) -> Optional[int]:
    """텍스트에서 리뷰 수 추출"""
    for pattern in [r'"reviewCount":\s*"?(\d+)"?', r'리뷰\s*(\d+)', r'(\d+)개의?\s*리뷰', r'후기\s*(\d+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def _parse_json_ld(soup: BeautifulSoup) -> Dict[str, Any]:
    """JSON-LD 구조화 데이터에서 상품 정보 추출"""
    info = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") in ("Product", "ItemPage"):
                if data.get("name"):
                    info["name"] = data["name"]
                if data.get("description"):
                    info["description"] = data["description"]
                brand = data.get("brand", {})
                if brand:
                    info["brand"] = brand.get("name", brand) if isinstance(brand, dict) else str(brand)
                img = data.get("image")
                if img:
                    info["image_url"] = img[0] if isinstance(img, list) else img
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0]
                if offers:
                    price_val = offers.get("price") or offers.get("lowPrice")
                    if price_val:
                        try:
                            info["price"] = float(str(price_val).replace(",", ""))
                        except ValueError:
                            pass
                agg = data.get("aggregateRating", {})
                if agg:
                    rv = agg.get("ratingValue")
                    if rv:
                        try:
                            info["rating"] = float(rv)
                        except ValueError:
                            pass
                    rc = agg.get("reviewCount") or agg.get("ratingCount")
                    if rc:
                        try:
                            info["review_count"] = int(rc)
                        except ValueError:
                            pass
                if info.get("name"):
                    break
        except (json.JSONDecodeError, AttributeError, KeyError):
            continue
    return info


def _parse_coupang(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    """쿠팡 전용 파서"""
    info = {}
    # 상품명
    for sel in ["h1.prod-buy-header__title", ".prod-title", "h2.prod-buy-header__title", "[class*='prod-buy-header']"]:
        el = soup.select_one(sel)
        if el:
            info["name"] = el.get_text(strip=True)
            break
    # 가격
    for sel in [".prod-sale-price .total-price strong", ".total-price strong", "[class*='sale-price'] strong"]:
        el = soup.select_one(sel)
        if el:
            p = _extract_price(el.get_text())
            if p:
                info["price"] = p
                break
    if not info.get("price"):
        p = _extract_price(html[:10000])
        if p:
            info["price"] = p
    # 평점
    for sel in [".rating-star-num", "[class*='rating-star']", ".prod-rating em"]:
        el = soup.select_one(sel)
        if el:
            r = _extract_rating(el.get_text())
            if r:
                info["rating"] = r
                break
    if not info.get("rating"):
        r = _extract_rating(html[:10000])
        if r:
            info["rating"] = r
    # 리뷰 수
    for sel in [".count-review", "[class*='review-count']", ".prod-review-count"]:
        el = soup.select_one(sel)
        if el:
            c = _extract_review_count(el.get_text())
            if c is not None:
                info["review_count"] = c
                break
    # 브랜드
    el = soup.select_one(".prod-brand-name, [class*='brand-name']")
    if el:
        info["brand"] = el.get_text(strip=True)
    # 이미지
    el = soup.select_one(".prod-image__detail img, .prod-image img")
    if el:
        info["image_url"] = el.get("src", "")
    # 카테고리 (breadcrumb)
    bc = soup.select(".breadcrumb li, [class*='breadcrumb'] li")
    if bc:
        cat = detect_category_from_text(" ".join(el.get_text(strip=True) for el in bc))
        if cat:
            info["category"] = cat
    return info


def _parse_naver(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    """네이버 스마트스토어/쇼핑 전용 파서"""
    info = {}
    # 상품명 (스마트스토어 다양한 클래스 대응)
    for sel in [
        "._3oDjSvLwozWFAHDeLMBXBq",
        ".product_title",
        "h3.product_title",
        "[class*='ProductName']",
        "[class*='product_title']",
        ".prod_name",
        "h1",
    ]:
        el = soup.select_one(sel)
        if el:
            name = el.get_text(strip=True)
            if len(name) > 3:
                info["name"] = name
                break
    # 가격
    for sel in ["._1LY7DqCnwR", ".price_num", "[class*='price_num']", ".cost strong", "[class*='_price']"]:
        el = soup.select_one(sel)
        if el:
            p = _extract_price(el.get_text())
            if p:
                info["price"] = p
                break
    if not info.get("price"):
        p = _extract_price(html[:10000])
        if p:
            info["price"] = p
    # 평점
    for sel in [".score_area em", "[class*='score'] em", ".rating em", "[class*='_rating']"]:
        el = soup.select_one(sel)
        if el:
            r = _extract_rating(el.get_text())
            if r:
                info["rating"] = r
                break
    if not info.get("rating"):
        r = _extract_rating(html[:10000])
        if r:
            info["rating"] = r
    # 리뷰 수
    for sel in [".count em", "[class*='reviewCount']", "[class*='review_count']", "[class*='_review']"]:
        el = soup.select_one(sel)
        if el:
            c = _extract_review_count(el.get_text())
            if c is not None:
                info["review_count"] = c
                break
    # 브랜드
    el = soup.select_one(".brand_name, [class*='brand']")
    if el:
        info["brand"] = el.get_text(strip=True)
    # 이미지
    el = soup.select_one(".product_img img, ._3oDjSvLwozWFAHDeLMBXBq img")
    if el:
        info["image_url"] = el.get("src", "")
    # 카테고리
    bc = soup.select(".breadcrumb a, [class*='breadcrumb'] a")
    if bc:
        cat = detect_category_from_text(" ".join(el.get_text(strip=True) for el in bc))
        if cat:
            info["category"] = cat
    return info


def _parse_11st(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    """11번가 전용 파서"""
    info = {}
    for sel in [".prd_name", "h1.prd_name", "[class*='prd_name']", ".product_name"]:
        el = soup.select_one(sel)
        if el:
            info["name"] = el.get_text(strip=True)
            break
    for sel in [".price_area .sale", ".price_area strong", "[class*='price'] strong"]:
        el = soup.select_one(sel)
        if el:
            p = _extract_price(el.get_text())
            if p:
                info["price"] = p
                break
    if not info.get("price"):
        p = _extract_price(html[:10000])
        if p:
            info["price"] = p
    el = soup.select_one(".review_area .avg_score, [class*='avg_score']")
    if el:
        r = _extract_rating(el.get_text())
        if r:
            info["rating"] = r
    el = soup.select_one(".review_area .review_cnt, [class*='review_cnt']")
    if el:
        c = _extract_review_count(el.get_text())
        if c is not None:
            info["review_count"] = c
    return info


def _parse_gmarket(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    """G마켓/옥션 전용 파서"""
    info = {}
    for sel in [".itemtit", "h1.itemtit", "[class*='itemtit']", ".item_title"]:
        el = soup.select_one(sel)
        if el:
            info["name"] = el.get_text(strip=True)
            break
    for sel in [".price_real strong", "[class*='price_real']", ".cost strong"]:
        el = soup.select_one(sel)
        if el:
            p = _extract_price(el.get_text())
            if p:
                info["price"] = p
                break
    if not info.get("price"):
        p = _extract_price(html[:10000])
        if p:
            info["price"] = p
    return info


def _parse_generic(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    """범용 파서 (JSON-LD + OpenGraph + 메타태그)"""
    info = _parse_json_ld(soup)

    # OpenGraph
    og_title = soup.find("meta", property="og:title")
    if og_title and not info.get("name"):
        info["name"] = og_title.get("content", "")
    og_image = soup.find("meta", property="og:image")
    if og_image and not info.get("image_url"):
        info["image_url"] = og_image.get("content", "")
    og_desc = soup.find("meta", property="og:description")
    if og_desc and not info.get("description"):
        info["description"] = og_desc.get("content", "")

    # 페이지 제목
    if not info.get("name"):
        title_el = soup.find("title")
        if title_el:
            title = title_el.get_text(strip=True)
            for sep in [" | ", " - ", " :: ", " > "]:
                if sep in title:
                    title = title.split(sep)[0].strip()
                    break
            if title:
                info["name"] = title

    # 폴백: 전체 텍스트에서 추출
    page_text = soup.get_text()
    if not info.get("price"):
        p = _extract_price(page_text[:5000])
        if p:
            info["price"] = p
    if not info.get("rating"):
        r = _extract_rating(page_text[:5000])
        if r:
            info["rating"] = r
    if not info.get("review_count"):
        c = _extract_review_count(page_text[:5000])
        if c is not None:
            info["review_count"] = c

    return info


async def extract_product_info(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    입력 데이터에서 상품 정보 추출
    - URL 입력: 웹 크롤링 후 쇼핑몰별 전용 파서 적용
    - 이미지 입력: Vision LLM으로 상품 정보 추출
    - 직접 입력: 그대로 사용
    """
    input_type = data.get("input_type", "manual")

    if input_type == "url" and data.get("product_url"):
        return await extract_from_url(data["product_url"])
    elif input_type == "image" and data.get("image_path"):
        return await extract_from_image(data["image_path"])
    elif data.get("product"):
        return data["product"]
    return None


async def extract_from_url(url: str) -> Optional[Dict[str, Any]]:
    """URL에서 상품 정보 크롤링 및 파싱 (쇼핑몰별 전용 파서)"""
    logger.info(f"URL 크롤링 시작: {url}")

    shop = detect_shop(url)
    logger.info(f"쇼핑몰 감지: {shop}")

    # HTML 가져오기
    html = None
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"URL 크롤링 실패: {e}")
        return _extract_from_url_fallback(url)

    soup = BeautifulSoup(html, "lxml")
    product_info = {}

    # 쇼핑몰별 전용 파서 적용
    if shop == "coupang":
        product_info = _parse_coupang(soup, html)
    elif shop == "naver":
        product_info = _parse_naver(soup, html)
    elif shop == "11st":
        product_info = _parse_11st(soup, html)
    elif shop in ("gmarket", "auction"):
        product_info = _parse_gmarket(soup, html)
    else:
        product_info = _parse_generic(soup, html)

    # 공통 폴백: 이름이 없으면 og:title 시도
    if not product_info.get("name"):
        og_title = soup.find("meta", property="og:title")
        if og_title:
            product_info["name"] = og_title.get("content", "")
    if not product_info.get("name"):
        title_el = soup.find("title")
        if title_el:
            title = title_el.get_text(strip=True)
            for sep in [" | ", " - ", " :: "]:
                if sep in title:
                    title = title.split(sep)[0].strip()
                    break
            product_info["name"] = title

    # 이미지 폴백
    if not product_info.get("image_url"):
        og_image = soup.find("meta", property="og:image")
        if og_image:
            product_info["image_url"] = og_image.get("content", "")

    # 카테고리 감지
    if not product_info.get("category"):
        text = f"{product_info.get('name', '')} {product_info.get('description', '')}"
        cat = detect_category_from_text(text)
        if cat:
            product_info["category"] = cat

    # LLM으로 추가 정보 보완 (API 키 있을 때)
    if OPENAI_API_KEY:
        llm_info = await parse_product_with_llm(html[:8000], url)
        if llm_info:
            for key, value in llm_info.items():
                if value and not product_info.get(key):
                    product_info[key] = value

    product_info["source_url"] = url
    product_info["shop"] = shop

    # 카테고리 '기타' → None (전체 상품 대상 추천)
    if product_info.get("category") == "기타":
        product_info["category"] = None

    logger.info(
        f"URL 파싱 완료: name={product_info.get('name')}, "
        f"price={product_info.get('price')}, "
        f"rating={product_info.get('rating')}, "
        f"category={product_info.get('category')}"
    )
    return product_info if product_info else None


async def parse_product_with_llm(html_text: str, url: str) -> Optional[Dict[str, Any]]:
    """LLM으로 HTML에서 상품 정보 파싱"""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""
다음 쇼핑몰 HTML에서 상품 정보를 추출하세요.
URL: {url}

반드시 JSON 형식으로만 응답하세요:
{{
  "name": "상품명",
  "brand": "브랜드명",
  "category": "카테고리 (전자제품/패션의류/식품건강/뷰티화장품/스포츠레저/가구인테리어/도서문구/유아아동/반려동물 중 하나)",
  "price": 가격(숫자),
  "rating": 평점(0-5 숫자),
  "review_count": 리뷰수(숫자),
  "return_rate": 반품률(숫자, 없으면 null),
  "description": "상품 설명 요약"
}}

HTML (일부):
{html_text[:5000]}
"""
        response = await client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "상품 정보를 JSON으로 추출하는 전문가입니다. JSON만 반환하세요."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
    except Exception as e:
        logger.error(f"LLM 상품 파싱 실패: {e}")
    return None


async def extract_from_image(image_path: str) -> Optional[Dict[str, Any]]:
    """이미지에서 상품 정보 추출 (Vision LLM)"""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 없음. 이미지 분석 불가.")
        return _extract_from_image_fallback(image_path)

    logger.info(f"이미지 분석 시작: {image_path}")

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """이 상품 이미지에서 다음 정보를 추출하여 JSON으로 반환하세요:
{
  "name": "상품명",
  "brand": "브랜드명",
  "category": "카테고리 (전자제품/패션의류/식품건강/뷰티화장품/스포츠레저/가구인테리어 중 하나)",
  "price": 가격(숫자, 이미지에 없으면 null),
  "description": "상품 설명",
  "specs": {"주요스펙": "값"}
}
JSON만 반환하세요.""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if content:
            result = json.loads(content)
            logger.info(f"이미지 분석 완료: {result.get('name', '이름 없음')}")
            return result

    except Exception as e:
        logger.error(f"이미지 분석 실패: {e}")

    return _extract_from_image_fallback(image_path)


def _extract_from_url_fallback(url: str) -> Dict[str, Any]:
    """URL 크롤링 실패 시 기본 정보 반환"""
    return {
        "name": "URL 입력 상품",
        "category": None,
        "description": f"URL: {url}",
        "source_url": url,
    }


def _extract_from_image_fallback(image_path: str) -> Dict[str, Any]:
    """이미지 분석 실패 시 기본 정보 반환"""
    return {
        "name": "이미지 입력 상품",
        "category": None,
        "description": "이미지로 입력된 상품",
    }
