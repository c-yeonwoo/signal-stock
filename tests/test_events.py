"""종목별 과거 이벤트 타임라인 — 공시 분류 + 엔드포인트(공시 필터·배당)."""


def test_disc_kind_classifies():
    from signal_desk import api
    assert api._disc_kind("주요사항보고서(자기주식취득결정)") == "good"
    assert api._disc_kind("주요사항보고서(감자결정)") == "caution"      # critical
    assert api._disc_kind("유상증자 결정") == "caution"                # serious
    assert api._disc_kind("기타 경영사항 안내") == "note"


def test_events_endpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/cache").mkdir(parents=True)
    from signal_desk import api, store
    store._write_json(store.FUNDAMENTALS_FILE, {"005930": {"dps": 1500}})
    api._corp_codes.cache_clear()
    api._disclosures_cached.cache_clear()
    monkeypatch.setattr(api, "_corp_codes", lambda: {"005930": "00126380"})
    monkeypatch.setattr(api, "_disclosures_cached", lambda c, b, e: (
        ("자기주식취득 결과보고서", "20260506", "X1"),
        ("주요사항보고서(감자결정)", "20260522", "X2"),
        ("분기보고서 (2026.03)", "20260401", "X3"),   # routine → 제외돼야
    ))
    monkeypatch.setattr(api, "_quotes", lambda: {"005930": {"price": 75000}})

    out = api.signal_events_get("005930", market="kospi")
    assert out["ready"] and out["has_corp"]
    names = [d["name"] for d in out["disclosures"]]
    assert any("자기주식" in n for n in names)
    assert not any("분기보고서" in n for n in names)       # routine 공시는 필터
    kinds = {d["name"]: d["kind"] for d in out["disclosures"]}
    assert kinds["자기주식취득 결과보고서"] == "good"
    assert out["disclosures"][0]["date"] == "2026-05-06"   # YYYY-MM-DD 포맷
    assert out["dividend"]["dps"] == 1500
    assert out["dividend"]["div_yield"] == round(1500 / 75000 * 100, 2)

    assert api.signal_events_get("005930", market="us")["ready"] is False
