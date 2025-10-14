import threading
import time
from typing import Optional, Callable, Literal, Dict
from datetime import datetime, timezone

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
    
    _MT5_TIMEFRAME: Dict[str, int] = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1,
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
        self._bars = pd.DataFrame(columns=["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"])
        self._last_candle_time: Optional[int] = None  # Unix timestamp of last candle

    @property
    def ticks(self) -> pd.DataFrame:
        """
        Return a copy of the rolling tick buffer.
        Timestamps are timezone-naive and represent broker's local time.
        """
        df = self._ticks.copy()
        if not df.empty and df["time"].dt.tz is not None:
            # Convert UTC to naive datetime (broker time)
            df["time"] = df["time"].dt.tz_localize(None)
        return df

    @property
    def bars(self) -> pd.DataFrame:
        """
        Return a copy of the rolling closed bar buffer with time as index.
        Timestamps are timezone-naive and represent broker's local time.
        """
        if self._bars.empty:
            return self._bars.copy()
        df = self._bars.copy()
        # Convert UTC to naive datetime (broker time)
        df["time"] = df["time"].dt.tz_localize(None)
        df = df.set_index("time")
        return df

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
                self._fetch_completed_candles()
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
            DataFrame of new ticks with UTC timestamps (internally) and expected columns.
            When accessed via the ticks property, timestamps are converted to broker's local time.
        """
        # Get broker's current time - this is critical for timezone correctness
        # MT5's copy_ticks_from() expects datetime in broker's local timezone
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is not None:
            # Use broker's server time (as naive datetime, no timezone)
            request_time = datetime.fromtimestamp(tick.time)
        else:
            # Fallback to UTC if we can't get broker time
            request_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        ticks = mt5.copy_ticks_from(
            self.symbol, request_time, 1000, mt5.COPY_TICKS_ALL
        )
        if ticks is None or len(ticks) == 0:
            return pd.DataFrame(columns=self._ticks.columns)
        df = pd.DataFrame(ticks)
        df = df[df["time_msc"] > self._last_tick_msc]
        if df.empty:
            return pd.DataFrame(columns=self._ticks.columns)
        # Convert timestamps to UTC (timezone-aware)
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

    def _get_period_start(self, timestamp: int) -> int:
        """
        Get the start timestamp of the period that contains the given timestamp.
        This aligns timestamps to timeframe boundaries (e.g., M5 aligns to :00, :05, :10, etc.)
        
        Args:
            timestamp: Unix timestamp in seconds
            
        Returns:
            Unix timestamp of the period start
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        if self.bars_timeframe == "M1":
            # Align to minute boundary
            return int(dt.replace(second=0, microsecond=0).timestamp())
        elif self.bars_timeframe == "M5":
            # Align to 5-minute boundary
            minute = (dt.minute // 5) * 5
            return int(dt.replace(minute=minute, second=0, microsecond=0).timestamp())
        elif self.bars_timeframe == "M15":
            # Align to 15-minute boundary
            minute = (dt.minute // 15) * 15
            return int(dt.replace(minute=minute, second=0, microsecond=0).timestamp())
        elif self.bars_timeframe == "H1":
            # Align to hour boundary
            return int(dt.replace(minute=0, second=0, microsecond=0).timestamp())
        elif self.bars_timeframe == "D1":
            # Align to day boundary (00:00:00)
            return int(dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        else:
            return timestamp

    def _fetch_completed_candles(self) -> None:
        """
        Fetch completed candles directly from MT5 broker data.
        This ensures candles match exactly what the broker provides,
        including accurate volume, spread, and OHLC values.
        
        Only fetches when a new period has completed (e.g., new minute for M1, new 5-min for M5).
        """
        if not self.bars_timeframe:
            return
        
        # Get broker's current time
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return
        
        current_time = tick.time
        current_period = self._get_period_start(current_time)
        
        # Check if we're in a new period (i.e., previous period just closed)
        if self._last_candle_time is not None:
            last_period = self._get_period_start(self._last_candle_time)
            # Only fetch if we've moved to a new period
            if current_period <= last_period:
                return  # Still in same period or went backwards, don't fetch
        
        mt5_timeframe = self._MT5_TIMEFRAME[self.bars_timeframe]
        
        # Determine how many candles to fetch
        # If first time, get recent history; otherwise get latest few
        count = self.rolling_bars if self._last_candle_time is None else 5
        
        # Fetch rates from broker using broker's server time
        broker_time = datetime.fromtimestamp(current_time)
        rates = mt5.copy_rates_from(self.symbol, mt5_timeframe, broker_time, count)
        
        if rates is None or len(rates) == 0:
            return
        
        # Convert to DataFrame with proper column names
        # Convert timestamps to UTC (timezone-aware)
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        
        # Filter to only new candles (those after last fetched candle)
        if self._last_candle_time is not None:
            df = df[df["time"].astype(int) // 10**9 > self._last_candle_time]
        
        if df.empty:
            return
        
        # Exclude the current forming candle (last one in the array)
        # Only keep completed candles
        if len(df) > 1:
            # Check if last candle's period equals current period
            last_candle_time = int(df["time"].iloc[-1].timestamp())
            last_candle_period = self._get_period_start(last_candle_time)
            
            if last_candle_period >= current_period:
                # Last candle is still forming, exclude it
                df = df.iloc[:-1]
        
        if df.empty:
            return
        
        # Select and rename columns to match expected format
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        
        # Append to bars buffer
        if self._bars.empty:
            self._bars = df.copy()
        else:
            self._bars = pd.concat([self._bars, df], ignore_index=True)
        
        # Enforce rolling window size
        if len(self._bars) > self.rolling_bars:
            self._bars = self._bars.iloc[-self.rolling_bars:].reset_index(drop=True)
        
        # Update last candle timestamp (use the latest completed candle)
        self._last_candle_time = int(df["time"].iloc[-1].timestamp())

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