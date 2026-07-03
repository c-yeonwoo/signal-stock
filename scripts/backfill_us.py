"""S&P500 전종목 US 시세 백필 — KIS 해외시세로 us_prices.parquet 채우기.

모의계좌 rate limit(~2/s)·간헐 500을 감안해 진행상황을 로그로 남기며 순차 수집한다.
"""
import sys
from signal_desk import config, store

config.load_env()
uni = store.fetch_us_universe()
tickers = [u["ticker"] for u in uni]
print(f"S&P500 {len(tickers)}종목 백필 시작", flush=True)

BATCH = 25
done = 0
for i in range(0, len(tickers), BATCH):
    chunk = tickers[i:i + BATCH]
    ok = store.fetch_us_prices(chunk, days=400)  # 기존 parquet에 병합(upsert)
    done += len(chunk)
    print(f"  진행 {done}/{len(tickers)} (이번 배치 성공 {ok}/{len(chunk)})", flush=True)

series = store.load_us_price_series()
print(f"백필 완료 — 시세 보유 종목: {len(series)}", flush=True)
