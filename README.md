# signal-desk

**Signal Desk** — "감이 아니라 검증된 적중률로" 주식 매매 타이밍을 찾는 논스톱 시그널 플랫폼.

[Signal APT](https://github.com/c-yeonwoo/apt-signal)(데이터로 찾는 아파트 매매 타이밍)의
서비스 본체·아키텍처를 이식하고, 자산을 부동산에서 주식으로 바꿔 재해석한 프로젝트.
현재 [`brightdesk`](../brightdesk)에서 시도했던 주식 시그널 기능 중 일부를 이 뼈대 위에
체리피킹해 얹는 중이다 — 배경은 [CLAUDE.md](CLAUDE.md), 체리피킹 대상은
[NOTES-cherrypick.md](NOTES-cherrypick.md) 참고.

## 현재 상태 (v0.1 — 스캐폴딩)

- ✅ FastAPI 앱 골격 + 인증(회원가입/로그인/세션 쿠키)
- ✅ 온보딩 프로필 API(투자성향·관심 섹터·초기 워치리스트)
- ✅ 워치리스트(즐겨찾기) CRUD API
- ✅ 단일 파일 SPA(`web/index.html`) — 브랜드 토큰, 5탭 해시 라우팅, 인증 게이트, 온보딩 모달
- ⬜ 시그널 엔진 + 백테스트 성적표 (2단계)
- ⬜ 시장 국면 + 매크로 미니차트 (3단계)
- ⬜ 통합 후보 뷰 + 기회도 (4단계)
- ⬜ 밸류에이션(저평가) 뷰 + 섹터 트리맵 (5단계)
- ⬜ 관심·비교·AI 리포트 실데이터 연동 (6단계)

## 설치 & 실행

> ⚠️ Python 3.12 권장 (Signal APT 이력상 3.14는 pandas/pyarrow 세그폴트 — 이 리포는 아직
> pandas 미도입이라 당장은 무관하나 2단계부터 유효).

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/sigdesk serve      # http://127.0.0.1:8765

.venv/bin/pytest -q
```

## 구조

```
src/signal_desk/
├── api.py       # FastAPI 앱 — 인증/온보딩/워치리스트 + 향후 탭용 스텁 라우트
├── auth.py      # pbkdf2 세션 인증 (외부 의존성 0)
├── db.py        # SQLite (users/sessions/profile/favorites/kv)
├── config.py    # 환경변수 로더 + 키 getter
├── store.py     # 캐시 로더 스텁 (2단계에서 시세/시그널 캐시로 확장)
├── cli.py       # typer CLI (serve 동작, fetch/build/report는 2단계 예정)
├── signals/     # 시그널 엔진 (2단계, 현재 빈 패키지)
├── ingest/      # 데이터 수집기 (2단계, 현재 빈 패키지)
└── web/index.html   # 단일 파일 SPA
```

## 환경변수

`.env.example` 참고. 실제 키는 `.env`에 넣고 절대 커밋하지 않는다.

주요 운영 변수:

| 변수 | 용도 |
|---|---|
| `APP_ENV=prod` | prod 모드 — 세션 쿠키 `secure` 플래그(HTTPS 전제) |
| `BROKER_BACKEND=paper\|kis` | 자동매매 백엔드. 미설정 시 KIS 자격증명 있으면 kis, 없으면 paper |
| `KIS_ENV=demo` | KIS 모의투자(권장). 실계좌는 `demo` 외 값 + `ALLOW_REAL_ORDERS=true` 필요 |
| `ALLOW_REAL_ORDERS` | 실계좌 실주문 이중 안전장치(기본 off) |
| `BOT_KILL_SWITCH` | 긴급정지 — 켜면 어떤 주문도 안 나감 |
| `BOT_DAILY_LOSS_LIMIT_PCT=0.08` | 당일 손실 한도 초과 시 신규매수 중단 |
| `ADMIN_EMAILS` | 관리자(엔진·KB 적재·데이터 갱신) 화이트리스트 |
| `FANDING_TT`·`OUTSTANDING_AUTHORS`·`YOUTUBE_CHANNELS` | KB 외부 소스(세션토큰·작가·채널) |
| `ANTHROPIC_API_KEY` | LLM 다이제스트·해설·자문(없으면 규칙기반 폴백) |

## 배포 (prod)

서버(uvicorn)가 자동매매 루프·KB 일일수집을 in-process로 함께 돌린다 —
**컨테이너/프로세스를 항상 켜두면 별도 스케줄러가 필요 없다**(단, 프로세스가 죽으면 멈추므로
docker restart 정책이나 systemd로 상시 기동 보장).

```bash
# 1) 도커
docker build -t signal-desk .
docker run -d --name signal-desk --restart unless-stopped \
  -p 8765:8765 --env-file .env -v signal_desk_data:/app/data signal-desk

# 2) 최초 1회 데이터 적재(컨테이너 안에서) — 실 시세/재무 캐시 생성
docker exec signal-desk sigdesk fetch
```

- **HTTPS**: 앞단에 리버스 프록시(Caddy/Nginx)로 TLS 종단 + `APP_ENV=prod`로 secure 쿠키.
- **DB 백업**: SQLite/parquet 캐시는 `/app/data` 볼륨 → 주기적 스냅샷 백업 권장.
- **데이터 신뢰성**: 샌드박스 캐시 시세는 종목별 스케일 이슈가 있으므로, prod 최초 `sigdesk fetch`로
  실 KRX/증권사 피드를 적재하고 절대값(백테스트·시나리오)이 합리적인지 확인할 것.
- **KB 수집**: 서버가 하루 1회 미주은·오건영·유튜브를 자동수집(증분). `FANDING_TT` 세션토큰은
  만료 시 `.env` 갱신 필요.
