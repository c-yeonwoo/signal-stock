"""상대강도 리더보드 — 조정장에서 '시장 대비 선방/역행하는' 종목을 감시하는 렌즈.

주의: 상대강도는 새 알파가 아니라 **재센터링**이다(횡단면 IC는 절대모멘텀과 동일 — 2026-07 실측).
'조정장 리더가 다음 상승장을 이끈다'는 그럴듯한 가설이지 검증된 예측이 아니다. 그래서 이건 **매수
신호가 아니라 감시 렌즈**로만 쓴다(대기 중 후보 관찰용). 지수는 동일가중 프록시(load_index_history).

rs = 종목 N일 수익률 − 지수 N일 수익률. 순수 함수(입력 주입, 테스트 분리).
"""

from __future__ import annotations


def _ret(closes: list[float], window: int) -> float | None:
    if not closes or len(closes) <= window:
        return None
    past = closes[-1 - window]
    return (closes[-1] / past - 1) if past else None


def leaderboard(prices_by_ticker: dict[str, list[float]], index_closes: list[float] | None,
                names: dict[str, str] | None = None, top: int = 12,
                window: int = 60, short_window: int = 20) -> list[dict]:
    """시장(지수) 대비 상대강도 상위 종목. rs = 종목수익 − 지수수익(window·short_window 각각).
    window 상대강도 내림차순 top개. 반환: [{ticker,name,rs,rs_short,ret}] (rs=%p)."""
    names = names or {}
    idx = _ret(index_closes or [], window)
    idx_s = _ret(index_closes or [], short_window)
    rows = []
    for ticker, closes in (prices_by_ticker or {}).items():
        r = _ret(closes, window)
        if r is None or idx is None:
            continue
        rs = (r - idx) * 100
        r_s = _ret(closes, short_window)
        rs_s = (r_s - idx_s) * 100 if (r_s is not None and idx_s is not None) else None
        rows.append({"ticker": ticker, "name": names.get(ticker, ticker),
                     "rs": round(rs, 1), "rs_short": round(rs_s, 1) if rs_s is not None else None,
                     "ret": round(r * 100, 1)})
    rows.sort(key=lambda x: x["rs"], reverse=True)
    return rows[:top]
