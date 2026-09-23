import asyncio
import json
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .config import settings
from .db import Database
from .indicators import enrich, latest_context
from .laya_engine import LayaDecisionEngine
from .market import BinanceMarket
from .portfolio import Portfolio
from .backtest import BacktestEngine, BacktestConfig
from .strategies import get_strategy, list_available_strategies

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory="app/templates")
db = Database(settings.db_path)
market = BinanceMarket(settings.binance_rest_url, settings.binance_ws_url)
laya = LayaDecisionEngine(settings.laya_enabled, settings.laya_model)
portfolio = Portfolio(settings.initial_cash, settings.initial_cash)

state = {
    "symbol": settings.default_symbol, "interval": settings.default_interval,
    "candles": [], "df": None, "latest_decision": None, "ticker": None,
    "connected": False, "processing": False, "decision_count": 0,
    "trading_active": False,
    "active_indicators": ["rsi", "macd", "ema", "bb", "atr", "volume"],
    "last_processed_candle_time": None
}
subscribers = set()
stream_task = None

@app.on_event("startup")
async def startup():
    global stream_task
    await load_market(state["symbol"], state["interval"])
    if settings.laya_enabled:
        await asyncio.to_thread(laya.load)
    stream_task = asyncio.create_task(stream_loop(state["symbol"], state["interval"]))

@app.on_event("shutdown")
async def shutdown():
    if stream_task:
        stream_task.cancel()
        try: await stream_task
        except asyncio.CancelledError: pass

async def load_market(symbol, interval):
    state["symbol"], state["interval"] = symbol.upper(), interval
    portfolio.set_active_symbol(symbol.upper())
    state["candles"] = await market.klines(symbol, interval, 300)
    state["df"] = enrich(pd.DataFrame(state["candles"]))
    try: state["ticker"] = await market.ticker24h(symbol)
    except Exception: state["ticker"] = None
    if state["candles"]:
        portfolio.mark(state["candles"][-1]["close"], symbol.upper())

async def broadcast(payload):
    raw = json.dumps(payload, default=str)
    dead = []
    for ws in subscribers:
        try: await ws.send_text(raw)
        except Exception: dead.append(ws)
    for ws in dead: subscribers.discard(ws)

def append_candle(candle):
    if not state["candles"] or candle["time"] > state["candles"][-1]["time"]:
        state["candles"].append(candle)
    else:
        state["candles"][-1] = candle
    state["candles"] = state["candles"][-300:]

def build_filtered_laya_state(ctx: dict, symbol: str, interval: str, portfolio_snapshot: dict, active_indicators: list[str]) -> dict:
    active_set = set(active_indicators or [])
    price = float(ctx.get("close", 0.0))
    ms = {
        "price": price,
        "return_1_percent": ctx.get("return_1"),
        "return_5_percent": ctx.get("return_5"),
        "trend": ctx.get("trend")
    }
    if "rsi" in active_set and ctx.get("rsi") is not None:
        ms["rsi_14"] = ctx["rsi"]
    if "macd" in active_set:
        if ctx.get("macd") is not None: ms["macd"] = ctx["macd"]
        if ctx.get("macd_signal") is not None: ms["macd_signal"] = ctx["macd_signal"]
        if ctx.get("macd_hist") is not None: ms["macd_histogram"] = ctx["macd_hist"]
    if "ema" in active_set:
        if ctx.get("ema20") is not None: ms["ema_20"] = ctx["ema20"]
        if ctx.get("ema50") is not None: ms["ema_50"] = ctx["ema50"]
    if "bb" in active_set and ctx.get("bb_position") is not None:
        ms["bollinger_position"] = ctx["bb_position"]
    if "atr" in active_set:
        if ctx.get("atr") is not None: ms["atr"] = ctx["atr"]
        if ctx.get("atr_pct") is not None: ms["atr_percent"] = ctx["atr_pct"]
    if "volume" in active_set and ctx.get("volume_ratio") is not None:
        ms["volume_ratio"] = ctx["volume_ratio"]

    qty = float(portfolio_snapshot.get("quantity", 0.0))
    pos_usd = float(portfolio_snapshot.get("position_usd", round(qty * price, 2)))
    cash = float(portfolio_snapshot.get("cash", 0.0))
    equity = float(portfolio_snapshot.get("equity", round(cash + pos_usd, 2)))

    return {
        "asset": symbol,
        "current_price": price,
        "timeframe": interval,
        "active_indicators": sorted(list(active_set)),
        "market_state": ms,
        "paper_position": {
            "cash": cash,
            "quantity": qty,
            "position_usd": pos_usd,
            "average_entry": float(portfolio_snapshot.get("avg_entry", 0.0)),
            "unrealized_pnl": float(portfolio_snapshot.get("unrealized_pnl", 0.0)),
            "equity": equity
        },
        "decision_policy": (
            "Spot trading only (no shorting). Choose between 'buy', 'sell', or 'hold'. "
            "Only BUY if available cash > 0 and bullish momentum is confirmed. "
            "Only SELL if currently holding a position (quantity > 0) to lock profit or stop loss. "
            "Otherwise, maintain HOLD."
        )
    }

