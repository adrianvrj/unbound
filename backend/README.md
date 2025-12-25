# Backend - Funding Rate Arbitrage Vault

Python backend that manages the delta-neutral funding rate strategy on Extended.

## Features

- **Strategy Logic**: Opens SHORT positions when funding is positive
- **Rebalancer**: Automated loop that checks every hour
- **REST API**: FastAPI endpoints for frontend integration

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Extended API keys
```

## Running

```bash
# Start API server
python main.py

# Server runs at http://localhost:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Vault status, funding rate, position |
| `/api/position` | GET | Current position details |
| `/api/funding-history` | GET | Funding payment history |
| `/api/apy` | GET | APY estimates at different leverage |
| `/api/rebalancer/status` | GET | Rebalancer status |
| `/api/rebalancer/start` | POST | Start automated rebalancing |
| `/api/rebalancer/stop` | POST | Stop rebalancing |
| `/api/rebalancer/run-once` | POST | Manual strategy execution |

## Architecture

```
src/
├── config.py           # Environment variables
├── extended_client.py  # Extended API wrapper
├── strategy.py         # Funding rate strategy logic
├── rebalancer.py       # Automated rebalancing loop
└── api.py              # FastAPI endpoints
```

## Strategy Logic

1. **Check Funding Rate**: Every hour
2. **If positive > threshold**: Open SHORT (receive funding)
3. **If negative < threshold**: Close position (avoid paying)
4. **Collect funding**: Automatically every hour
