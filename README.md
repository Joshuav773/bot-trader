# Bot Trader - Options Order Flow Detection System

A sophisticated options trading bot that detects large orders and unusual volume activity in real-time using the Schwab API. The system uses a multi-layer detection approach to identify significant market movements and order flow.

## Overview

This bot scans the options market for:
- **Large Orders**: Detects significant bid/ask size changes and price impact
- **Large Trades**: Identifies volume spikes and executed trades
- **Unusual Volume**: Compares current activity to historical baselines
- **Volume Analytics**: Tracks peak volume periods and highest volume strikes

The core logic is implemented in `test_real_data.py`, which will eventually become the streamer's logic.

## Features

### Core Detection Capabilities

1. **Large Order Detection** (`order_tracker.py`)
   - Monitors bid/ask size changes
   - Detects price impact from large orders
   - Multi-signal detection with deduplication
   - Configurable minimum order value threshold

2. **Large Trade Detection** (`trade_tracker.py`)
   - Tracks immediate volume spikes
   - Monitors accumulated trade volume
   - Identifies executed large trades
   - Deduplication to prevent false positives

3. **Unusual Volume Tracking** (`unusual_volume_tracker.py`)
   - Establishes baseline volume for each contract
   - Detects volume spikes (e.g., 2x average)
   - Parses options symbols (underlying, expiration, type, strike)
   - Tracks volume trends over time

4. **Options Chain Analysis** (`test_real_data.py`)
   - Fetches complete options chains with full parameters
   - Filters contracts by volume > open interest
   - Finds highest volume strikes across all expirations
   - Tracks peak volume periods (hourly)

### API Integration

- **Schwab Options Chain API**: Full chain retrieval with:
  - `contractType=ALL` (Calls and Puts)
  - `strikeRange=ALL` (All strikes, not just near-the-money)
  - `strategy=SINGLE` (Individual contracts, not spreads)
  
- **Schwab Price History API**: Historical volume analysis
- **Schwab Streaming API**: Real-time Level 1 and Level 2 data

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example .env file
cp .env.example .env

# Edit .env and add your Schwab API credentials
# Get them from: https://developer.schwab.com
```

Required environment variables:
- `SCHWAB_APP_KEY`: Schwab API App Key
- `SCHWAB_APP_SECRET`: Schwab API App Secret
- `SCHWAB_CALLBACK_URL`: OAuth callback URL (default: http://127.0.0.1:8080)
- `DATABASE_URL`: PostgreSQL connection string (optional, for persistence)
- `GMAIL_USER`: Gmail address for notifications (optional)
- `GMAIL_PASSWORD`: Gmail app password for notifications (optional)

### 3. Get Schwab API Token

First time only - this will open a browser for OAuth:

```bash
# The streamer will automatically prompt for OAuth on first run
python3 schwab_streamer.py
```

After OAuth completes, `token.json` will be created. This file allows automatic authentication without browser in the future.

**For Production**: Use `SCHWAB_TOKEN_JSON` environment variable instead of `token.json` file.

### 4. Test with Real Data

The `test_real_data.py` script is the core testing and development tool:

```bash
# List contracts for a symbol (with detailed info)
python3 test_real_data.py OXY --list-only

# List specific number of contracts
python3 test_real_data.py OXY --max-contracts 20 --list-only

# Test detection system with real contracts
python3 test_real_data.py OXY --max-contracts 5

# Test with specific options symbols
python3 test_real_data.py AAPL --symbols "AAPL_260303C150,AAPL_260303P150"
```

## test_real_data.py - Core Logic

This script contains all the core logic that will eventually be integrated into the streamer. It demonstrates:

### Key Functions

#### `get_real_options_symbols(client, symbol, max_contracts=10)`
Fetches real options contracts from Schwab API with full parameters:
- Uses `contractType=ALL`, `strikeRange=ALL`, `strategy=SINGLE` for complete feed
- Filters contracts where `volume > openInterest`
- Returns contracts with full quote data (bid, ask, last, volume, open interest)

**API Endpoint**: `GET /marketdata/v1/chains?symbol={SYMBOL}&contractType=ALL&strategy=SINGLE&range=ALL`

#### `find_highest_volume_strike(client, symbol, use_nearest_expiration=False)`
Finds the strike price with highest total volume:
- Aggregates volume by strike across all expiration dates (or nearest only)
- Returns strike, total volume, calls volume, and puts volume
- Useful for identifying most active strike prices

#### `fetch_peak_volume_period(client, symbol)`
Identifies the hourly period with highest volume during the trading day:
- Fetches minute-by-minute price history for underlying symbol
- Groups into hourly intervals
- Returns time and volume of peak period
- Suppresses HTTP request logs for cleaner output

#### `create_quotes_from_contract_data(contract, num_quotes=50)`
Creates quote entries from contract data:
- Extracts bid, ask, last, volume, open interest, bid/ask sizes
- Generates multiple quote entries to simulate stream
- Displays detailed contract information

#### `fetch_real_quote_data(client, symbol, num_quotes=50)`
Fetches real-time quote data for options:
- Handles both underscore and space formats for options symbols
- Parses nested API response structure
- Returns quote data ready for detection testing

#### `test_detection(quotes, symbol)`
Tests the detection system with quote data:
- Uses `LargeOrderTracker` for order detection
- Uses `LargeTradeTracker` for trade detection
- Uses `UnusualVolumeTracker` for volume analysis
- Simulates real-time processing

### Command Line Arguments

```bash
python3 test_real_data.py SYMBOL [OPTIONS]

