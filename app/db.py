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
