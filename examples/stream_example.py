"""
Example script demonstrating sz_mt5stream library usage.

This script shows:
- Basic tick streaming with debug output
- Bar aggregation from ticks
- Callback function usage
- Manual polling mode
- Order execution (commented out for safety)

IMPORTANT: Update the configuration variables before running!
"""

import time
import sys
from datetime import datetime

# Add parent directory to path if running from examples folder
sys.path.insert(0, '..')

from sz_mt5stream import MT5Stream, MT5Executor


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES FOR YOUR SETUP
# ============================================================================

SYMBOL = "EURUSD"  # Change to your preferred symbol
TERMINAL_PATH = "C:/Program Files/MetaTrader 5/terminal64.exe"  # Path to MT5
TERMINAL_PATH = "C:/Program Files/FPMarkets MT5 Terminal/terminal64.exe"
LOGIN = None  # Your MT5 login (or None to use already logged-in terminal)
PASSWORD = None  # Your MT5 password
SERVER = None  # Your broker server name

# Stream configuration
POLL_INTERVAL = 0.5  # Seconds between polls
BARS_TIMEFRAME = "M1"  # Bar aggregation timeframe: M1, M5, M15, H1, D1
ROLLING_TICKS = 1000  # Keep last 1000 ticks in memory
ROLLING_BARS = 100  # Keep last 100 bars in memory

# Test duration
TEST_DURATION = 30  # Run test for 30 seconds


# ============================================================================
# EXAMPLE 1: Basic Tick Streaming
# ============================================================================

def example_basic_streaming():
    """Basic tick streaming without bar aggregation"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Tick Streaming")
    print("="*80 + "\n")
    
    # Create stream instance
    stream = MT5Stream(
        symbol=SYMBOL,
        poll_interval=POLL_INTERVAL,
        rolling_ticks=ROLLING_TICKS,
        terminal_path=TERMINAL_PATH if LOGIN else None,
        login=LOGIN,
        password=PASSWORD,
        server=SERVER
    )
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting stream for {SYMBOL}...")
    stream.start()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stream started successfully!\n")
    
    try:
        # Run for specified duration
        end_time = time.time() + 10  # 10 seconds for this example
        
        while time.time() < end_time:
            # Get current ticks
            ticks = stream.ticks
            
            if not ticks.empty:
                latest = ticks.iloc[-1]
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Ticks in buffer: {len(ticks):4d} | "
                      f"Latest - Bid: {latest['bid']:.5f}, "
                      f"Ask: {latest['ask']:.5f}, "
                      f"Spread: {(latest['ask'] - latest['bid']):.5f}")
            
            time.sleep(2)
    
    finally:
        stream.stop()
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stream stopped.\n")


# ============================================================================
# EXAMPLE 2: Streaming with Bar Aggregation
# ============================================================================

def example_with_bars():
    """Tick streaming with bar aggregation"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Streaming with Bar Aggregation")
    print("="*80 + "\n")
    
    stream = MT5Stream(
        symbol=SYMBOL,
        poll_interval=POLL_INTERVAL,
        rolling_ticks=ROLLING_TICKS,
        rolling_bars=ROLLING_BARS,
        bars_timeframe=BARS_TIMEFRAME,
        terminal_path=TERMINAL_PATH if LOGIN else None,
        login=LOGIN,
        password=PASSWORD,
        server=SERVER
    )
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting stream with {BARS_TIMEFRAME} bar aggregation...")
    stream.start()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stream started!\n")
    
    try:
        end_time = time.time() + 15  # 15 seconds for this example
        last_bar_count = 0
        
        while time.time() < end_time:
            ticks = stream.ticks
            bars = stream.bars
            
            # Debug output for ticks
            if not ticks.empty:
                latest_tick = ticks.iloc[-1]
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Ticks: {len(ticks):4d} | "
                      f"Bid: {latest_tick['bid']:.5f} | "
                      f"Ask: {latest_tick['ask']:.5f}")
            
            # Debug output for bars (only when new bar appears)
            if not bars.empty and len(bars) > last_bar_count:
                print(f"\n{'>>> NEW BAR DETECTED! <<<':^80}\n")
                latest_bar = bars.iloc[-1]
                print(f"    Time: {bars.index[-1]}")
                print(f"    Open:   {latest_bar['open']:.5f}")
                print(f"    High:   {latest_bar['high']:.5f}")
                print(f"    Low:    {latest_bar['low']:.5f}")
                print(f"    Close:  {latest_bar['close']:.5f}")
                print(f"    Volume: {int(latest_bar['tick_volume'])}")
                print(f"    Total bars in buffer: {len(bars)}\n")
                last_bar_count = len(bars)
            
            time.sleep(2)
    
    finally:
        stream.stop()
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stream stopped.\n")


# ============================================================================
# EXAMPLE 3: Using Callback Function
# ============================================================================

