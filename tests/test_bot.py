import datetime

import pytest

from signal_desk import bot
from signal_desk.signals.engine import SignalResult


def _creds():
    return {"app_key": "k", "app_secret": "s", "account_no": "1", "product_cd": "01", "env": "demo"}


def _sig(ticker, name, kind, score=0.0):
    return SignalResult(
        ticker=ticker, name=name, score=score, kind=kind, confidence=0.5,
        technical_score=0.0, fundamental_score=0.0, has_fundamental=False, reasons=[],
    )


def _setup_common(monkeypatch, universe, prices, signals, balance_sequence):
    monkeypatch.setattr(bot.config, "kis_credentials", lambda: _creds())
    monkeypatch.setattr(bot, "is_market_hours", lambda: True)
    monkeypatch.setattr(bot.store, "load_universe", lambda: universe)
    monkeypatch.setattr(bot.store, "load_price_series", lambda: prices)
    monkeypatch.setattr(bot.store, "load_fundamentals", lambda: {})
    monkeypatch.setattr(bot.engine, "evaluate", lambda *a, **k: signals)

    calls = iter(balance_sequence)
    monkeypatch.setattr(bot.kis, "balance", lambda creds=None: next(calls))


def test_no_credentials(monkeypatch):
    monkeypatch.setattr(bot.config, "kis_credentials", lambda: None)
    out = bot.run_once()
    assert out == {"ok": False, "reason": "KIS 인증정보 없음(.env 확인)"}


def test_outside_market_hours_blocked_unless_forced(monkeypatch):
    monkeypatch.setattr(bot.config, "kis_credentials", lambda: _creds())
    monkeypatch.setattr(bot, "is_market_hours", lambda: False)
    out = bot.run_once()
    assert out["ok"] is False and "장 시간" in out["reason"]


def test_balance_failure(monkeypatch):
    monkeypatch.setattr(bot.config, "kis_credentials", lambda: _creds())
    monkeypatch.setattr(bot, "is_market_hours", lambda: True)
    monkeypatch.setattr(bot.kis, "balance", lambda creds=None: None)
    out = bot.run_once()
    assert out == {"ok": False, "reason": "KIS 잔고조회 실패"}


def test_no_price_data(monkeypatch):
    monkeypatch.setattr(bot.config, "kis_credentials", lambda: _creds())
    monkeypatch.setattr(bot, "is_market_hours", lambda: True)
    monkeypatch.setattr(bot.kis, "balance", lambda creds=None: {"cash": 100.0, "total_eval": 100.0, "holdings": []})
    monkeypatch.setattr(bot.store, "load_universe", lambda: [])
    monkeypatch.setattr(bot.store, "load_price_series", lambda: {})
    out = bot.run_once()
    assert out["ok"] is False and "시세 데이터" in out["reason"]


