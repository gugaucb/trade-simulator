import pytest
from app.portfolio import Portfolio
from fastapi.testclient import TestClient
from app.main import app, portfolio, state

def test_portfolio_multi_asset_holdings():
    p = Portfolio(initial_cash=10000.0, cash=10000.0)
    assert p.equity == 10000.0
    assert p.quantity == 0.0

    # Buy BTC
    p.set_active_symbol("BTCUSDT")
    qty_btc = p.buy(price=50000.0, fraction=0.5)  # spends 5000, gets 0.1 BTC
    assert qty_btc == 0.1
    assert p.cash == 5000.0
    assert p.quantity == 0.1
    assert p.holdings["BTCUSDT"]["quantity"] == 0.1

    # Switch to ETH and buy ETH
    p.set_active_symbol("ETHUSDT")
    assert p.quantity == 0.0  # ETH position is 0
    qty_eth = p.buy(price=2500.0, fraction=0.5)  # spends 2500, gets 1.0 ETH
    assert qty_eth == 1.0
    assert p.cash == 2500.0
    assert p.quantity == 1.0
    assert p.holdings["ETHUSDT"]["quantity"] == 1.0

    # Mark prices
    p.mark(price=55000.0, symbol="BTCUSDT")  # BTC up 10%
    p.mark(price=2600.0, symbol="ETHUSDT")   # ETH up 100

    # Total equity = cash (2500) + BTC (0.1 * 55000 = 5500) + ETH (1.0 * 2600 = 2600) = 10600
    assert p.equity == 10600.0
    assert p.pnl == 600.0
    assert p.pnl_pct == 6.0

def test_manual_paper_order_api():
    client = TestClient(app)
    state["symbol"] = "BTCUSDT"
    state["candles"] = [{"time": 1000, "open": 50000, "high": 50100, "low": 49900, "close": 50000, "volume": 10}]
    portfolio.cash = 10000.0
    portfolio.set_active_symbol("BTCUSDT")

    # Buy order
    res = client.post("/api/portfolio/order", json={"side": "BUY", "fraction": 0.25, "symbol": "BTCUSDT"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["trade"]["side"] == "BUY"
    assert data["trade"]["price"] == 50000
    assert data["portfolio"]["cash"] < 10000.0
    assert data["portfolio"]["quantity"] > 0

    # Sell order
    res_sell = client.post("/api/portfolio/order", json={"side": "SELL", "fraction": 1.0, "symbol": "BTCUSDT"})
    assert res_sell.status_code == 200
    data_sell = res_sell.json()
    assert data_sell["ok"] is True
    assert data_sell["trade"]["side"] == "SELL"
    assert data_sell["portfolio"]["quantity"] == 0.0
