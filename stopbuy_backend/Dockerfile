FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 프로덕션 모드 실행
# 개발 모드(--reload + 소스 마운트)는 docker-compose.dev.yml의 command 항목이 이 CMD를 오버라이드함
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
