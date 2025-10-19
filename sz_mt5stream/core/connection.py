from typing import Optional
import MetaTrader5 as mt5
import time
from ..my_types import MT5ConnectionError, MT5SymbolError

"""Connection management utilities for MetaTrader 5"""


def ensure_connection(
    terminal_path: Optional[str] = None,
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
):
    """
    Initialize the MT5 terminal, optionally auto-launching via terminal_path and logging in.
    Raises:
        MT5ConnectionError on failure.
    """
    kwargs = {}
    if terminal_path:
        kwargs["path"] = terminal_path
    if login and password and server:
        ok = mt5.initialize(login=login, password=password, server=server, **kwargs)
    else:
        ok = mt5.initialize(**kwargs)
    if not ok:
        raise MT5ConnectionError(mt5.last_error())


def ensure_symbol(symbol: str):
    """
    Ensure the symbol is selected and visible in Market Watch.
    Raises:
        MT5SymbolError on failure.
    """
    if not mt5.symbol_select(symbol, True):
        raise MT5SymbolError(symbol)


def reconnect(
    terminal_path: Optional[str] = None,
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
    symbol: Optional[str] = None,
):
    """
    Attempt a simple reconnection cycle to recover from transient errors.
    Raises:
        MT5ConnectionError
        MT5SymbolError
    """
    try:
        mt5.shutdown()
    except Exception:
        # MetaTrader5 shutdown does not document its exceptions
        pass
    time.sleep(0.5)
    ensure_connection(terminal_path, login, password, server)
    if symbol:
        ensure_symbol(symbol)
