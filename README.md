# sz_mt5stream

Minimal library to stream real-time ticks from MetaTrader 5 into pandas DataFrames, fetch official broker candles with period-aware timing, auto-launch and log into MT5, and send basic orders (market/limit/stop) with optional SL/TP.

Key features:
- Real-time tick streaming with accurate broker timezone handling
- Period-aware candle fetching - gets official MT5 candles exactly when periods close
- Automatic timezone alignment for correct data retrieval
- Complete candle data including tick volume, real volume, and spread

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

### Fetching Broker Candles

```python
stream = MT5Stream(
    symbol="EURUSD",
    bars_timeframe="M1",  # Fetch official 1-minute candles from broker
    rolling_ticks=10000,
    rolling_bars=2000
)
stream.start()

# Access official broker candles (fetched when each period closes)
df_bars = stream.bars
print(df_bars.head())
# Includes: open, high, low, close, tick_volume, spread, real_volume

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

## Data Structures

### Ticks DataFrame

The `stream.ticks` property returns a pandas DataFrame with real-time tick data.

**Columns:**
- `time` (datetime64): Timestamp in broker timezone
- `bid` (float): Bid price
- `ask` (float): Ask price  
- `last` (float): Last traded price (0 for forex/CFDs)
- `volume` (int): Trade volume (0 for forex/CFDs quote ticks)
- `time_msc` (int): Timestamp in milliseconds

**Example:**
```
                           time       bid       ask      last  volume        time_msc
0  2025-10-14 01:10:23  1.08945   1.08952      0.0       0  1728869423542
1  2025-10-14 01:10:24  1.08946   1.08953      0.0       0  1728869424128
2  2025-10-14 01:10:25  1.08944   1.08951      0.0       0  1728869425671
3  2025-10-14 01:10:26  1.08947   1.08954      0.0       0  1728869426234
4  2025-10-14 01:10:27  1.08945   1.08952      0.0       0  1728869427891
```

### Bars DataFrame

The `stream.bars` property returns a pandas DataFrame with official broker candles, indexed by time.

**Index:**
- `time` (datetime64): Candle timestamp in broker timezone

**Columns:**
- `open` (float): Opening price
- `high` (float): Highest price
- `low` (float): Lowest price
- `close` (float): Closing price
- `tick_volume` (int): Number of price updates (tick count)
- `spread` (int): Average spread in points
- `real_volume` (int): Actual traded volume

**Example:**
```
time                          open      high       low     close  tick_volume  spread  real_volume
2025-10-14 01:05:00       1.08940   1.08965   1.08935   1.08950          234      15         1250
2025-10-14 01:06:00       1.08950   1.08972   1.08943   1.08968          187      14         1180
2025-10-14 01:07:00       1.08968   1.08980   1.08955   1.08962          201      16         1320
2025-10-14 01:08:00       1.08962   1.08975   1.08948   1.08956          178      15         1090
2025-10-14 01:09:00       1.08956   1.08971   1.08949   1.08965          195      14         1240
```

### Position Data

The `executor.positions()` method returns a list of `TradePosition` objects with the following attributes:

**Attributes:**
- `ticket` (int): Position ticket number
- `time` (int): Position open time (Unix timestamp)
- `type` (int): Position type (0=BUY, 1=SELL)
- `magic` (int): Magic number
- `identifier` (int): Position identifier
- `volume` (float): Position volume in lots
- `price_open` (float): Opening price
- `sl` (float): Stop Loss price (0 if not set)
- `tp` (float): Take Profit price (0 if not set)
- `price_current` (float): Current price
- `swap` (float): Accumulated swap
- `profit` (float): Current profit/loss
- `symbol` (str): Trading symbol
- `comment` (str): Position comment
- `external_id` (str): External identifier

**Example:**
```python
positions = executor.positions(symbol="EURUSD")
for pos in positions:
    print(f"Ticket: {pos.ticket}")
    print(f"Type: {'BUY' if pos.type == 0 else 'SELL'}")
    print(f"Volume: {pos.volume}")
    print(f"Open Price: {pos.price_open}")
    print(f"Current Price: {pos.price_current}")
    print(f"Profit: {pos.profit}")
    print(f"SL: {pos.sl}, TP: {pos.tp}")
```

### Order Result

Order execution methods return an `OrderSendResult` object with the following attributes:

**Attributes:**
- `retcode` (int): Return code (10009 = success)
- `deal` (int): Deal ticket if executed
- `order` (int): Order ticket
- `volume` (float): Order volume
- `price` (float): Order price
- `bid` (float): Current bid price
- `ask` (float): Current ask price
- `comment` (str): Broker comment
- `request_id` (int): Request identifier
- `retcode_external` (int): External return code

**Example:**
```python
result = executor.market_buy("EURUSD", volume=0.1, sl=1.0800, tp=1.0900)

if result.retcode == 10009:  # TRADE_RETCODE_DONE
    print(f"Order successful!")
    print(f"Deal ticket: {result.deal}")
    print(f"Execution price: {result.price}")
    print(f"Volume: {result.volume}")
else:
    print(f"Order failed: {result.retcode}")
    print(f"Comment: {result.comment}")
```

**Common Return Codes:**
- `10009`: Request completed successfully
- `10013`: Invalid request
- `10014`: Invalid volume
- `10015`: Invalid price
- `10016`: Invalid stops (SL/TP)
- `10018`: Market is closed
- `10019`: No money (insufficient funds)
- `10027`: Trading disabled

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
- `bars`: Returns copy of rolling bar DataFrame with time as index (columns: open, high, low, close, tick_volume, spread, real_volume). Candles are fetched directly from MT5 broker when periods close.

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
- **Candles are fetched directly from MT5 broker**, not aggregated from ticks - this ensures 100% accuracy with broker data
- **Period-aware fetching**: Candles are retrieved exactly when each timeframe period closes (e.g., at :00 seconds for M1, at :00/:05/:10 for M5)
- **Timezone handling**: The library automatically uses broker server time for data requests, ensuring correct alignment regardless of your local timezone
- Candles include complete broker data: OHLC prices, tick volume (number of price updates), real volume (actual traded volume), and average spread
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
