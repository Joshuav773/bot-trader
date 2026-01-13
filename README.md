# Bot Trader

Simple FastAPI backend with Schwab streaming integration.

## Features

- **FastAPI Backend**: Clean REST API
- **Schwab Streaming**: Real-time market data streaming
- **Simple Architecture**: Minimal dependencies, easy to understand

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

### 3. Get Schwab API Token

First time only - this will open a browser for OAuth:

```bash
# The streamer will automatically prompt for OAuth on first run
# OR create token manually by running:
python3 schwab_streamer.py
```

After OAuth completes, `token.json` will be created. This file allows automatic authentication without browser in the future.

### 4. Run Services

```bash
# Run both FastAPI server and Schwab streamer
python3 start.py

# Or run separately:
# Terminal 1: FastAPI server
uvicorn main:app --reload

# Terminal 2: Schwab streamer
python3 schwab_streamer.py
```

### 5. Access API

- **API**: http://localhost:8000
- **Health**: http://localhost:8000/health
- **Status**: http://localhost:8000/api/status
- **Docs**: http://localhost:8000/docs

## Project Structure

```
bot-trader/
├── main.py              # FastAPI application
├── schwab_streamer.py   # Schwab streaming client
├── start.py             # Startup script (runs both services)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # This file
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SCHWAB_APP_KEY` | Schwab API App Key | Yes |
| `SCHWAB_APP_SECRET` | Schwab API App Secret | Yes |
| `SCHWAB_CALLBACK_URL` | OAuth callback URL (default: http://127.0.0.1) | No |
| `PORT` | FastAPI server port (default: 8000) | No |
| `HOST` | FastAPI server host (default: 0.0.0.0) | No |

## Token Management

- **First Run**: OAuth flow will open browser for authorization
- **After First Run**: `token.json` contains refresh token, no browser needed
- **Automatic Refresh**: `schwab-py` automatically refreshes expired tokens
- **Production**: Use `SCHWAB_TOKEN_JSON` environment variable instead of file

## Development

```bash
# Install dev dependencies (if any)
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## License

MIT