def laya_state(ctx):
    return build_filtered_laya_state(ctx, state["symbol"], state["interval"], portfolio.snapshot(), state["active_indicators"])

async def process_closed_candle():
    if state["processing"] or state["df"] is None or len(state["candles"]) < 20: return
    current_candle_time = state["candles"][-1]["time"]
    if state.get("last_processed_candle_time") == current_candle_time:
        return
    state["processing"] = True
    try:
        state["df"] = enrich(pd.DataFrame(state["candles"]))
        ctx = latest_context(state["df"])
        if ctx.get("close") is None: return
        state["last_processed_candle_time"] = current_candle_time
        state["decision_count"] += 1
        if state["decision_count"] % max(1, settings.decision_every_candles) != 0: return

        decision = await laya.decide(laya_state(ctx))
        action = decision["action"] if decision["action"] in {"buy","sell","hold"} else "hold"
        price = ctx["close"]
        portfolio.mark(price)
        trade = None

        conf_threshold = 0.40  # Aggressive mode (exceeds random 33.3% prior)
        if state["trading_active"]:
            if action == "buy" and decision["confidence"] >= conf_threshold and portfolio.quantity <= 1e-12:
                if portfolio.cash > 1.0:
                    qty = portfolio.buy(price, 0.25)
                    if qty:
                        trade = {"ts":datetime.now(timezone.utc).isoformat(),"symbol":state["symbol"],"side":"BUY",
                                 "price":price,"quantity":qty,"cash_after":portfolio.cash,
                                 "position_after":portfolio.quantity,"realized_pnl":0.0}
                        db.add_trade(trade)

            elif action == "sell" and decision["confidence"] >= conf_threshold and portfolio.quantity > 0:
                result = portfolio.sell(price, 1.0)
                if result:
                    trade = {"ts":datetime.now(timezone.utc).isoformat(),"symbol":state["symbol"],"side":"SELL",
                             "price":price,"quantity":result["quantity"],"cash_after":portfolio.cash,
                             "position_after":portfolio.quantity,"realized_pnl":result["realized_pnl"]}
                    db.add_trade(trade)
        else:
            decision["reason"] = f"{decision.get('reason', '')} [Trading Pausado - Modo Observação]"

        record = {"ts":datetime.now(timezone.utc).isoformat(),"candle_time":current_candle_time,
                  "symbol":state["symbol"],"interval":state["interval"],"price":price,
                  "action":action,"confidence":decision["confidence"],"latency_ms":decision["latency_ms"],
                  "indicators":ctx,"reason":decision["reason"],"model":decision["model"],
                  "is_live_trading": bool(state["trading_active"]),
                  "executed": bool(trade is not None),
                  "trade": trade}
        db.add_decision(record)
        state["latest_decision"] = record
        await broadcast({
            "type":"decision",
            "decision":record,
            "trade":trade,
            "portfolio":portfolio.snapshot(),
            "trading_active":state["trading_active"]
        })
    finally:
        state["processing"] = False

