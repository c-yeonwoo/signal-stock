"""중기 모멘텀 팩터(12-1개월) — 가격 기반, 라이브+백테스트 반영."""

from signal_desk.signals import engine, momentum


def _cfg():
    return engine.SignalConfig()


def test_momentum_uptrend_positive():
    cfg = _cfg()
    closes = [100.0 + i * 0.3 for i in range(300)]  # 꾸준한 상승
    n, w, r, ret, has = momentum.score_at(closes, len(closes) - 1, cfg)
    assert has and n > 0 and ret > 0 and "[모멘텀]" in r[0] and "상승" in r[0]


def test_momentum_downtrend_negative():
    cfg = _cfg()
    closes = [200.0 - i * 0.3 for i in range(300)]  # 꾸준한 하락
    n, w, r, ret, has = momentum.score_at(closes, len(closes) - 1, cfg)
    assert has and n < 0 and ret < 0 and "하락" in r[0]


def test_momentum_excluded_short_history():
    cfg = _cfg()
    n, w, r, ret, has = momentum.score_at([100.0] * 100, 99, cfg)  # 252봉 미만
    assert not has and w == 0.0 and ret is None


def test_evaluate_includes_momentum():
    uni = [{"ticker": "005930", "name": "삼성전자"}]
    prices = {"005930": [100.0 + i * 0.2 for i in range(300)]}
    r = engine.evaluate(uni, prices)[0]
    assert r.has_momentum and r.momentum_ret is not None and any("[모멘텀]" in x for x in r.reasons)