def example_with_callback():
    """Streaming with callback function for real-time processing"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Streaming with Callback Function")
    print("="*80 + "\n")
    
    tick_count = [0]  # Use list to allow modification in nested function
    
    def on_new_ticks(ticks_df):
        """Callback function called for each batch of new ticks"""
        tick_count[0] += len(ticks_df)
        
        if len(ticks_df) > 0:
            latest = ticks_df.iloc[-1]
            timestamp = latest['time']
            
            print(f"[CALLBACK] Received {len(ticks_df)} new tick(s) | "
                  f"Total processed: {tick_count[0]:5d} | "
                  f"Bid: {latest['bid']:.5f} | "
                  f"Ask: {latest['ask']:.5f} | "
                  f"Time: {timestamp}")
    
    stream = MT5Stream(
        symbol=SYMBOL,
        poll_interval=POLL_INTERVAL,
        rolling_ticks=ROLLING_TICKS,
        terminal_path=TERMINAL_PATH if LOGIN else None,
        login=LOGIN,
        password=PASSWORD,
        server=SERVER
    )
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting stream with callback...")
    stream.start(callback=on_new_ticks)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stream started! Callback will be triggered on new ticks.\n")
    
    try:
        # Just wait while callback processes ticks in background
        time.sleep(10)
    
    finally:
        stream.stop()
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stream stopped.")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Total ticks processed: {tick_count[0]}\n")


# ============================================================================
# EXAMPLE 4: Manual Polling Mode
# ============================================================================

def example_manual_polling():
    """Manual polling without background thread"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Manual Polling Mode")
    print("="*80 + "\n")
    
    stream = MT5Stream(
        symbol=SYMBOL,
        terminal_path=TERMINAL_PATH if LOGIN else None,
        login=LOGIN,
        password=PASSWORD,
        server=SERVER
    )
    
    # Initialize connection but don't start background thread
    import MetaTrader5 as mt5
    if LOGIN and PASSWORD and SERVER:
        mt5.initialize(path=TERMINAL_PATH, login=LOGIN, password=PASSWORD, server=SERVER)
    else:
        mt5.initialize(path=TERMINAL_PATH if TERMINAL_PATH else None)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Manual polling mode started...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calling poll() manually every 2 seconds...\n")
    
    try:
        total_ticks = 0
        for i in range(5):  # Poll 5 times
            print(f"--- Poll #{i+1} ---")
            new_ticks = stream.poll()
            
            if not new_ticks.empty:
                total_ticks += len(new_ticks)
                latest = new_ticks.iloc[-1]
                print(f"    New ticks: {len(new_ticks)}")
                print(f"    Latest bid: {latest['bid']:.5f}, ask: {latest['ask']:.5f}")
                print(f"    Total ticks collected: {total_ticks}")
            else:
                print(f"    No new ticks")
            
            print()
            time.sleep(2)
    
    finally:
        mt5.shutdown()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Manual polling stopped.\n")


# ============================================================================
# EXAMPLE 5: Order Execution (COMMENTED OUT FOR SAFETY)
# ============================================================================

def example_order_execution():
    """
    Order execution example - COMMENTED OUT FOR SAFETY
    
    Uncomment the actual order calls only when you're ready to trade!
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Order Execution (DRY RUN - NO ACTUAL ORDERS)")
    print("="*80 + "\n")
    
    # Initialize MT5 connection
    import MetaTrader5 as mt5
    if LOGIN and PASSWORD and SERVER:
        ok = mt5.initialize(path=TERMINAL_PATH, login=LOGIN, password=PASSWORD, server=SERVER)
    else:
        ok = mt5.initialize(path=TERMINAL_PATH if TERMINAL_PATH else None)
    
    if not ok:
        print(f"Failed to initialize MT5: {mt5.last_error()}")
        return
    
    try:
        # Create executor
        executor = MT5Executor(magic=999, deviation=20)
        
        print("Executor created with:")
        print(f"  Magic number: 999")
        print(f"  Deviation: 20 points\n")
        
        # Get current positions
        positions = executor.positions()
        print(f"Current open positions: {len(positions) if positions else 0}")
        if positions:
            for pos in positions:
                print(f"  - {pos.symbol}: {pos.type} | Volume: {pos.volume} | Profit: {pos.profit}")
        print()
        
        # Example order calls (COMMENTED OUT FOR SAFETY)
        print("Example order calls (currently disabled):")
        print()
        
        print("# Market buy order:")
        print(f"# result = executor.market_buy('{SYMBOL}', volume=0.01, sl=1.0800, tp=1.0900)")
        print(f"# print(f'Order result: {{result.retcode}}, Deal: {{result.deal}}')")
        print()
        
        print("# Market sell order:")
        print(f"# result = executor.market_sell('{SYMBOL}', volume=0.01, sl=1.0950, tp=1.0850)")
        print()
        
        print("# Buy limit order:")
        print(f"# result = executor.buy_limit('{SYMBOL}', volume=0.01, price=1.0850, sl=1.0800, tp=1.0900)")
        print()
        
        print("# Close all positions:")
        print(f"# closed = executor.close_all(symbol='{SYMBOL}')")
        print(f"# print(f'Closed {{closed}} position(s)')")
        print()
        
        print("REMINDER: Uncomment these calls when you're ready to place actual orders!")
        print()
        
    finally:
        mt5.shutdown()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MT5 connection closed.\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("sz_mt5stream Library Examples")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Symbol: {SYMBOL}")
    print(f"  Terminal: {TERMINAL_PATH if TERMINAL_PATH else 'Default'}")
    print(f"  Login: {'Configured' if LOGIN else 'Using current MT5 login'}")
    print()
    
    try:
        # Run examples
        example_basic_streaming()
        time.sleep(2)
        
        example_with_bars()
        time.sleep(2)
        
        example_with_callback()
        time.sleep(2)
        
        example_manual_polling()
        time.sleep(2)
        
        example_order_execution()
        
        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n!!! ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nMake sure:")
        print("1. MetaTrader 5 is installed")
        print("2. The symbol exists in your Market Watch")
        print("3. Terminal path and credentials are correct (if using auto-login)")
        print()


if __name__ == "__main__":
    main()

