"""중기 모멘텀 팩터 — 12-1개월 수익률(직전 1개월 제외). 학술적으로 가장 견고한 가격 팩터 중 하나.

기술(RSI/MACD 단기)·낙폭과대(급락 반등)와 달리 '중기 추세의 방향·강도'를 본다. 가격만 필요해
결정론적 → 백테스트(_price_only_components)에도 동일 반영해 라이브와 일관되게 한다.
직전 1개월(skip)을 빼는 건 단기 반전 노이즈 제거(모멘텀 문헌 표준).
"""

from __future__ import annotations


def score_at(closes: list[float], i: int, config) -> tuple[float, float, list[str], float | None, bool]:
    """인덱스 i 시점의 12-1개월 모멘텀. (norm[-1,1], weight, reasons, ret, has). 이력 부족 시 제외."""
    lb, sk = config.momentum_lookback, config.momentum_skip
    if i < lb:                       # 12개월치 이력 없으면 제외(가중치 0)
        return 0.0, 0.0, [], None, False
    past = closes[i - lb]
    recent = closes[i - sk] if i - sk >= 0 else closes[i]
    if not past or past <= 0:
        return 0.0, 0.0, [], None, False
    ret = recent / past - 1
    norm = max(-1.0, min(1.0, ret / config.momentum_scale))
    tag = "상승 추세" if ret > 0 else "하락 추세"
    reason = f"[모멘텀] 12-1개월 {ret * 100:+.0f}% — {tag}"
    return round(norm, 3), config.weight_momentum, [reason], round(ret, 4), True
