import pytest
import pandas as pd
import numpy as np
from app.backtest import BacktestEngine, BacktestConfig, calculate_metrics
from app.strategies import BuyAndHoldStrategy, RsiMacdStrategy

def create_synthetic_candles(num_candles=100, trend=0.002):
    candles = []
    price = 100.0
    for i in range(num_candles):
        # Deterministic price oscillation with slight upward trend
        ret = trend + 0.01 * np.sin(i / 5.0)
        open_p = price
        close_p = price * (1.0 + ret)
        high_p = max(open_p, close_p) * 1.002
        low_p = min(open_p, close_p) * 0.998
        candles.append({
            "time": 1700000000 + i * 3600,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": 1000.0 + (i % 10) * 100,
            "closed": True
        })
        price = close_p
    return candles

def test_calculate_metrics():
    # Equity curve starting at 10000 and ending at 12000
    equity = [10000.0, 10500.0, 10200.0, 11000.0, 10800.0, 12000.0]
    trades = [
        {"side": "BUY", "price": 100, "quantity": 10, "pnl": 500.0, "return_pct": 5.0},
        {"side": "SELL", "price": 105, "quantity": 10, "pnl": -200.0, "return_pct": -1.9},
        {"side": "BUY", "price": 108, "quantity": 10, "pnl": 1200.0, "return_pct": 11.1},
    ]
    metrics = calculate_metrics(equity, trades, initial_cash=10000.0, candle_interval_seconds=3600)
    
    assert metrics["total_return_pct"] == 20.0
    assert metrics["max_drawdown_pct"] > 0.0
    assert len(metrics["drawdowns"]) == len(equity)
    assert metrics["total_trades"] == 3
    assert metrics["win_rate_pct"] == pytest.approx(66.67, rel=1e-2)
    assert metrics["profit_factor"] == pytest.approx(1700.0 / 200.0, rel=1e-2)
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics

def test_backtest_engine_buy_and_hold():
    candles = create_synthetic_candles(num_candles=60, trend=0.005)
    config = BacktestConfig(initial_cash=10000.0, fee_rate=0.001, slippage_rate=0.0)
    engine = BacktestEngine(config)
    
    strategy = BuyAndHoldStrategy()
    result = engine.run_single(strategy, candles)
    
    assert result["strategy_id"] == "buy_and_hold"
    assert len(result["equity_curve"]) == len(candles)
    # In buy & hold, first candle buys, final equity should reflect asset growth minus fee
    assert len(result["trades"]) >= 1
    assert result["metrics"]["total_return_pct"] > 0
    assert result["metrics"]["max_drawdown_pct"] >= 0

def test_backtest_comparator():
    candles = create_synthetic_candles(num_candles=80)
    config = BacktestConfig(initial_cash=10000.0, fee_rate=0.001)
    engine = BacktestEngine(config)
    
    strategies = [BuyAndHoldStrategy(), RsiMacdStrategy()]
    comparison = engine.run_comparison(strategies, candles)
    
    assert "summary" in comparison
    assert len(comparison["results"]) == 2
    assert comparison["results"][0]["strategy_id"] == "buy_and_hold"
    assert comparison["results"][1]["strategy_id"] == "rsi_macd"
