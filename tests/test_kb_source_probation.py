"""채널/피드 수습 · 퇴출후보 — 자동 disable 없음."""

from signal_desk import db, kb


def test_lazy_child_starts_probation(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    ch = db.kb_source_ensure("youtube:spamchan", display_name="@spam", parent_key="youtube")
    assert ch["lifecycle"] == "probation"
    assert ch["pinned"] is False
    root = db.kb_source_get("youtube")
    assert root["pinned"] is True and root["lifecycle"] == "active"


def test_evaluate_promotes_and_evicts(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    db.kb_source_ensure("youtube:good", display_name="good", parent_key="youtube")
    for _ in range(3):
        db.kb_sources_bump_run("youtube:good")
        db.kb_sources_touch("youtube:good", "ok", accepted=2)
    out = kb.evaluate_source_quality("youtube:good")
    assert out["lifecycle"] == "active"
    assert db.kb_source_get("youtube:good")["lifecycle"] == "active"

    db.kb_source_ensure("youtube:bad", display_name="bad", parent_key="youtube")
    for _ in range(3):
        db.kb_sources_bump_run("youtube:bad")
    db.kb_sources_touch("youtube:bad", "rejected", rejected=8)
    db.kb_sources_touch("youtube:bad", "ok", accepted=1)
    out2 = kb.evaluate_source_quality("youtube:bad")
    assert out2["lifecycle"] == "eviction_candidate"
    bad = db.kb_source_get("youtube:bad")
    assert bad["lifecycle"] == "eviction_candidate"
    assert bad["enabled"] is True  # 자동 disable 없음


def test_pinned_skips_eviction(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    db.kb_source_ensure("youtube:keep", display_name="keep", parent_key="youtube")
    db.kb_source_lifecycle_action("youtube:keep", "pin")
    for _ in range(3):
        db.kb_sources_bump_run("youtube:keep")
    db.kb_sources_touch("youtube:keep", "rejected", rejected=10)
    out = kb.evaluate_source_quality("youtube:keep")
    assert out.get("skipped") is True
    assert db.kb_source_get("youtube:keep")["lifecycle"] == "active"


def test_eviction_candidate_blocked_by_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    db.kb_source_ensure("youtube:x", display_name="x", parent_key="youtube")
    db.kb_source_set_quality("youtube:x", score=-0.5, note="t", lifecycle="eviction_candidate")
    out = kb.ingest_document(
        source_key="youtube:x", ticker=kb.MACRO_TICKER, title="t",
        summary="시황 " * 20, scope="market", parent_key="youtube",
    )
    assert out["ok"] is False and "퇴출" in out["reason"]


def test_admin_evict_disables(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    db.kb_source_ensure("youtube:z", display_name="z", parent_key="youtube")
    db.kb_source_set_quality("youtube:z", score=-1, note="t", lifecycle="eviction_candidate")
    r = db.kb_source_lifecycle_action("youtube:z", "evict")
    assert r["ok"] and r["source"]["enabled"] is False
    r2 = db.kb_source_lifecycle_action("youtube:z", "keep")
    assert r2["source"]["enabled"] is True and r2["source"]["lifecycle"] == "active"


def test_immature_stays_probation(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "app.db")
    db.kb_source_ensure("youtube:new", display_name="n", parent_key="youtube")
    db.kb_sources_bump_run("youtube:new")
    db.kb_sources_touch("youtube:new", "rejected", rejected=2)
    out = kb.evaluate_source_quality("youtube:new")
    assert out["mature"] is False and out["lifecycle"] == "probation"
