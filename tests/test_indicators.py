import pytest

from signal_desk.signals import indicators as ind


def test_sma():
    out = ind.sma([1, 2, 3, 4, 5], 3)
    assert out[:2] == [None, None]
    assert out[2:] == pytest.approx([2, 3, 4])


def test_ema():
    out = ind.ema([1, 2, 3, 4, 5], 3)
    assert out[:2] == [None, None]
    assert out[2:] == pytest.approx([2, 3, 4])


def test_ema_insufficient_data():
    assert ind.ema([1, 2], 3) == [None, None]


def test_rsi_hand_computed():
    out = ind.rsi([44, 44.5, 43.5, 44], period=2)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(33.333, abs=1e-2)
    assert out[3] == pytest.approx(60.0, abs=1e-2)


def test_rsi_all_losses_is_zero():
    out = ind.rsi([10, 9, 8, 7], period=2)
    assert out[2] == pytest.approx(0.0)


def test_macd_converges_on_linear_series():
    # 등차수열은 두 EMA의 차이가 일정 구간 이후 상수로 수렴 -> histogram이 0으로 수렴
    values = [1, 2, 3, 4, 5, 6, 7]
    out = ind.macd(values, fast=2, slow=3, signal=2)
    assert out["macd"][:2] == [None, None]
    assert out["macd"][2:] == pytest.approx([0.5] * 5)
    assert out["histogram"][3:] == pytest.approx([0.0] * 4, abs=1e-9)


def test_sigmoid_bounds():
    assert ind.sigmoid(0) == pytest.approx(0.5)
    assert 0 < ind.sigmoid(-10) < 0.01
    assert 0.99 < ind.sigmoid(10) < 1
