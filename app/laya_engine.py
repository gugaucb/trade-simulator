import asyncio
import hashlib
import json
import time

def compute_state_hash(state: dict) -> str:
    serialized = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

class LayaDecisionEngine:
    def __init__(self, enabled=True, model_name="typed-decisions"):
        self.enabled = enabled
        self.model_name = model_name
        self.agent = None
        self.load_error = None

    def load(self):
        if not self.enabled:
            return
        try:
            import laya
            self.agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions")
        except Exception as exc:
            self.load_error = str(exc)

    def _predict_sync(self, state):
        questions = {
            "action": {
                "type": "choice",
                "instructions": (
                    "Choose the single next paper-trading action for this crypto asset. "
                    "Use only the supplied quantitative state. Prefer HOLD when evidence is mixed or weak."
                ),
                "criteria": {
                    "buy": "Open or increase a long paper position when bullish evidence is sufficiently coherent.",
                    "sell": "Close or reduce a long paper position when bearish evidence is sufficiently coherent.",
                    "hold": "Do not change the position because evidence is mixed, weak, or risk is elevated."
                }
            },
            "setup_quality": {
                "type": "score",
                "instructions": "Score the quality of the current setup from weak to strong.",
                "criteria": ["very weak", "weak", "mixed", "good", "very good"]
            }
        }
        return self.agent.predict(state, questions)

    async def decide(self, state):
        started = time.perf_counter()
        if not self.enabled:
            return {"action":"hold","confidence":0.0,"latency_ms":0.0,"model":"disabled","reason":"Laya disabled"}
        if self.agent is None:
            return {"action":"hold","confidence":0.0,"latency_ms":0.0,"model":"unavailable",
                    "reason":self.load_error or "Laya model not loaded"}
        try:
            result = await asyncio.to_thread(self._predict_sync, state)
            answers = result.get("answers", {})
            action = answers.get("action", {})
            quality = answers.get("setup_quality", {})
            return {
                "action": str(action.get("choice", "hold")).lower(),
                "confidence": float(action.get("confidence", 0.0)),
                "setup_quality": quality.get("score"),
                "latency_ms": (time.perf_counter()-started)*1000,
                "model": self.model_name,
                "reason": "Laya typed decision",
            }
        except Exception as exc:
            return {"action":"hold","confidence":0.0,"setup_quality":None,
                    "latency_ms":(time.perf_counter()-started)*1000,
                    "model":self.model_name,"reason":f"Laya error: {exc}"}

    async def decide_cached(self, state: dict, db=None, force_refresh: bool = False) -> dict:
        shash = compute_state_hash(state)
        symbol = state.get("asset", "")
        candle_time = state.get("candle_time")

        if not force_refresh and db is not None:
            cached = db.get_laya_cache(shash)
            if cached:
                return {
                    "action": cached["action"],
                    "confidence": cached["confidence"],
                    "setup_quality": cached.get("setup_quality"),
                    "latency_ms": 0.0,
                    "model": cached.get("model", self.model_name),
                    "reason": cached.get("reason", "Laya cached decision"),
                    "cached": True,
                    "state_hash": shash
                }

        decision = await self.decide(state)
        decision["cached"] = False
        decision["state_hash"] = shash

        if db is not None:
            db.save_laya_cache(shash, symbol, candle_time, decision)

        return decision
