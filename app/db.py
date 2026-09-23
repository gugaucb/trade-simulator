import json
import sqlite3
import threading
from typing import Any

class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.init()

    def init(self):
        with self.lock, self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                candle_time INTEGER,
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                price REAL NOT NULL,
                action TEXT NOT NULL,
                confidence REAL,
                latency_ms REAL,
                indicators_json TEXT NOT NULL,
                reason TEXT,
                model TEXT
            );
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                cash_after REAL NOT NULL,
                position_after REAL NOT NULL,
                realized_pnl REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cached_klines (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                time INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (symbol, interval, time)
            );
            CREATE INDEX IF NOT EXISTS idx_cached_klines_time ON cached_klines(symbol, interval, time);
            CREATE TABLE IF NOT EXISTS laya_cache (
                state_hash TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                candle_time INTEGER,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                setup_quality TEXT,
                reason TEXT,
                model TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_laya_cache_sym ON laya_cache(symbol, candle_time);
            """)

    def add_decision(self, d: dict[str, Any]):
        with self.lock, self.conn:
            self.conn.execute(
                """INSERT INTO decisions
                (ts,candle_time,symbol,interval,price,action,confidence,latency_ms,indicators_json,reason,model)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (d["ts"], d.get("candle_time"), d["symbol"], d["interval"], d["price"], d["action"],
                 d.get("confidence"), d.get("latency_ms"),
                 json.dumps(d.get("indicators", {})), d.get("reason", ""), d.get("model", ""))
            )

    def add_trade(self, t: dict[str, Any]):
        with self.lock, self.conn:
            self.conn.execute(
                """INSERT INTO trades
                (ts,symbol,side,price,quantity,cash_after,position_after,realized_pnl)
                VALUES (?,?,?,?,?,?,?,?)""",
                (t["ts"], t["symbol"], t["side"], t["price"], t["quantity"],
                 t["cash_after"], t["position_after"], t["realized_pnl"])
            )

    def recent_decisions(self, symbol: str, limit: int = 30):
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM decisions WHERE symbol=? ORDER BY id DESC LIMIT ?",
                (symbol, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    def recent_trades(self, symbol: str, limit: int = 30):
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM trades WHERE symbol=? ORDER BY id DESC LIMIT ?",
                (symbol, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    def save_klines(self, symbol: str, interval: str, klines: list[dict[str, Any]]) -> int:
        symbol = symbol.upper()
        with self.lock, self.conn:
            self.conn.executemany(
                """INSERT OR REPLACE INTO cached_klines (symbol, interval, time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(symbol, interval, int(k["time"]), float(k["open"]), float(k["high"]),
                  float(k["low"]), float(k["close"]), float(k["volume"]))
                 for k in klines]
            )
        return len(klines)

    def get_klines(self, symbol: str, interval: str, limit: int | None = None,
                   start_time: int | None = None, end_time: int | None = None) -> list[dict[str, Any]]:
        symbol = symbol.upper()
        query = "SELECT time, open, high, low, close, volume FROM cached_klines WHERE symbol=? AND interval=?"
        params: list[Any] = [symbol, interval]
        if start_time is not None:
            query += " AND time >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND time <= ?"
            params.append(end_time)
        if limit is not None:
            query = f"SELECT * FROM ({query} ORDER BY time DESC LIMIT ?) ORDER BY time ASC"
            params.append(limit)
        else:
            query += " ORDER BY time ASC"
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        return [{"time": r["time"], "open": r["open"], "high": r["high"], "low": r["low"],
                 "close": r["close"], "volume": r["volume"], "closed": True} for r in rows]

    def count_klines(self, symbol: str, interval: str) -> int:
        with self.lock:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM cached_klines WHERE symbol=? AND interval=?",
                (symbol.upper(), interval)
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def get_laya_cache(self, state_hash: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT * FROM laya_cache WHERE state_hash=?",
                (state_hash,)
            ).fetchone()
        return dict(row) if row else None

    def save_laya_cache(self, state_hash: str, symbol: str, candle_time: int | None, decision: dict[str, Any]):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO laya_cache 
                (state_hash, symbol, candle_time, action, confidence, setup_quality, reason, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (state_hash, symbol.upper(), candle_time, decision["action"],
                 float(decision.get("confidence", 0.0)), decision.get("setup_quality"),
                 decision.get("reason", ""), decision.get("model", ""), now)
            )

    def clear_laya_cache(self, symbol: str | None = None):
        with self.lock, self.conn:
            if symbol:
                self.conn.execute("DELETE FROM laya_cache WHERE symbol=?", (symbol.upper(),))
            else:
                self.conn.execute("DELETE FROM laya_cache")

    def close(self):
        with self.lock:
            self.conn.close()
