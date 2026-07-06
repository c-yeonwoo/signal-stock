"""유저별 예약 주문 실행 — paper 계좌 기준."""

import json

from signal_desk import bot, db, store

UID = 6


def _setup(monkeypatch, tmp_path, prices):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(store, "load_price_series", lambda: prices)
    monkeypatch.setattr(store, "load_us_price_series", lambda: {})
    monkeypatch.setattr(store, "load_universe", lambda: [{"ticker": "AAA", "name": "가"}])
    db.kv_set(f"paper_account:{UID}", json.dumps({"cash": 100_000.0, "positions": {}}))


def test_execute_reservation_fills_within_chase(tmp_path, monkeypatch):
    _setup(monkeypatch, tmp_path, {"AAA": [100.0, 101.0]})  # 현재가 101
    db.bot_reservation_add(UID, "AAA", "가", "buy", 100.0, 0.02, "테스트")  # 상한 102
    out = bot.execute_reservations(UID)
    assert out["executed"][0]["status"] == "filled"          # 101 ≤ 102 → 체결
    assert db.bot_reservations_pending(UID) == []
    assert db.bot_position_get(UID, "AAA")["qty"] >= 1        # paper에 반영


def test_execute_reservation_skips_when_price_ran_up(tmp_path, monkeypatch):
    _setup(monkeypatch, tmp_path, {"AAA": [100.0, 110.0]})  # 현재가 110(+10%)
    db.bot_reservation_add(UID, "AAA", "가", "buy", 100.0, 0.02, "테스트")  # 상한 102
    out = bot.execute_reservations(UID)
    assert out["executed"][0]["status"] == "skipped_price"   # 110 > 102 → 추격 안 함
    assert db.bot_position_get(UID, "AAA") is None


def test_execute_reservations_none_pending(tmp_path, monkeypatch):
    _setup(monkeypatch, tmp_path, {"AAA": [100.0]})
    out = bot.execute_reservations(UID)
    assert out["ok"] is True and out["executed"] == []


def test_reservations_isolated_by_market(tmp_path, monkeypatch):
    """국내/해외 예약 격리 — 한 시장 예약이 다른 시장에 안 보이고, 실행도 각자 계좌로."""
    _setup(monkeypatch, tmp_path, {"AAA": [100.0, 101.0]})
    monkeypatch.setattr(store, "load_us_price_series", lambda: {"AAPL": [200.0, 201.0]})
    monkeypatch.setattr(store, "load_us_universe", lambda: [{"ticker": "AAPL", "name": "Apple"}])
    db.kv_set(f"paper_account:{UID}:us", json.dumps({"cash": 100_000.0, "positions": {}}))

    db.bot_reservation_add(UID, "AAA", "가", "buy", 100.0, 0.02, "국내", market="kr")
    db.bot_reservation_add(UID, "AAPL", "Apple", "buy", 200.0, 0.02, "해외", market="us")

    kr = db.bot_reservations_pending(UID, "kr")
    us = db.bot_reservations_pending(UID, "us")
    assert [r["ticker"] for r in kr] == ["AAA"]      # 국내엔 국내만
    assert [r["ticker"] for r in us] == ["AAPL"]     # 해외엔 해외만

    out = bot.execute_reservations(UID, market="us")
    assert out["market"] == "us" and out["executed"][0]["ticker"] == "AAPL"
    assert db.bot_position_get(UID, "AAPL") is not None                 # us 계좌에 체결
    assert db.bot_reservations_pending(UID, "kr")[0]["ticker"] == "AAA"  # 국내 예약은 그대로 대기