Arguments:
  SYMBOL              Underlying symbol (e.g., AAPL, NVDA, OXY)

Options:
  --symbols           Comma-separated options symbols (e.g., AAPL_260303C150,NVDA_260303C400)
  --max-contracts    Max contracts to fetch/test (default: 10)
  --periods          Number of quote entries to generate (default: 50)
  --list-only        Only list contracts with detailed info, don't run detection tests
```

### Output Features

When using `--list-only`, the script provides:

1. **Contract Details**:
   - Type (CALL/PUT), Strike, Expiration
   - Bid/Ask/Last prices with sizes
   - Volume and Open Interest
   - Estimated order values (bid/ask side)

2. **Peak Volume Period**:
   - Highest volume hour of the trading day
   - Volume in contracts

3. **Highest Volume Strike**:
   - Single strike with highest volume across ALL expirations
   - Aggregated calls and puts volume
   - Note: This is per-strike, not total volume

## Project Structure

```
bot-trader/
├── test_real_data.py      # Core testing/development script (main logic)
├── schwab_streamer.py     # Real-time streaming bot
├── order_tracker.py       # Large order detection
├── trade_tracker.py       # Large trade detection
├── unusual_volume_tracker.py  # Unusual volume detection
├── notifications.py       # Email notification service
├── db.py                  # Database persistence
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## API Parameters

### Options Chain API

The script uses full parameters to get complete, non-truncated feeds:

```python
client.get_option_chain(
    symbol,
    contract_type=client.Options.ContractType.ALL,      # All contract types
    strike_range=client.Options.StrikeRange.ALL,        # All strikes
    strategy=client.Options.Strategy.SINGLE             # Individual contracts
)
```

**URL Format**: 
```
https://api.schwabapi.com/marketdata/v1/chains?symbol={SYMBOL}&contractType=ALL&strategy=SINGLE&range=ALL
```

### Important Notes

- **Expired Contracts**: The API only returns active/upcoming expirations. Expired contracts are not included.
- **Volume Data**: Uses `totalVolume` field (daily volume snapshot) from the API.
- **Filtering**: Contracts are filtered where `volume > openInterest` to focus on active trading.

## Detection System Architecture

### Layer 1: Level 1 Quotes (Real-time)
- Processes bid/ask/last price updates
- Monitors bid/ask size changes
- Tracks volume spikes
- Detects price impact

### Layer 2: Level 2 Order Book (Real-time)
- Scans order book depth
- Identifies large resting orders
- Monitors order book imbalances

### Layer 3: Historical Analysis
- Compares current volume to baseline
- Identifies unusual activity patterns
- Tracks volume trends

## Token Management

- **First Run**: OAuth flow will open browser for authorization
- **After First Run**: `token.json` contains refresh token, no browser needed
- **Automatic Refresh**: `schwab-py` automatically refreshes expired tokens
- **Token Expiration**: If refresh token expires (~90 days), OAuth will be triggered automatically
- **Production**: Use `SCHWAB_TOKEN_JSON` environment variable instead of file

## Development Workflow

The `test_real_data.py` script is the primary development tool:

1. **Test with Real Data**: Always uses real API data, never mock data
2. **Iterate on Logic**: Refine detection algorithms with real contracts
3. **Validate Results**: Compare against expected volumes and patterns
4. **Integrate to Streamer**: Once logic is validated, integrate into `schwab_streamer.py`

## Future Integration

The logic in `test_real_data.py` will be integrated into `schwab_streamer.py` for:
- Real-time options chain monitoring
- Live volume tracking
- Continuous unusual activity detection
- Automated notifications for significant events

## License

MIT
