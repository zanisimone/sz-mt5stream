import threading
import time
from typing import Optional, Callable, Literal, Dict

import pandas as pd
import MetaTrader5 as mt5


Timeframe = Literal["M1", "M5", "M15", "H1", "D1"]


class MT5Stream:
    """
    Minimal real-time tick stream from MetaTrader 5 with optional bar aggregation and auto-launch/login.

    Usage:
        s = MT5Stream(
            symbol="US100",
            terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe",
            login=1234567, password="***", server="YourBroker-Server",
            poll_interval=0.25,
            bars_timeframe="M1",
            rolling_ticks=10000,
            rolling_bars=2000
        )
        s.start(callback=on_ticks)
        df_ticks = s.ticks
        df_bars = s.bars
        s.stop()

    Notes:
        The MT5 terminal must be installed locally. Initialization attempts to launch and log in if
        'terminal_path' and credentials are provided. DataFrames returned by properties are copies.
        Bar aggregation appends only closed bars.
    """

    _RESAMPLE_RULE: Dict[str, str] = {
        "M1": "1min",
        "M5": "5min",
        "M15": "15min",
        "H1": "1H",
        "D1": "1D",
    }

    def __init__(
        self,
        symbol: str,
        *,
        poll_interval: float = 0.25,
        rolling_ticks: int = 10_000,
        terminal_path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        bars_timeframe: Optional[Timeframe] = None,
        rolling_bars: int = 2_000,
    ):
        """
        Initialize the stream configuration.

        Args:
            symbol: Trading symbol visible in MT5 Market Watch.
            poll_interval: Sleep time between polling iterations in seconds.
            rolling_ticks: Maximum rows retained in the tick buffer.
            terminal_path: Optional path to MT5 terminal executable for auto-launch.
            login: Optional MT5 account login.
            password: Optional MT5 account password.
            server: Optional MT5 server name.
            bars_timeframe: Optional timeframe for bar aggregation from ticks.
            rolling_bars: Maximum rows retained in the bar buffer.
        """
        self.symbol = symbol
        self.poll_interval = poll_interval
        self.rolling_ticks = rolling_ticks
        self.terminal_path = terminal_path
        self.login = login
        self.password = password
        self.server = server
        self.bars_timeframe = bars_timeframe
        self.rolling_bars = rolling_bars
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_tick_msc: int = 0
        self._ticks = pd.DataFrame(columns=["time", "bid", "ask", "last", "volume", "time_msc"])
        self._bars = pd.DataFrame(columns=["open", "high", "low", "close", "tick_volume"])
        self._last_bar_close: Optional[pd.Timestamp] = None

    @property
    def ticks(self) -> pd.DataFrame:
        """
        Return a copy of the rolling tick buffer.
        """
        return self._ticks.copy()

    @property
    def bars(self) -> pd.DataFrame:
        """
        Return a copy of the rolling closed bar buffer.
        """
        return self._bars.copy()

    def start(self, callback: Optional[Callable[[pd.DataFrame], None]] = None) -> None:
        """
        Start the background polling loop and optional tick callback.

        Args:
            callback: Optional function accepting a pandas DataFrame of new ticks.
        """
        self._ensure_connection()
        self._ensure_symbol(self.symbol)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """
        Stop the background polling loop and wait briefly for the thread to join.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def poll(self) -> pd.DataFrame:
        """
        Pull-only mode. Fetch only new ticks since the last call and update buffers.
        Returns:
            DataFrame of new ticks, possibly empty.
        """
        df_new = self._fetch_new_ticks()
        if not df_new.empty:
            self._append_ticks(df_new)
            if self.bars_timeframe:
                self._update_bars_from_ticks(df_new)
        return df_new

    def _loop(self, callback: Optional[Callable[[pd.DataFrame], None]]) -> None:
        """
        Background loop. Polls ticks, updates buffers, and invokes callback for each new batch.
        """
        while self._running:
            try:
                df_new = self.poll()
                if callback and not df_new.empty:
                    callback(df_new)
            except Exception:
                self._reconnect()
            time.sleep(self.poll_interval)

    def _fetch_new_ticks(self) -> pd.DataFrame:
        """
        Retrieve only new ticks based on time_msc frontier.

        Returns:
            DataFrame of new ticks with UTC timestamps and expected columns.
        """
        ticks = mt5.copy_ticks_from(
            self.symbol, pd.Timestamp.utcnow().to_pydatetime(), 1000, mt5.COPY_TICKS_ALL
        )
        if ticks is None or len(ticks) == 0:
            return pd.DataFrame(columns=self._ticks.columns)
        df = pd.DataFrame(ticks)
        df = df[df["time_msc"] > self._last_tick_msc]
        if df.empty:
            return pd.DataFrame(columns=self._ticks.columns)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        self._last_tick_msc = int(df["time_msc"].iloc[-1])
        return df[["time", "bid", "ask", "last", "volume", "time_msc"]]

    def _append_ticks(self, df_new: pd.DataFrame) -> None:
        """
        Append new ticks to the rolling buffer with size enforcement.
        """
        if self._ticks.empty:
            self._ticks = df_new.copy()
        else:
            self._ticks = pd.concat([self._ticks, df_new], ignore_index=True)
        if len(self._ticks) > self.rolling_ticks:
            self._ticks = self._ticks.iloc[-self.rolling_ticks :].reset_index(drop=True)

    def _update_bars_from_ticks(self, df_new: pd.DataFrame) -> None:
        """
        Aggregate closed bars from accumulated ticks using pandas resampling.
        Only closed bars are appended to the rolling bar buffer.
        """
        rule = self._RESAMPLE_RULE[self.bars_timeframe]
        df = self._ticks.copy().set_index("time")
        ohlc = df["last"].resample(rule, label="right", closed="right").agg(["first", "max", "min", "last"])
        vol = df["volume"].resample(rule, label="right", closed="right").sum()
        bars = pd.concat([ohlc, vol], axis=1)
        bars.columns = ["open", "high", "low", "close", "tick_volume"]
        if bars.empty:
            return
        last_close_time = bars.index[-1]
        if self._last_bar_close is None:
            closed_bars = bars.iloc[:-1] if len(bars) > 1 else bars.iloc[0:0]
        else:
            closed_bars = bars[bars.index > self._last_bar_close]
            if len(closed_bars) > 0 and closed_bars.index[-1] == last_close_time:
                closed_bars = closed_bars.iloc[:-1]
        if closed_bars.empty:
            return
        if self._bars.empty:
            self._bars = closed_bars.copy()
        else:
            self._bars = pd.concat([self._bars, closed_bars])
        self._bars = self._bars.iloc[-self.rolling_bars :]
        self._last_bar_close = self._bars.index[-1]

    def _ensure_connection(self) -> None:
        """
        Initialize the MT5 terminal, optionally auto-launching via terminal_path and logging in.
        Raises:
            RuntimeError on failure.
        """
        kwargs = {}
        if self.terminal_path:
            kwargs["path"] = self.terminal_path
        if self.login and self.password and self.server:
            ok = mt5.initialize(login=self.login, password=self.password, server=self.server, **kwargs)
        else:
            ok = mt5.initialize(**kwargs)
        if not ok:
            raise RuntimeError(f"mt5.initialize() failed: {mt5.last_error()}")

    def _ensure_symbol(self, symbol: str) -> None:
        """
        Ensure the symbol is selected and visible in Market Watch.
        Raises:
            RuntimeError on failure.
        """
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"symbol_select({symbol}) failed")

    def _reconnect(self) -> None:
        """
        Attempt a simple reconnection cycle to recover from transient errors.
        """
        try:
            mt5.shutdown()
        except Exception:
            pass
        time.sleep(0.5)
        self._ensure_connection()
        self._ensure_symbol(self.symbol)


from .exec import MT5Executor

__all__ = ["MT5Stream", "MT5Executor", "Timeframe"]