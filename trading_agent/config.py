import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Config:
    mt5_login: int
    mt5_password: str
    mt5_server: str
    mt5_path: str

    symbol: str
    timeframe: str
    magic_number: int

    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    sl_atr_multiplier: float
    tp_atr_multiplier: float

    fast_ma_period: int
    slow_ma_period: int
    rsi_period: int
    rsi_overbought: float
    rsi_oversold: float

    poll_interval_seconds: int
    live_trading_confirmed: bool

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            mt5_login=_get_int("MT5_LOGIN", 0),
            mt5_password=os.getenv("MT5_PASSWORD", ""),
            mt5_server=os.getenv("MT5_SERVER", ""),
            mt5_path=os.getenv("MT5_PATH", ""),
            symbol=os.getenv("SYMBOL", "XAUUSD"),
            timeframe=os.getenv("TIMEFRAME", "M15"),
            magic_number=_get_int("MAGIC_NUMBER", 234000),
            risk_per_trade_pct=_get_float("RISK_PER_TRADE_PCT", 1.0),
            max_daily_loss_pct=_get_float("MAX_DAILY_LOSS_PCT", 5.0),
            max_open_positions=_get_int("MAX_OPEN_POSITIONS", 1),
            sl_atr_multiplier=_get_float("SL_ATR_MULTIPLIER", 2.0),
            tp_atr_multiplier=_get_float("TP_ATR_MULTIPLIER", 3.0),
            fast_ma_period=_get_int("FAST_MA_PERIOD", 20),
            slow_ma_period=_get_int("SLOW_MA_PERIOD", 50),
            rsi_period=_get_int("RSI_PERIOD", 14),
            rsi_overbought=_get_float("RSI_OVERBOUGHT", 70),
            rsi_oversold=_get_float("RSI_OVERSOLD", 30),
            poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 60),
            live_trading_confirmed=_get_bool("LIVE_TRADING_CONFIRMED", False),
        )
