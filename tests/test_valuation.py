from signal_desk.signals import valuation


def test_screen_ranks_cheapest_first():
    universe = [
        {"ticker": "A", "name": "가"},
        {"ticker": "B", "name": "나"},
        {"ticker": "C", "name": "다"},
    ]
    fundamentals = {
        "A": {"per": 30.0, "pbr": 3.0, "roe": 10.0},
        "B": {"per": 5.0, "pbr": 0.5, "roe": 8.0},
        "C": {"per": 15.0, "pbr": 1.5, "roe": 12.0},
    }
    out = valuation.screen(universe, fundamentals)
    assert [r["ticker"] for r in out] == ["B", "C", "A"]
    assert out[0]["valuation_score"] < out[-1]["valuation_score"]


def test_screen_excludes_missing_per_or_pbr():
    universe = [{"ticker": "A", "name": "가"}, {"ticker": "B", "name": "나"}]
    fundamentals = {
        "A": {"per": 10.0, "pbr": 1.0},
        "B": {"pbr": 1.0},  # per 없음(적자 기업 등) -> 제외
    }
    out = valuation.screen(universe, fundamentals)
    assert [r["ticker"] for r in out] == ["A"]


def test_screen_empty_when_no_eligible():
    out = valuation.screen([], {"A": {"per": 10.0}})
    assert out == []


def test_percentile_rank_handles_ties():
    ranks = valuation._percentile_rank({"A": 10.0, "B": 10.0, "C": 20.0})
    assert ranks["A"] == ranks["B"]
    assert ranks["A"] < ranks["C"]