async def stream_loop(symbol, interval):
    async def on_kline(candle):
        if "error" in candle:
            state["connected"] = False
            await broadcast({"type":"status","connected":False,"message":candle["error"]})
            return
        state["connected"] = True
        closed = candle["closed"]
        append_candle(candle)
        portfolio.mark(candle["close"], symbol.upper())
        await broadcast({"type":"candle","candle":candle,"portfolio":portfolio.snapshot(),"connected":True,"trading_active":state["trading_active"]})
        if closed: await process_closed_candle()
    await market.start(symbol, interval, on_kline)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/bootstrap")
async def bootstrap():
    ticker = state["ticker"]
    if ticker is None:
        try: ticker = await market.ticker24h(state["symbol"])
        except Exception: ticker = {}
    return JSONResponse({
        "symbol":state["symbol"],"interval":state["interval"],"candles":state["candles"],"ticker":ticker,
        "portfolio":portfolio.snapshot(),"latest_decision":state["latest_decision"],
        "decisions":db.recent_decisions(state["symbol"]),"trades":db.recent_trades(state["symbol"]),
        "trading_active": state["trading_active"], "active_indicators": state["active_indicators"],
        "laya":{"enabled":settings.laya_enabled,"loaded":laya.agent is not None,
                "error":laya.load_error,"model":settings.laya_model}
    })

@app.get("/api/trading/status")
async def trading_status():
    return JSONResponse({
        "trading_active": state["trading_active"],
        "symbol": state["symbol"],
        "interval": state["interval"],
        "active_indicators": state["active_indicators"]
    })

@app.post("/api/trading/toggle")
async def trading_toggle(payload: dict | None = None):
    if payload and "active" in payload:
        state["trading_active"] = bool(payload["active"])
    else:
        state["trading_active"] = not state["trading_active"]

    liquidated_trades = []
    if not state["trading_active"]:
        liquidated_trades = portfolio.liquidate_all()
        for t in liquidated_trades:
            trade_record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": t["symbol"],
                "side": t["side"],
                "price": t["price"],
                "quantity": t["quantity"],
                "cash_after": portfolio.cash,
                "position_after": 0.0,
                "realized_pnl": t["realized_pnl"]
            }
            db.add_trade(trade_record)
            await broadcast({
                "type": "trade",
                "trade": trade_record,
                "portfolio": portfolio.snapshot()
            })

    snap = portfolio.snapshot()
    await broadcast({
        "type": "trading_status",
        "trading_active": state["trading_active"],
        "symbol": state["symbol"],
        "interval": state["interval"],
        "active_indicators": state["active_indicators"],
        "portfolio": snap
    })
    return JSONResponse({
        "ok": True,
        "trading_active": state["trading_active"],
        "portfolio": snap,
        "liquidated_trades": liquidated_trades
    })

@app.post("/api/trading/config")
async def trading_config(payload: dict):
    global stream_task
    symbol = str(payload.get("symbol", state["symbol"])).upper()
    interval = str(payload.get("interval", state["interval"]))
    active_indicators = payload.get("active_indicators", state["active_indicators"])

    allowed = {"1m","3m","5m","15m","30m","1h","4h","1d"}
    if interval not in allowed:
        return JSONResponse({"error": f"Unsupported interval: {interval}"}, status_code=400)

    state["active_indicators"] = list(active_indicators)
    market_changed = (symbol != state["symbol"] or interval != state["interval"])
    if market_changed:
        if stream_task:
            stream_task.cancel()
            try: await stream_task
            except asyncio.CancelledError: pass
        await load_market(symbol, interval)
        stream_task = asyncio.create_task(stream_loop(symbol, interval))

    await broadcast({
        "type": "trading_config",
        "trading_active": state["trading_active"],
        "symbol": state["symbol"],
        "interval": state["interval"],
        "active_indicators": state["active_indicators"],
        "candles": state["candles"] if market_changed else None
    })

    return JSONResponse({
        "ok": True,
        "trading_active": state["trading_active"],
        "symbol": state["symbol"],
        "interval": state["interval"],
        "active_indicators": state["active_indicators"]
    })

