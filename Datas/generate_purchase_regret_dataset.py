import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

OUT_DIR = Path('/home/ubuntu/purchase_regret_dataset')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# 1. 현실적 사용자 세그먼트 정의
# -----------------------------
# 월수입 단위: 원. 직업별·연령대별로 현실적인 소득 범위를 부여한다.
job_profiles = {
    '학생': {'income': [500000, 800000, 1200000, 1600000], 'ages': list(range(19, 30)), 'stability': 0.25},
    '취업준비생': {'income': [600000, 900000, 1300000, 1700000], 'ages': list(range(22, 34)), 'stability': 0.20},
    '사무직': {'income': [2600000, 3200000, 4100000, 5200000, 6500000], 'ages': list(range(24, 56)), 'stability': 0.65},
    '전문직': {'income': [5000000, 7000000, 9500000, 13000000, 17000000], 'ages': list(range(28, 61)), 'stability': 0.85},
    '공무원': {'income': [2800000, 3600000, 4600000, 5800000, 7200000], 'ages': list(range(25, 61)), 'stability': 0.90},
    '자영업': {'income': [2200000, 3300000, 5000000, 8000000, 12000000], 'ages': list(range(30, 66)), 'stability': 0.45},
    '프리랜서': {'income': [1800000, 2800000, 4300000, 6500000, 9000000], 'ages': list(range(24, 56)), 'stability': 0.40},
    '대기업직원': {'income': [4200000, 5500000, 7200000, 9500000, 12500000], 'ages': list(range(26, 58)), 'stability': 0.78},
    '주부': {'income': [800000, 1400000, 2200000, 3200000, 4500000], 'ages': list(range(30, 62)), 'stability': 0.55},
    '은퇴자': {'income': [1200000, 1800000, 2600000, 3800000, 5200000], 'ages': list(range(58, 76)), 'stability': 0.60},
}

# -----------------------------
# 2. 상품 세그먼트 정의
# -----------------------------
# 가격등급 범위는 국내 전자상거래의 일반적 체감 가격대를 기준으로 설정한다.
price_grade_ranges = {
    '초저가': (3000, 25000),
    '저가': (25000, 90000),
    '중저가': (90000, 300000),
    '고가': (300000, 1500000),
    '초고가': (1500000, 9000000),
}

category_profiles = {
    '식품': {'brands': ['CJ', '오뚜기', '풀무원', '동원', '노브랜드'], 'regret_base': 0.12, 'practical': 0.90, 'trend': 0.10, 'typical_grades': ['초저가', '저가', '중저가']},
    '생활용품': {'brands': ['다이소', '깨끗한나라', '유한킴벌리', '락앤락', '3M'], 'regret_base': 0.14, 'practical': 0.90, 'trend': 0.10, 'typical_grades': ['초저가', '저가', '중저가']},
    '패션': {'brands': ['무신사스탠다드', 'ZARA', '나이키', '아디다스', 'COS'], 'regret_base': 0.35, 'practical': 0.40, 'trend': 0.80, 'typical_grades': ['저가', '중저가', '고가']},
    '화장품': {'brands': ['이니스프리', '올리브영PB', '설화수', '라네즈', '에스티로더'], 'regret_base': 0.28, 'practical': 0.55, 'trend': 0.65, 'typical_grades': ['저가', '중저가', '고가']},
    '전자기기': {'brands': ['삼성', 'LG', '애플', '소니', '레노버'], 'regret_base': 0.38, 'practical': 0.65, 'trend': 0.60, 'typical_grades': ['중저가', '고가', '초고가']},
    '가구': {'brands': ['이케아', '한샘', '리바트', '일룸', '오늘의집'], 'regret_base': 0.32, 'practical': 0.70, 'trend': 0.45, 'typical_grades': ['중저가', '고가', '초고가']},
    '명품': {'brands': ['구찌', '루이비통', '샤넬', '프라다', '버버리'], 'regret_base': 0.55, 'practical': 0.25, 'trend': 0.85, 'typical_grades': ['고가', '초고가']},
    '여행': {'brands': ['대한항공', '아시아나', '하나투어', '마이리얼트립', '야놀자'], 'regret_base': 0.42, 'practical': 0.35, 'trend': 0.70, 'typical_grades': ['중저가', '고가', '초고가']},
    '교육': {'brands': ['클래스101', '패스트캠퍼스', '윌라', '시원스쿨', '메가스터디'], 'regret_base': 0.24, 'practical': 0.80, 'trend': 0.35, 'typical_grades': ['저가', '중저가', '고가']},
    '건강관리': {'brands': ['정관장', '센트룸', '종근당', '락토핏', '바디프랜드'], 'regret_base': 0.22, 'practical': 0.85, 'trend': 0.25, 'typical_grades': ['저가', '중저가', '고가', '초고가']},
}

