import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_backtest_strategies():
    response = client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [s["id"] for s in data]
    assert "buy_and_hold" in ids
    assert "laya_pure" in ids
    assert "laya_confluence" in ids

def test_api_backtest_run_validation():
    # Invalid interval
    response = client.post("/api/backtest/run", json={"interval": "invalid_interval"})
    assert response.status_code == 400
    assert "Unsupported interval" in response.json()["error"]

def test_api_backtest_run_success():
    payload = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "candle_count": 50,
        "strategy_ids": ["buy_and_hold", "rsi_macd"],
        "initial_cash": 10000.0,
        "fee_rate": 0.001
    }
    response = client.post("/api/backtest/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "results" in data
    assert len(data["results"]) == 2
    assert "timestamps" in data