@app.post("/api/config")
async def configure(payload: dict):
    global stream_task
    symbol = str(payload.get("symbol", state["symbol"])).upper()
    interval = str(payload.get("interval", state["interval"]))
    allowed = {"1m","3m","5m","15m","30m","1h","4h","1d"}
    if interval not in allowed:
        return JSONResponse({"error":"Unsupported interval"}, status_code=400)
    if stream_task:
        stream_task.cancel()
        try: await stream_task
        except asyncio.CancelledError: pass
    await load_market(symbol, interval)
    stream_task = asyncio.create_task(stream_loop(symbol, interval))
    await broadcast({"type":"config","symbol":symbol,"interval":interval,"candles":state["candles"],"portfolio":portfolio.snapshot(),"trading_active":state["trading_active"]})
    return {"ok":True,"symbol":symbol,"interval":interval,"portfolio":portfolio.snapshot(),"trading_active":state["trading_active"]}

@app.post("/api/portfolio/order")
async def manual_paper_order(payload: dict):
    side = str(payload.get("side", "BUY")).upper()
    fraction = float(payload.get("fraction", 0.25 if side == "BUY" else 1.0))
    symbol = str(payload.get("symbol", state["symbol"])).upper()

    portfolio.set_active_symbol(symbol)
    price = 0.0
    if state["candles"]:
        price = float(state["candles"][-1]["close"])
    elif state["ticker"] and "lastPrice" in state["ticker"]:
        price = float(state["ticker"]["lastPrice"])

    if price <= 0:
        return JSONResponse({"error": "Price unavailable for order execution"}, status_code=400)

    trade = None
    if side == "BUY":
        qty = portfolio.buy(price, fraction=fraction, symbol=symbol)
        if not qty:
            return JSONResponse({"error": "Insufficient cash for BUY"}, status_code=400)
        trade = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "side": "BUY",
            "price": price,
            "quantity": qty,
            "cash_after": portfolio.cash,
            "position_after": portfolio.current_position["quantity"],
            "realized_pnl": 0.0
        }
        db.add_trade(trade)
    elif side == "SELL":
        res = portfolio.sell(price, fraction=fraction, symbol=symbol)
        if not res:
            return JSONResponse({"error": f"No {symbol} position to SELL"}, status_code=400)
        trade = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "side": "SELL",
            "price": price,
            "quantity": res["quantity"],
            "cash_after": portfolio.cash,
            "position_after": portfolio.current_position["quantity"],
            "realized_pnl": res["realized_pnl"]
        }
        db.add_trade(trade)
    else:
        return JSONResponse({"error": f"Invalid side: {side}"}, status_code=400)

    snap = portfolio.snapshot()
    await broadcast({
        "type": "portfolio",
        "portfolio": snap,
        "trade": trade
    })
    return JSONResponse({"ok": True, "trade": trade, "portfolio": snap})

@app.websocket("/ws/live")
async def live_socket(ws: WebSocket):
    await ws.accept()
    subscribers.add(ws)
    try:
        await ws.send_text(json.dumps({"type":"hello","connected":True,"symbol":state["symbol"],
                                       "interval":state["interval"],"portfolio":portfolio.snapshot(),
                                       "trading_active":state["trading_active"]}))
        while True: await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        subscribers.discard(ws)

@app.get("/api/backtest/strategies")
async def backtest_strategies():
    return JSONResponse(list_available_strategies())

