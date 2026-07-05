"""포트폴리오 시나리오 분석(#9) — 부트스트랩 몬테카를로 투영."""

import math

from signal_desk.signals import scenario


def _prices(n=260):
    a = [100 * (1.0006 ** i) * (1 + 0.02 * math.sin(i / 7)) for i in range(n)]
    b = [50 * (1.0003 ** i) * (1 + 0.03 * math.sin(i / 5)) for i in range(n)]
    return {"A": a, "B": b}


def test_project_basic_and_monotonic_exposure():
    out = scenario.project([{"ticker": "A", "qty": 10}, {"ticker": "B", "qty": 20}], _prices(),
                           years=3, sims=1500)
    assert out["ready"] and out["current_value"] > 0
    c = out["strategies"]["conservative"]["cagr"]["p50"]
    b = out["strategies"]["balanced"]["cagr"]["p50"]
    ag = out["strategies"]["aggressive"]["cagr"]["p50"]
    assert c < b < ag                                   # 노출↑ → 기대수익↑(추세장 표본)
    # 분포 순서: p10 ≤ p50 ≤ p90
    t = out["strategies"]["balanced"]["terminal"]
    assert t["p10"] <= t["p50"] <= t["p90"]
    # fan은 연도 수만큼, 시점이 뒤일수록 중앙값 증가(추세)
    fan = out["strategies"]["balanced"]["fan"]
    assert [f["year"] for f in fan] == [1, 2, 3]
    assert fan[0]["p50"] < fan[2]["p50"]


def test_project_reproducible():
    h, p = [{"ticker": "A", "qty": 5}], _prices()
    assert scenario.project(h, p, sims=800) == scenario.project(h, p, sims=800)


def test_project_insufficient_history():
    out = scenario.project([{"ticker": "A", "qty": 1}], {"A": [100, 101, 102]}, years=3)
    assert out["ready"] is False
