import pytest
from fastapi.testclient import TestClient
from app.main import app, build_filtered_laya_state

client = TestClient(app)

def test_build_filtered_laya_state():
    ctx = {
        "close": 50000.0,
        "return_1": 0.1,
        "return_5": 0.5,
        "trend": "bullish",
        "rsi": 62.0,
        "macd": 10.5,
        "macd_signal": 8.2,
        "macd_hist": 2.3,
        "ema20": 49800.0,
        "ema50": 49000.0,
        "bb_position": 0.75,
        "atr": 450.0,
        "atr_pct": 0.9,
        "volume_ratio": 1.25
    }
    p_snap = {"cash": 10000.0, "quantity": 0.0, "avg_entry": 0.0, "unrealized_pnl": 0.0}
    
    # 1. All indicators enabled
    all_inds = ["rsi", "macd", "ema", "bb", "atr", "volume"]
    state_all = build_filtered_laya_state(ctx, "BTCUSDT", "1m", p_snap, all_inds)
    ms_all = state_all["market_state"]
    assert "rsi_14" in ms_all
    assert "macd" in ms_all
    assert "ema_20" in ms_all
    assert "bollinger_position" in ms_all
    assert "atr" in ms_all
    assert "volume_ratio" in ms_all
    
    # 2. Only RSI and MACD enabled
    custom_inds = ["rsi", "macd"]
    state_custom = build_filtered_laya_state(ctx, "BTCUSDT", "1m", p_snap, custom_inds)
    ms_custom = state_custom["market_state"]
    assert "rsi_14" in ms_custom
    assert "macd" in ms_custom
    assert "ema_20" not in ms_custom
    assert "bollinger_position" not in ms_custom
    assert "atr" not in ms_custom
    assert "volume_ratio" not in ms_custom

def test_trading_status_endpoint():
    res = client.get("/api/trading/status")
    assert res.status_code == 200
    data = res.json()
    assert "trading_active" in data
    assert "symbol" in data
    assert "interval" in data
    assert "active_indicators" in data

def test_trading_toggle_endpoint():
    # Fetch initial status
    res1 = client.get("/api/trading/status")
    initial_active = res1.json()["trading_active"]
    
    # Toggle it
    res2 = client.post("/api/trading/toggle", json={})
    assert res2.status_code == 200
    assert res2.json()["trading_active"] == (not initial_active)
    
    # Explicitly set to false
    res3 = client.post("/api/trading/toggle", json={"active": False})
    assert res3.status_code == 200
    assert res3.json()["trading_active"] is False

def test_trading_config_endpoint():
    payload = {
        "symbol": "ETHUSDT",
        "interval": "1m",
        "active_indicators": ["rsi", "ema"]
    }
    res = client.post("/api/trading/config", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "ETHUSDT"
    assert data["interval"] == "1m"
    assert set(data["active_indicators"]) == {"rsi", "ema"}
