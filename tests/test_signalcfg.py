import pytest

from signal_desk import db, signalcfg


def test_default_matches_engine_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = signalcfg.get_config()
    assert cfg.weight_technical == 0.35 and cfg.buy_threshold == 1.2


def test_set_and_get_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = signalcfg.set_dict({"weight_technical": 0.5, "buy_threshold": 1.5, "ignored": 9})
    assert out["weight_technical"] == 0.5 and out["buy_threshold"] == 1.5
    assert "ignored" not in out
    assert signalcfg.get_config().weight_technical == 0.5


def test_reset_restores_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    signalcfg.set_dict({"weight_qualitative": 0.4})
    assert signalcfg.get_config().weight_qualitative == 0.4
    signalcfg.reset()
    assert signalcfg.get_config().weight_qualitative == 0.15


def test_effective_config_raises_buy_threshold_in_weak_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg, adapt = signalcfg.effective_config({"regime": "약세"}, {"bias": "비우호"})
    assert cfg.buy_threshold == pytest.approx(1.2 + 0.7)  # 약세 0.4 + 거시 비우호 0.3
    assert cfg.strong_buy_threshold == pytest.approx(2.0 + 0.7)
    assert adapt["bump"] == pytest.approx(0.7) and adapt["reasons"]


def test_effective_config_no_change_when_favorable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg, adapt = signalcfg.effective_config({"regime": "강세"}, {"bias": "우호"})
    assert cfg.buy_threshold == 1.2 and adapt["bump"] == 0.0


def test_effective_config_off_when_regime_adaptive_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    signalcfg.set_dict({"regime_adaptive": 0})
    cfg, adapt = signalcfg.effective_config({"regime": "조정"}, {"bias": "비우호"})
    assert cfg.buy_threshold == 1.2 and adapt["bump"] == 0.0
