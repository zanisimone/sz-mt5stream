import MetaTrader5 as mt5
from ..exceptions import MT5ConnectionError, MT5SymbolError


def ensure_connection(terminal_path=None, login=None, password=None, server=None):
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
        raise MT5ConnectionError(f"mt5.initialize() failed: {mt5.last_error()}")


def ensure_symbol(symbol: str):
    """
    Ensure the symbol is selected and visible in Market Watch.
    Raises:
        MT5SymbolError on failure.
    """
    if not mt5.symbol_select(symbol, True):
        raise MT5SymbolError(f"symbol_select({symbol}) failed")


def reconnect(terminal_path=None, login=None, password=None, server=None, symbol=None):
    """
    Attempt a simple reconnection cycle to recover from transient errors.
    """
    import time
    try:
        mt5.shutdown()
    except Exception:
        pass
    time.sleep(0.5)
    ensure_connection(terminal_path, login, password, server)
    if symbol:
        ensure_symbol(symbol)