@app.post("/api/backtest/run")
async def backtest_run(payload: dict):
    symbol = str(payload.get("symbol", "BTCUSDT")).upper()
    interval = str(payload.get("interval", "1h"))
    allowed_intervals = {"1m","3m","5m","15m","30m","1h","4h","1d"}
    if interval not in allowed_intervals:
        return JSONResponse({"error": f"Unsupported interval: {interval}"}, status_code=400)

    candle_count = int(payload.get("candle_count", 300))
    strategy_ids = payload.get("strategy_ids", ["buy_and_hold", "rsi_macd", "ema_cross", "laya_pure", "laya_confluence"])
    if not strategy_ids:
        strategy_ids = ["buy_and_hold"]

    initial_cash = float(payload.get("initial_cash", 10000.0))
    fee_rate = float(payload.get("fee_rate", 0.001))
    slippage_rate = float(payload.get("slippage_rate", 0.0005))
    position_size_pct = float(payload.get("position_size_pct", 1.0))
    stop_loss_pct = payload.get("stop_loss_pct")
    if stop_loss_pct is not None and str(stop_loss_pct).strip():
        stop_loss_pct = float(stop_loss_pct)
    else:
        stop_loss_pct = None

    take_profit_pct = payload.get("take_profit_pct")
    if take_profit_pct is not None and str(take_profit_pct).strip():
        take_profit_pct = float(take_profit_pct)
    else:
        take_profit_pct = None

    use_laya_cache = bool(payload.get("use_laya_cache", True))
    force_fresh = bool(payload.get("force_fresh_data", False))

    # 1. Fetch & cache historical candles
    candles = await market.fetch_and_cache_klines(db, symbol, interval, candle_count, force_refresh=force_fresh)
    if not candles or len(candles) < 10:
        return JSONResponse({"error": "Insufficient candle data returned for backtest"}, status_code=400)

    # 2. Enrich data
    df = enrich(pd.DataFrame(candles))

    # 3. Instantiate strategies
    strategies = []
    needs_laya = False
    for sid in strategy_ids:
        try:
            s = get_strategy(sid)
            strategies.append(s)
            if s.requires_laya:
                needs_laya = True
        except Exception:
            pass

    if not strategies:
        strategies = [get_strategy("buy_and_hold")]

    # 4. Pre-compute/retrieve decisions if needed
    laya_decisions = {}
    if needs_laya:
        total_candles = len(candles)
        for i, c in enumerate(candles):
            sub_df = df.iloc[:i+1]
            ctx = latest_context(sub_df)
            ts = int(c["time"])
            state_payload = build_filtered_laya_state(
                ctx=ctx,
                symbol=symbol,
                interval=interval,
                portfolio_snapshot={"cash": initial_cash, "quantity": 0.0, "avg_entry": 0.0, "unrealized_pnl": 0.0, "position_usd": 0.0, "equity": initial_cash},
                active_indicators=["rsi", "macd", "ema", "bb", "atr", "volume"]
            )
            state_payload["candle_time"] = ts
            dec = await laya.decide_cached(state_payload, db, force_refresh=not use_laya_cache)
            laya_decisions[ts] = dec

            if i % 15 == 0 or i == total_candles - 1:
                await broadcast({
                    "type": "backtest_progress",
                    "current": i + 1,
                    "total": total_candles,
                    "symbol": symbol,
                    "cached": dec.get("cached", False),
                    "pct": round(((i + 1) / total_candles) * 100, 1)
                })

    # 5. Run simulation
    config = BacktestConfig(
        initial_cash=initial_cash,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        position_size_pct=position_size_pct,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct
    )
    engine = BacktestEngine(config)
    comparison = engine.run_comparison(strategies, candles, laya_decisions)
    comparison["symbol"] = symbol
    comparison["interval"] = interval
    comparison["candle_count"] = len(candles)
    comparison["config"] = {
        "initial_cash": initial_cash,
        "fee_rate": fee_rate,
        "slippage_rate": slippage_rate,
        "position_size_pct": position_size_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct
    }

    return JSONResponse(comparison)

@app.post("/api/backtest/clear-cache")
async def backtest_clear_cache(payload: dict | None = None):
    symbol = payload.get("symbol") if payload else None
    db.clear_laya_cache(symbol)
    return {"ok": True, "message": "Laya cache cleared"}
