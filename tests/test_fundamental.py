from signal_desk.signals import fundamental as fnd


def test_no_data():
    r = fnd.score({})
    assert r.has_data is False
    assert r.score == 0.0
    assert "재무데이터 없음" in r.reasons


def test_all_positive_clamped_to_2():
    r = fnd.score({"roe": 20, "per": 8, "pbr": 0.8, "revenue_growth": 20, "dividend_yield": 4})
    assert r.has_data is True
    assert r.score == 2.0  # 1.0+0.7+0.5+0.7+0.2 = 3.1 -> clamp 2.0


def test_all_negative_clamped_to_neg2():
    r = fnd.score({"roe": 2, "per": 30, "pbr": 4, "revenue_growth": -5, "debt_ratio": 250})
    assert r.has_data is True
    assert r.score == -2.0  # -0.5-0.5-0.3-0.5-0.5 = -2.3 -> clamp -2.0


def test_per_zero_or_negative_ignored():
    r = fnd.score({"per": -5, "roe": 12})
    assert r.score == 0.5  # only ROE band applies, per<=0 skipped


def test_roe_neutral_band_no_reason():
    r = fnd.score({"roe": 7})
    assert r.score == 0.0
    assert r.reasons == []