grade_risk = {'초저가': 0.05, '저가': 0.12, '중저가': 0.25, '고가': 0.47, '초고가': 0.70}

# -----------------------------
# 3. 결정론적 보조 함수
# -----------------------------
def stable_float(*values, low=0.0, high=1.0):
    """입력값 조합에서 항상 같은 값을 산출하는 결정론적 변동 함수."""
    s = '|'.join(map(str, values))
    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
    v = int(h[:12], 16) / float(16**12 - 1)
    return low + (high - low) * v


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def price_from_grade(category, grade, idx):
    low, high = price_grade_ranges[grade]
    # 가격은 균등 난수가 아니라 로그 스케일의 결정론적 분위수로 생성하여 저가 구간 밀도를 현실적으로 높인다.
    q = stable_float(category, grade, idx, low=0.05, high=0.95)
    price = int(round(math.exp(math.log(low) + q * (math.log(high) - math.log(low))) / 1000) * 1000)
    return max(low, min(high, price))


def marital_status(age, job, idx):
    # 연령대별 혼인 가능성을 결정론적으로 반영한다.
    if age < 27:
        p = 0.08
    elif age < 33:
        p = 0.33
    elif age < 45:
        p = 0.67
    else:
        p = 0.76
    if job in ['학생', '취업준비생']:
        p -= 0.18
    if job in ['주부']:
        p += 0.20
    return '기혼' if stable_float(age, job, idx) < clamp(p) else '미혼'


def spending_orientation(age, job, income, idx):
    # 젊고 소득이 높거나 프리랜서·전문직일수록 진보적 소비 비중을 높인다.
    p = 0.47
    if age < 35:
        p += 0.16
    if age >= 55:
        p -= 0.18
    if income >= 7000000:
        p += 0.08
    if job in ['프리랜서', '전문직', '대기업직원']:
        p += 0.07
    if job in ['공무원', '은퇴자']:
        p -= 0.09
    return '진보적' if stable_float('orientation', age, job, income, idx) < clamp(p) else '보수적'


def behavior_values(category, grade, price, income, orientation, age, idx):
    burden = price / max(income, 1)
    cat = category_profiles[category]
    base_interest = 6 + int(18 * grade_risk[grade]) + int(10 * cat['trend'])
    if orientation == '보수적':
        base_interest += 4
    if burden > 0.30:
        base_interest += 7
    if age >= 45:
        base_interest += 3

    # 조회수·비교상품수·재방문은 구매 전 검토 강도이며, 가격부담이 크고 보수적일수록 상승한다.
    view_count = max(1, int(base_interest + stable_float('views', idx, category, price, low=-5, high=12)))
    comparison_count = max(0, int(1 + 6 * grade_risk[grade] + 4 * burden + (2 if orientation == '보수적' else 0) + stable_float('comp', idx, low=-1.5, high=2.5)))
    revisit_count = max(0, int(1 + 4 * burden + 3 * grade_risk[grade] + (2 if category in ['전자기기', '가구', '명품', '여행'] else 0) + stable_float('revisit', idx, low=-1.0, high=3.0)))

    # 구매 시간대: 심야 충동구매 가능성을 일부 반영하되, 일반 구매 시간대 비중을 높인다.
    hq = stable_float('hour', idx, category, grade)
    if hq < 0.08:
        hour = int(stable_float('night', idx, low=0, high=4)) % 24
    elif hq < 0.22:
        hour = int(stable_float('late', idx, low=21, high=24)) % 24
    else:
        hour = int(stable_float('day', idx, low=9, high=21))

    # 할부는 가격부담률과 가격등급이 높을수록 증가한다.
    installment_p = 0.04 + 0.75 * clamp((burden - 0.08) / 0.55) + 0.22 * grade_risk[grade]
    if grade in ['고가', '초고가']:
        installment_p += 0.12
    if category in ['전자기기', '가구', '명품', '여행', '건강관리']:
        installment_p += 0.05
    installment = 'Y' if stable_float('installment', idx, price, income) < clamp(installment_p) else 'N'
    return view_count, comparison_count, hour, installment, revisit_count


