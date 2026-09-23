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

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory="app/templates")
db = Database(settings.db_path)
market = BinanceMarket(settings.binance_rest_url, settings.binance_ws_url)
laya = LayaDecisionEngine(settings.laya_enabled, settings.laya_model)
portfolio = Portfolio(settings.initial_cash, settings.initial_cash)

state = {
    "symbol": settings.default_symbol, "interval": settings.default_interval,
    "candles": [], "df": None, "latest_decision": None, "ticker": None,
    "connected": False, "processing": False, "decision_count": 0
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
    state["candles"] = await market.klines(symbol, interval, 300)
    state["df"] = enrich(pd.DataFrame(state["candles"]))
    try: state["ticker"] = await market.ticker24h(symbol)
    except Exception: state["ticker"] = None

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

def laya_state(ctx):
    p = portfolio.snapshot()
    return {
        "asset": state["symbol"], "timeframe": state["interval"],
        "market_state": {
            "price": ctx["close"], "return_1_percent": ctx["return_1"], "return_5_percent": ctx["return_5"],
            "trend": ctx["trend"], "rsi_14": ctx["rsi"], "macd": ctx["macd"],
            "macd_signal": ctx["macd_signal"], "macd_histogram": ctx["macd_hist"],
            "ema_20": ctx["ema20"], "ema_50": ctx["ema50"], "bollinger_position": ctx["bb_position"],
            "atr": ctx["atr"], "atr_percent": ctx["atr_pct"], "volume_ratio": ctx["volume_ratio"]
        },
        "paper_position": {
            "cash": p["cash"], "quantity": p["quantity"], "average_entry": p["avg_entry"],
            "unrealized_pnl": p["unrealized_pnl"]
        },
        "decision_policy": "Paper trading only. Prefer HOLD when signals conflict."
    }

async def process_closed_candle():
    if state["processing"] or state["df"] is None or len(state["df"]) < 60: return
    state["processing"] = True
    try:
        state["df"] = enrich(pd.DataFrame(state["candles"]))
        ctx = latest_context(state["df"])
        if any(ctx[k] is None for k in ["rsi","macd","ema20","ema50"]): return
        state["decision_count"] += 1
        if state["decision_count"] % max(1, settings.decision_every_candles) != 0: return

        decision = await laya.decide(laya_state(ctx))
        action = decision["action"] if decision["action"] in {"buy","sell","hold"} else "hold"
        price = ctx["close"]
        portfolio.mark(price)
        trade = None

        if action == "buy" and decision["confidence"] >= 0.55 and portfolio.quantity <= 1e-12:
            qty = portfolio.buy(price, 0.25)
            if qty:
                trade = {"ts":datetime.now(timezone.utc).isoformat(),"symbol":state["symbol"],"side":"BUY",
                         "price":price,"quantity":qty,"cash_after":portfolio.cash,
                         "position_after":portfolio.quantity,"realized_pnl":0.0}
                db.add_trade(trade)

        elif action == "sell" and decision["confidence"] >= 0.55 and portfolio.quantity > 0:
            result = portfolio.sell(price, 1.0)
            if result:
                trade = {"ts":datetime.now(timezone.utc).isoformat(),"symbol":state["symbol"],"side":"SELL",
                         "price":price,"quantity":result["quantity"],"cash_after":portfolio.cash,
                         "position_after":portfolio.quantity,"realized_pnl":result["realized_pnl"]}
                db.add_trade(trade)

        record = {"ts":datetime.now(timezone.utc).isoformat(),"candle_time":state["candles"][-1]["time"],
                  "symbol":state["symbol"],"interval":state["interval"],"price":price,
                  "confidence":decision["confidence"],"latency_ms":decision["latency_ms"],
                  "indicators":ctx,"reason":decision["reason"],"model":decision["model"]}
        db.add_decision(record)
        state["latest_decision"] = record
        await broadcast({"type":"decision","decision":record,"trade":trade,"portfolio":portfolio.snapshot()})
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
        portfolio.mark(candle["close"])
        await broadcast({"type":"candle","candle":candle,"portfolio":portfolio.snapshot(),"connected":True})
        if closed: await process_closed_candle()
    await market.start(symbol, interval, on_kline)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request":request})

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
        "laya":{"enabled":settings.laya_enabled,"loaded":laya.agent is not None,
                "error":laya.load_error,"model":settings.laya_model}
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
    await broadcast({"type":"config","symbol":symbol,"interval":interval,"candles":state["candles"]})
    return {"ok":True,"symbol":symbol,"interval":interval}

@app.websocket("/ws/live")
async def live_socket(ws: WebSocket):
    await ws.accept()
    subscribers.add(ws)
    try:
        await ws.send_text(json.dumps({"type":"hello","connected":True,"symbol":state["symbol"],
                                       "interval":state["interval"],"portfolio":portfolio.snapshot()}))
        while True: await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        subscribers.discard(ws)
