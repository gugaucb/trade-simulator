from abc import ABC, abstractmethod
from typing import Any

class Strategy(ABC):
    id: str = "base"
    name: str = "Base Strategy"
    description: str = ""
    requires_laya: bool = False

    @abstractmethod
    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        """Returns 'BUY', 'SELL', or 'HOLD'"""
        raise NotImplementedError

class BuyAndHoldStrategy(Strategy):
    id = "buy_and_hold"
    name = "Buy & Hold (Benchmark)"
    description = "Abre posição comprada no primeiro candle e segura até o final do período."
    requires_laya = False

    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        if position_qty <= 1e-12:
            return "BUY"
        return "HOLD"

class RsiMacdStrategy(Strategy):
    id = "rsi_macd"
    name = "RSI + MACD Reversal"
    description = "Entrada em sobrevenda (RSI baixo + MACD histograma virando positivo); saída em sobrecompra."
    requires_laya = False

    def __init__(self, rsi_oversold: float = 35.0, rsi_overbought: float = 65.0):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        rsi = ctx.get("rsi")
        macd_hist = ctx.get("macd_hist")
        if rsi is None:
            return "HOLD"

        if position_qty <= 1e-12:
            if rsi <= self.rsi_oversold and (macd_hist is None or macd_hist >= 0):
                return "BUY"
        else:
            if rsi >= self.rsi_overbought or (macd_hist is not None and macd_hist < -5.0):
                return "SELL"
        return "HOLD"

class EmaCrossStrategy(Strategy):
    id = "ema_cross"
    name = "EMA 20/50 Crossover"
    description = "Seguidor de tendência: compra no cruzamento de alta (EMA 20 > EMA 50) e encerra no cruzamento de baixa."
    requires_laya = False

    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        ema20 = ctx.get("ema20")
        ema50 = ctx.get("ema50")
        if ema20 is None or ema50 is None:
            return "HOLD"

        if position_qty <= 1e-12:
            if ema20 > ema50:
                return "BUY"
        else:
            if ema20 < ema50:
                return "SELL"
        return "HOLD"

class LayaPureStrategy(Strategy):
    id = "laya_pure"
    name = "Laya AI Pure Decisions"
    description = "Toma decisões estritamente baseadas na inferência tipada do Laya com filtro de confiança mínima."
    requires_laya = True

    def __init__(self, confidence_threshold: float = 0.55):
        self.confidence_threshold = confidence_threshold

    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        if not laya_decision:
            return "HOLD"
        action = str(laya_decision.get("action", "hold")).lower()
        confidence = float(laya_decision.get("confidence", 0.0))

        if action == "buy" and confidence >= self.confidence_threshold and position_qty <= 1e-12:
            return "BUY"
        elif action == "sell" and confidence >= self.confidence_threshold and position_qty > 0:
            return "SELL"
        return "HOLD"

class LayaConfluenceStrategy(Strategy):
    id = "laya_confluence"
    name = "Laya + Confluência Técnica"
    description = "Combina o julgamento do Laya com alinhamento da tendência técnica e médias móveis (elimina falsos sinais)."
    requires_laya = True

    def __init__(self, confidence_threshold: float = 0.55):
        self.confidence_threshold = confidence_threshold

    def on_candle(self, candle: dict[str, Any], ctx: dict[str, Any], laya_decision: dict[str, Any] | None, position_qty: float) -> str:
        if not laya_decision:
            return "HOLD"
        action = str(laya_decision.get("action", "hold")).lower()
        confidence = float(laya_decision.get("confidence", 0.0))
        trend = ctx.get("trend", "neutral")
        ema20 = ctx.get("ema20")
        ema50 = ctx.get("ema50")

        tech_bullish = trend == "bullish" or (ema20 is not None and ema50 is not None and ema20 > ema50)

        if action == "buy" and confidence >= self.confidence_threshold and tech_bullish and position_qty <= 1e-12:
            return "BUY"

        tech_bearish = trend == "bearish" or (ema20 is not None and ema50 is not None and ema20 < ema50)
        if position_qty > 0:
            if (action == "sell" and confidence >= self.confidence_threshold) or tech_bearish:
                return "SELL"

        return "HOLD"

REGISTRY: dict[str, type[Strategy]] = {
    "buy_and_hold": BuyAndHoldStrategy,
    "rsi_macd": RsiMacdStrategy,
    "ema_cross": EmaCrossStrategy,
    "laya_pure": LayaPureStrategy,
    "laya_confluence": LayaConfluenceStrategy,
}

def get_strategy(strategy_id: str, **kwargs) -> Strategy:
    cls = REGISTRY.get(strategy_id)
    if not cls:
        raise ValueError(f"Unknown strategy: {strategy_id}")
    return cls(**kwargs)

def list_available_strategies() -> list[dict[str, Any]]:
    result = []
    for sid, cls in REGISTRY.items():
        inst = cls()
        result.append({
            "id": inst.id,
            "name": inst.name,
            "description": inst.description,
            "requires_laya": inst.requires_laya,
        })
    return result
