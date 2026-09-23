import tempfile
import os
import pytest
from app.db import Database
from app.market import BinanceMarket

@pytest.mark.anyio
async def test_fetch_and_cache_klines_from_binance():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite3")
        db = Database(db_path)
        try:
            market = BinanceMarket("https://data-api.binance.vision", "wss://data-stream.binance.vision:443/ws")
            # Fetch 50 candles of BTCUSDT 1h
            candles = await market.fetch_and_cache_klines(db, "BTCUSDT", "1h", count=50)
            assert len(candles) >= 50
            assert db.count_klines("BTCUSDT", "1h") >= 50
            
            # Second call should use cache if available or update
            cached = db.get_klines("BTCUSDT", "1h", limit=50)
            assert len(cached) == 50
            assert cached[0]["close"] > 0
        finally:
            db.close()
