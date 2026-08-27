from dataclasses import dataclass
from enum import Enum

import pandas as pd

from trading_agent.indicators import atr, rsi, sma


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class StrategyParams:
    fast_ma_period: int = 20
    slow_ma_period: int = 50
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    atr_period: int = 14


def compute_indicators(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    out = df.copy()
    out["fast_ma"] = sma(out["close"], params.fast_ma_period)
    out["slow_ma"] = sma(out["close"], params.slow_ma_period)
    out["rsi"] = rsi(out["close"], params.rsi_period)
    out["atr"] = atr(out, params.atr_period)
    return out


def generate_signal(df: pd.DataFrame, params: StrategyParams = StrategyParams()) -> Signal:
    """MA-crossover trend filter + RSI timing.

    BUY when the fast MA is above the slow MA (uptrend) and RSI has just
    recovered out of oversold territory. SELL is the mirror image. Requires
    at least two fully-formed indicator rows to detect the RSI cross.
    """
    data = compute_indicators(df, params)
    valid = data.dropna(subset=["fast_ma", "slow_ma", "rsi"])
    if len(valid) < 2:
        return Signal.HOLD

    prev, last = valid.iloc[-2], valid.iloc[-1]

    uptrend = last["fast_ma"] > last["slow_ma"]
    downtrend = last["fast_ma"] < last["slow_ma"]

    rsi_cross_up = prev["rsi"] <= params.rsi_oversold < last["rsi"]
    rsi_cross_down = prev["rsi"] >= params.rsi_overbought > last["rsi"]

    if uptrend and rsi_cross_up:
        return Signal.BUY
    if downtrend and rsi_cross_down:
        return Signal.SELL
    return Signal.HOLD


def generate_trend_signal(df: pd.DataFrame, params: StrategyParams = StrategyParams()) -> Signal:
    """Trend direction only, ignoring RSI timing.

    Used as a relaxed fallback when a minimum daily trade count needs to be
    met and the full MA+RSI signal hasn't fired. Trades more often and with
    less selectivity than generate_signal, so it carries more risk.
    """
    data = compute_indicators(df, params)
    valid = data.dropna(subset=["fast_ma", "slow_ma"])
    if len(valid) < 1:
        return Signal.HOLD

    last = valid.iloc[-1]
    if last["fast_ma"] > last["slow_ma"]:
        return Signal.BUY
    if last["fast_ma"] < last["slow_ma"]:
        return Signal.SELL
    return Signal.HOLD
