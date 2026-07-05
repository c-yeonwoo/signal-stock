"""포트폴리오 시나리오 분석(#9) — 보유종목 과거 일간수익률을 부트스트랩 몬테카를로로 재표집해
전략(성향)별 N년 후 가치 분포를 확률·범위로 투영한다.

'예측'이 아니라 과거 변동성 구조를 재현한 확률적 시나리오다(면책 상시). 성향은 주식 노출도로
반영 — 안정형은 현금 비중이 커 변동성·기대수익 둘 다 낮고, 공격형은 전액 주식에 가깝다.
현금 부분은 무위험(수익·변동성 0)으로 근사해, 노출도가 일간수익을 비례 축소한다.

⚠️ 시세 데이터가 스케일/근사라 절대 금액은 예시 수준 — 전략 간 상대 비교·방법론 용도로 본다.
"""

from __future__ import annotations

import numpy as np

# 성향별 주식 노출도(나머지는 현금). 리밸런싱 목표비중과 결이 같게 안정형↓·공격형↑.
EQUITY_EXPOSURE = {"conservative": 0.60, "balanced": 0.85, "aggressive": 1.00}
_TRADING_DAYS = 252
_MIN_HISTORY = 60  # 최소 과거 표본(일)


def _portfolio_returns(holdings: list[dict], prices: dict[str, list[float]]) -> tuple[np.ndarray, float]:
    """보유종목을 현재 평가액 가중으로 합친 일간수익률 배열 + 현재 총평가액. 유효 종목 없으면 (빈,0)."""
    series, weights, total = {}, {}, 0.0
    for h in holdings:
        closes = prices.get(h["ticker"])
        if not closes or len(closes) < _MIN_HISTORY:
            continue
        px = float(closes[-1])
        val = px * float(h.get("qty") or 0)
        if val <= 0:
            continue
        series[h["ticker"]] = np.asarray(closes, dtype=float)
        weights[h["ticker"]] = val
        total += val
    if not series or total <= 0:
        return np.array([]), 0.0
    n = min(len(s) for s in series.values())
    port = np.zeros(n - 1)
    for t, s in series.items():
        r = np.diff(s[-n:]) / s[-n:][:-1]
        port += (weights[t] / total) * r
    return port, total


def _simulate(daily: np.ndarray, exposure: float, years: int, sims: int, seed: int) -> np.ndarray:
    """부트스트랩: 과거 일간수익률을 복원추출해 노출도 반영, years년 종료 배수 분포(sims개) 반환."""
    rng = np.random.default_rng(seed)
    steps = years * _TRADING_DAYS
    idx = rng.integers(0, len(daily), size=(sims, steps))
    sampled = daily[idx] * exposure          # 현금 비중만큼 수익·변동성 축소
    return np.prod(1.0 + sampled, axis=1)     # 각 시뮬 종료 배수


def _pct(arr: np.ndarray, base: float, ps=(10, 25, 50, 75, 90)) -> dict:
    return {f"p{p}": round(base * float(np.percentile(arr, p)), 2) for p in ps}


def project(holdings: list[dict], prices: dict[str, list[float]], years: int = 3,
            sims: int = 2000, styles: tuple[str, ...] = ("conservative", "balanced", "aggressive")) -> dict:
    """전략별 N년 후 포트폴리오 가치 분포. 반환: {ready, current_value, years, strategies:{...}}.
    각 strategy: {exposure, terminal:{p10..p90 금액}, cagr:{p10/p50/p90 %}, fan:[연도별 p10/p50/p90]}."""
    daily, total = _portfolio_returns(holdings, prices)
    if daily.size < _MIN_HISTORY or total <= 0:
        return {"ready": False, "reason": "투영에 쓸 과거 시세가 있는 보유종목이 부족합니다."}
    out = {}
    for style in styles:
        exp = EQUITY_EXPOSURE.get(style, 0.85)
        term = _simulate(daily, exp, years, sims, seed=1234)  # 고정 시드(재현성)
        cagr = {f"p{p}": round((float(np.percentile(term, p)) ** (1 / years) - 1) * 100, 2)
                for p in (10, 50, 90)}
        fan = []
        for y in range(1, years + 1):
            py = _simulate(daily, exp, y, sims, seed=1234)
            fan.append({"year": y, "p10": round(total * float(np.percentile(py, 10)), 2),
                        "p50": round(total * float(np.percentile(py, 50)), 2),
                        "p90": round(total * float(np.percentile(py, 90)), 2)})
        out[style] = {"exposure": exp, "terminal": _pct(term, total), "cagr": cagr, "fan": fan}
    return {"ready": True, "current_value": round(total, 2), "years": years,
            "sims": sims, "strategies": out,
            "disclaimer": "과거 변동성 기반 확률적 시나리오 — 수익 보장·예측이 아니며, 시세가 스케일 데이터라 "
                          "절대 금액은 예시 수준입니다. 전략 간 상대 비교 용도로 참고하세요."}
