import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import pandas as pd

from app.portfolio import Portfolio
from app.main import process_closed_candle, state, portfolio, db, laya

@pytest.mark.anyio
async def test_live_execution_paused_does_not_trade():
    # Setup state
    state["trading_active"] = False
    state["symbol"] = "BTCUSDT"
    state["interval"] = "1m"
    state["processing"] = False
    
    # 70 fake candles
    candles = []
    for i in range(70):
        candles.append({"time": 1000 + i*60, "open": 50000.0, "high": 50500.0, "low": 49500.0, "close": 50000.0 + i*10, "volume": 100.0, "closed": True})
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    
    # Portfolio initial state
    portfolio.cash = 10000.0
    portfolio.quantity = 0.0
    
    # Mock laya.decide to return a strong BUY
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "buy",
            "confidence": 0.85,
            "setup_quality": "good",
            "latency_ms": 12.0,
            "model": "typed-decisions",
            "reason": "Strong bullish setup"
        }
        await process_closed_candle()
        
        # When paused, NO trade should have occurred
        assert portfolio.quantity == 0.0
        assert portfolio.cash == 10000.0
        assert state["latest_decision"] is not None
        assert "Trading Pausado" in state["latest_decision"]["reason"]

@pytest.mark.anyio
async def test_live_execution_active_executes_buy_and_sell():
    state["trading_active"] = True
    state["symbol"] = "BTCUSDT"
    state["interval"] = "1m"
    state["processing"] = False
    
    candles = []
    for i in range(70):
        candles.append({"time": 2000 + i*60, "open": 50000.0, "high": 50500.0, "low": 49500.0, "close": 50000.0 + i*10, "volume": 100.0, "closed": True})
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    
    portfolio.cash = 10000.0
    portfolio.quantity = 0.0
    
    # 1. Test BUY execution
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "buy",
            "confidence": 0.75,
            "setup_quality": "good",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Bullish momentum"
        }
        await process_closed_candle()
        
        # Should have bought 25% of cash
        assert portfolio.quantity > 0.0
        assert portfolio.cash < 10000.0
        assert state["latest_decision"]["action"] == "buy"
        
        recent_trades = db.recent_trades("BTCUSDT", limit=1)
        assert len(recent_trades) >= 1
        assert recent_trades[0]["side"] == "BUY"

    # 2. Test SELL execution
    candles.append({"time": 2000 + 71*60, "open": 51000.0, "high": 51500.0, "low": 50800.0, "close": 51200.0, "volume": 120.0, "closed": True})
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    state["processing"] = False
    
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "sell",
            "confidence": 0.80,
            "setup_quality": "good",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Take profit"
        }
        await process_closed_candle()
        
        # Position should now be closed
        assert portfolio.quantity == 0.0
        assert portfolio.cash > 0.0
        
        recent_trades = db.recent_trades("BTCUSDT", limit=1)
        assert recent_trades[0]["side"] == "SELL"

@pytest.mark.anyio
async def test_live_execution_idempotency_same_candle():
    state["trading_active"] = True
    state["symbol"] = "BTCUSDT"
    state["interval"] = "1m"
    state["processing"] = False
    
    candles = []
    for i in range(70):
        candles.append({"time": 3000 + i*60, "open": 50000.0, "high": 50500.0, "low": 49500.0, "close": 50000.0, "volume": 100.0, "closed": True})
    state["candles"] = candles
    state["df"] = pd.DataFrame(candles)
    
    portfolio.cash = 10000.0
    portfolio.quantity = 0.0
    
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {"action": "buy", "confidence": 0.8, "latency_ms": 10, "model": "typed-decisions", "reason": "Go"}
        
        # First call on candle 3000 + 69*60
        await process_closed_candle()
        qty_after_first = portfolio.quantity
        assert qty_after_first > 0.0
        
        # Second call on same candle time without new candles should NOT double buy
        state["processing"] = False
        await process_closed_candle()
        assert portfolio.quantity == qty_after_first
