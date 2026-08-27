import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskParams:
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    sl_atr_multiplier: float
    tp_atr_multiplier: float


class RiskManager:
    def __init__(self, params: RiskParams):
        self.params = params
        self._day_start_balance: float | None = None
        self._current_day: str | None = None

    def _refresh_day(self, balance: float, today: str) -> None:
        if self._current_day != today:
            self._current_day = today
            self._day_start_balance = balance

    def daily_loss_limit_hit(self, balance: float, today: str) -> bool:
        self._refresh_day(balance, today)
        assert self._day_start_balance is not None
        loss_pct = (self._day_start_balance - balance) / self._day_start_balance * 100
        if loss_pct >= self.params.max_daily_loss_pct:
            logger.warning(
                "Daily loss limit hit: %.2f%% >= %.2f%%", loss_pct, self.params.max_daily_loss_pct
            )
            return True
        return False

    def can_open_new_position(self, open_position_count: int) -> bool:
        return open_position_count < self.params.max_open_positions

    def stop_loss_price(self, entry_price: float, atr_value: float, is_buy: bool) -> float:
        offset = atr_value * self.params.sl_atr_multiplier
        return entry_price - offset if is_buy else entry_price + offset

    def take_profit_price(self, entry_price: float, atr_value: float, is_buy: bool) -> float:
        offset = atr_value * self.params.tp_atr_multiplier
        return entry_price + offset if is_buy else entry_price - offset

    def position_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss_price: float,
        contract_size: float,
        volume_step: float,
        volume_min: float,
        volume_max: float,
    ) -> float:
        """Size the trade so that a stop-loss hit loses risk_per_trade_pct of balance."""
        risk_amount = balance * (self.params.risk_per_trade_pct / 100)
        price_distance = abs(entry_price - stop_loss_price)
        if price_distance <= 0:
            return 0.0

        raw_volume = risk_amount / (price_distance * contract_size)

        steps = round(raw_volume / volume_step)
        volume = steps * volume_step
        volume = max(volume_min, min(volume, volume_max))
        return round(volume, 8)
