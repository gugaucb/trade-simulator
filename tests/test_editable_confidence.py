import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app, state, portfolio, process_closed_candle, laya

def test_api_trading_config_updates_confidence_threshold():
    client = TestClient(app)
    # Set to 0.48
    res = client.post("/api/trading/config", json={"confidence_threshold": 0.48})
    assert res.status_code == 200
    data = res.json()
    assert data["confidence_threshold"] == 0.48
    assert state["confidence_threshold"] == 0.48

    # Reset back to 0.40
    res = client.post("/api/trading/config", json={"confidence_threshold": 0.40})
    assert res.status_code == 200
    assert state["confidence_threshold"] == 0.40

@pytest.mark.anyio
async def test_process_closed_candle_sets_already_in_position_status():
    state["trading_active"] = True
    state["confidence_threshold"] = 0.40
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["candles"] = [
        {"time": 5000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0}
        for i in range(30)
    ]
    import pandas as pd
    from app.indicators import enrich
    state["df"] = enrich(pd.DataFrame(state["candles"]))

    # Portfolio already has BTC!
    portfolio.holdings["BTCUSDT"]["quantity"] = 0.05
    portfolio.cash = 7500.0

    # Laya says BUY with 45% (> 40%)
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "buy",
            "confidence": 0.45,
            "setup_quality": "good",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Test buy"
        }
        await process_closed_candle()

    rec = state["latest_decision"]
    assert rec["executed"] is False
    assert rec["execution_status"] == "already_in_position"
    assert "posicionado" in rec["filter_reason"].lower()

@pytest.mark.anyio
async def test_process_closed_candle_sets_no_position_to_sell_status():
    state["trading_active"] = True
    state["confidence_threshold"] = 0.40
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["candles"] = [
        {"time": 6000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0}
        for i in range(30)
    ]
    import pandas as pd
    from app.indicators import enrich
    state["df"] = enrich(pd.DataFrame(state["candles"]))

    # Portfolio has 0 BTC (100% in cash)
    portfolio.holdings["BTCUSDT"]["quantity"] = 0.0
    portfolio.cash = 10000.0

    # Laya says SELL with 45% (> 40%)
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "sell",
            "confidence": 0.45,
            "setup_quality": "good",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Test sell"
        }
        await process_closed_candle()

    rec = state["latest_decision"]
    assert rec["executed"] is False
    assert rec["execution_status"] == "no_position_to_sell"
    assert "cash" in rec["filter_reason"].lower()
