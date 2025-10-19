from collections import namedtuple
from typing import Optional
import MetaTrader5 as mt5
from ..my_types import Tick


class MT5Executor:
    """
    Minimal order execution adapter for MetaTrader 5.
    Reuses the already-initialized MT5 connection created by your application or MT5Stream.
    Provides market, limit, and stop orders with optional absolute-price SL/TP.
    Does not implement guards or validations.
    """

    def __init__(self, *, magic: int = 42, deviation: int = 20):
        """
        Configure the order adapter.

        Args:
            magic: Magic number to tag orders from this adapter.
            deviation: Max price deviation in points for order execution.
        """
        self.magic = magic
        self.deviation = deviation

    def _tick(self, symbol: str) -> Tick:
        """
        Retrieve current tick snapshot for a symbol.
        Raises:
            RuntimeError if no tick is available.
        """
        t = mt5.symbol_info_tick(symbol)
        if t is None:
            raise RuntimeError("No tick for symbol")
        return Tick(**t._asdict())

    def _send(self, request: dict) -> mt5.OrderSendResult:
        """
        Send a prepared order request to MT5.
        Raises:
            RuntimeError if order_send returns None.
        """
        res = mt5.order_send(request)
        if res is None:
            raise RuntimeError("order_send returned None")
        return res

    def market_buy(
        self,
        symbol: str,
        volume: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a market buy order with optional SL/TP as absolute prices.
        Returns:
            OrderSendResult
        """
        tick = self._tick(symbol)
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_BUY,
            "volume": volume,
            "price": tick.ask,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def market_sell(
        self,
        symbol: str,
        volume: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a market sell order with optional SL/TP as absolute prices.
        Returns:
            OrderSendResult
        """
        tick = self._tick(symbol)
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_SELL,
            "volume": volume,
            "price": tick.bid,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def buy_limit(
        self,
        symbol: str,
        volume: float,
        price: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a buy limit pending order with optional SL/TP.
        Returns:
            OrderSendResult
        """
        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "volume": volume,
            "price": price,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def sell_limit(
        self,
        symbol: str,
        volume: float,
        price: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a sell limit pending order with optional SL/TP.
        Returns:
            OrderSendResult
        """
        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "volume": volume,
            "price": price,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def buy_stop(
        self,
        symbol: str,
        volume: float,
        price: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a buy stop pending order with optional SL/TP.
        Returns:
            OrderSendResult
        """
        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "volume": volume,
            "price": price,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def sell_stop(
        self,
        symbol: str,
        volume: float,
        price: float,
        *,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "mt5stream",
    ) -> mt5.OrderSendResult:
        """
        Place a sell stop pending order with optional SL/TP.
        Returns:
            OrderSendResult
        """
        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "volume": volume,
            "price": price,
            "deviation": self.deviation,
            "sl": sl if sl is not None else 0.0,
            "tp": tp if tp is not None else 0.0,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req)

    def positions(self, symbol: Optional[str] = None) -> namedtuple:
        """
        Return open positions, optionally filtered by symbol.
        """
        return mt5.positions_get(symbol=symbol)

    def close_all(self, symbol: Optional[str] = None) -> int:
        """
        Close all open positions by sending an opposite market order with the same volume.

        Only positions for which the order result retcode is DONE are counted as closed.
        If an exception occurs during the closing process, it may interrupt and prevent further positions from being closed.

        Returns:
            Number of positions reported as closed by retcode DONE.
        """
        poss = self.positions(symbol)
        if not poss:
            return 0
        closed = 0
        for p in poss:
            if symbol and p.symbol != symbol:
                continue
            if p.type == mt5.POSITION_TYPE_BUY:
                res = self.market_sell(p.symbol, p.volume, sl=p.sl, tp=p.tp)
            else:
                res = self.market_buy(p.symbol, p.volume, sl=p.sl, tp=p.tp)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
        return closed
