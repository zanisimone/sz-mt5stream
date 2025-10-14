# sz_mt5stream Examples

This folder contains example scripts demonstrating the usage of the sz_mt5stream library.

## Files

- `stream_example.py` - Comprehensive example demonstrating all library features

## Running the Examples

### Prerequisites

1. Install the library:
```bash
pip install sz_mt5stream
```

Or if running from the repository:
```bash
cd ..
pip install -e .
```

2. Ensure MetaTrader 5 is installed on your system

3. Update the configuration variables in `stream_example.py`:
   - `SYMBOL` - Trading symbol (e.g., "EURUSD", "US100")
   - `TERMINAL_PATH` - Path to your MT5 terminal
   - `LOGIN`, `PASSWORD`, `SERVER` - Your MT5 credentials (optional if already logged in)

### Run the Examples

```bash
python stream_example.py
```

## What the Examples Demonstrate

### Example 1: Basic Tick Streaming
- Simple tick streaming without bar aggregation
- Real-time bid/ask prices and spread calculation
- Buffer management

### Example 2: Bar Aggregation
- Streaming ticks with automatic bar aggregation
- Detection of new closed bars
- OHLC data display

### Example 3: Callback Function
- Using callback functions for real-time tick processing
- Background thread execution
- Tick counting and processing

### Example 4: Manual Polling
- Pull-based tick retrieval without background threads
- Manual control over polling frequency
- Synchronous data access

### Example 5: Order Execution
- Order executor demonstration (dry run)
- Position management
- Market and pending orders (commented out for safety)

## Safety Note

Order execution examples are commented out by default to prevent accidental trading. Only uncomment and use them when you're ready to place actual trades on your account.

## Troubleshooting

If you encounter errors:

1. **"mt5.initialize() failed"**
   - Ensure MT5 terminal is installed
   - Check the terminal path is correct
   - Verify login credentials if using auto-login

2. **"symbol_select() failed"**
   - The symbol must exist in your broker's symbol list
   - Add the symbol to Market Watch in MT5

3. **No ticks received**
   - Ensure the market is open for your symbol
   - Check your internet connection
   - Verify the symbol is subscribed in Market Watch

