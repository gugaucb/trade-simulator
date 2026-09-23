import pytest
from app.portfolio import Portfolio
from app.main import app, state, portfolio, db
from fastapi.testclient import TestClient

def test_portfolio_liquidate_all():
    p = Portfolio(initial_cash=10000.0, cash=10000.0)
    # Buy BTC
    p.mark(50000.0, "BTCUSDT")
    qty_btc = p.buy(50000.0, fraction=0.25, symbol="BTCUSDT")
    assert qty_btc is not None
    assert p.holdings["BTCUSDT"]["quantity"] > 0
    assert p.cash < 10000.0

    # Buy ETH
    p.mark(3000.0, "ETHUSDT")
    qty_eth = p.buy(3000.0, fraction=0.25, symbol="ETHUSDT")
    assert qty_eth is not None
    assert p.holdings["ETHUSDT"]["quantity"] > 0

    # Price moves
    p.mark(55000.0, "BTCUSDT")
    p.mark(3200.0, "ETHUSDT")

    # Liquidate all
    trades = p.liquidate_all()
    assert len(trades) == 2
    symbols_liquidated = {t["symbol"] for t in trades}
    assert "BTCUSDT" in symbols_liquidated
    assert "ETHUSDT" in symbols_liquidated

    # Verify all positions are 0
    for sym, h in p.holdings.items():
        assert h["quantity"] == 0.0

    # Verify equity == cash
    assert p.position_equity == 0.0
    assert abs(p.equity - p.cash) < 1e-6
    assert p.cash > 10000.0  # Profitable liquidation

def test_stop_toggle_liquidates_open_positions():
    client = TestClient(app)
    # Reset portfolio
    portfolio.cash = 10000.0
    portfolio.initial_cash = 10000.0
    portfolio.realized_pnl = 0.0
    for s in portfolio.holdings:
        portfolio.holdings[s]["quantity"] = 0.0
        portfolio.holdings[s]["avg_entry"] = 0.0

    # Set active and buy something
    portfolio.mark(60000.0, "BTCUSDT")
    portfolio.buy(60000.0, fraction=0.25, symbol="BTCUSDT")
    assert portfolio.holdings["BTCUSDT"]["quantity"] > 0
    assert portfolio.cash < 10000.0

    state["trading_active"] = True

    # Now toggle stop (set active = False)
    res = client.post("/api/trading/toggle", json={"active": False})
    assert res.status_code == 200
    data = res.json()
    assert data["trading_active"] is False
    assert "liquidated_trades" in data

    # Verify holdings are liquidated
    assert portfolio.holdings["BTCUSDT"]["quantity"] == 0.0
    assert portfolio.position_equity == 0.0
    assert abs(portfolio.equity - portfolio.cash) < 1e-6

def test_buy_requires_positive_cash_balance():
    p = Portfolio(initial_cash=10000.0, cash=0.0)
    p.mark(50000.0, "BTCUSDT")
    qty = p.buy(50000.0, fraction=0.5, symbol="BTCUSDT")
    assert qty is None
    assert p.holdings["BTCUSDT"]["quantity"] == 0.0
    assert p.cash == 0.0
