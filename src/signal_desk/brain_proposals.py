"""두뇌 개선 제안 — 실측 IC 기반 보수적 가중 조정 초안 + 관리자 승인 적용.

자동 적용 없음. refresh()가 draft 카드를 만들고, review(approved)만이
signalcfg에 반영한다. 카드 문구는 수식 없이 한국어로 읽히게 쓴다.
"""

from __future__ import annotations

import logging
import time
from datetime import date

from signal_desk import db, signalcfg
from signal_desk.brain import _TIMING_FACTORS

log = logging.getLogger(__name__)

# 랭킹 알파 후보만 가중 nudge (타이밍/게이트 팩터는 IC 낮음이 정상 → 제외)
_FACTOR_KO = {
    "fundamental": "기본적",
    "valuation": "저평가",
    "flow": "수급",
    "quality": "퀄리티",
    "momentum": "모멘텀",
    "short": "공매도",
}
_WEIGHT_KEY = {k: f"weight_{k}" for k in _FACTOR_KO}
_DELTA = 0.05          # 한 번에 바꾸는 최대 폭(보수)
_WEIGHT_FLOOR = 0.05   # 가중치 하한
_IC_MIN_SAMPLES = 20
_METHOD_KEY = "ic_weighting"


def _confidence(ic: float, n: int) -> str:
    if n >= 60 and abs(ic) >= 0.08:
        return "high"
    if n >= _IC_MIN_SAMPLES and abs(ic) >= 0.03:
        return "medium"
    return "low"


def _conf_ko(c: str) -> str:
    return {"high": "높음", "medium": "보통", "low": "낮음"}.get(c, c)


def build_weight_nudge(factor: str, ic: float, n: int, weights: dict) -> dict | None:
    """음수 IC 랭킹 팩터 → 비중 ↓ 제안 1장. 타이밍 팩터·이미 하한·표본 부족이면 None."""
    if factor in _TIMING_FACTORS or factor not in _FACTOR_KO:
        return None
    if n < _IC_MIN_SAMPLES or ic is None or ic >= 0:
        return None
    wkey = _WEIGHT_KEY[factor]
    cur = float(weights.get(wkey) or 0)
    if cur <= _WEIGHT_FLOOR + 1e-9:
        return None
    new_w = round(max(_WEIGHT_FLOOR, cur - _DELTA), 3)
    if new_w >= cur:
        return None
    label = _FACTOR_KO[factor]
    conf = _confidence(ic, n)
    return {
        "kind": "weight_nudge",
        "title": f"{label} 비중을 조금 줄이기",
        "body_ko": (
            f"최근 실측에서 ‘{label}’ 신호가 잘 안 맞았습니다. "
            f"이 팩터에 덜 기대도록 비중을 {cur:.2f} → {new_w:.2f}로 살짝 낮춥니다. "
            f"한 번에 크게 바꾸지 않습니다."
        ),
        "rationale_ko": (
            f"{label} 예측력(IC) {ic:+.2f} · 표본 {n}건 · 신뢰 {_conf_ko(conf)}"
        ),
        "patch": {wkey: new_w},
        "evidence": {
            "factor": factor,
            "factor_ic": round(ic, 4),
            "matured_primary": n,
            "from_weight": cur,
            "to_weight": new_w,
        },
        "method_key": _METHOD_KEY,
        "confidence": conf,
    }


def refresh(accuracy: dict, weights: dict | None = None) -> dict:
    """실측 accuracy → draft 제안 upsert. 트래커 미성숙이면 생성 스킵.

    반환: {ok, created, skipped, reason?, items[]}
    """
    weights = weights or signalcfg.get_dict()
    if not (accuracy or {}).get("ready"):
        return {"ok": True, "created": 0,
                "reason": "실측 트래커가 아직 성숙하지 않아 제안을 만들지 않습니다.",
                "items": []}
    n = int(((accuracy.get("coverage") or {}).get("matured_primary") or 0))
    if n < _IC_MIN_SAMPLES:
        return {"ok": True, "created": 0,
                "reason": f"성숙 표본 {n}/{_IC_MIN_SAMPLES}건 — 제안 보류.",
                "items": []}
    factor_ic = accuracy.get("factor_ic") or {}
    today = date.today().isoformat().replace("-", "")
    created, items = 0, []
    baseline = dict(weights)

    for factor, ic in factor_ic.items():
        if not isinstance(ic, (int, float)):
            continue
        draft = build_weight_nudge(factor, float(ic), n, weights)
        if not draft:
            continue
        # 동일 팩터 미검토 draft가 이미 있으면 내용만 갱신(id 유지) — 카드 폭증 방지
        existing = db.brain_proposal_draft_for_factor(factor)
        pid = existing["id"] if existing else f"bp_{today}_w_{factor}"
        item = {
            **draft,
            "id": pid,
            "baseline": baseline,
            "status": "draft",
            "created": existing["created"] if existing else int(time.time()),
            "reviewed": None,
            "note": None,
        }
        db.brain_proposal_upsert(item)
        created += 1
        items.append(item)
    return {"ok": True, "created": created, "items": items}


def review(pid: str, status: str, note: str = "") -> dict:
    """승인|반려. 승인 시 patch를 현재 설정에 병합·이력 기록·캐시는 호출측에서 clear."""
    if status not in ("approved", "rejected"):
        return {"ok": False, "error": "status는 approved|rejected"}
    item = db.brain_proposal_get(pid)
    if not item:
        return {"ok": False, "error": "제안을 찾을 수 없습니다."}
    if item["status"] != "draft":
        return {"ok": False, "error": f"이미 처리된 제안입니다({item['status']})."}

    applied = None
    if status == "approved":
        before = signalcfg.get_dict()
        patch = {k: v for k, v in (item.get("patch") or {}).items() if k in signalcfg.FIELDS}
        if not patch:
            return {"ok": False, "error": "적용할 변경값이 없습니다."}
        merged = {**before, **patch}
        after = signalcfg.set_dict(merged)
        signalcfg.append_history({
            "ts": int(time.time()),
            "source": "brain_proposal",
            "proposal_id": pid,
            "title": item.get("title"),
            "before": before,
            "after": after,
            "patch": patch,
            "note": note or None,
        })
        applied = {"patch": patch, "config": after}
        log.info("brain proposal approved id=%s patch=%s", pid, patch)

    db.brain_proposal_set_status(pid, status, note)
    return {"ok": True, "id": pid, "status": status, "applied": applied}


def list_proposals(status: str | None = "draft", limit: int = 50) -> list[dict]:
    return db.brain_proposal_list(status=status, limit=limit)
