"""참고용 목표가 — 밸류에이션 정상화(PER 회귀) + 기술적 저항. 매도 실행 규칙(risk.py)과 별개의
'참고 지표'다(투자 자문·보장 아님). 데이터 없으면 해당 항목은 None.

- value_target: 현재 PER이 유니버스(향후 섹터) 중앙값 PER로 회귀한다고 가정한 적정가.
  target = price × (median_per / per). 이상치 방지로 현재가의 0.5~2.0배로 클램프.
- resistance: 최근 N거래일 고점(직전 저항선). 현재가가 이미 그 위면 upside는 음수.
"""

from __future__ import annotations

import statistics

_MED_MIN = 5         # 중앙값 신뢰 위한 최소 표본
_CLAMP_LO = 0.5      # 목표가 하한(현재가 대비)
_CLAMP_HI = 2.0      # 목표가 상한(현재가 대비) — 초저PER 이상치로 과대 목표 방지
_RESIST_WINDOW = 60  # 저항선 산정 최근 거래일


def median_per(fundamentals: dict[str, dict]) -> float | None:
    """유니버스 내 유효 PER(>0) 중앙값. 표본 부족 시 None."""
    pers = [m["per"] for m in fundamentals.values()
            if m.get("per") is not None and m["per"] > 0]
    return round(statistics.median(pers), 2) if len(pers) >= _MED_MIN else None


def compute(price: float | None, per: float | None, med_per: float | None,
            closes: list[float] | None) -> dict | None:
    """참고 목표가 dict. {value_target, value_upside_pct, resistance, resistance_upside_pct, basis}.
    계산 가능한 항목만 채우고 전부 불가하면 None."""
    if not price or price <= 0:
        return None
    out: dict = {"basis": []}

    if per and per > 0 and med_per and med_per > 0:
        raw = price * (med_per / per)
        target = round(max(price * _CLAMP_LO, min(price * _CLAMP_HI, raw)))
        out["value_target"] = target
        out["value_upside_pct"] = round((target / price - 1) * 100, 1)
        out["basis"].append(f"PER {per:.1f}→중앙값 {med_per:.1f} 회귀")

    if closes and len(closes) >= 20:
        resist = round(max(closes[-_RESIST_WINDOW:]))
        out["resistance"] = resist
        out["resistance_upside_pct"] = round((resist / price - 1) * 100, 1)
        out["basis"].append(f"최근 {min(len(closes), _RESIST_WINDOW)}일 고점")

    return out if (out.get("value_target") or out.get("resistance")) else None
