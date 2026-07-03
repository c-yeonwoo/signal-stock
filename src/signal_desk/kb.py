"""지식베이스(KB) — 뉴스·영상 원자료를 '한 번 더 가공'(요약·감성)해 종목별 다이제스트로 적재.

흐름: ingest.news.collect(원자료) → db.kb_entry_add_many(원자료 보관) → build_digest(LLM 요약·감성)
→ db.kb_digest_set(가공 결과 보관). 다이제스트는 (1) 시그널의 정성적 팩터(signals/qualitative.py)와
(2) 봇 LLM 자문(signals/advisor.py)의 입력으로 재사용된다.

리소스 절약: 전 종목이 아니라 호출자가 넘긴 대상(보유·후보·관심종목)만 갱신한다.
LLM 미설정 시 규칙기반(키워드) 감성으로 폴백 — KB는 여전히 쌓인다.
"""

from __future__ import annotations

import logging
import time

from signal_desk import db, llm
from signal_desk.ingest import news

log = logging.getLogger("signal_desk.kb")

_POS = ["상승", "급등", "호재", "최대", "돌파", "수주", "흑자", "개선", "성장", "신고가", "강세", "기대", "수혜"]
_NEG = ["하락", "급락", "악재", "부진", "적자", "감소", "우려", "리콜", "제재", "약세", "손실", "하향", "경고"]

# 매수 후보에서 제외(veto)할 '악재 이벤트' 키워드 — 명백한 하방 사건만(고정밀). 업종과 충돌하는
# 일반어(화재/사고/폭발/소송/파업 등, 예: 화재보험사)나 중립어(유상증자/감산)는 오탐이 많아 제외.
_EVENT_TERMS = [
    "횡령", "배임", "분식회계", "불성실공시", "상장폐지", "거래정지", "감사의견 거절", "관리종목 지정",
    "압수수색", "검찰 기소", "구속영장", "과징금", "리콜 결정", "어닝쇼크", "적자전환", "영업정지",
]
EVENT_TTL_DAYS = 5  # 이 기간 지난 악재는 veto에서 해제(신선도)


def detect_event(items: list[dict]) -> tuple[bool, str]:
    """원자료 제목/요약에서 악재 이벤트 키워드를 찾아 (플래그, 사유) 반환. 없으면 (False, "")."""
    for it in items:
        text = f"{it.get('title', '')} {it.get('summary', '')}"
        for term in _EVENT_TERMS:
            if term in text:
                return True, f"{term} — {(it.get('title') or '').strip()[:60]}"
    return False, ""


def _newest_ts(items: list[dict]) -> int | None:
    """원자료 중 가장 최근 발행 시각(epoch). 파싱 가능한 게 없으면 None."""
    times = [dt.timestamp() for it in items if (dt := news._parse_dt(it.get("published", "")))]
    return int(max(times)) if times else None


def _rule_digest(name: str, items: list[dict]) -> dict:
    """LLM 없을 때 폴백 — 제목 키워드로 감성 근사, 최근 제목을 포인트로."""
    text = " ".join(f"{it.get('title', '')} {it.get('summary', '')}" for it in items)
    pos = sum(text.count(w) for w in _POS)
    neg = sum(text.count(w) for w in _NEG)
    total = pos + neg
    sentiment = round((pos - neg) / total, 2) if total else 0.0
    points = [it["title"] for it in items[:3] if it.get("title")]
    summary = f"{name} 최근 뉴스 {len(items)}건 기준 키워드 감성 {sentiment:+.2f}(규칙기반)."
    return {"sentiment": sentiment, "summary": summary, "points": points}


def build_digest(name: str, items: list[dict]) -> dict:
    """원자료 → {sentiment[-1..1], summary(1문장), points[≤3]}. LLM 우선, 실패 시 규칙기반."""
    if not items:
        return {"sentiment": 0.0, "summary": "최근 수집된 뉴스·영상이 없습니다.", "points": []}
    if llm.available():
        headlines = "\n".join(f"- [{it.get('source', '')}] {it.get('title', '')} :: {it.get('summary', '')[:120]}"
                              for it in items[:12])
        system = ("너는 한국 주식 애널리스트다. 주어진 종목의 최근 뉴스·영상 헤드라인을 근거로 투자 관점의 "
                  "정성 요약을 만든다. 과장/추천 금지, 사실 기반. 헤드라인에 없는 내용은 지어내지 마라.")
        user = (f"종목: {name}\n최근 헤드라인:\n{headlines}\n\n"
                'JSON으로만: {"sentiment": -1.0~1.0 사이 실수(투자심리), '
                '"summary": "한국어 한 문장 요약", "points": ["핵심 포인트 최대 3개(한국어 짧게)"]}')
        out = llm.complete_json(system, user, max_tokens=500)
        if out and isinstance(out.get("sentiment"), (int, float)):
            s = max(-1.0, min(1.0, float(out["sentiment"])))
            pts = [str(p) for p in (out.get("points") or [])][:3]
            return {"sentiment": round(s, 2), "summary": str(out.get("summary", ""))[:200], "points": pts}
        log.info("LLM 다이제스트 파싱 실패 — 규칙기반 폴백")
    return _rule_digest(name, items)


def refresh(targets: list[dict], news_n: int = 8, lookback_days: int = 7) -> dict:
    """targets: [{ticker, name}]. 각 종목 증권 뉴스 수집(신선도·관련성 필터)→저장→다이제스트 갱신.
    유튜브는 화이트리스트 확보 전까지 보류. 갱신 건수 반환."""
    updated = 0
    for t in targets:
        ticker, name = t.get("ticker"), t.get("name", "")
        if not ticker or not name:
            continue
        items = news.collect(name, news_n=news_n, lookback_days=lookback_days)
        if not items:
            continue
        db.kb_entry_add_many(ticker, items)
        digest = build_digest(name, items)
        event_flag, event_note = detect_event(items)
        db.kb_digest_set(ticker, name, digest["sentiment"], digest["summary"], digest["points"],
                         len(items), newest_ts=_newest_ts(items), event_flag=event_flag, event_note=event_note)
        updated += 1
    return {"updated": updated}


def sentiment_map() -> dict[str, dict]:
    """ticker -> {score, reasons, event_risk, event_note} — engine이 소비.
    event_risk는 '최근(EVENT_TTL_DAYS 이내) 악재 이벤트'만 True(오래된 악재는 해제)."""
    now = time.time()
    out = {}
    for ticker, dg in db.kb_digests_all().items():
        reasons = []
        if dg.get("summary"):
            reasons.append(f"[정성] {dg['summary']}")
        fresh = dg.get("newest_ts") is None or (now - dg["newest_ts"]) <= EVENT_TTL_DAYS * 86400
        out[ticker] = {
            "score": dg.get("sentiment", 0.0), "reasons": reasons,
            "event_risk": bool(dg.get("event_flag")) and fresh,
            "event_note": dg.get("event_note") or "",
        }
    return out
