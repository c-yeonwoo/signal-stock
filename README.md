# signal-stock

**Signal STOCK** — "감이 아니라 검증된 적중률로" 주식 매매 타이밍을 찾는 논스톱 시그널 플랫폼.

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

.venv/bin/sigstock serve      # http://127.0.0.1:8765

.venv/bin/pytest -q
```

## 구조

```
src/signal_stock/
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
