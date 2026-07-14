"""상대강도 리더보드(relative.leaderboard) — 시장 대비 상대강도 순위."""

from signal_desk.signals import relative


def _s(v0, v40, v60):
    a = [v0] * 61
    a[40] = v40
    a[60] = v60
    return a


def test_leaderboard_ranks_by_relative_strength():
    idx = _s(100, 95, 90)                     # 지수 60일 -10%
    prices = {"A": _s(100, 100, 100),         # 0% → rs +10%p
              "B": _s(100, 90, 80),           # -20% → rs -10%p
              "C": _s(100, 110, 110)}         # +10% → rs +20%p
    lb = relative.leaderboard(prices, idx, names={"A": "에이", "C": "씨"}, top=3, window=60, short_window=20)
    assert [r["ticker"] for r in lb] == ["C", "A", "B"]
    c = next(r for r in lb if r["ticker"] == "C")
    assert c["rs"] == 20.0 and c["name"] == "씨"
    assert next(r for r in lb if r["ticker"] == "B")["rs"] == -10.0


def test_leaderboard_empty_without_index():
    assert relative.leaderboard({"A": [1, 2, 3]}, None) == []
