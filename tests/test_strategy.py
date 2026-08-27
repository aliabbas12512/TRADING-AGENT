import pandas as pd
import pytest

from trading_agent import strategy
from trading_agent.strategy import Signal, StrategyParams, generate_signal

PARAMS = StrategyParams(rsi_overbought=70, rsi_oversold=30)


def _patched_indicators(monkeypatch, rows: list[dict]):
    df = pd.DataFrame(rows)

    def fake_compute_indicators(_df, _params):
        return df

    monkeypatch.setattr(strategy, "compute_indicators", fake_compute_indicators)
    return df


def _base_row(fast_ma, slow_ma, rsi_value):
    return {
        "close": 100,
        "fast_ma": fast_ma,
        "slow_ma": slow_ma,
        "rsi": rsi_value,
        "atr": 1.0,
    }


def test_buy_signal_on_uptrend_and_rsi_cross_up(monkeypatch):
    rows = [
        _base_row(fast_ma=105, slow_ma=100, rsi_value=25),  # prev: oversold
        _base_row(fast_ma=106, slow_ma=100, rsi_value=35),  # last: recovered, uptrend
    ]
    _patched_indicators(monkeypatch, rows)

    assert generate_signal(pd.DataFrame({"close": [100, 101]}), PARAMS) == Signal.BUY


def test_sell_signal_on_downtrend_and_rsi_cross_down(monkeypatch):
    rows = [
        _base_row(fast_ma=95, slow_ma=100, rsi_value=75),  # prev: overbought
        _base_row(fast_ma=94, slow_ma=100, rsi_value=65),  # last: dropped, downtrend
    ]
    _patched_indicators(monkeypatch, rows)

    assert generate_signal(pd.DataFrame({"close": [100, 99]}), PARAMS) == Signal.SELL


def test_hold_when_trend_and_rsi_disagree(monkeypatch):
    rows = [
        _base_row(fast_ma=105, slow_ma=100, rsi_value=75),  # overbought in an uptrend
        _base_row(fast_ma=106, slow_ma=100, rsi_value=65),  # no oversold recovery
    ]
    _patched_indicators(monkeypatch, rows)

    assert generate_signal(pd.DataFrame({"close": [100, 101]}), PARAMS) == Signal.HOLD


def test_hold_when_insufficient_data():
    df = pd.DataFrame({"close": [100.0] * 5, "high": [101.0] * 5, "low": [99.0] * 5})
    assert generate_signal(df, PARAMS) == Signal.HOLD
