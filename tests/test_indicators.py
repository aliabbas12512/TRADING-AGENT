import numpy as np
import pandas as pd

from trading_agent.indicators import atr, rsi, sma


def test_sma_basic():
    series = pd.Series([1, 2, 3, 4, 5])
    result = sma(series, 2)
    assert np.isnan(result.iloc[0])
    assert result.iloc[1] == 1.5
    assert result.iloc[-1] == 4.5


def test_rsi_bounds():
    series = pd.Series(np.linspace(100, 200, 50))
    result = rsi(series, 14).dropna()
    assert (result >= 0).all() and (result <= 100).all()


def test_rsi_all_gains_is_100():
    series = pd.Series(range(1, 30))
    result = rsi(series, 14).dropna()
    assert (result == 100).all()


def test_atr_positive():
    df = pd.DataFrame(
        {
            "high": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            "low": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            "close": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
        }
    )
    result = atr(df, 14).dropna()
    assert (result > 0).all()
