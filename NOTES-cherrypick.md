# brightdesk 체리피킹 참조 노트

`brightdesk`(TanStack Start + Supabase 주식 프로토타입)에서 이미 만들어본 시그널/지표/KB 로직
카탈로그. 이번 1단계 스캐폴딩에는 반영하지 않았고, **2단계(시그널 엔진) 이후 설계 시 참조**한다.
brightdesk 자체 코드를 그대로 옮기지 않고, 여기 정리된 개념·수치만 참고해 Signal APT 구조 위에
새로 구현한다.

## 시그널 엔진 (`signals.server.ts` + `indicators.ts`)

- 시그널 종류: `BUY`(score ≥ 1.2) / `SELL`(score ≤ −1.2) / `HOLD`(그 사이)
- 지표: RSI14(과매도 <30 +1.5pt, 과매수 >70 −1.5pt), MACD(골든/데드크로스 ±1), MA20/60/120(정배열)
- 3팩터 가중(`DEFAULT_WEIGHTS`): technical 0.35 · fundamental 0.30 · kb 0.35 (합=1.0, env로 override)
- 팩터별 점수: technical(−3~+3), fundamental(−2~+2, PER/PBR/ROE/성장/부채비율), kb(−2~+2, sentiment×reliability)
- confidence = sigmoid(score), reasons에 `[기술]/[기본]/[KB]` 태그

## KB / 감성 (`kb.functions.ts`)

- 도메인: macro(거시) · theme(테마) · news(뉴스) · politics(정치)
- fact 필드: fact_key, title, related_tickers[], sentiment(−1~1), reliability(0~1), is_active
- sentiment 라벨: >0.5 강한긍정 / 0.2~0.5 긍정 / −0.2~0.2 중립 / −0.5~−0.2 부정 / <−0.5 강한부정
- source_registry: 소스별 reliability 기본값 예시 — broker_pdf 0.85, news 0.75, ticker_research 0.72,
  mijueun_youtube 0.60, snoomi_kakao 0.40 (스키마 변경 없이 소스 추가 가능한 구조가 핵심 아이디어)

## 리스크/포트폴리오 (`risk.server.ts`, `portfolio.server.ts`)

- 기본 룰: stopLoss −7% / takeProfit +15% / trailing(고점대비) −5%
- 매도 사유 enum: STOP_LOSS · TAKE_PROFIT · TRAILING · SIGNAL · REGIME_DOWNGRADE
- 포지션: portfolio_id/ticker/qty/avg_price. 거래: side(BUY/SELL)/qty/price/fee/tax/signal_id
- 수수료: 국내 0.015%+세금 0.18%(매도시), 해외 0.25%

## 워치리스트 (`user_watchlist`)

- 필드: user_id, ticker, label, priority(1~5, 기본 3), source('manual' 등), is_active,
  last_researched_at
- Signal APT의 `favorites(uid, kind, key, label)`로 대체 — kind='ticker'

## 백테스트/성과 (`outcomes.server.ts`)

- hit 판정: BUY는 ret_5d > 0.5%, SELL은 ret_5d < −0.5%(회피 성공)일 때 hit=true
- entry_price = 시그널 다음 거래일 시가, 평가 lookback 90일, 5거래일 미만 시그널은 스킵
- 저장 필드: signal_id, ticker, kind, entry_date, entry_price, ret_5d, ret_20d, hit, score
- 집계: kind·ticker별 n(건수), winrate(%), avg_ret_5d, avg_ret_20d → **Signal APT의 "성적표" 개념과
  직접 대응** — 2단계 백테스트 성적표 설계 시 이 필드셋을 그대로 기반으로 삼는다.

## 활용 원칙

- 위 수치(가중치·임계값)는 brightdesk에서의 초기값일 뿐 재검증 없이 그대로 채택하지 않는다.
  Signal APT처럼 `signals/engine.py`의 `SignalConfig` 같은 단일 설정 객체에 모아 튜닝 가능하게 한다.
- Signal APT의 "매수세우위(raw) vs 매수우위지수(참고용)" 구분처럼, 주식에서도 시그널 트리거로 쓰는
  지표와 차트 참고용 지표를 명확히 분리해서 설계한다.
