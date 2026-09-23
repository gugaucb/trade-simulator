import pytest
from app.strategies import (
    get_strategy,
    list_available_strategies,
    BuyAndHoldStrategy,
    RsiMacdStrategy,
    EmaCrossStrategy,
    LayaPureStrategy,
    LayaConfluenceStrategy
)

def test_list_available_strategies():
    strategies = list_available_strategies()
    ids = [s["id"] for s in strategies]
    assert "buy_and_hold" in ids
    assert "rsi_macd" in ids
    assert "ema_cross" in ids
    assert "laya_pure" in ids
    assert "laya_confluence" in ids

def test_buy_and_hold_strategy():
    strat = BuyAndHoldStrategy()
    candle = {"time": 1000, "close": 50000.0}
    ctx = {"trend": "neutral", "rsi": 50.0}
    
    # When no position, should signal BUY
    assert strat.on_candle(candle, ctx, None, position_qty=0.0) == "BUY"
    
    # When already holding position, should HOLD
    assert strat.on_candle(candle, ctx, None, position_qty=0.5) == "HOLD"

def test_rsi_macd_strategy():
    strat = RsiMacdStrategy(rsi_oversold=35, rsi_overbought=65)
    candle = {"time": 1000, "close": 50000.0}
    
    # Oversold with positive momentum -> BUY
    ctx_buy = {"rsi": 30.0, "macd_hist": 5.0, "trend": "bullish"}
    assert strat.on_candle(candle, ctx_buy, None, position_qty=0.0) == "BUY"
    
    # Overbought -> SELL
    ctx_sell = {"rsi": 70.0, "macd_hist": -2.0, "trend": "bearish"}
    assert strat.on_candle(candle, ctx_sell, None, position_qty=0.5) == "SELL"

def test_ema_cross_strategy():
    strat = EmaCrossStrategy()
    candle = {"time": 1000, "close": 50000.0}
    
    # EMA20 > EMA50 -> Golden cross / Bullish -> BUY
    ctx_bull = {"ema20": 51000.0, "ema50": 50000.0}
    assert strat.on_candle(candle, ctx_bull, None, position_qty=0.0) == "BUY"
    
    # EMA20 < EMA50 -> Death cross / Bearish -> SELL
    ctx_bear = {"ema20": 49000.0, "ema50": 50000.0}
    assert strat.on_candle(candle, ctx_bear, None, position_qty=0.5) == "SELL"

def test_laya_pure_strategy():
    strat = LayaPureStrategy(confidence_threshold=0.55)
    candle = {"time": 1000, "close": 50000.0}
    ctx = {}
    
    # Laya says BUY with 65% confidence -> BUY
    laya_buy = {"action": "buy", "confidence": 0.65}
    assert strat.on_candle(candle, ctx, laya_buy, position_qty=0.0) == "BUY"
    
    # Laya says BUY but confidence is too low -> HOLD
    laya_low = {"action": "buy", "confidence": 0.45}
    assert strat.on_candle(candle, ctx, laya_low, position_qty=0.0) == "HOLD"
    
    # Laya says SELL with 60% confidence -> SELL
    laya_sell = {"action": "sell", "confidence": 0.60}
    assert strat.on_candle(candle, ctx, laya_sell, position_qty=0.5) == "SELL"

def test_laya_confluence_strategy():
    strat = LayaConfluenceStrategy(confidence_threshold=0.55)
    candle = {"time": 1000, "close": 50000.0}
    
    # Laya BUY and Trend is Bullish -> BUY
    laya_buy = {"action": "buy", "confidence": 0.70}
    ctx_bull = {"trend": "bullish", "rsi": 55.0, "ema20": 51000, "ema50": 50000}
    assert strat.on_candle(candle, ctx_bull, laya_buy, position_qty=0.0) == "BUY"
    
    # Laya BUY but Trend is Bearish -> HOLD (confluence filters out the bad signal!)
    ctx_bear = {"trend": "bearish", "rsi": 40.0, "ema20": 49000, "ema50": 50000}
    assert strat.on_candle(candle, ctx_bear, laya_buy, position_qty=0.0) == "HOLD"
