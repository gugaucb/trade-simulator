import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.laya_engine import LayaDecisionEngine
from app.portfolio import Portfolio
from app.main import process_closed_candle, state, portfolio, db, laya

def test_laya_engine_extracts_class_probability_as_confidence():
    engine = LayaDecisionEngine(enabled=True)
    engine.agent = MagicMock()
    # Mock realistic laya output with broken raw confidence (0.007) but actual probability (0.48)
    engine.agent.predict.return_value = {
        "answers": {
            "action": {
                "type": "choice",
                "choice": "buy",
                "probabilities": {"buy": 0.482, "sell": 0.218, "hold": 0.300},
                "confidence": 0.0072
            },
            "setup_quality": {"score": 2.5}
        }
    }
    import asyncio
    decision = asyncio.run(engine.decide({"asset": "BTCUSDT"}))

    assert decision["action"] == "buy"
    # Confidence must be the choice probability (0.482), NOT the broken raw confidence (0.0072)
    assert decision["confidence"] == 0.482
    assert decision["probabilities"]["buy"] == 0.482

@pytest.mark.anyio
async def test_process_closed_candle_executes_when_confidence_reaches_aggressive_threshold():
    # Setup state
    state["trading_active"] = True
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["candles"] = [
        {"time": 1000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0}
        for i in range(30)
    ]
    import pandas as pd
    from app.indicators import enrich
    state["df"] = enrich(pd.DataFrame(state["candles"]))

    # Setup portfolio
    portfolio.cash = 10000.0
    portfolio.initial_cash = 10000.0
    portfolio.holdings["BTCUSDT"]["quantity"] = 0.0
    portfolio.holdings["BTCUSDT"]["avg_entry"] = 0.0
    portfolio.holdings["BTCUSDT"]["last_price"] = 50000.0

    # Mock laya.decide to return BUY with 45% confidence (>= 40% aggressive threshold)
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "buy",
            "confidence": 0.45,
            "setup_quality": "good",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Test strong buy"
        }
        await process_closed_candle()

    # Verify execution happened
    assert portfolio.holdings["BTCUSDT"]["quantity"] > 0
    assert portfolio.cash < 10000.0
    latest = state["latest_decision"]
    assert latest["executed"] is True
    assert latest["trade"] is not None
    assert latest["trade"]["side"] == "BUY"

@pytest.mark.anyio
async def test_process_closed_candle_filters_when_confidence_below_threshold():
    # Setup state
    state["trading_active"] = True
    state["processing"] = False
    state["last_processed_candle_time"] = None
    state["candles"] = [
        {"time": 2000 + i * 60, "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0, "volume": 10.0}
        for i in range(30)
    ]
    import pandas as pd
    from app.indicators import enrich
    state["df"] = enrich(pd.DataFrame(state["candles"]))

    portfolio.cash = 10000.0
    portfolio.holdings["BTCUSDT"]["quantity"] = 0.0

    # Mock laya.decide to return BUY with 25% confidence (< 40% threshold)
    with patch.object(laya, "decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = {
            "action": "buy",
            "confidence": 0.25,
            "setup_quality": "weak",
            "latency_ms": 10.0,
            "model": "typed-decisions",
            "reason": "Test weak buy"
        }
        await process_closed_candle()

    # Verify NO execution happened
    assert portfolio.holdings["BTCUSDT"]["quantity"] == 0.0
    assert portfolio.cash == 10000.0
    latest = state["latest_decision"]
    assert latest["executed"] is False
    assert latest["trade"] is None