def test_sells_on_stop_loss(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    universe = [{"ticker": "005930", "name": "삼성전자"}]
    prices = {"005930": [100.0, 100.0, 90.0]}  # -10% -> 손절(-7%) 발동
    signals = [_sig("005930", "삼성전자", "HOLD")]
    bal_holding = {"cash": 0.0, "total_eval": 900.0,
                   "holdings": [{"ticker": "005930", "name": "삼성전자", "qty": 10, "avg_price": 100.0}]}
    bal_after = {"cash": 900.0, "total_eval": 900.0, "holdings": []}
    _setup_common(monkeypatch, universe, prices, signals, [bal_holding, bal_after, bal_after])

    orders = []
    monkeypatch.setattr(bot.kis, "place_order", lambda ticker, side, qty, price=None, creds=None:
                         orders.append((ticker, side, qty)) or {"order_no": "1", "order_time": "t"})

    out = bot.run_once()
    assert out["ok"] is True
    assert out["sells"] == [{"ticker": "005930", "qty": 10, "reason": "STOP_LOSS", "ok": True}]
    assert orders == [("005930", "sell", 10)]
    assert bot.db.bot_position_get("005930") is None  # 매도 성공 -> 포지션 삭제


def test_sells_on_signal_flip_when_no_risk_trigger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    universe = [{"ticker": "005930", "name": "삼성전자"}]
    prices = {"005930": [100.0, 100.0, 101.0]}  # +1% -> 리스크 룰 미발동
    signals = [_sig("005930", "삼성전자", "SELL")]
    bal_holding = {"cash": 0.0, "total_eval": 1010.0,
                   "holdings": [{"ticker": "005930", "name": "삼성전자", "qty": 10, "avg_price": 100.0}]}
    bal_after = {"cash": 1010.0, "total_eval": 1010.0, "holdings": []}
    _setup_common(monkeypatch, universe, prices, signals, [bal_holding, bal_after, bal_after])
    monkeypatch.setattr(bot.kis, "place_order", lambda *a, **k: {"order_no": "1", "order_time": "t"})

    out = bot.run_once()
    assert out["sells"] == [{"ticker": "005930", "qty": 10, "reason": "SIGNAL", "ok": True}]


def test_holds_position_and_tracks_peak_when_no_exit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    universe = [{"ticker": "005930", "name": "삼성전자"}]
    signals = [_sig("005930", "삼성전자", "HOLD")]
    bal = {"cash": 0.0, "total_eval": 1080.0,
           "holdings": [{"ticker": "005930", "name": "삼성전자", "qty": 10, "avg_price": 100.0}]}

    # 1회차: 오늘 종가 108 -> peak = max(avg_price=100, 108) = 108(이번 회차엔 DB에 이전 기록 없음)
    _setup_common(monkeypatch, universe, {"005930": [108.0]}, signals, [bal, bal, bal])
    out = bot.run_once()
    assert out["sells"] == []
    assert bot.db.bot_position_get("005930")["peak_price"] == 108.0

    # 2회차: 오늘 종가 105로 하락 -> peak은 이전 회차 108을 유지해야 함(트레일링스탑 기준점 보존)
    _setup_common(monkeypatch, universe, {"005930": [105.0]}, signals, [bal, bal, bal])
    out = bot.run_once()
    assert out["sells"] == []
    assert bot.db.bot_position_get("005930")["peak_price"] == 108.0


def test_reconciles_stale_db_position_not_in_kis_balance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot.db.bot_position_upsert("999999", "유령종목", 5, 100.0, 100.0, "2026-01-01")

    universe = [{"ticker": "005930", "name": "삼성전자"}]
    prices = {"005930": [100.0]}
    signals = [_sig("005930", "삼성전자", "HOLD")]
    bal = {"cash": 1000.0, "total_eval": 1000.0, "holdings": []}  # KIS엔 유령종목 없음
    _setup_common(monkeypatch, universe, prices, signals, [bal, bal, bal])

    bot.run_once()
    assert bot.db.bot_position_get("999999") is None


def test_buys_top_scored_signals_respecting_slots_and_lot_size(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    universe = [
        {"ticker": "AAA", "name": "가"}, {"ticker": "BBB", "name": "나"},
        {"ticker": "CCC", "name": "다"}, {"ticker": "EXP", "name": "비싼종목"},
    ]
    prices = {"AAA": [100.0], "BBB": [100.0], "CCC": [100.0], "EXP": [999_999.0]}
    signals = [
        _sig("AAA", "가", "BUY", score=1.5),
        _sig("BBB", "나", "BUY", score=2.0),  # 가장 높은 점수 -> 우선 매수
        _sig("CCC", "다", "BUY", score=1.3),
        _sig("EXP", "비싼종목", "BUY", score=3.0),  # 점수는 1등이지만 배분금액(800)보다 비싸 스킵
    ]
    # position_pct=0.08(기본) * total_eval(10000) = 800원 배분 -> 100원 종목은 8주, EXP(999999원)는 스킵
    bal = {"cash": 10_000.0, "total_eval": 10_000.0, "holdings": []}
    _setup_common(monkeypatch, universe, prices, signals, [bal, bal, bal])

    orders = []
    monkeypatch.setattr(bot.kis, "place_order", lambda ticker, side, qty, price=None, creds=None:
                         orders.append((ticker, side, qty)) or {"order_no": "1", "order_time": "t"})

    out = bot.run_once()
    assert orders == [("BBB", "buy", 8), ("AAA", "buy", 8), ("CCC", "buy", 8)]  # 점수 내림차순
    assert [b["ticker"] for b in out["buys"]] == ["BBB", "AAA", "CCC"]
    assert bot.db.bot_position_get("BBB") == {
        "ticker": "BBB", "name": "나", "qty": 8, "avg_price": 100.0,
        "peak_price": 100.0, "entry_date": bot._today(),
    }


def test_buys_respect_max_positions_slot_limit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    universe = [{"ticker": f"T{i}", "name": f"종목{i}"} for i in range(3)]
    prices = {f"T{i}": [100.0] for i in range(3)}
    signals = [_sig(f"T{i}", f"종목{i}", "BUY", score=float(i)) for i in range(3)]
    bal = {"cash": 10_000.0, "total_eval": 10_000.0, "holdings": []}
    _setup_common(monkeypatch, universe, prices, signals, [bal, bal, bal])
    monkeypatch.setattr(bot.kis, "place_order", lambda *a, **k: {"order_no": "1", "order_time": "t"})

    # max_positions=1로 좁혀서 슬롯 제한 확인
    bot.db.bot_config_get()  # 기본 행 시딩
    conn = bot.db.conn()
    conn.execute("UPDATE bot_config SET max_positions=1 WHERE id=1")
    conn.commit()
    conn.close()

    out = bot.run_once()
    assert len(out["buys"]) == 1
    assert out["buys"][0]["ticker"] == "T2"  # 점수 가장 높은 것만
