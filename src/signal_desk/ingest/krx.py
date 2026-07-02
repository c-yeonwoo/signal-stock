"""KRX 시세 수집 — pykrx 래핑.

주의(2026-07 직접 확인): pykrx의 "시장 전체/지수 구성종목" 계열 엔드포인트
(`get_index_portfolio_deposit_file`, `get_market_cap_by_ticker`, `get_market_ohlcv_by_ticker`,
`get_market_ticker_list`)가 전부 `Expecting value: line 1 column 1` JSON 파싱 에러로 깨져 있다 —
KRX가 해당 응답 스키마를 바꿨고 pykrx 최신(1.2.8)이 아직 못 따라간 것으로 보인다(재현 확인됨).
반면 **종목별 시계열**(`get_market_ohlcv_by_date`)과 **단일 종목명 조회**(`get_market_ticker_name`)는
정상 동작한다.

그래서 이번 1차 구현은 "코스피200 편입종목"을 프로그래밍적으로 가져오지 못하고, 잘 알려진
대형주를 임시 유니버스로 하드코딩한다 — 각 코드는 `get_market_ticker_name`으로 실시간 검증해
존재하지 않으면 제외한다. KRX Data Marketplace 키가 오거나 pykrx가 위 엔드포인트를 고치면
`universe()` 내부만 교체하면 되고, 상위 레이어(engine/store/api)는 이 함수의 반환 형태에만
의존하므로 영향 없다.
"""

from __future__ import annotations

import logging

from pykrx import stock

log = logging.getLogger("signal_desk.ingest.krx")

# TODO(코스피200): pykrx 지수구성종목 API가 깨져 있어(위 설명 참고) 임시로 대형주를 하드코딩.
# 실제 코스피200 전체 리스트로 교체 필요 — KRX Data Marketplace 키 확보 시 최우선 작업.
_INTERIM_TICKERS = [
    "005930", "000660", "373220", "207940", "005380", "000270", "005490", "035420",
    "068270", "035720", "051910", "006400", "105560", "055550", "012330", "032830",
    "003670", "066570", "028260", "015760", "034730", "018260", "010130", "042660",
    "011200", "086790", "024110", "138040", "323410", "259960",
]


def universe() -> list[dict]:
    """유니버스(ticker+name) 목록. 코드마다 실시간 검증해 존재하지 않는 코드는 제외한다."""
    out = []
    for code in _INTERIM_TICKERS:
        try:
            name = stock.get_market_ticker_name(code)
        except Exception:
            name = None
        if not name or not isinstance(name, str):
            log.warning("유니버스 종목코드 검증 실패, 제외: %s", code)
            continue
        out.append({"ticker": code, "name": name})
    return out


def ohlcv(ticker: str, start: str, end: str) -> list[dict]:
    """종목별 일봉(시가/종가). start/end는 'YYYYMMDD'. 오래된→최신 순 정렬."""
    df = stock.get_market_ohlcv_by_date(start, end, ticker)
    if df is None or df.empty:
        return []
    df = df.sort_index()
    return [
        {"date": idx.strftime("%Y-%m-%d"), "open": float(row["시가"]), "close": float(row["종가"])}
        for idx, row in df.iterrows()
    ]
