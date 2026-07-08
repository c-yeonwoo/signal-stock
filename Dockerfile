# Signal Desk — prod 컨테이너. 서버(FastAPI+uvicorn)가 자동매매 루프·KB 일일수집을
# in-process로 함께 돌리므로, 컨테이너를 항상 켜두면 별도 스케줄러가 필요 없다.
FROM python:3.12-slim

WORKDIR /app

# 숏폼 영상 렌더 시스템 의존성 — ffmpeg(영상 조립) + libcairo/fontconfig(cairosvg의 SVG→PNG).
# cairosvg는 cairocffi가 런타임에 libcairo.so.2를 로드하므로 시스템 라이브러리가 반드시 있어야 한다
# (없으면 import 실패 → 렌더가 'cairosvg 미설치'로 뜬다). 한글 폰트는 레포에도 번들(assets/fonts)하지만
# fonts-nanum도 함께 설치해 안전망을 둔다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libcairo2 libfontconfig1 fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저(레이어 캐시)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# 데이터 캐시/SQLite는 볼륨으로 마운트 권장(백업 대상): -v signal_desk_data:/app/data
ENV HOST=0.0.0.0 PORT=8765 APP_ENV=prod
EXPOSE 8765

# 시세·재무 캐시가 없으면 최초 1회 `sigdesk fetch` 필요(README 참고)
CMD ["sigdesk", "serve"]
