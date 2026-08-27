import logging

import MetaTrader5 as mt5
import pandas as pd

from trading_agent.config import Config

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5ConnectionError(RuntimeError):
    pass


class MT5Connector:
    """Thin wrapper around the MetaTrader5 terminal API."""

    def __init__(self, config: Config):
        self.config = config

    def connect(self) -> None:
        init_kwargs = {}
        if self.config.mt5_path:
            init_kwargs["path"] = self.config.mt5_path
        if self.config.mt5_login:
            init_kwargs["login"] = self.config.mt5_login
            init_kwargs["password"] = self.config.mt5_password
            init_kwargs["server"] = self.config.mt5_server

        if not mt5.initialize(**init_kwargs):
            raise MT5ConnectionError(f"initialize() failed: {mt5.last_error()}")

        if self.config.mt5_login:
            authorized = mt5.login(
                self.config.mt5_login,
                password=self.config.mt5_password,
                server=self.config.mt5_server,
            )
            if not authorized:
                mt5.shutdown()
                raise MT5ConnectionError(f"login() failed: {mt5.last_error()}")

        account_info = mt5.account_info()
        if account_info is None:
            mt5.shutdown()
            raise MT5ConnectionError(f"account_info() failed: {mt5.last_error()}")

        logger.info(
            "Connected to MT5 account #%s on %s (balance=%.2f %s, trade_mode=%s)",
            account_info.login,
            account_info.server,
            account_info.balance,
            account_info.currency,
            "DEMO" if account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "LIVE",
        )

    def shutdown(self) -> None:
        mt5.shutdown()

    def account_balance(self) -> float:
        info = mt5.account_info()
        if info is None:
            raise MT5ConnectionError(f"account_info() failed: {mt5.last_error()}")
        return info.balance

    def is_demo_account(self) -> bool:
        info = mt5.account_info()
        if info is None:
            raise MT5ConnectionError(f"account_info() failed: {mt5.last_error()}")
        return info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO

    def symbol_info(self, symbol: str):
        info = mt5.symbol_info(symbol)
        if info is None:
            raise MT5ConnectionError(f"symbol_info({symbol}) failed: {mt5.last_error()}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise MT5ConnectionError(f"symbol_select({symbol}) failed: {mt5.last_error()}")
        return info

    def fetch_rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        mt5_timeframe = TIMEFRAME_MAP.get(timeframe.upper())
        if mt5_timeframe is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        if rates is None or len(rates) == 0:
            raise MT5ConnectionError(f"copy_rates_from_pos({symbol}) failed: {mt5.last_error()}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def open_positions(self, symbol: str, magic_number: int):
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == magic_number]

    def send_order(self, request: dict):
        result = mt5.order_send(request)
        if result is None:
            raise MT5ConnectionError(f"order_send() failed: {mt5.last_error()}")
        return result
