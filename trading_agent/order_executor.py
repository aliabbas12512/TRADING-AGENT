import logging

import MetaTrader5 as mt5

from trading_agent.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class OrderExecutor:
    def __init__(self, connector: MT5Connector, symbol: str, magic_number: int):
        self.connector = connector
        self.symbol = symbol
        self.magic_number = magic_number

    def open_market_order(
        self,
        is_buy: bool,
        volume: float,
        stop_loss: float,
        take_profit: float,
        deviation: int = 20,
        comment: str = "trading-agent",
    ):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"symbol_info_tick({self.symbol}) failed: {mt5.last_error()}")

        price = tick.ask if is_buy else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": deviation,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = self.connector.send_order(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Order failed: retcode=%s comment=%s", result.retcode, result.comment)
        else:
            logger.info(
                "Order filled: %s %.2f lots %s @ %.5f (sl=%.5f tp=%.5f)",
                "BUY" if is_buy else "SELL",
                volume,
                self.symbol,
                price,
                stop_loss,
                take_profit,
            )
        return result

    def close_position(self, position, deviation: int = 20, comment: str = "trading-agent-close"):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"symbol_info_tick({self.symbol}) failed: {mt5.last_error()}")

        is_buy_position = position.type == mt5.ORDER_TYPE_BUY
        price = tick.bid if is_buy_position else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if is_buy_position else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": price,
            "deviation": deviation,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = self.connector.send_order(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Close failed: retcode=%s comment=%s", result.retcode, result.comment)
        else:
            logger.info("Position #%s closed @ %.5f", position.ticket, price)
        return result
