"""자동매매봇 — 시그널 → 리스크 판정 → KIS 모의투자 주문 실행 (BACKLOG #7).

KIS 모의계좌는 서비스 전체가 공유하는 단일 데모 계좌(brightdesk의 "Track A: 자동 운용"과 동일
개념 — 유저별 계좌가 아니라 서버 env 하나). 그래서 `db.py`의 bot_* 테이블도 uid로 스코프하지 않는다.

주문 실행 후에는 항상 KIS 잔고(`broker.kis.balance()`)를 다시 조회해 우리 DB의 포지션을
덮어쓴다 — 우리 계산이 아니라 KIS를 source of truth로 삼는다. 진입 후 고점(peak_price)만은
KIS가 안 줘서 우리가 매 회차 직접 갱신·보관한다(리스크 엔진의 트레일링스탑 판정에 필요).
"""

from __future__ import annotations

import datetime
import logging
from zoneinfo import ZoneInfo

from signal_desk import config, db, store
from signal_desk.broker import kis
from signal_desk.signals import engine, risk

log = logging.getLogger("signal_desk.bot")

_KST = ZoneInfo("Asia/Seoul")
_MARKET_OPEN = datetime.time(9, 0)
_MARKET_CLOSE = datetime.time(15, 20)  # 동시호가 등 마감 직전 여유 두고 컷오프


def is_market_hours(now: datetime.datetime | None = None) -> bool:
    """평일 09:00~15:20(KST)만 True — 장 시간 밖에서는 자동 루프가 조용히 스킵."""
    now = now or datetime.datetime.now(_KST)
    if now.weekday() >= 5:  # 토(5)/일(6)
        return False
    return _MARKET_OPEN <= now.time() <= _MARKET_CLOSE


def _today() -> str:
    return datetime.date.today().isoformat()


def _sell_note(reason: str, qty: int, avg_price: float, current_price: float,
               pl_pct: float, risk_cfg: "risk.RiskConfig") -> str:
    """매도 사유를 사람이 읽는 한 줄 근거로. 왜 지금(타이밍)·얼마나(수량)를 함께 남긴다."""
    trigger = {
        "STOP_LOSS": f"손절선 {risk_cfg.stop_loss_pct * 100:.0f}% 이탈",
        "TAKE_PROFIT": f"익절선 +{risk_cfg.take_profit_pct * 100:.0f}% 도달",
        "TRAILING": f"고점 대비 {risk_cfg.trailing_from_peak_pct * 100:.0f}% 되돌림(트레일링)",
        "SIGNAL": "시그널 SELL 전환",
    }.get(reason, reason)
    return (f"{trigger} — 평단 {int(avg_price):,}원 → 현재 {int(current_price):,}원"
            f"({pl_pct:+.1f}%), 보유 전량 {qty}주 청산")


def get_state() -> dict:
    """포트폴리오 탭용 종합 상태 — 봇 설정/현금·평가금액/보유종목/최근거래."""
    cfg = db.bot_config_get()
    creds = config.kis_credentials()
    bal = kis.balance(creds) if creds else None
    return {
        "enabled": cfg["enabled"],
        "config": cfg,
        "kis_connected": bal is not None,
        "cash": bal["cash"] if bal else None,
        "total_eval": bal["total_eval"] if bal else None,
        "positions": db.bot_positions_all(),
        "recent_trades": db.bot_trades_recent(20),
    }


def set_enabled(enabled: bool) -> None:
    db.bot_config_set_enabled(enabled)


