import time
import sys
from datetime import datetime, timezone, timedelta

# Add parent directory to path if running from examples folder
sys.path.insert(0, '..')

import MetaTrader5 as mt5
from sz_mt5stream import MT5Stream, MT5Executor

# Note: All timestamps from stream.ticks and stream.bars are now automatically
# in broker's local timezone (timezone-naive). No conversion needed.

SYMBOL = "BTCUSD"  # set to the exact Market Watch symbol
TERMINAL_PATH = "C:/Program Files/FPMarkets MT5 Terminal/terminal64.exe"

LOGIN = None      # keep None to reuse the terminal's current session
PASSWORD = None
SERVER = None

# Stream configuration
POLL_INTERVAL = 0.5
BARS_TIMEFRAME = "M1"  # Try M1, M5, M15, H1, or D1
ROLLING_TICKS = 1000
ROLLING_BARS = 100

TEST_DURATION = 180  # seconds (3 minutes to see multiple candles)

# Helper function to calculate next candle close time
def get_next_candle_time(current_dt, timeframe):
    """Calculate when the next candle will close based on timeframe."""
    if timeframe == "M1":
        # Next minute boundary
        next_time = current_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    elif timeframe == "M5":
        # Next 5-minute boundary
        minute = ((current_dt.minute // 5) + 1) * 5
        if minute >= 60:
            next_time = (current_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        else:
            next_time = current_dt.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == "M15":
        # Next 15-minute boundary
        minute = ((current_dt.minute // 15) + 1) * 15
        if minute >= 60:
            next_time = (current_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        else:
            next_time = current_dt.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == "H1":
        # Next hour boundary
        next_time = (current_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    elif timeframe == "D1":
        # Next day boundary
        next_time = (current_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        next_time = current_dt + timedelta(minutes=1)
    return next_time


# ============================================================================
# HEADER: Show configuration and connection info
# ============================================================================

print("\n" + "="*80)
print(f"  MT5 PERIOD-AWARE CANDLE STREAMING TEST".center(80))
print("="*80)
print(f"\n  Symbol:     {SYMBOL}")
print(f"  Timeframe:  {BARS_TIMEFRAME}")
print(f"  Duration:   {TEST_DURATION}s\n")

stream = MT5Stream(
    symbol=SYMBOL,
    poll_interval=POLL_INTERVAL,
    rolling_ticks=ROLLING_TICKS,
    rolling_bars=ROLLING_BARS,
    bars_timeframe=BARS_TIMEFRAME,
    terminal_path=TERMINAL_PATH,
    login=LOGIN,
    password=PASSWORD,
    server=SERVER,
)

print("Connecting to MT5...")
stream.start()

# Get symbol info
si = mt5.symbol_info(SYMBOL)
ai = mt5.account_info()
ti = mt5.terminal_info()
digits = (si.digits if si else 5)

print(f"\n[OK] Connected to {ai.company if ai else '?'} (Server: {ai.server if ai else '?'})")
print(f"[OK] Symbol: {SYMBOL} - {si.description if si else '?'}")

# Show broker time
broker_dt = datetime.fromtimestamp(mt5.symbol_info_tick(SYMBOL).time, tz=timezone.utc).replace(tzinfo=None)
print(f"[OK] Broker Time: {broker_dt.strftime('%Y-%m-%d %H:%M:%S')}")

print("\n" + "="*80)
print("  STREAMING STARTED - Watching for new candles...")
print("="*80 + "\n")

try:
    end_time = time.time() + TEST_DURATION
    last_candle_time = None  # Track timestamp of last seen candle
    update_interval = 2  # seconds between updates

    while time.time() < end_time:
        ticks = stream.ticks
        bars = stream.bars
        
        # Get current broker time
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick:
            broker_time = datetime.fromtimestamp(tick.time, tz=timezone.utc).replace(tzinfo=None)
            next_candle = get_next_candle_time(broker_time, BARS_TIMEFRAME)
            seconds_to_next = int((next_candle - broker_time).total_seconds())
            
            # Display current status
            if not ticks.empty:
                latest = ticks.iloc[-1]
                
                # Build status line with countdown (using broker time)
                status = (f"[{broker_time.strftime('%H:%M:%S')}] | "
                         f"Next {BARS_TIMEFRAME} in {seconds_to_next:3d}s | "
                         f"Ticks: {len(ticks):4d} | "
                         f"Bid: {latest['bid']:.{digits}f} | "
                         f"Ask: {latest['ask']:.{digits}f}")
                
                # Add candle count if we have bars
                if not bars.empty:
                    status += f" | Candles: {len(bars)}"
                
                print(status)

        # Check for NEW candles by comparing latest candle timestamp
        if not bars.empty:
            current_latest_time = bars.index[-1]
            
            # Check if we have a new candle (different timestamp than before)
            if last_candle_time is None or current_latest_time > last_candle_time:
                # Determine how many new candles (usually 1, but could be more if we skipped a poll)
                if last_candle_time is None:
                    # First time - show only the latest candle, not all history
                    new_candles = bars.tail(1)
                    num_new = 1
                else:
                    # Get all candles newer than last seen
                    new_candles = bars[bars.index > last_candle_time]
                    num_new = len(new_candles)
                
                if num_new > 0:
                    print("\n" + "="*80)
                    print(f">>> NEW CANDLE DETECTED: {BARS_TIMEFRAME} candle completed <<<".center(80))
                    print("="*80)
                    
                    # Show the new candle(s)
                    for idx, (candle_time, row) in enumerate(new_candles.iterrows(), 1):
                        if num_new > 1:
                            print(f"\n  Candle {idx} of {num_new}:")
                        print(f"  ┌─ Time:        {candle_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  ├─ Open:        {row['open']:.{digits}f}")
                        print(f"  ├─ High:        {row['high']:.{digits}f}")
                        print(f"  ├─ Low:         {row['low']:.{digits}f}")
                        print(f"  ├─ Close:       {row['close']:.{digits}f}")
                        print(f"  ├─ Tick Volume: {int(row['tick_volume']):,}")
                        print(f"  ├─ Real Volume: {int(row['real_volume']):,}")
                        print(f"  └─ Spread:      {int(row['spread'])}")
                    
                    # Show recent history (last 5 candles)
                    if len(bars) >= 2:
                        print(f"\n  Recent {BARS_TIMEFRAME} Candles (last 5):")
                        print(f"  {'Time':<20} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>10}")
                        print(f"  {'-'*78}")
                        for candle_time, row in bars.tail(5).iterrows():
                            time_str = candle_time.strftime('%Y-%m-%d %H:%M:%S')
                            print(f"  {time_str:<20} "
                                  f"{row['open']:>12.{digits}f} "
                                  f"{row['high']:>12.{digits}f} "
                                  f"{row['low']:>12.{digits}f} "
                                  f"{row['close']:>12.{digits}f} "
                                  f"{int(row['tick_volume']):>10,}")
                    
                    print("\n" + "="*80 + "\n")
                
                # Update last seen candle timestamp
                last_candle_time = current_latest_time

        time.sleep(update_interval)

finally:
    stream.stop()
    bars = stream.bars
    
    print("\n" + "="*80)
    print("  TEST COMPLETED")
    print("="*80)
    
    if not bars.empty:
        first_time = bars.index[0].strftime('%Y-%m-%d %H:%M:%S')
        last_time = bars.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n[OK] Total candles collected: {len(bars)}")
        print(f"[OK] Time range: {first_time} to {last_time}")
        print(f"[OK] Final close price: {bars.iloc[-1]['close']:.{digits}f}")
    else:
        print("\n[WARNING] No candles were collected during this test.")
        print("          Try running for a longer duration or check your connection.")
    
    print("\n" + "="*80 + "\n")