def regret_score(row):
    price = row['가격']
    income = row['월수입']
    burden = price / max(income, 1)
    category = row['카테고리']
    grade = row['가격등급']
    cat = category_profiles[category]
    stability = job_profiles[row['직업']]['stability']

    # 경제적 부담: 구매후회의 가장 큰 요인.
    burden_score = clamp((burden - 0.03) / 0.65)

    # 상품·카테고리 고유 위험.
    product_score = 0.55 * cat['regret_base'] + 0.45 * grade_risk[grade]

    # 구매 전 신중성: 높을수록 후회 감소.
    deliberation = clamp(0.35 * math.log1p(row['상품조회수']) / math.log(60)
                         + 0.35 * clamp(row['비교상품수'] / 12)
                         + 0.30 * clamp(row['재방문횟수'] / 10))

    # 충동구매 신호.
    night = 1 if (row['구매시간대'] >= 22 or row['구매시간대'] <= 3) else 0
    low_compare = 1 if row['비교상품수'] <= 1 else 0
    low_revisit = 1 if row['재방문횟수'] <= 1 else 0
    installment = 1 if row['카드할부여부'] == 'Y' else 0
    impulse = clamp(0.33 * night + 0.25 * low_compare + 0.18 * low_revisit + 0.24 * installment)

    # 사용자-상품 적합성.
    mismatch = 0.0
    if row['소비성향'] == '진보적' and cat['trend'] >= 0.65 and grade in ['고가', '초고가']:
        mismatch += 0.12  # 유행·과시성 고가 상품의 사후 후회 가능성
    if row['소비성향'] == '보수적' and cat['practical'] >= 0.75:
        mismatch -= 0.07  # 실용재 구매에는 후회 감소
    if row['결혼여부'] == '기혼' and category in ['명품', '패션', '여행'] and burden > 0.18:
        mismatch += 0.10
    if row['나이'] < 25 and grade in ['고가', '초고가']:
        mismatch += 0.08
    if row['나이'] >= 55 and category in ['전자기기', '명품'] and grade in ['고가', '초고가']:
        mismatch += 0.06

    # 직업 안정성과 소득 변동성.
    instability_penalty = (1 - stability) * clamp((burden - 0.08) / 0.45)

    score = (
        0.34 * burden_score
        + 0.22 * product_score
        + 0.18 * impulse
        + 0.14 * instability_penalty
        + 0.12 * mismatch
        - 0.24 * deliberation
        + 0.16
    )

    # 결정론적 미세 변동: 동일 규칙 내에서 현실의 설명되지 않는 차이를 ±0.025만 반영한다.
    eps = stable_float('eps', row['성별'], row['나이'], row['직업'], row['가격'], row['브랜드'], row['상품조회수'], low=-0.025, high=0.025)
    return round(clamp(score + eps), 3)

# -----------------------------
# 4. 데이터 생성
# -----------------------------
rows = []
idx = 0
sexes = ['male', 'female']
jobs = list(job_profiles.keys())
categories = list(category_profiles.keys())