def run_once(force: bool = False) -> dict:
    """한 사이클 실행. force=True면 장 시간 체크를 건너뜀(수동 테스트/데모용)."""
    creds = config.kis_credentials()
    if not creds:
        return {"ok": False, "reason": "KIS 인증정보 없음(.env 확인)"}
    if not force and not is_market_hours():
        return {"ok": False, "reason": "장 시간이 아님(평일 09:00~15:20 KST만 실행)"}

    bal = kis.balance(creds)
    if bal is None:
        return {"ok": False, "reason": "KIS 잔고조회 실패"}

    universe = store.load_universe()
    prices = store.load_price_series()
    if not universe or not prices:
        return {"ok": False, "reason": "시세 데이터 없음 — /api/refresh 먼저 호출 필요"}

    fundamentals = store.load_fundamentals()
    signals = engine.evaluate(universe, prices, fundamentals)
    signal_by_ticker = {s.ticker: s for s in signals}
    name_by_ticker = {u["ticker"]: u["name"] for u in universe}

    held_tickers = {h["ticker"] for h in bal["holdings"]}
    # DB에는 있지만 KIS 잔고엔 없는 포지션(외부에서 청산됨 등) 정리 — KIS가 source of truth
    for ticker in {p["ticker"] for p in db.bot_positions_all()} - held_tickers:
        db.bot_position_delete(ticker)

    risk_cfg = risk.RiskConfig()
    sells: list[dict] = []
    for h in bal["holdings"]:
        ticker, qty, avg_price = h["ticker"], h["qty"], h["avg_price"]
        closes = prices.get(ticker)
        if not closes:
            continue  # 유니버스 밖 종목(수동 보유 등) — 우리 봇 판단 대상 아님
        current_price = closes[-1]
        pos = db.bot_position_get(ticker)
        peak = max(pos["peak_price"] if pos else avg_price, current_price)

        reason = risk.check_exit(avg_price, current_price, peak, risk_cfg)
        if not reason:
            sig = signal_by_ticker.get(ticker)
            if sig and sig.kind == "SELL":
                reason = "SIGNAL"

        if reason:
            result = kis.place_order(ticker, "sell", qty, creds=creds)
            ok = result is not None
            pl_pct = (current_price / avg_price - 1) * 100 if avg_price else 0
            sig = signal_by_ticker.get(ticker)
            note = _sell_note(reason, qty, avg_price, current_price, pl_pct, risk_cfg)
            db.bot_trade_log(ticker, name_by_ticker.get(ticker, ticker), "sell", qty,
                              current_price, reason, result["order_no"] if ok else None,
                              score=sig.score if sig else None, note=note)
            sells.append({"ticker": ticker, "qty": qty, "reason": reason, "ok": ok})
            if ok:
                db.bot_position_delete(ticker)
        else:
            db.bot_position_upsert(ticker, name_by_ticker.get(ticker, ticker), qty, avg_price,
                                    peak, pos["entry_date"] if pos else _today())

    # 매도 반영된 최신 잔고로 매수 슬롯 계산(모의투자는 즉시체결 가정)
    bal2 = kis.balance(creds) or bal
    held_after = {h["ticker"] for h in bal2["holdings"]}
    cfg = db.bot_config_get()
    available_slots = max(0, cfg["max_positions"] - len(held_after))

    buys: list[dict] = []
    if available_slots > 0:
        candidates = sorted(
            (s for s in signals if s.kind == "BUY" and s.ticker not in held_after),
            key=lambda s: s.score, reverse=True,
        )[:available_slots]
        cash = bal2["cash"]
        target_alloc = bal2["total_eval"] * cfg["position_pct"]
        for s in candidates:
            closes = prices.get(s.ticker)
            if not closes:
                continue
            price = closes[-1]
            alloc = min(target_alloc, cash)
            qty = int(alloc // price)
            if qty < 1:
                continue  # 배분금액보다 1주 가격이 비싸면 스킵(정수주 제약)
            result = kis.place_order(s.ticker, "buy", qty, creds=creds)
            ok = result is not None
            note = (f"BUY 시그널 점수 {s.score:+.2f}(신뢰도 {s.confidence:.2f}) — 동일가중 배분 "
                    f"{cfg['position_pct'] * 100:.0f}%(약 {int(alloc):,}원) ÷ {int(price):,}원 = {qty}주")
            db.bot_trade_log(s.ticker, s.name, "buy", qty, price, "SIGNAL",
                              result["order_no"] if ok else None, score=s.score, note=note)
            buys.append({"ticker": s.ticker, "qty": qty, "ok": ok})
            if ok:
                db.bot_position_upsert(s.ticker, s.name, qty, price, price, _today())
                cash -= qty * price

    final_bal = kis.balance(creds) or bal2
    return {
        "ok": True, "sells": sells, "buys": buys,
        "cash": final_bal["cash"], "total_eval": final_bal["total_eval"],
        "holdings": len(final_bal["holdings"]),
    }
