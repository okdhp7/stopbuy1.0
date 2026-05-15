# StopBuy Frontend Dockerfile
# 멀티스테이지 빌드: Node.js(Vite) 빌드 → Nginx 서빙

# ── 1단계: 빌드 ──────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# pnpm 설치
RUN npm install -g pnpm@10.4.1

# 의존성 파일 복사
COPY package.json pnpm-lock.yaml* ./

# wouter 패치 설정 제거 (한 줄 처리 - Docker 파싱 오류 방지)
RUN node -e "var f='package.json',p=JSON.parse(require('fs').readFileSync(f,'utf8'));if(p.pnpm&&p.pnpm.patchedDependencies)delete p.pnpm.patchedDependencies;require('fs').writeFileSync(f,JSON.stringify(p,null,2));"

# 의존성 설치
RUN pnpm install --no-frozen-lockfile

# 소스 복사
COPY . .

# Vite 빌드만 실행 (esbuild server 번들링 제외 - Nginx가 정적 파일 서빙)
RUN pnpm run build:docker

# ── 2단계: 서빙 ──────────────────────────────────────────
FROM nginx:1.27-alpine AS production

# Nginx 설정 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Vite 빌드 결과물 복사 (vite.config.ts: outDir = dist/public)
COPY --from=builder /app/dist/public /usr/share/nginx/html

# 헬스체크용 파일 생성
RUN echo "ok" > /usr/share/nginx/html/health.txt

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
