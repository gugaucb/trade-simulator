import tempfile
import os
import pytest
from app.db import Database

def test_cache_and_retrieve_klines():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite3")
        db = Database(db_path)
        try:
            sample_klines = [
                {"time": 1000, "open": 50000.0, "high": 50500.0, "low": 49800.0, "close": 50200.0, "volume": 12.5, "closed": True},
                {"time": 1060, "open": 50200.0, "high": 50600.0, "low": 50100.0, "close": 50450.0, "volume": 15.0, "closed": True},
                {"time": 1120, "open": 50450.0, "high": 50800.0, "low": 50300.0, "close": 50700.0, "volume": 18.2, "closed": True},
            ]
            
            # Save to database
            saved = db.save_klines("BTCUSDT", "1m", sample_klines)
            assert saved == 3
            
            # Retrieve from database
            retrieved = db.get_klines("BTCUSDT", "1m")
            assert len(retrieved) == 3
            assert retrieved[0]["time"] == 1000
            assert retrieved[0]["close"] == 50200.0
            assert retrieved[-1]["close"] == 50700.0
            
            # Re-saving same candles should not duplicate (idempotent / upsert)
            saved_again = db.save_klines("BTCUSDT", "1m", sample_klines)
            assert db.count_klines("BTCUSDT", "1m") == 3
            
            # Limit query (should return the latest 2)
            limited = db.get_klines("BTCUSDT", "1m", limit=2)
            assert len(limited) == 2
            assert limited[0]["time"] == 1060
            assert limited[1]["time"] == 1120
        finally:
            db.close()
