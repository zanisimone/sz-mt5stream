"""Custom types for sz_mt5stream package."""

# There is a built-in types module, so avoid that name.

from dataclasses import dataclass
from enum import IntFlag
import MetaTrader5 as mt5
from typing import Dict, Literal


Timeframe = Literal["M1", "M5", "M15", "H1", "D1"]

RESAMPLE_RULE: Dict[Timeframe, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "H1": "1H",
    "D1": "1D",
}

MT5_TIMEFRAME: Dict[Timeframe, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "D1": mt5.TIMEFRAME_D1,
}


class TickFlag(IntFlag):
    BID = mt5.TICK_FLAG_BID
    ASK = mt5.TICK_FLAG_ASK
    LAST = mt5.TICK_FLAG_LAST
    VOLUME = mt5.TICK_FLAG_VOLUME
    BUY = mt5.TICK_FLAG_BUY
    SELL = mt5.TICK_FLAG_SELL


@dataclass
class Tick:
    """Typed representation of an MT5 tick returned by mt5.symbol_info_tick()"""

    time: int
    bid: float
    ask: float
    last: float
    volume: int
    time_msc: int
    flags: TickFlag
    volume_real: float


@dataclass
class OrderSendResult:
    """Typed representation of the result returned by mt5.order_send()."""

    retcode: int
    """Return code (10009 = success)."""
    deal: int
    """Deal ticket if executed."""
    order: int
    """Order ticket."""
    volume: float
    """Order volume."""
    price: float
    """Order price."""
    bid: float
    """Current bid price."""
    ask: float
    """Current ask price."""
    comment: str
    """Broker comment."""
    request_id: int
    """Request identifier."""
    retcode_external: int
    """External return code."""


class MT5SymbolError(RuntimeError):
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Could not select symbol {symbol} in Market Watch.")


class MT5ConnectionError(RuntimeError):
    def __init__(self, last_error: int):
        self.last_error = last_error
        message: str
        if last_error == mt5.RES_E_FAIL:
            message = "generic fail"
        elif last_error == mt5.RES_E_INVALID_PARAMS:
            message = "invalid arguments/parameters"
        elif last_error == mt5.RES_E_NO_MEMORY:
            message = "no memory condition"
        elif last_error == mt5.RES_E_NOT_FOUND:
            message = "no history"
        elif last_error == mt5.RES_E_INVALID_VERSION:
            message = "invalid version"
        elif last_error == mt5.RES_E_AUTH_FAILED:
            message = "authorization failed"
        elif last_error == mt5.RES_E_UNSUPPORTED:
            message = "unsupported method"
        elif last_error == mt5.RES_E_AUTO_TRADING_DISABLED:
            message = "auto-trading disabled"
        elif last_error == mt5.RES_E_INTERNAL_FAIL:
            message = "internal IPC general error"
        elif last_error == mt5.RES_E_INTERNAL_FAIL_SEND:
            message = "internal IPC send failed"
        elif last_error == mt5.RES_E_INTERNAL_FAIL_RECEIVE:
            message = "internal IPC recv failed"
        elif last_error == mt5.RES_E_INTERNAL_FAIL_INIT:
            message = "internal IPC initialization fail"
        elif last_error == mt5.RES_E_INTERNAL_FAIL_CONNECT:
            message = "internal IPC no ipc"
        elif last_error == mt5.RES_E_INTERNAL_FAIL_TIMEOUT:
            message = "internal timeout"
        else:
            message = f"unknown error code {last_error}"
        super().__init__(message)
