import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd
from app.main import app, state, portfolio, process_closed_candle, db, laya

@pytest.mark.anyio
async def test_trading_lock_when_paused():
    # Ensure trading is paused
    state["trading_active"] = False
    state["symbol"] = "BTCUSDT"
    state["interval"] = "1m"
    candles = [
        {"time": 5000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0, "closed": True}
        for i in range(50)
    ]
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["decision_count"] = 0
    portfolio.cash = 10000.0
    portfolio.set_active_symbol("BTCUSDT")
    portfolio.quantity = 0.0

    mock_decision = {
        "action": "buy",
        "confidence": 0.95,
        "latency_ms": 12.0,
        "reason": "Strong momentum",
        "model": "laya-test"
    }

    initial_trades_count = len(db.recent_trades("BTCUSDT"))

    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = mock_decision
        await process_closed_candle()

    # When paused, no trade must be executed!
    assert portfolio.cash == 10000.0
    assert portfolio.quantity == 0.0
    assert len(db.recent_trades("BTCUSDT")) == initial_trades_count

    # The latest decision should be marked with is_live_trading = False
    latest = state["latest_decision"]
    assert latest is not None
    assert latest["is_live_trading"] is False

@pytest.mark.anyio
async def test_trading_execution_when_active():
    # When active, orders must execute normally
    state["trading_active"] = True
    state["symbol"] = "BTCUSDT"
    state["interval"] = "1m"
    candles = [
        {"time": 8000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0, "closed": True}
        for i in range(50)
    ]
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["decision_count"] = 0
    portfolio.cash = 10000.0
    portfolio.set_active_symbol("BTCUSDT")
    portfolio.quantity = 0.0

    mock_decision = {
        "action": "buy",
        "confidence": 0.85,
        "latency_ms": 10.0,
        "reason": "Signal confirmed",
        "model": "laya-test"
    }

    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = mock_decision
        await process_closed_candle()

    # When active, buy order must be executed!
    assert portfolio.cash < 10000.0
    assert portfolio.quantity > 0.0
    assert state["latest_decision"]["is_live_trading"] is True
