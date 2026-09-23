# Crypto Laya Trader

Monolithic Python application for a **paper-trading crypto simulator**, focused on Bitcoin.

Stack:
- FastAPI + Jinja2
- Tailwind CSS via CDN
- Lightweight Charts
- Native browser WebSocket
- Binance public market-data REST/WebSocket streams
- pandas/numpy technical indicators
- Laya typed decisions for BUY / SELL / HOLD
- SQLite persistence

No exchange credentials are required because this project is simulation-only.

## Architecture

```text
Browser
  │
  ├── HTTP /api/*
  └── WebSocket /ws/live
            │
            ▼
       FastAPI monolith
       ├── MarketDataService
       ├── IndicatorEngine
       ├── LayaDecisionEngine
       ├── PaperPortfolio
       └── SQLite
            │
            ├── Binance public REST
            └── Binance public WebSocket
```

## Run

Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

Set `LAYA_ENABLED=false` only to test the UI without loading Laya. The UI will clearly show that Laya is unavailable/disabled and will keep the decision as HOLD.

## Laya

The engine uses the `typed-decisions` checkpoint. The application sends a compact English quantitative state containing price, returns, RSI, MACD, EMA20/EMA50, Bollinger position, ATR, volume ratio, trend and the simulated position.

Laya receives one typed `choice` question with exactly:
- buy
- sell
- hold

It also receives a typed `score` for setup quality.

The application records action, confidence, latency, indicators and model metadata.

## UI

The dashboard is inspired by the supplied screenshot:
- finance-terminal visual language
- left account/watchlist rail
- large central candlestick chart
- right signal/quant panel
- live connection badge
- accumulated P&L
- model latency
- confidence
- paper position
- decision log
- trade log
- crypto and timeframe selectors

## Important

This is a research/paper-trading application, not an execution bot and not financial advice. Laya is a general typed-decision engine, not a crypto forecasting model. Validate the strategy with out-of-sample backtests, transaction costs, slippage and walk-forward testing before considering any real-money use.
