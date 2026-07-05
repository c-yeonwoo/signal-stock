"""통합 후보 유형 분류(#14) — 시그널의 팩터 구성으로 각 종목을 '기회 유형'으로 태깅한다.

시그널 점수(#3)가 이미 기회도(종합) 역할을 하므로 순위는 점수순 그대로 쓰고, 여기서는
'어떤 종류의 기회인가'만 분류해 리스트에서 유형별로 걸러 볼 수 있게 한다. IPO·실적서프라이즈·
턴어라운드는 별도 데이터(상장일·어닝 서프라이즈·점별 재무추세)가 있어야 정확해 지금은 제외.
"""

from __future__ import annotations

from signal_desk.signals.engine import SignalResult

# 유형 임계값 — 팩터 점수/percentile 기준(설명 가능·보수적)
_TECH_MOMENTUM = 0.5     # 기술 점수 이상이면 모멘텀
_FUND_STRONG = 0.6       # 기본 점수 이상이면 실적우량
_VALUE_PCTL = 0.30       # 저평가 percentile 이하(하위 30%)
_QUAL_POS = 0.2          # 정성 심리 이상이면 정성호재

TYPES = ("낙폭과대", "저평가", "모멘텀", "실적우량", "정성호재")


def classify(r: SignalResult) -> list[str]:
    """SignalResult → 기회 유형 태그 목록(0개 이상). 팩터가 없으면(해당 데이터 미보유) 그 유형은 제외."""
    tags = []
    if r.has_reversion and r.reversion_score > 0:            # 과매도 반등 후보
        tags.append("낙폭과대")
    if r.has_valuation and r.valuation_percentile is not None and r.valuation_percentile <= _VALUE_PCTL:
        tags.append("저평가")
    if r.technical_score >= _TECH_MOMENTUM:
        tags.append("모멘텀")
    if r.has_fundamental and r.fundamental_score >= _FUND_STRONG:
        tags.append("실적우량")
    if r.has_qualitative and (r.qualitative_score or 0) >= _QUAL_POS:
        tags.append("정성호재")
    return tags
