# sz_mt5stream

Minimal library to stream real-time ticks from MetaTrader 5 into pandas DataFrames, optionally aggregate closed bars from ticks, auto-launch and log into MT5, and send basic orders (market/limit/stop) with optional SL/TP.

The design is intentionally small and explicit:
- One streaming class: `MT5Stream`
- One execution adapter: `MT5Executor`

---

## Installation

```bash
pip install sz_mt5stream
```

For development installation:

```bash
git clone https://github.com/zanisimone/sz_mt5stream.git
cd sz_mt5stream
pip install -e .
```

---

## Requirements

- Python 3.9 or higher
- MetaTrader 5 terminal installed locally
- MetaTrader 5 Python package
- pandas

---

## Quick Start

### Streaming Ticks

```python
from sz_mt5stream import MT5Stream

# Basic tick streaming
stream = MT5Stream(symbol="EURUSD")
stream.start()

# Access tick data
df_ticks = stream.ticks
print(df_ticks.head())

stream.stop()
```

### Auto-Launch and Login

```python
stream = MT5Stream(
    symbol="US100",
    terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe",
    login=1234567,
    password="your_password",
    server="YourBroker-Server"
)
stream.start()
```

### Bar Aggregation from Ticks

```python
stream = MT5Stream(
    symbol="EURUSD",
    bars_timeframe="M1",  # Aggregate 1-minute bars
    rolling_ticks=10000,
    rolling_bars=2000
)
stream.start()

# Access aggregated bars
df_bars = stream.bars
print(df_bars.head())

stream.stop()
```

### Using a Callback Function

```python
def on_new_ticks(ticks_df):
    print(f"Received {len(ticks_df)} new ticks")
    print(f"Latest bid: {ticks_df['bid'].iloc[-1]}")

stream = MT5Stream(symbol="EURUSD", poll_interval=0.5)
stream.start(callback=on_new_ticks)

# Stream runs in background, calling on_new_ticks for each new batch
# ... your application logic ...

stream.stop()
```

### Pull-Only Mode (No Background Thread)

```python
stream = MT5Stream(symbol="EURUSD")

# Manual polling without starting background thread
while True:
    new_ticks = stream.poll()
    if not new_ticks.empty:
        print(f"Got {len(new_ticks)} new ticks")
    time.sleep(1)
```

---

## Order Execution

The `MT5Executor` class provides basic order execution capabilities. It reuses the existing MT5 connection established by your application or `MT5Stream`.

### Market Orders

```python
from sz_mt5stream import MT5Executor

executor = MT5Executor(magic=42, deviation=20)

# Market buy
result = executor.market_buy("EURUSD", volume=0.1, sl=1.0800, tp=1.0900)
print(f"Order result: {result.retcode}, deal: {result.deal}")

# Market sell
result = executor.market_sell("EURUSD", volume=0.1, sl=1.0950, tp=1.0850)
```

### Pending Orders

```python
# Buy limit
result = executor.buy_limit("EURUSD", volume=0.1, price=1.0850, sl=1.0800, tp=1.0900)

# Sell limit
result = executor.sell_limit("EURUSD", volume=0.1, price=1.0950, sl=1.1000, tp=1.0900)

# Buy stop
result = executor.buy_stop("EURUSD", volume=0.1, price=1.0950, sl=1.0900, tp=1.1000)

# Sell stop
result = executor.sell_stop("EURUSD", volume=0.1, price=1.0850, sl=1.0900, tp=1.0800)
```

### Position Management

```python
# Get all open positions
positions = executor.positions()

# Get positions for specific symbol
positions = executor.positions(symbol="EURUSD")

# Close all positions
closed_count = executor.close_all()
print(f"Closed {closed_count} positions")

# Close positions for specific symbol
closed_count = executor.close_all(symbol="EURUSD")
```

---

## Complete Example: Live Trading Bot

```python
import time
from sz_mt5stream import MT5Stream, MT5Executor

def trading_callback(ticks_df):
    """Process new ticks and make trading decisions"""
    latest_bid = ticks_df['bid'].iloc[-1]
    latest_ask = ticks_df['ask'].iloc[-1]
    
    # Your trading logic here
    print(f"Bid: {latest_bid}, Ask: {latest_ask}")

# Initialize stream with auto-login
stream = MT5Stream(
    symbol="EURUSD",
    terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe",
    login=1234567,
    password="your_password",
    server="YourBroker-Server",
    poll_interval=0.25,
    bars_timeframe="M1",
    rolling_ticks=10000,
    rolling_bars=2000
)

# Initialize executor
executor = MT5Executor(magic=42, deviation=20)

# Start streaming with callback
stream.start(callback=trading_callback)

try:
    # Keep application running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
    stream.stop()
```

---

## API Reference

### MT5Stream

**Constructor Parameters:**

- `symbol` (str): Trading symbol visible in MT5 Market Watch
- `poll_interval` (float, default=0.25): Sleep time between polling iterations in seconds
- `rolling_ticks` (int, default=10000): Maximum rows retained in tick buffer
- `terminal_path` (str, optional): Path to MT5 terminal executable for auto-launch
- `login` (int, optional): MT5 account login
- `password` (str, optional): MT5 account password
- `server` (str, optional): MT5 server name
- `bars_timeframe` (Timeframe, optional): Timeframe for bar aggregation ("M1", "M5", "M15", "H1", "D1")
- `rolling_bars` (int, default=2000): Maximum rows retained in bar buffer

**Methods:**

- `start(callback=None)`: Start background polling loop with optional callback function
- `stop()`: Stop background polling loop
- `poll()`: Manual polling mode - fetch new ticks since last call (returns DataFrame)

**Properties:**

- `ticks`: Returns copy of rolling tick DataFrame (columns: time, bid, ask, last, volume, time_msc)
- `bars`: Returns copy of rolling bar DataFrame (columns: open, high, low, close, tick_volume)

### MT5Executor

**Constructor Parameters:**

- `magic` (int, default=42): Magic number to tag orders
- `deviation` (int, default=20): Maximum price deviation in points

**Methods:**

- `market_buy(symbol, volume, sl=None, tp=None, comment="mt5stream")`: Place market buy order
- `market_sell(symbol, volume, sl=None, tp=None, comment="mt5stream")`: Place market sell order
- `buy_limit(symbol, volume, price, sl=None, tp=None, comment="mt5stream")`: Place buy limit order
- `sell_limit(symbol, volume, price, sl=None, tp=None, comment="mt5stream")`: Place sell limit order
- `buy_stop(symbol, volume, price, sl=None, tp=None, comment="mt5stream")`: Place buy stop order
- `sell_stop(symbol, volume, price, sl=None, tp=None, comment="mt5stream")`: Place sell stop order
- `positions(symbol=None)`: Get open positions, optionally filtered by symbol
- `close_all(symbol=None)`: Close all positions, optionally filtered by symbol (returns count)

All order methods return `mt5.OrderSendResult` object.

---

## Notes

- The MT5 terminal must be installed and accessible on your system
- DataFrames returned by properties (`ticks`, `bars`) are copies to prevent race conditions
- Bar aggregation only appends closed bars to ensure data integrity
- The library does not implement validation guards - ensure your orders comply with broker requirements
- SL/TP values in order methods are absolute price levels, not pip distances

---

## License

MIT License - see LICENSE file for details

---

## Author

Simone Zani

## Repository

https://github.com/zanisimone/sz_mt5stream
