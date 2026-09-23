from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Crypto Laya Trader")
    binance_rest_url: str = os.getenv("BINANCE_REST_URL", "https://data-api.binance.vision")
    binance_ws_url: str = os.getenv("BINANCE_WS_URL", "wss://data-stream.binance.vision:443/ws")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
    default_interval: str = os.getenv("DEFAULT_INTERVAL", "1m")
    initial_cash: float = float(os.getenv("INITIAL_CASH", "10000"))
    decision_every_candles: int = int(os.getenv("DECISION_EVERY_CANDLES", "1"))
    laya_enabled: bool = os.getenv("LAYA_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    laya_model: str = os.getenv("LAYA_MODEL", "typed-decisions")
    db_path: str = os.getenv("DB_PATH", "crypto_laya.sqlite3")

settings = Settings()
