"""자체 모의계좌(paper) 브로커 백엔드 — 가상 체결·현금·포지션 정합성."""

from signal_desk import config, store
from signal_desk.broker import paper


def _seed(monkeypatch, tmp_path, price=70000.0):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "paper_seed_cash", lambda: 1_000_000.0)
    monkeypatch.setattr(store, "load_price_series", lambda: {"005930": [price]})
    monkeypatch.setattr(store, "load_universe", lambda: [{"ticker": "005930", "name": "삼성전자"}])


def test_paper_buy_sell_cash_and_positions(tmp_path, monkeypatch):
    _seed(monkeypatch, tmp_path)
    assert paper.balance()["cash"] == 1_000_000.0

    assert paper.place_order("005930", "buy", 10, price=70000.0)["order_no"] == "PAPER"
    b = paper.balance()
    assert b["cash"] == 300_000.0                      # 100만 − 70만
    assert b["holdings"][0] == {"ticker": "005930", "name": "삼성전자", "qty": 10,
                                "avg_price": 70000.0, "price": 70000.0, "pnl_pct": 0.0}

    paper.place_order("005930", "sell", 4, price=75000.0)
    b = paper.balance()
    assert b["cash"] == 600_000.0                      # 30만 + 4×75000
    assert b["holdings"][0]["qty"] == 6


def test_paper_rejects_insufficient(tmp_path, monkeypatch):
    _seed(monkeypatch, tmp_path)
    assert paper.place_order("005930", "buy", 100, price=70000.0) is None  # 현금 부족
    assert paper.place_order("005930", "sell", 1, price=70000.0) is None   # 미보유


def test_paper_pnl_from_price_cache(tmp_path, monkeypatch):
    _seed(monkeypatch, tmp_path, price=70000.0)
    paper.place_order("005930", "buy", 5, price=70000.0)
    monkeypatch.setattr(store, "load_price_series", lambda: {"005930": [77000.0]})  # +10%
    h = paper.balance()["holdings"][0]
    assert h["price"] == 77000.0 and h["pnl_pct"] == 10.0
