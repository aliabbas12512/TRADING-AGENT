import logging
import time
from datetime import datetime, timezone

import MetaTrader5 as mt5

from trading_agent.config import Config
from trading_agent.mt5_connector import MT5Connector
from trading_agent.order_executor import OrderExecutor
from trading_agent.risk_manager import RiskManager, RiskParams
from trading_agent.strategy import (
    Signal,
    StrategyParams,
    compute_indicators,
    generate_signal,
    generate_trend_signal,
)

logger = logging.getLogger(__name__)

RATES_LOOKBACK = 200


class TradingAgent:
    def __init__(self, config: Config):
        self.config = config
        self.connector = MT5Connector(config)
        self.risk_manager = RiskManager(
            RiskParams(
                risk_per_trade_pct=config.risk_per_trade_pct,
                max_daily_loss_pct=config.max_daily_loss_pct,
                max_open_positions=config.max_open_positions,
                sl_atr_multiplier=config.sl_atr_multiplier,
                tp_atr_multiplier=config.tp_atr_multiplier,
            )
        )
        self.strategy_params = StrategyParams(
            fast_ma_period=config.fast_ma_period,
            slow_ma_period=config.slow_ma_period,
            rsi_period=config.rsi_period,
            rsi_overbought=config.rsi_overbought,
            rsi_oversold=config.rsi_oversold,
        )
        self.executor: OrderExecutor | None = None
        self._trade_count_date: str | None = None
        self._trade_count_today: int = 0

    def start(self) -> None:
        self.connector.connect()
        self._enforce_live_trading_gate()
        self.executor = OrderExecutor(self.connector, self.config.symbol, self.config.magic_number)
        logger.info(
            "Config: symbol=%s timeframe=%s min_daily_trades=%d risk_per_trade_pct=%.2f "
            "max_open_positions=%d",
            self.config.symbol,
            self.config.timeframe,
            self.config.min_daily_trades,
            self.config.risk_per_trade_pct,
            self.config.max_open_positions,
        )

    def stop(self) -> None:
        self.connector.shutdown()

    def _enforce_live_trading_gate(self) -> None:
        if self.connector.is_demo_account():
            return
        if not self.config.live_trading_confirmed:
            self.connector.shutdown()
            raise RuntimeError(
                "Connected account is LIVE (real money), but LIVE_TRADING_CONFIRMED is not "
                "set to 'true' in your .env. Test on a demo account first, then set "
                "LIVE_TRADING_CONFIRMED=true only once you have verified the strategy."
            )
        logger.warning(
            "LIVE TRADING is active on a real-money account. Real orders will be placed."
        )

    def run_once(self) -> None:
        assert self.executor is not None, "call start() first"

        balance = self.connector.account_balance()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._reset_trade_count_if_new_day(today)

        if self.risk_manager.daily_loss_limit_hit(balance, today):
            logger.warning("Daily loss limit reached; skipping trading for today.")
            return

        df = self.connector.fetch_rates(self.config.symbol, self.config.timeframe, RATES_LOOKBACK)
        signal = generate_signal(df, self.strategy_params)

        indicators = compute_indicators(df, self.strategy_params)
        last_row = indicators.dropna(subset=["fast_ma", "slow_ma", "rsi"]).iloc[-1]
        logger.info(
            "close=%.3f fast_ma=%.3f slow_ma=%.3f rsi=%.1f primary_signal=%s trades_today=%d/%d",
            last_row["close"],
            last_row["fast_ma"],
            last_row["slow_ma"],
            last_row["rsi"],
            signal.value,
            self._trade_count_today,
            self.config.min_daily_trades,
        )

        if signal == Signal.HOLD and self._trade_count_today < self.config.min_daily_trades:
            signal = generate_trend_signal(df, self.strategy_params)
            if signal != Signal.HOLD:
                logger.info(
                    "No MA+RSI signal but only %d/%d trades today; using relaxed trend signal=%s.",
                    self._trade_count_today,
                    self.config.min_daily_trades,
                    signal.value,
                )

        open_positions = self.connector.open_positions(self.config.symbol, self.config.magic_number)

        if signal == Signal.HOLD:
            logger.info("Signal=HOLD, no action.")
            return

        if open_positions:
            logger.info(
                "Signal=%s but %d open position(s) already exist for this symbol/magic.",
                signal.value,
                len(open_positions),
            )

        if not self.risk_manager.can_open_new_position(len(open_positions)):
            logger.info("Signal=%s but max open positions (%d) reached.", signal.value, len(open_positions))
            return

        if self._open_position_for_signal(signal, df, balance):
            self._trade_count_today += 1

    def _reset_trade_count_if_new_day(self, today: str) -> None:
        if self._trade_count_date != today:
            self._trade_count_date = today
            self._trade_count_today = 0

    def _open_position_for_signal(self, signal: Signal, df, balance: float) -> bool:
        indicators = compute_indicators(df, self.strategy_params)
        last = indicators.dropna(subset=["atr"]).iloc[-1]
        atr_value = last["atr"]

        symbol_info = self.connector.symbol_info(self.config.symbol)
        is_buy = signal == Signal.BUY
        entry_price = symbol_info.ask if is_buy else symbol_info.bid

        sl = self.risk_manager.stop_loss_price(entry_price, atr_value, is_buy)
        tp = self.risk_manager.take_profit_price(entry_price, atr_value, is_buy)

        volume = self.risk_manager.position_size(
            balance=balance,
            entry_price=entry_price,
            stop_loss_price=sl,
            contract_size=symbol_info.trade_contract_size,
            volume_step=symbol_info.volume_step,
            volume_min=symbol_info.volume_min,
            volume_max=symbol_info.volume_max,
        )

        if volume <= 0:
            logger.warning("Computed volume <= 0, skipping order.")
            return False

        result = self.executor.open_market_order(is_buy=is_buy, volume=volume, stop_loss=sl, take_profit=tp)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def run_forever(self) -> None:
        self.start()
        try:
            while True:
                try:
                    self.run_once()
                except Exception:
                    logger.exception("Error during trading cycle")
                time.sleep(self.config.poll_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Shutting down on user interrupt.")
        finally:
            self.stop()
