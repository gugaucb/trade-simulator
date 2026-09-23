import pytest
from unittest.mock import MagicMock
from app.laya_engine import LayaDecisionEngine

def test_predict_sync_questions_structure():
    engine = LayaDecisionEngine(enabled=True)
    engine.agent = MagicMock()
    engine.agent.predict.return_value = {
        "answers": {
            "action": {"choice": "buy", "confidence": 0.88},
            "setup_quality": {"score": "good"}
        }
    }

    dummy_state = {
        "asset": "BTCUSDT",
        "current_price": 60000.0,
        "timeframe": "1m",
        "active_indicators": ["rsi", "macd"],
        "market_state": {"price": 60000.0, "rsi_14": 65.0},
        "paper_position": {"cash": 10000.0, "quantity": 0.0, "position_usd": 0.0, "equity": 10000.0},
        "decision_policy": "Spot trading only. Choose buy, sell, or hold."
    }

    res = engine._predict_sync(dummy_state)
    assert engine.agent.predict.called

    # Extract questions passed to agent.predict
    call_args, call_kwargs = engine.agent.predict.call_args
    passed_state = call_args[0]
    questions = call_args[1]

    assert passed_state == dummy_state
    assert "action" in questions
    assert "setup_quality" in questions

    action_q = questions["action"]
    assert action_q["type"] == "choice"
    instructions = action_q["instructions"]

    # Verify that buy, sell, and hold are explicitly declared in instructions
    assert "'buy'" in instructions or "buy" in instructions
    assert "'sell'" in instructions or "sell" in instructions
    assert "'hold'" in instructions or "hold" in instructions

    # Verify criteria keys
    criteria = action_q["criteria"]
    assert set(criteria.keys()) == {"buy", "sell", "hold"}
    assert "cash" in criteria["buy"].lower()
    assert "cash" in criteria["sell"].lower() or "liquidate" in criteria["sell"].lower() or "close" in criteria["sell"].lower()