# 충분한 조합 다양성을 확보하기 위해 사용자-상품-행동 조합을 결정론적으로 순회한다.
while len(rows) < 1500:
    job = jobs[idx % len(jobs)]
    jp = job_profiles[job]
    age = jp['ages'][idx % len(jp['ages'])]
    income_base = jp['income'][(idx // len(jobs)) % len(jp['income'])]
    income_adjustment = int(round(stable_float('income_adj', job, age, idx, low=-0.08, high=0.10) * income_base / 10000) * 10000)
    income = max(300000, income_base + income_adjustment)
    sex = sexes[(idx // 3) % 2]
    married = marital_status(age, job, idx)
    orientation = spending_orientation(age, job, income, idx)

    category = categories[(idx * 7 + idx // 5) % len(categories)]
    cat = category_profiles[category]
    typical = cat['typical_grades']
    # 카테고리의 일반 가격등급을 우선하되, 일부 인접 등급도 포함한다.
    grade = typical[(idx // 2) % len(typical)]
    if stable_float('grade_shift', idx, category) < 0.12:
        grade = list(price_grade_ranges.keys())[(list(price_grade_ranges.keys()).index(grade) + 1) % len(price_grade_ranges)]
    price = price_from_grade(category, grade, idx)
    brand = cat['brands'][(idx * 3 + len(job)) % len(cat['brands'])]

    views, comps, hour, installment, revisit = behavior_values(category, grade, price, income, orientation, age, idx)

    row = {
        '성별': sex,
        '나이': age,
        '월수입': income,
        '직업': job,
        '결혼여부': married,
        '소비성향': orientation,
        '가격': price,
        '가격등급': grade,
        '카테고리': category,
        '브랜드': brand,
        '상품조회수': views,
        '비교상품수': comps,
        '구매시간대': hour,
        '카드할부여부': installment,
        '재방문횟수': revisit,
    }
    row['구매후회값'] = regret_score(row)
    rows.append(row)
    idx += 1

columns = ['성별', '나이', '월수입', '직업', '결혼여부', '소비성향', '가격', '가격등급', '카테고리', '브랜드', '상품조회수', '비교상품수', '구매시간대', '카드할부여부', '재방문횟수', '구매후회값']
df = pd.DataFrame(rows, columns=columns)

csv_path = OUT_DIR / 'purchase_regret_training_dataset_1500.csv'
xlsx_path = OUT_DIR / 'purchase_regret_training_dataset_1500.xlsx'
df.to_csv(csv_path, index=False, encoding='utf-8-sig')
df.to_excel(xlsx_path, index=False)

# -----------------------------
# 5. 품질 요약 및 시각화
# -----------------------------
summary = []
summary.append('# 구매후회 예측 학습용 데이터셋 품질 요약\n')
summary.append(f'- 총 행 수: {len(df):,}건')
summary.append(f'- 총 열 수: {len(df.columns):,}개')
summary.append(f'- 구매후회값 범위: {df["구매후회값"].min():.3f} ~ {df["구매후회값"].max():.3f}')
summary.append(f'- 구매후회값 평균: {df["구매후회값"].mean():.3f}')
summary.append(f'- 구매후회값 표준편차: {df["구매후회값"].std():.3f}')
summary.append('\n## 가격등급별 평균 구매후회값\n')
summary.append(df.groupby('가격등급')['구매후회값'].agg(['count', 'mean', 'min', 'max']).reindex(['초저가','저가','중저가','고가','초고가']).round(3).to_markdown())
summary.append('\n\n## 카테고리별 평균 구매후회값\n')
summary.append(df.groupby('카테고리')['구매후회값'].agg(['count', 'mean', 'min', 'max']).sort_values('mean', ascending=False).round(3).to_markdown())
summary.append('\n\n## 카드할부여부별 평균 구매후회값\n')
summary.append(df.groupby('카드할부여부')['구매후회값'].agg(['count', 'mean']).round(3).to_markdown())
summary.append('\n\n## 검증 관찰\n')
summary.append('가격등급이 높고, 소득 대비 가격 부담률이 높으며, 심야 구매·할부·낮은 비교 행동이 결합된 표본에서 구매후회값이 상승하도록 설계되었다. 반대로 실용 카테고리, 낮은 부담률, 높은 조회·비교·재방문 행동에서는 구매후회값이 낮아진다.')

summary_path = OUT_DIR / 'dataset_quality_summary.md'
summary_path.write_text('\n'.join(summary), encoding='utf-8')

sns.set_theme(style='whitegrid')
plt.rcParams['axes.unicode_minus'] = False

plt.figure(figsize=(8, 5))
sns.histplot(df['구매후회값'], bins=30, kde=True, color='#4C72B0')
plt.title('Distribution of Purchase Regret Score')
plt.xlabel('Purchase Regret Score')
plt.ylabel('Count')
plt.tight_layout()
plt.savefig(OUT_DIR / 'regret_score_distribution.png', dpi=160)
plt.close()

plot_df = df.copy()
grade_en = {'초저가': 'Ultra-low', '저가': 'Low', '중저가': 'Mid-low', '고가': 'High', '초고가': 'Ultra-high'}
category_en = {
    '식품': 'Food', '생활용품': 'Household', '패션': 'Fashion', '화장품': 'Cosmetics',
    '전자기기': 'Electronics', '가구': 'Furniture', '명품': 'Luxury', '여행': 'Travel',
    '교육': 'Education', '건강관리': 'Health Care'
}
plot_df['price_grade_en'] = plot_df['가격등급'].map(grade_en)
plot_df['category_en'] = plot_df['카테고리'].map(category_en)

plt.figure(figsize=(8, 5))
order = ['Ultra-low', 'Low', 'Mid-low', 'High', 'Ultra-high']
sns.barplot(data=plot_df, x='price_grade_en', y='구매후회값', order=order, color='#55A868')
plt.title('Average Purchase Regret by Price Grade')
plt.xlabel('Price Grade')
plt.ylabel('Average Regret Score')
plt.tight_layout()
plt.savefig(OUT_DIR / 'avg_regret_by_price_grade.png', dpi=160)
plt.close()

plt.figure(figsize=(10, 5))
cat_order_ko = df.groupby('카테고리')['구매후회값'].mean().sort_values(ascending=False).index
cat_order = [category_en[c] for c in cat_order_ko]
sns.barplot(data=plot_df, x='category_en', y='구매후회값', order=cat_order, color='#C44E52')
plt.title('Average Purchase Regret by Category')
plt.xlabel('Category')
plt.ylabel('Average Regret Score')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(OUT_DIR / 'avg_regret_by_category.png', dpi=160)
plt.close()

print(csv_path)
print(xlsx_path)
print(summary_path)
print(df.head(10).to_string(index=False))
