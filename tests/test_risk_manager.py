import pytest

from trading_agent.risk_manager import RiskManager, RiskParams


def make_manager(**overrides):
    defaults = dict(
        risk_per_trade_pct=1.0,
        max_daily_loss_pct=5.0,
        max_open_positions=1,
        sl_atr_multiplier=2.0,
        tp_atr_multiplier=3.0,
    )
    defaults.update(overrides)
    return RiskManager(RiskParams(**defaults))


def test_stop_loss_and_take_profit_for_buy():
    rm = make_manager()
    sl = rm.stop_loss_price(entry_price=2000, atr_value=10, is_buy=True)
    tp = rm.take_profit_price(entry_price=2000, atr_value=10, is_buy=True)
    assert sl == 1980
    assert tp == 2030


def test_stop_loss_and_take_profit_for_sell():
    rm = make_manager()
    sl = rm.stop_loss_price(entry_price=2000, atr_value=10, is_buy=False)
    tp = rm.take_profit_price(entry_price=2000, atr_value=10, is_buy=False)
    assert sl == 2020
    assert tp == 1970


def test_position_size_respects_risk_budget():
    rm = make_manager(risk_per_trade_pct=1.0)
    volume = rm.position_size(
        balance=10_000,
        entry_price=2000,
        stop_loss_price=1980,
        contract_size=100,
        volume_step=0.01,
        volume_min=0.01,
        volume_max=100,
    )
    # risk_amount = 100; price_distance = 20; raw = 100 / (20*100) = 0.05
    assert volume == pytest.approx(0.05, abs=1e-6)


def test_position_size_clamped_to_min():
    rm = make_manager(risk_per_trade_pct=0.01)
    volume = rm.position_size(
        balance=100,
        entry_price=2000,
        stop_loss_price=1900,
        contract_size=100,
        volume_step=0.01,
        volume_min=0.01,
        volume_max=100,
    )
    assert volume == 0.01


def test_position_size_zero_when_no_price_distance():
    rm = make_manager()
    volume = rm.position_size(
        balance=10_000,
        entry_price=2000,
        stop_loss_price=2000,
        contract_size=100,
        volume_step=0.01,
        volume_min=0.01,
        volume_max=100,
    )
    assert volume == 0.0


def test_daily_loss_limit_hit():
    rm = make_manager(max_daily_loss_pct=5.0)
    assert rm.daily_loss_limit_hit(balance=10_000, today="2026-08-27") is False
    assert rm.daily_loss_limit_hit(balance=9_400, today="2026-08-27") is True


def test_daily_loss_resets_on_new_day():
    rm = make_manager(max_daily_loss_pct=5.0)
    rm.daily_loss_limit_hit(balance=10_000, today="2026-08-27")
    assert rm.daily_loss_limit_hit(balance=9_400, today="2026-08-27") is True
    # New day resets the baseline balance
    assert rm.daily_loss_limit_hit(balance=9_400, today="2026-08-28") is False


def test_can_open_new_position():
    rm = make_manager(max_open_positions=2)
    assert rm.can_open_new_position(0) is True
    assert rm.can_open_new_position(1) is True
    assert rm.can_open_new_position(2) is False
