# TRADING-AGENT — XAUUSD Automated Trading Agent

An automated trading agent for gold (XAUUSD) built on the MetaTrader 5 (MT5)
Python API. It fetches price data, generates entry signals from a
trend-following strategy (moving-average crossover filtered by RSI), sizes
positions by risk, attaches ATR-based stop-loss/take-profit levels, and
places/manages orders through your MT5 terminal.

## ⚠️ Real money warning

This agent is configured for **live trading** by default and will place real
orders with real funds against whatever account it logs into. Before running
it against a live account:

1. Run it against a **demo account** first (set `MT5_SERVER` to your broker's
   demo server) and watch it trade for at least a few days/weeks.
2. Review and tune the strategy and risk parameters in `.env` for your risk
   tolerance.
3. Only then point `MT5_LOGIN`/`MT5_SERVER` at a real account **and**
   explicitly set `LIVE_TRADING_CONFIRMED=true` in `.env`.

The agent refuses to trade on a detected live account unless
`LIVE_TRADING_CONFIRMED=true` is set — this is a deliberate safety gate, not
a bug. Demo accounts are always allowed to trade without this flag.

## Requirements

- Windows (the `MetaTrader5` Python package only works on Windows, where it
  talks to a locally running MT5 terminal — it cannot be installed or run on
  Linux/macOS or in this cloud sandbox).
- A running MetaTrader 5 terminal, logged into a broker that offers XAUUSD.
- Python 3.10+.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your MT5 login, password, server, and desired parameters
python main.py
```

## Project layout

- `trading_agent/config.py` — loads configuration from `.env`.
- `trading_agent/mt5_connector.py` — thin wrapper around the MT5 terminal API
  (connect, fetch OHLC rates, read positions, send orders).
- `trading_agent/indicators.py` — SMA, RSI, ATR (pure pandas, no MT5
  dependency, unit tested).
- `trading_agent/strategy.py` — MA-crossover + RSI signal generation (pure
  pandas, no MT5 dependency, unit tested).
- `trading_agent/risk_manager.py` — position sizing from account risk %,
  ATR-based stop-loss/take-profit, daily loss circuit breaker (pure Python,
  unit tested).
- `trading_agent/order_executor.py` — places and closes MT5 market orders.
- `trading_agent/agent.py` — orchestrates the loop: fetch data → signal →
  risk checks → execute. Includes the live-trading safety gate.
- `main.py` — entrypoint; runs the agent loop until interrupted.

## Strategy

Default strategy is a trend filter + timing signal:

- **Trend**: fast SMA (default 20) vs. slow SMA (default 50) on the close
  price determines the trend direction.
- **Timing**: RSI (default period 14) crossing back up through the oversold
  threshold (default 30) triggers a BUY in an uptrend; crossing back down
  through the overbought threshold (default 70) triggers a SELL in a
  downtrend.
- **Exits**: every position gets an ATR-based stop-loss and take-profit set
  at trade entry (default 2x ATR / 3x ATR).

All of these are configurable via `.env` and the strategy module is
decoupled from MT5, so it can be swapped or backtested independently.

## Risk management

- `RISK_PER_TRADE_PCT` — % of account balance risked per trade (position
  size is derived from this and the stop-loss distance).
- `MAX_DAILY_LOSS_PCT` — trading halts for the day once realized/floating
  losses reach this % of the day's starting balance.
- `MAX_OPEN_POSITIONS` — caps concurrent positions on the traded symbol.

## Testing

The strategy, indicator, and risk-management logic have no MT5 dependency
and are covered by unit tests:

```bash
pytest tests/ -v
```

(`mt5_connector.py`, `order_executor.py`, and `agent.py` require the
Windows-only `MetaTrader5` package and a live terminal connection, so they
are exercised via integration/manual testing on a demo account rather than
in this test suite.)

## Disclaimer

Trading leveraged instruments like gold CFDs carries substantial risk of
loss. This code is provided for educational purposes and is not financial
advice. Past or simulated performance does not guarantee future results.
Use at your own risk, and never risk money you cannot afford to lose.
