"""시장 전체(KOSPI) 투자자 수급(토스) — pykrx 종목별 수급 대체. 파싱·집계·국면 바이어스."""

from signal_desk import store
from signal_desk.ingest import toss
from signal_desk.signals import regime


def _body(records):
    return {"result": {"records": records, "nextUntil": None}}


def test_toss_market_investor_trading_parses_nets(monkeypatch):
    recs = [
        {"date": "2026-07-07", "foreigner": {"buyAmount": "300", "sellAmount": "100"},
         "institution": {"buyAmount": "50", "sellAmount": "80"},
         "individual": {"buyAmount": "200", "sellAmount": "370"},
         "otherCorporation": {"buyAmount": "10", "sellAmount": "10"}},
        {"date": "2026-07-06", "foreigner": {"buyAmount": "100", "sellAmount": "150"},
         "institution": {"buyAmount": "40", "sellAmount": "20"},
         "individual": {"buyAmount": "0", "sellAmount": "0"},
         "otherCorporation": {"buyAmount": "0", "sellAmount": "0"}},
    ]
    monkeypatch.setattr(toss, "_get", lambda path, params=None: _body(recs))
    out = toss.market_investor_trading("KOSPI", "1d", 20)
    assert out[0]["date"] == "2026-07-07"                    # 최신 우선 정렬
    assert out[0]["foreigner_net"] == 200.0                  # 300-100
    assert out[0]["institution_net"] == -30.0                # 50-80
    assert out[0]["total_buy"] == 560.0                      # 300+50+200+10


def test_market_flow_summary_cumulates_to_jo():
    # 원 단위 순매수 2일치 → 조원 환산 누적
    recs = [
        {"date": "2026-07-07", "foreigner_net": 3e12, "institution_net": -1e12},
        {"date": "2026-07-06", "foreigner_net": 1e12, "institution_net": 2e12},
    ]
    s = store._market_flow_summary(recs)
    assert s["as_of"] == "2026-07-07" and s["days"] == 2
    assert s["foreign_net_20d"] == 4.0 and s["inst_net_20d"] == 1.0
    assert s["smart_net_20d"] == 5.0                          # (3-1)+(1+2)


def test_market_flow_bias_labels():
    mk = lambda n: {"KOSPI": {"smart_net_20d": n, "foreign_net_20d": n, "inst_net_20d": 0, "as_of": "d"}}
    assert regime.market_flow_bias(mk(-3.0))["bias"] == "순매도"
    assert regime.market_flow_bias(mk(3.0))["bias"] == "순매수"
    assert regime.market_flow_bias(mk(0.5))["bias"] == "중립"
    assert regime.market_flow_bias(None)["available"] is False
    assert regime.market_flow_bias({})["available"] is False


def test_fetch_market_flow_skips_without_toss(monkeypatch):
    monkeypatch.setattr(toss, "available", lambda: False)
    assert store.fetch_market_flow() == {}
