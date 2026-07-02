from signal_desk.signals import macro


def _ind(key, value, change, direction=None):
    d = {"key": key, "label": key, "unit": "%", "value": value, "change": change}
    d["dir"] = direction if direction is not None else (0 if not change else (1 if change > 0 else -1))
    return d


def test_read_empty_is_not_ready():
    out = macro.read([])
    assert out["ready"] is False and out["bias"] is None


def test_hot_rising_cpi_and_rising_rates_are_unfavorable():
    indicators = [
        _ind("CPIAUCSL", 4.3, 0.3),   # 3% 초과 + 상승
        _ind("FEDFUNDS", 5.0, 0.25),  # 금리 상승
        _ind("DGS10", 4.6, 0.1),      # 금리 상승
    ]
    out = macro.read(indicators)
    assert out["ready"] is True
    assert out["bias"] == "비우호"
    assert out["score"] < 0


def test_disinflation_and_falling_rates_calm_vix_are_favorable():
    indicators = [
        _ind("CPIAUCSL", 2.5, -0.2),         # 둔화
        _ind("FEDFUNDS", 3.0, -0.25),        # 금리 인하
        _ind("NASDAQCOM", 15000, 1.5),       # 나스닥 상승
        _ind("VIXCLS", 15.0, -1.0),          # 안도
    ]
    out = macro.read(indicators)
    assert out["bias"] == "우호"
    assert out["score"] > 0
    assert any("나스닥" in r for r in out["reasons"])


def test_mixed_signals_are_neutral():
    indicators = [
        _ind("FEDFUNDS", 4.0, 0.25),    # 비우호
        _ind("NASDAQCOM", 15000, 1.0),  # 우호
    ]
    out = macro.read(indicators)
    assert out["bias"] == "중립"
