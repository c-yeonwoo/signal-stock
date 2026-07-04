"""자체 모의계좌(paper) 브로커 — KIS 대체 백엔드. 외부 연결 없이 가격캐시(종가) 기준으로
가상 체결·현금·포지션을 내부 관리한다. KIS 비표준 포트(29443/9443)가 막힌 환경에서도 동작.

broker.kis와 동일한 함수 시그니처(balance/place_order/current_price)를 노출해 bot이 백엔드만
바꿔 끼울 수 있게 한다(creds 인자는 무시). 계좌 상태는 db.kv('paper_account')에 JSON으로 보관.

한계: 실시장 미시구조(호가·슬리피지·부분체결) 없음 — 신호가/종가로 즉시 전량 체결로 가정한다.
"""

from __future__ import annotations

import json
import logging

from signal_desk import config, db, store

log = logging.getLogger("signal_desk.broker.paper")

_KEY = "paper_account"


def _load() -> dict:
    raw = db.kv_get(_KEY)
    if not raw:
        return {"cash": config.paper_seed_cash(), "positions": {}}
    acct = json.loads(raw) if isinstance(raw, str) else raw
    acct.setdefault("cash", config.paper_seed_cash())
    acct.setdefault("positions", {})
    return acct


def _save(acct: dict) -> None:
    db.kv_set(_KEY, json.dumps(acct, ensure_ascii=False))


def _name_map() -> dict[str, str]:
    return {u["ticker"]: u["name"] for u in store.load_universe()}


def current_price(ticker: str, creds: dict | None = None) -> float | None:
    """가격캐시(최근 종가) 기준 현재가. 없으면 None."""
    closes = store.load_price_series().get(ticker)
    return float(closes[-1]) if closes else None


def balance(creds: dict | None = None, retries: int = 1) -> dict:
    """KIS balance와 동일 형태 — 자체 모의계좌 현금·보유·평가손익. 항상 성공(외부 연결 없음)."""
    acct = _load()
    names = _name_map()
    holdings, stock_eval, invested = [], 0.0, 0.0
    for t, p in acct["positions"].items():
        price = current_price(t) or p["avg_price"]
        stock_eval += price * p["qty"]
        invested += p["avg_price"] * p["qty"]
        pnl_pct = round((price / p["avg_price"] - 1) * 100, 2) if p["avg_price"] else 0.0
        holdings.append({"ticker": t, "name": p.get("name") or names.get(t, t),
                         "qty": p["qty"], "avg_price": round(p["avg_price"], 2),
                         "price": round(price, 2), "pnl_pct": pnl_pct})
    pnl = stock_eval - invested
    return {
        "cash": round(acct["cash"], 2), "stock_eval": round(stock_eval, 2),
        "invested": round(invested, 2), "pnl": round(pnl, 2),
        "pnl_pct": round(pnl / invested * 100, 2) if invested else None,
        "total_eval": round(acct["cash"] + stock_eval, 2), "holdings": holdings,
    }


def place_order(ticker: str, side: str, qty: int, price: float | None = None,
                creds: dict | None = None) -> dict | None:
    """가상 체결. 매수는 현금 차감·평단 재계산, 매도는 현금 증가·수량 차감. 체결가는 price(지정가)
    또는 현재가(종가). 실패(현금·수량 부족, 가격 없음) 시 None(KIS place_order와 동일 계약)."""
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    if qty <= 0:
        return None
    px = float(price) if price else current_price(ticker)
    if not px or px <= 0:
        return None
    acct = _load()
    pos = acct["positions"].get(ticker)
    if side == "buy":
        cost = px * qty
        if cost > acct["cash"]:
            log.info("paper 매수 현금부족(%s x%d @%.0f, 현금 %.0f)", ticker, qty, px, acct["cash"])
            return None
        acct["cash"] -= cost
        if pos:
            total = pos["qty"] + qty
            pos["avg_price"] = (pos["avg_price"] * pos["qty"] + px * qty) / total
            pos["qty"] = total
        else:
            acct["positions"][ticker] = {"name": _name_map().get(ticker, ticker),
                                         "qty": qty, "avg_price": px}
    else:  # sell
        if not pos or pos["qty"] < qty:
            return None
        acct["cash"] += px * qty
        pos["qty"] -= qty
        if pos["qty"] <= 0:
            del acct["positions"][ticker]
    _save(acct)
    return {"order_no": "PAPER", "order_time": "", "fill_price": round(px, 2)}
