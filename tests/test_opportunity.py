"""통합 후보 유형 분류(#14)."""

from signal_desk.signals.engine import SignalResult
from signal_desk.signals import opportunity


def _r(**kw):
    base = dict(ticker="A", name="가", score=1.0, kind="BUY", confidence=0.6,
                technical_score=0.0, fundamental_score=0.0, has_fundamental=False)
    base.update(kw)
    return SignalResult(**base)


def test_classify_each_type():
    assert "낙폭과대" in opportunity.classify(_r(has_reversion=True, reversion_score=0.4))
    assert "저평가" in opportunity.classify(_r(has_valuation=True, valuation_percentile=0.2))
    assert "모멘텀" in opportunity.classify(_r(technical_score=0.6))
    assert "실적우량" in opportunity.classify(_r(has_fundamental=True, fundamental_score=0.7))
    assert "정성호재" in opportunity.classify(_r(has_qualitative=True, qualitative_score=0.3))


def test_classify_thresholds_and_missing_data():
    # 데이터 없으면(has_*=False) 태그 없음
    assert opportunity.classify(_r(reversion_score=0.9, valuation_percentile=0.1)) == []
    # 경계 미달
    assert "저평가" not in opportunity.classify(_r(has_valuation=True, valuation_percentile=0.5))
    assert "모멘텀" not in opportunity.classify(_r(technical_score=0.3))


def test_classify_multi_tag():
    tags = opportunity.classify(_r(technical_score=0.6, has_fundamental=True, fundamental_score=0.7,
                                   has_valuation=True, valuation_percentile=0.1))
    assert set(tags) == {"모멘텀", "실적우량", "저평가"}
