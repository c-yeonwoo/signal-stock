"""참고 목표가 — 밸류 정상화(PER 회귀) + 기술적 저항."""

from signal_desk.signals import target


def test_median_per_needs_min_sample():
    assert target.median_per({"A": {"per": 10}}) is None            # 표본 부족(<5)
    fund = {t: {"per": p} for t, p in zip("ABCDE", [8, 10, 12, 14, 100])}
    assert target.median_per(fund) == 12.0                          # 적자/None·음수 제외한 중앙값


def test_value_target_and_clamp():
    # 저PER(10) < 중앙값(20) → 정상화 목표가 2배지만 상한 클램프(×2.0)
    t = target.compute(price=1000.0, per=10.0, med_per=20.0, closes=None)
    assert t["value_target"] == 2000 and t["value_upside_pct"] == 100.0
    # 고PER(40) > 중앙값(20) → 하향 목표(×0.5) 클램프
    t2 = target.compute(price=1000.0, per=40.0, med_per=20.0, closes=None)
    assert t2["value_target"] == 500 and t2["value_upside_pct"] == -50.0


def test_technical_resistance():
    closes = [90.0] * 40 + [100.0, 120.0, 110.0]   # 최근 고점 120
    t = target.compute(price=110.0, per=None, med_per=None, closes=closes)
    assert t["resistance"] == 120 and t["resistance_upside_pct"] == round((120/110-1)*100, 1)


def test_none_when_no_data():
    assert target.compute(price=None, per=10, med_per=20, closes=None) is None
    assert target.compute(price=1000.0, per=None, med_per=None, closes=[1, 2]) is None  # 표본<20, PER없음
