import tempfile
import os
import pytest
from app.db import Database
from app.laya_engine import LayaDecisionEngine, compute_state_hash

def test_state_hash_deterministic():
    state1 = {
        "asset": "BTCUSDT",
        "market_state": {"price": 50000.0, "rsi_14": 65.4, "trend": "bullish"}
    }
    state2 = {
        "market_state": {"trend": "bullish", "rsi_14": 65.4, "price": 50000.0},
        "asset": "BTCUSDT"
    }
    # Hashes should be identical regardless of key order
    assert compute_state_hash(state1) == compute_state_hash(state2)
    assert len(compute_state_hash(state1)) == 64 # SHA256 hex

@pytest.mark.anyio
async def test_laya_decide_cached():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite3")
        db = Database(db_path)
        try:
            # When Laya is disabled, decide() returns a fallback decision
            engine = LayaDecisionEngine(enabled=False)
            
            sample_state = {
                "asset": "BTCUSDT",
                "candle_time": 1700000000,
                "market_state": {"price": 95000.0, "rsi_14": 72.0, "trend": "bullish"}
            }
            
            # First call: computes and saves to cache
            dec1 = await engine.decide_cached(sample_state, db)
            assert dec1["action"] == "hold"
            assert dec1["cached"] is False
            
            # Second call with same state: hits cache!
            dec2 = await engine.decide_cached(sample_state, db)
            assert dec2["action"] == "hold"
            assert dec2["cached"] is True
            
            # Verify it exists in db
            shash = compute_state_hash(sample_state)
            cached_db = db.get_laya_cache(shash)
            assert cached_db is not None
            assert cached_db["action"] == "hold"
        finally:
            db.close()
