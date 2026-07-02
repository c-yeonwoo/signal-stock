"""캐시 로더 — apt-signal 컨벤션(parquet=시계열, json=메타/소형 데이터)을 그대로 따른다.

ingest 모듈은 데이터만 반환하고, 캐시 형식·경로 결정은 전부 이 파일이 담당한다.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

import pandas as pd

from signal_desk.ingest import dart, krx

log = logging.getLogger("signal_desk.store")

CACHE_DIR = Path("data/cache")
UNIVERSE_FILE = CACHE_DIR / "universe.json"
PRICES_FILE = CACHE_DIR / "prices.parquet"
FUNDAMENTALS_FILE = CACHE_DIR / "fundamentals.json"

PRICE_HISTORY_DAYS = 400  # MA120 워밍업 + 백테스트 여유분


def _write_json(path: Path, data) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_universe() -> list[dict]:
    items = krx.universe()
    _write_json(UNIVERSE_FILE, items)
    return items


def fetch_prices(universe: list[dict] | None = None, days: int = PRICE_HISTORY_DAYS) -> pd.DataFrame:
    universe = universe if universe is not None else load_universe()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    rows = []
    for item in universe:
        ticker = item["ticker"]
        try:
            bars = krx.ohlcv(ticker, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        except Exception as e:
            log.error("시세 수집 실패(%s): %s", ticker, e)
            continue
        for bar in bars:
            rows.append({"ticker": ticker, **bar})

    df = pd.DataFrame(rows, columns=["date", "ticker", "open", "close"])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PRICES_FILE, index=False)
    return df


def fetch_fundamentals(universe: list[dict] | None = None, bsns_year: str | None = None) -> dict:
    universe = universe if universe is not None else load_universe()
    bsns_year = bsns_year or str(datetime.date.today().year - 1)  # 최신 사업보고서는 보통 전년도분

    codes = dart.corp_codes()
    if not codes:
        log.warning("DART_API_KEY 미설정 — 기본적분석 생략(기술점수만 사용)")
        _write_json(FUNDAMENTALS_FILE, {})
        return {}

    out: dict[str, dict] = {}
    for item in universe:
        ticker = item["ticker"]
        corp_code = codes.get(ticker)
        if not corp_code:
            continue
        metrics = dart.fundamentals(ticker, corp_code, bsns_year)
        if metrics:
            out[ticker] = metrics
    _write_json(FUNDAMENTALS_FILE, out)
    return out


def load_universe() -> list[dict]:
    if not UNIVERSE_FILE.exists():
        return []
    return json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))


def load_price_series() -> dict[str, list[float]]:
    """ticker -> 종가 리스트(오래된→최신). engine.evaluate()/backtest_summary()에 바로 투입 가능."""
    if not PRICES_FILE.exists():
        return {}
    df = pd.read_parquet(PRICES_FILE)
    if df.empty:
        return {}
    df = df.sort_values(["ticker", "date"])
    return {ticker: g["close"].tolist() for ticker, g in df.groupby("ticker")}


def load_fundamentals() -> dict[str, dict]:
    if not FUNDAMENTALS_FILE.exists():
        return {}
    return json.loads(FUNDAMENTALS_FILE.read_text(encoding="utf-8"))


def is_ready() -> bool:
    return PRICES_FILE.exists() and UNIVERSE_FILE.exists()
