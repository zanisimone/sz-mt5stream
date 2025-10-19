import time
from sz_mt5stream import MT5Stream, MT5Executor


def trading_callback(ticks_df):
    """Process new ticks and make trading decisions"""
    latest_bid = ticks_df["bid"].iloc[-1]
    latest_ask = ticks_df["ask"].iloc[-1]

    # Your trading logic here
    print(f"Bid: {latest_bid}, Ask: {latest_ask}")


# Initialize stream with auto-login
stream = MT5Stream(
    symbol="BTCUSD",
    terminal_path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    poll_interval=0.25,
    bars_timeframe="M1",
    rolling_ticks=10000,
    rolling_bars=2000,
)

print("Connecting to MT5 and starting stream...")

# Initialize executor
executor = MT5Executor(magic=42, deviation=20)

print("Executor initialized.")
# Start streaming with callback
stream.start(callback=trading_callback)

print("Streaming started. Press Ctrl+C to stop.")

try:
    # Keep application running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
    stream.stop()
