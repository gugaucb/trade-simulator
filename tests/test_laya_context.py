import pytest
from app.main import build_filtered_laya_state

def test_build_filtered_laya_state_includes_price_and_active_indicators():
    ctx = {
        "close": 65432.10,
        "return_1": 0.25,
        "return_5": 1.15,
        "trend": "bullish",
        "rsi": 58.2,
        "macd": 12.3,
        "macd_signal": 10.1,
        "macd_hist": 2.2,
        "ema20": 65000.0,
        "ema50": 64500.0,
        "bb_position": 0.75,
        "atr": 450.0,
        "atr_pct": 0.69,
        "volume_ratio": 1.4
    }
    portfolio_snap = {
        "cash": 7500.0,
        "quantity": 0.0382,
        "position_usd": 2500.0,
        "avg_entry": 65000.0,
        "unrealized_pnl": 16.5,
        "equity": 10000.0
    }
    
    # Filter with only RSI and Volume
    state = build_filtered_laya_state(
        ctx=ctx,
        symbol="BTCUSDT",
        interval="1m",
        portfolio_snapshot=portfolio_snap,
        active_indicators=["rsi", "volume"]
    )

    # 1. Price at root level and in market_state
    assert state["current_price"] == 65432.10
    assert state["market_state"]["price"] == 65432.10

    # 2. Active indicators declared
    assert state["active_indicators"] == ["rsi", "volume"]

    # 3. Only selected indicators are in market_state
    assert "rsi_14" in state["market_state"]
    assert "volume_ratio" in state["market_state"]
    assert "macd" not in state["market_state"]
    assert "ema_20" not in state["market_state"]
    assert "bollinger_position" not in state["market_state"]
    assert "atr" not in state["market_state"]

    # 4. paper_position has full valuation
    pos = state["paper_position"]
    assert pos["cash"] == 7500.0
    assert pos["quantity"] == 0.0382
    assert pos["position_usd"] == 2500.0
    assert pos["equity"] == 10000.0

    # 5. Clear decision policy
    assert "Spot trading only" in state["decision_policy"]
    assert "buy" in state["decision_policy"]
    assert "sell" in state["decision_policy"]
    assert "hold" in state["decision_policy"]

def test_build_filtered_laya_state_all_indicators():
    ctx = {
        "close": 3500.0,
        "return_1": -0.1,
        "return_5": -0.4,
        "trend": "bearish",
        "rsi": 42.0,
        "macd": -5.0,
        "macd_signal": -3.0,
        "macd_hist": -2.0,
        "ema20": 3510.0,
        "ema50": 3550.0,
        "bb_position": 0.25,
        "atr": 25.0,
        "atr_pct": 0.71,
        "volume_ratio": 0.95
    }
    portfolio_snap = {
        "cash": 10000.0,
        "quantity": 0.0,
        "avg_entry": 0.0,
        "unrealized_pnl": 0.0,
        "position_usd": 0.0,
        "equity": 10000.0
    }
    all_indicators = ["rsi", "macd", "ema", "bb", "atr", "volume"]
    state = build_filtered_laya_state(ctx, "ETHUSDT", "5m", portfolio_snap, all_indicators)

    assert state["current_price"] == 3500.0
    assert "rsi_14" in state["market_state"]
    assert "macd" in state["market_state"]
    assert "ema_20" in state["market_state"]
    assert "bollinger_position" in state["market_state"]
    assert "atr" in state["market_state"]
    assert "volume_ratio" in state["market_state"]
